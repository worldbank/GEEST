# -*- coding: utf-8 -*-
"""Multi-resolution vector grid pyramid utilities.

Builds a cascading, scale-dependent set of coarser study_area_grid tables
(study_area_grid_200, study_area_grid_400, ...) so visualization can swap
resolution on zoom instead of rasterizing/masking a GeoTIFF. Each level is
a WIDE table mirroring study_area_grid itself - one row per coarse cell,
with the same score columns added lazily as needed - never one table per
(level, column); with dozens of indicators/factors/dimensions that would
mean hundreds of tiny tables instead of a handful of wide ones.

Each level's cell is the max of the 4 cells (2x2 block) in the level
immediately below it (never diluting a high score by averaging it with
lower neighbours as you zoom out); cell size doubles per level. Only
local/national (square-grid) analyses are supported - regional (H3 hex)
analyses keep using add_grid_layer_to_map().
"""

import datetime
import os
from typing import List, Optional, Tuple

from osgeo import ogr
from qgis.core import Qgis

from geest.core.grid_column_utils import (
    _execute_sql_with_retry,
    _open_gpkg_for_write,
    _quote_sql_identifier,
    _quote_sql_literal,
    _sanitize_column_name,
)
from geest.utilities import log_message

PYRAMID_DOUBLINGS = 4  # base -> 2x -> 4x -> 8x -> 16x - every level is exposed on the map
PYRAMID_TABLE_PREFIX = "study_area_grid_"  # study_area_grid_200, study_area_grid_400, ...
PYRAMID_META_TABLE = "pyr_meta"

# Columns derived via raster algebra elsewhere (opportunity masks,
# population-weighted aggregation) stay on the single-resolution
# add_grid_layer_to_map() path - reimplementing that math in SQL is a
# separate, larger effort than this visualization pyramid.
OUT_OF_SCOPE_PYRAMID_COLUMNS = frozenset(
    {
        "geoe3_masked",
        "geoe3_by_population",
        "geoe3_by_population_masked",
        "opportunities_mask",
    }
)

# Scale-denominator formula: at 96 DPI, 1 map metre is ~3779.5 screen pixels
# at scale 1:1. Solve for the scale denominator at which one cell renders at
# TARGET_PIXELS_PER_CELL on screen: S = cell_size_m * PIXELS_PER_METRE_AT_1_1 / TARGET_PIXELS_PER_CELL.
PIXELS_PER_METRE_AT_1_1 = 3779.5
TARGET_PIXELS_PER_CELL = 8


def compute_level_cell_sizes(base_cell_size_m: float, doublings: int = PYRAMID_DOUBLINGS) -> List[float]:
    """Return the cell size in metres for every pyramid level, finest first.

    Args:
        base_cell_size_m: The analysis grid's native cell size.
        doublings: Number of doubling steps beyond the base level.

    Returns:
        [base, 2x, 4x, ..., 2^doublings * x].
    """
    return [base_cell_size_m * (2**i) for i in range(doublings + 1)]


def scale_denominator_for_cell_size(cell_size_m: float) -> float:
    """Return the scale denominator at which a cell renders at the target on-screen size."""
    return (cell_size_m * PIXELS_PER_METRE_AT_1_1) / TARGET_PIXELS_PER_CELL


def _level_table_name(level_cell_size_m: float) -> str:
    """Name of the wide pyramid table for one level, e.g. study_area_grid_400."""
    return f"{PYRAMID_TABLE_PREFIX}{int(level_cell_size_m)}"


def ensure_row_col_index_columns(gpkg_path: str, cell_size_m: float) -> bool:
    """Backfill integer row_index/col_index columns on study_area_grid.

    Additive and idempotent - never touches grid creation itself. Every
    cell's lower-left corner is already an exact multiple of cell_size_m
    (the whole analysis shares one CRS and one grid aligned to origin 0,0),
    so these indices are deterministic and only ever need computing once
    per cell. row_index/col_index are NOT made unique: two different areas'
    cell-aligned extents can legitimately share a (row, col) near a shared
    boundary, and aggregation must be free to combine them.

    Args:
        gpkg_path: Path to the GeoPackage containing study_area_grid.
        cell_size_m: The analysis grid's native cell size.

    Returns:
        True on success, False on failure.
    """
    if not os.path.exists(gpkg_path):
        log_message(f"GeoPackage not found: {gpkg_path}", level=Qgis.Warning)
        return False

    try:
        ds = _open_gpkg_for_write(gpkg_path)
        if not ds:
            log_message(f"Could not open GeoPackage: {gpkg_path}", level=Qgis.Critical)
            return False

        layer = ds.GetLayerByName("study_area_grid")
        if not layer:
            log_message("study_area_grid layer not found", level=Qgis.Critical)
            ds = None
            return False

        layer_defn = layer.GetLayerDefn()
        existing_fields = {layer_defn.GetFieldDefn(i).GetName().lower() for i in range(layer_defn.GetFieldCount())}

        if "row_index" not in existing_fields:
            layer.CreateField(ogr.FieldDefn("row_index", ogr.OFTInteger))
        if "col_index" not in existing_fields:
            layer.CreateField(ogr.FieldDefn("col_index", ogr.OFTInteger))

        # Two single-column indexes (not one composite) so SQLite can plan
        # "row_index IS NULL OR col_index IS NULL" as an indexed multi-index
        # OR lookup instead of a full table scan - a composite index on
        # (row_index, col_index) does not serve that query at all.
        _execute_sql_with_retry(
            ds,
            "CREATE INDEX IF NOT EXISTS idx_study_area_grid_row ON study_area_grid(row_index)",  # nosec B608
        )
        _execute_sql_with_retry(
            ds,
            "CREATE INDEX IF NOT EXISTS idx_study_area_grid_col ON study_area_grid(col_index)",  # nosec B608
        )
        # Composite index: refresh_pyramid_column's correlated subquery
        # filters study_area_grid on a row_index range AND a col_index
        # range together - see the matching comment in
        # _ensure_level_table_scaffold for why the two single-column
        # indexes above do not serve that query well on a large grid.
        _execute_sql_with_retry(
            ds,
            "CREATE INDEX IF NOT EXISTS idx_study_area_grid_rowcol ON study_area_grid(row_index, col_index)",  # nosec B608
        )

        # Cheap, index-backed short-circuit: skip the UPDATE entirely once
        # every cell already has an index, so a backfill that already ran
        # doesn't pay any per-call cost on repeat "Add to map" clicks.
        check = _execute_sql_with_retry(
            ds,
            "SELECT COUNT(*) AS n FROM study_area_grid "  # nosec B608
            "WHERE row_index IS NULL OR col_index IS NULL",
        )
        unresolved = 0
        if check is not None:
            feature = check.GetNextFeature()
            if feature is not None:
                unresolved = feature.GetField("n") or 0
            ds.ReleaseResultSet(check)

        if unresolved:
            _execute_sql_with_retry(
                ds,
                "UPDATE study_area_grid "  # nosec B608
                "SET row_index = CAST(ROUND(ST_MinY(geom) / "
                f"{cell_size_m}) AS INTEGER), "
                "col_index = CAST(ROUND(ST_MinX(geom) / "
                f"{cell_size_m}) AS INTEGER) "
                "WHERE row_index IS NULL OR col_index IS NULL",
                dialect="SQLite",
            )
            still_unresolved = _execute_sql_with_retry(
                ds,
                "SELECT COUNT(*) AS n FROM study_area_grid "  # nosec B608
                "WHERE row_index IS NULL OR col_index IS NULL",
            )
            if still_unresolved is not None:
                feature = still_unresolved.GetNextFeature()
                unresolved = (feature.GetField("n") or 0) if feature is not None else 0
                ds.ReleaseResultSet(still_unresolved)

        ds = None

        if unresolved:
            log_message(
                f"{unresolved} study_area_grid cell(s) could not get a row/col index "
                "(empty/invalid geometry?) - pyramid aggregation will skip them",
                level=Qgis.Warning,
            )
        return True

    except Exception as error:
        log_message(f"Error backfilling row_index/col_index: {error}", level=Qgis.Critical)
        return False


def _ensure_level_table_scaffold(ds, level_cs: float, source_table: str, srs) -> str:
    """Ensure one level's wide table exists with its row_index/col_index/geometry scaffold.

    Built ONCE per level, independent of any particular score column: the
    row set is every coarse cell derivable from source_table's existing
    cells, regardless of which columns are populated. Columns are added
    lazily later, per-column, exactly like study_area_grid itself.

    Args:
        ds: Open OGR DataSource for the GeoPackage.
        level_cs: This level's cell size in metres.
        source_table: The immediately finer table (study_area_grid or a
            previous pyramid level) to derive this level's row/col pairs from.
        srs: Spatial reference to create the table with.

    Returns:
        The level table's name.
    """
    table_name = _level_table_name(level_cs)
    layer = ds.GetLayerByName(table_name)
    if layer is not None and layer.GetFeatureCount() > 0:
        return table_name

    if layer is None:
        layer = ds.CreateLayer(table_name, srs, geom_type=ogr.wkbPolygon)
        layer.CreateField(ogr.FieldDefn("row_index", ogr.OFTInteger))
        layer.CreateField(ogr.FieldDefn("col_index", ogr.OFTInteger))

    # Floor (not truncating) division going from a finer table's indices to
    # this coarser level: SQLite's "/" on integers truncates toward zero,
    # which would misbucket a 2x2 block whenever an index is negative (e.g.
    # a future non-UTM/local CRS with coordinates near 0,0).
    distinct_sql = (
        "SELECT DISTINCT "  # nosec B608
        "CAST(FLOOR(CAST(row_index AS REAL) / 2) AS INTEGER) AS r, "
        "CAST(FLOOR(CAST(col_index AS REAL) / 2) AS INTEGER) AS c "
        f"FROM {source_table}"
    )
    result = _execute_sql_with_retry(ds, distinct_sql)
    pairs: List[Tuple[int, int]] = []
    if result is not None:
        feature = result.GetNextFeature()
        while feature is not None:
            pairs.append((feature.GetField("r"), feature.GetField("c")))
            feature = result.GetNextFeature()
        ds.ReleaseResultSet(result)

    layer_defn = layer.GetLayerDefn()
    layer.StartTransaction()
    try:
        for row_index, col_index in pairs:
            xmin, ymin = col_index * level_cs, row_index * level_cs
            xmax, ymax = xmin + level_cs, ymin + level_cs
            wkt = f"POLYGON(({xmin} {ymin},{xmax} {ymin},{xmax} {ymax},{xmin} {ymax},{xmin} {ymin}))"
            feature = ogr.Feature(layer_defn)
            feature.SetField("row_index", row_index)
            feature.SetField("col_index", col_index)
            feature.SetGeometry(ogr.CreateGeometryFromWkt(wkt))
            layer.CreateFeature(feature)
            feature = None
        layer.CommitTransaction()
    except Exception:
        layer.RollbackTransaction()
        raise

    _execute_sql_with_retry(
        ds,
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_row ON {table_name}(row_index)",  # nosec B608
    )
    _execute_sql_with_retry(
        ds,
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_col ON {table_name}(col_index)",  # nosec B608
    )
    # Composite index: refresh_pyramid_column's correlated subquery filters
    # on a row_index range AND a col_index range together. The single-
    # column indexes above only serve the OR-based NULL-check query in
    # ensure_row_col_index_columns - with just those, SQLite can narrow by
    # one dimension and then has to linearly scan every row in that slice
    # for the other, which is the real cost driver on a large grid.
    _execute_sql_with_retry(
        ds,
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_rowcol ON {table_name}(row_index, col_index)",  # nosec B608
    )
    return table_name


def _ensure_level_column(ds, table_name: str, quoted_column: str, sanitized_column: str) -> None:
    """Add a REAL column to a level table if it doesn't already have one."""
    layer = ds.GetLayerByName(table_name)
    layer_defn = layer.GetLayerDefn()
    existing = {layer_defn.GetFieldDefn(i).GetName().lower() for i in range(layer_defn.GetFieldCount())}
    if sanitized_column.lower() not in existing:
        layer.CreateField(ogr.FieldDefn(sanitized_column, ogr.OFTReal))
    _ = quoted_column  # kept for signature symmetry with callers that already have it quoted


def _sync_level_table_columns(ds, table_name: str, source_table: str) -> None:
    """Add every score column that exists on source_table but is missing
    from table_name, so each pyramid level stays a complete, scaled
    mirror of the layer below it - not just whichever columns have
    happened to be explicitly refresh_pyramid_column()'d so far. A column
    a workflow hasn't run yet is simply NULL on both tables, exactly like
    the base grid itself.

    Called on every refresh, not just when a level table is first
    scaffolded, so a column added to study_area_grid after a level table
    already exists still gets picked up.

    Args:
        ds: Open OGR DataSource for the GeoPackage.
        table_name: The level table to bring up to date.
        source_table: The immediately finer table (study_area_grid or a
            previous pyramid level) whose columns to mirror.
    """
    source_layer = ds.GetLayerByName(source_table)
    level_layer = ds.GetLayerByName(table_name)
    level_defn = level_layer.GetLayerDefn()
    existing = {level_defn.GetFieldDefn(i).GetName().lower() for i in range(level_defn.GetFieldCount())}
    source_defn = source_layer.GetLayerDefn()
    for i in range(source_defn.GetFieldCount()):
        field_defn = source_defn.GetFieldDefn(i)
        if field_defn.GetType() != ogr.OFTReal:
            continue
        name = field_defn.GetName()
        if name.lower() in OUT_OF_SCOPE_PYRAMID_COLUMNS or name.lower() in existing:
            continue
        level_layer.CreateField(ogr.FieldDefn(name, ogr.OFTReal))
        existing.add(name.lower())


def is_pyramid_fresh(gpkg_path: str, column_name: str) -> bool:
    """Return True if column_name's pyramid is already built and up to date."""
    if not os.path.exists(gpkg_path):
        return False
    sanitized = _sanitize_column_name(column_name)
    try:
        ds = _open_gpkg_for_write(gpkg_path)
        if not ds:
            return False
        _ensure_meta_table(ds)
        result = _execute_sql_with_retry(
            ds,
            f"SELECT 1 AS fresh FROM {PYRAMID_META_TABLE} "  # nosec B608
            f"WHERE column_name = {_quote_sql_literal(sanitized)}",
        )
        fresh = False
        if result is not None:
            feature = result.GetNextFeature()
            fresh = feature is not None
            ds.ReleaseResultSet(result)
        ds = None
        return fresh
    except Exception as error:
        log_message(f"Error checking pyramid freshness for {column_name}: {error}", level=Qgis.Warning)
        return False


def has_pyramid_structure(gpkg_path: str, column_name: str, base_cell_size_m: float) -> bool:
    """Return True if column_name has ever been built into the pyramid.

    Unlike is_pyramid_fresh(), this never goes False again once True:
    invalidate_pyramid() only deletes the freshness bookkeeping row, it
    never drops the column refresh_pyramid_column() already added to the
    level tables. Use this (not is_pyramid_fresh()) to decide whether a
    project needs the one-time pyramid-migration offer - every successful
    analysis run invalidates freshness, so that would otherwise re-fire the
    migration prompt on every project open. A column that is merely stale
    is rebuilt transparently, on demand, the next time it is viewed.
    """
    if not os.path.exists(gpkg_path):
        return False
    sanitized = _sanitize_column_name(column_name)
    level_sizes = compute_level_cell_sizes(base_cell_size_m)
    table_name = _level_table_name(level_sizes[1])
    try:
        ds = ogr.Open(gpkg_path, 0)
        if not ds:
            return False
        layer = ds.GetLayerByName(table_name)
        if layer is None:
            ds = None
            return False
        layer_defn = layer.GetLayerDefn()
        field_names = {layer_defn.GetFieldDefn(i).GetName().lower() for i in range(layer_defn.GetFieldCount())}
        ds = None
        return sanitized.lower() in field_names
    except Exception as error:
        log_message(f"Error checking pyramid structure for {column_name}: {error}", level=Qgis.Warning)
        return False


def invalidate_pyramid(gpkg_path: str, column_name: str) -> None:
    """Mark column_name's pyramid as stale, forcing a rebuild on next view.

    Safe to call even if the pyramid was never built; failures are logged
    and swallowed since this is best-effort bookkeeping, never load-bearing
    for the caller's own success/failure.
    """
    if not os.path.exists(gpkg_path):
        return
    sanitized = _sanitize_column_name(column_name)
    try:
        ds = _open_gpkg_for_write(gpkg_path)
        if not ds:
            return
        _ensure_meta_table(ds)
        _execute_sql_with_retry(
            ds,
            f"DELETE FROM {PYRAMID_META_TABLE} "  # nosec B608
            f"WHERE column_name = {_quote_sql_literal(sanitized)}",
        )
        ds = None
    except Exception as error:
        log_message(f"Could not invalidate pyramid for {column_name}: {error}", level=Qgis.Warning)


def _ensure_meta_table(ds) -> None:
    """Create the pyramid freshness-tracking table if missing."""
    _execute_sql_with_retry(
        ds,
        f"CREATE TABLE IF NOT EXISTS {PYRAMID_META_TABLE} "  # nosec B608
        "(column_name TEXT PRIMARY KEY, built_at TEXT NOT NULL)",
    )


def refresh_pyramid_column(gpkg_path: str, column_name: str, base_cell_size_m: float) -> bool:
    """(Re)populate one column across every pyramid level table, cascading from the base grid.

    Idempotent and safe to call repeatedly: every level's column is fully
    recomputed (never incrementally patched), so a cell whose children
    became entirely NULL since the last build correctly reverts to NULL
    (a correlated-subquery MAX over zero matching rows is NULL) instead of
    lingering with a stale value.

    Args:
        gpkg_path: Path to the GeoPackage containing study_area_grid.
        column_name: The study_area_grid score column to pyramid.
        base_cell_size_m: The analysis grid's native cell size.

    Returns:
        True on success, False on failure.
    """
    if not os.path.exists(gpkg_path):
        log_message(f"GeoPackage not found: {gpkg_path}", level=Qgis.Warning)
        return False

    if not ensure_row_col_index_columns(gpkg_path, base_cell_size_m):
        return False

    level_sizes = compute_level_cell_sizes(base_cell_size_m)

    try:
        # Validate+sanitize inside the try block: an id with characters
        # _quote_sql_identifier rejects (indicator/factor ids come straight
        # from a spreadsheet column with no slugify) must be reported as a
        # clean failure, not an uncaught ValueError reaching the GUI layer.
        sanitized = _sanitize_column_name(column_name)
        quoted_column = _quote_sql_identifier(sanitized)

        ds = _open_gpkg_for_write(gpkg_path)
        if not ds:
            log_message(f"Could not open GeoPackage: {gpkg_path}", level=Qgis.Critical)
            return False

        grid_layer = ds.GetLayerByName("study_area_grid")
        srs = grid_layer.GetSpatialRef()

        # A column that doesn't exist on study_area_grid must fail loudly,
        # not silently build a plausible pyramid from garbage: SQLite's
        # double-quoted-identifier fallback reinterprets an unknown
        # "colname" as the string literal 'colname' rather than raising, so
        # MAX("colname") would otherwise evaluate to that literal string
        # for every row instead of erroring.
        grid_defn = grid_layer.GetLayerDefn()
        grid_fields = {grid_defn.GetFieldDefn(i).GetName().lower() for i in range(grid_defn.GetFieldCount())}
        if sanitized.lower() not in grid_fields:
            log_message(
                f"Cannot build pyramid: column '{sanitized}' does not exist on study_area_grid",
                level=Qgis.Warning,
            )
            ds = None
            return False

        source_table = "study_area_grid"
        for level_cs in level_sizes[1:]:
            table_name = _ensure_level_table_scaffold(ds, level_cs, source_table, srs)
            _sync_level_table_columns(ds, table_name, source_table)
            _ensure_level_column(ds, table_name, quoted_column, sanitized)

            # Child bounds computed by multiplying the parent index (never
            # dividing the child index), so this is exact integer arithmetic
            # with no floor/truncation ambiguity. The composite
            # (row_index, col_index) index on source_table is what makes
            # this a cheap range seek instead of a near-full scan per row -
            # but SQLite's planner has no ANALYZE statistics on this
            # connection and reliably picks the single-column col_index
            # index instead (benchmarked ~22x slower), so it has to be
            # forced with INDEXED BY rather than left to the planner.
            update_sql = (
                f"UPDATE {table_name} "  # nosec B608
                f'SET "{sanitized}" = ('
                f'SELECT MAX(b."{sanitized}") FROM {source_table} AS b '
                f"INDEXED BY idx_{source_table}_rowcol "
                f"WHERE b.row_index >= {table_name}.row_index * 2 "
                f"AND b.row_index <= {table_name}.row_index * 2 + 1 "
                f"AND b.col_index >= {table_name}.col_index * 2 "
                f"AND b.col_index <= {table_name}.col_index * 2 + 1 "
                f'AND b."{sanitized}" IS NOT NULL'
                f")"
            )
            _execute_sql_with_retry(ds, update_sql)

            source_table = table_name

        _ensure_meta_table(ds)
        _execute_sql_with_retry(
            ds,
            f"DELETE FROM {PYRAMID_META_TABLE} "  # nosec B608
            f"WHERE column_name = {_quote_sql_literal(sanitized)}",
        )
        _execute_sql_with_retry(
            ds,
            f"INSERT INTO {PYRAMID_META_TABLE} (column_name, built_at) "  # nosec B608
            f"VALUES ({_quote_sql_literal(sanitized)}, {_quote_sql_literal(datetime.datetime.now().isoformat())})",
        )
        ds = None
        return True

    except Exception as error:
        log_message(f"Error refreshing pyramid for column {column_name}: {error}", level=Qgis.Critical)
        return False


def get_exposed_levels(gpkg_path: str, column_name: str, base_cell_size_m: float) -> List[Tuple[float, Optional[str]]]:
    """Return every built pyramid level, finest first, for map visualization.

    Every level built by refresh_pyramid_column() is exposed - there is no
    point building optimized scale-dependent levels and then hiding most
    of them from the actual scale-dependent visualization.

    Args:
        gpkg_path: Path to the GeoPackage containing study_area_grid.
        column_name: The study_area_grid score column (kept for signature
            symmetry/future use - the level tables are column-agnostic).
        base_cell_size_m: The analysis grid's native cell size.

    Returns:
        List of (cell_size_m, table_name) tuples. table_name is None for the
        base level, meaning "use study_area_grid itself".
    """
    _ = gpkg_path, column_name
    level_sizes = compute_level_cell_sizes(base_cell_size_m)
    levels: List[Tuple[float, Optional[str]]] = [(level_sizes[0], None)]
    for cell_size in level_sizes[1:]:
        levels.append((cell_size, _level_table_name(cell_size)))
    return levels
