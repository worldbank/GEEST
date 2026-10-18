# -*- coding: utf-8 -*-
"""Multi-resolution H3 grid pyramid utilities.

Sibling of geest.core.grid_pyramid_utils, built for the same purpose
(scale-dependent map visualization without rasterizing/masking a GeoTIFF)
but for local/national analyses whose project opted into an H3 hexagonal
grid instead of a square one (see geest.core.grid_type_utils). Regional
analyses always use H3 too, but never touch this module - they keep using
add_grid_layer_to_map() because a single fixed resolution is sufficient at
that scale (see geest.core.utilities.add_pyramid_layer_to_map).

H3's hierarchy has no exact "2x2 quad aggregation" like a square grid: each
cell's parent (one coarser resolution step) has on average ~7 children, not
4. So instead of doubling cell size per level, each pyramid level here is
one H3 resolution step coarser than the one below it, with a cell's value
the MIN of every finer cell whose h3.cell_to_parent() resolves to it - a
coarse cell shows its worst (most conservative) child score, not its best.

Exactly like grid_pyramid_utils, each level is a WIDE table
(study_area_grid_h3_res<N>) mirroring study_area_grid - one row per coarse
hex, with score columns added lazily - never one table per (level, column).
Freshness/structure bookkeeping is shared with the square-grid pyramid: both
write into grid_pyramid_utils.PYRAMID_META_TABLE, keyed only by column_name,
so callers use the exact same is_pyramid_fresh()/invalidate_pyramid() for
either grid shape without needing to know which one a project uses.
"""

import datetime
import os
from typing import List, Optional, Tuple

from osgeo import ogr
from qgis.core import Qgis

from geest.core.arrow_batch_writer import log_arrow_batch_fallback, write_features_arrow_batch
from geest.core.grid_column_utils import (
    _execute_sql_with_retry,
    _open_gpkg_for_write,
    _quote_sql_identifier,
    _quote_sql_literal,
    _sanitize_column_name,
)
from geest.core.grid_pyramid_utils import PYRAMID_META_TABLE, _ensure_meta_table, _uniform_column_value
from geest.core.h3_utils import h3_cell_area_km2, transform_wgs84_to_target
from geest.core.settings import setting
from geest.utilities import log_message

H3_PYRAMID_RESOLUTION_STEPS = 3  # base -> -1 -> -2 -> -3 resolution steps, default; see h3_pyramid_steps() below
H3_PYRAMID_TABLE_PREFIX = "study_area_grid_h3_res"  # study_area_grid_h3_res5, ...
H3_LEVEL_BATCH_SIZE = 500


def h3_pyramid_steps(analysis_scale: str) -> int:
    """Return the configured number of H3 resolution steps the pyramid builds below base.

    National and local projects are tuned separately (GeoE3 Options > Grid
    Pyramid Visualization Options), since they typically pick very
    different base H3 resolutions and so want a different number of
    coarser zoom levels. Read fresh from QGIS settings on every call
    rather than cached, so a user change takes effect on the next build
    without requiring a restart. Regional analyses never call into this
    module at all (no pyramid is built for them), so any scale other than
    "local" is treated as "national".

    Args:
        analysis_scale: "local" or "national" (anything else falls back
            to the national setting).

    Returns:
        The configured step count, or H3_PYRAMID_RESOLUTION_STEPS if unset.
    """
    key = "h3_pyramid_steps_local" if analysis_scale == "local" else "h3_pyramid_steps_national"
    return int(setting(key=key, default=H3_PYRAMID_RESOLUTION_STEPS))


def compute_h3_level_resolutions(base_h3_resolution: int, steps: int = H3_PYRAMID_RESOLUTION_STEPS) -> List[int]:
    """Return the H3 resolution for every pyramid level, finest (base) first.

    Resolution cannot go below 0, so once a step would go negative it stays
    clamped at 0 for every remaining, coarser step.

    Args:
        base_h3_resolution: The analysis grid's native H3 resolution.
        steps: Number of resolution steps beyond the base level.

    Returns:
        [base, base-1, base-2, ..., max(0, base-steps)].
    """
    return [max(0, base_h3_resolution - i) for i in range(steps + 1)]


def h3_effective_cell_size_m(h3_resolution: int) -> float:
    """Approximate an H3 cell's "effective" square-equivalent size in metres.

    Used only to pick a sensible scale-dependent rendering threshold (see
    geest.core.grid_pyramid_utils.scale_denominator_for_cell_size) - an H3
    hexagon has no single "cell size", so this is the side length of a
    square with the same average area, the same area-based equivalence
    get_h3_resolution_for_cell_size() already uses the other way round.

    Args:
        h3_resolution: H3 resolution level.

    Returns:
        Effective cell size in metres.
    """
    area_km2 = h3_cell_area_km2(h3_resolution)
    return (area_km2**0.5) * 1000.0


def _h3_level_table_name(h3_resolution: int) -> str:
    """Name of the wide pyramid table for one H3 level, e.g. study_area_grid_h3_res4."""
    return f"{H3_PYRAMID_TABLE_PREFIX}{h3_resolution}"


def _epsg_from_srs(srs) -> Optional[int]:
    """Return the integer EPSG code for an OGR spatial reference, or None if unknown."""
    if srs is None:
        return None
    code = srs.GetAuthorityCode(None)
    try:
        return int(code) if code else None
    except (TypeError, ValueError):
        return None


def has_h3_pyramid_structure(
    gpkg_path: str, column_name: str, base_h3_resolution: Optional[int], analysis_scale: str = "national"
) -> bool:
    """Return True if column_name has ever been built into the H3 pyramid.

    Mirrors grid_pyramid_utils.has_pyramid_structure(): unlike
    is_pyramid_fresh(), this never goes False again once True, so it is
    what decides whether a project needs the one-time pyramid-migration
    offer - a merely-stale column is rebuilt transparently on demand.

    Args:
        gpkg_path: Path to the GeoPackage containing study_area_grid.
        column_name: The study_area_grid score column.
        base_h3_resolution: The analysis grid's native H3 resolution, or
            None (e.g. a corrupt/incomplete model.json), in which case this
            always returns False.
        analysis_scale: "local" or "national" - picks which pyramid-depth
            setting to check against (see h3_pyramid_steps()).

    Returns:
        True if the first coarser level table already has this column.
    """
    if not os.path.exists(gpkg_path) or base_h3_resolution is None:
        return False
    sanitized = _sanitize_column_name(column_name)
    resolutions = compute_h3_level_resolutions(base_h3_resolution, steps=h3_pyramid_steps(analysis_scale))
    table_name = _h3_level_table_name(resolutions[1])
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
        log_message(f"Error checking H3 pyramid structure for {column_name}: {error}", level=Qgis.Warning)
        return False


def _load_clip_boundary_geom(ds):
    """Load the union of every study_area_clip_polygons feature, or None.

    Mirrors the geometry GridFromBboxH3Task clips the base grid against
    (see StudyAreaProcessingTask's dissolved AOI), so a coarser pyramid
    level's edge cells are clipped to the exact same boundary the base
    grid itself was clipped to - not an approximation of it.

    Args:
        ds: Open OGR DataSource for the GeoPackage.

    Returns:
        A single (possibly multi-part) OGR geometry, or None if the layer
        is missing/empty.
    """
    layer = ds.GetLayerByName("study_area_clip_polygons")
    if layer is None:
        return None
    union_geom = None
    layer.ResetReading()
    feature = layer.GetNextFeature()
    while feature is not None:
        geom = feature.GetGeometryRef()
        if geom is not None and not geom.IsEmpty():
            clone = geom.Clone()
            union_geom = clone if union_geom is None else union_geom.Union(clone)
        feature = layer.GetNextFeature()
    return union_geom


def _clip_to_boundary(polygon_geometry, boundary_geom):
    """Return polygon_geometry, clipped to boundary_geom if it crosses the edge.

    A cell fully inside the boundary is returned unchanged - Intersection()
    is only computed for genuine edge cells, since it is pure wasted work
    for interior ones. A cell with no overlap at all returns None (should
    not normally happen: every coarser cell is derived from finer cells
    that already overlap the boundary).

    Args:
        polygon_geometry: The cell geometry, already in the target CRS.
        boundary_geom: The study area boundary geometry, same CRS.

    Returns:
        A geometry to store, or None if the cell has no overlap at all.
    """
    if boundary_geom.Contains(polygon_geometry):
        return polygon_geometry
    if not boundary_geom.Intersects(polygon_geometry):
        return None
    clipped = boundary_geom.Intersection(polygon_geometry)
    if clipped is None or clipped.IsEmpty():
        return None
    return clipped


def _ensure_h3_level_table_scaffold(
    ds, h3_module, resolution: int, source_table: str, srs, target_epsg, boundary_geom=None
) -> Optional[str]:
    """Ensure one H3 level's wide table exists with its h3_index/geometry scaffold.

    Built once per level, independent of any particular score column - the
    row set is every coarser cell derivable from source_table's existing
    h3_index values, via h3.cell_to_parent().

    Args:
        ds: Open OGR DataSource for the GeoPackage.
        h3_module: The imported h3 library module (passed in so callers only
            import it once, after confirming it's installed).
        resolution: This level's H3 resolution.
        source_table: The immediately finer table (study_area_grid or a
            previous pyramid level) to derive this level's cells from.
        srs: Spatial reference to create the table with.
        target_epsg: EPSG code of srs, or None if unknown (assumed WGS84).
        boundary_geom: If given, edge cells are clipped to this geometry -
            matches the base grid's own clip_to_boundary behavior (see
            geest.core.grid_type_utils.get_h3_clip_to_boundary). None
            (the default) keeps every cell as a full, unclipped hexagon.

    Returns:
        The level table's name, or None on failure.
    """
    table_name = _h3_level_table_name(resolution)
    layer = ds.GetLayerByName(table_name)
    if layer is not None and layer.GetFeatureCount() > 0:
        return table_name

    if layer is None:
        layer = ds.CreateLayer(table_name, srs, geom_type=ogr.wkbPolygon)
        h3_index_field = ogr.FieldDefn("h3_index", ogr.OFTString)
        h3_index_field.SetWidth(16)
        layer.CreateField(h3_index_field)

    result = _execute_sql_with_retry(ds, f"SELECT DISTINCT h3_index FROM {source_table}")  # nosec B608
    child_indexes: List[str] = []
    if result is not None:
        feature = result.GetNextFeature()
        while feature is not None:
            value = feature.GetField("h3_index")
            if value:
                child_indexes.append(value)
            feature = result.GetNextFeature()
        ds.ReleaseResultSet(result)

    parent_cells = set()
    for child_index in child_indexes:
        try:
            parent_cells.add(h3_module.cell_to_parent(child_index, resolution))
        except Exception as error:
            log_message(f"Could not resolve H3 parent for {child_index}: {error}", level=Qgis.Warning)

    layer_defn = layer.GetLayerDefn()

    def _parent_cell_polygon(parent_cell):
        boundary = h3_module.cell_to_boundary(parent_cell)  # [(lat, lon), ...]
        ring = ogr.Geometry(ogr.wkbLinearRing)
        for lat, lon in boundary:
            if target_epsg is not None and target_epsg != 4326:
                x, y = transform_wgs84_to_target(lon, lat, target_epsg)
            else:
                x, y = lon, lat
            ring.AddPoint(x, y)
        ring.CloseRings()
        polygon_geometry = ogr.Geometry(ogr.wkbPolygon)
        polygon_geometry.AddGeometry(ring)
        if boundary_geom is not None:
            polygon_geometry = _clip_to_boundary(polygon_geometry, boundary_geom)
        return polygon_geometry

    wrote_via_arrow = False
    if parent_cells:
        try:
            h3_indexes = []
            geometries = []
            for parent_cell in parent_cells:
                polygon_geometry = _parent_cell_polygon(parent_cell)
                if polygon_geometry is None:
                    continue
                h3_indexes.append(parent_cell)
                geometries.append(polygon_geometry)
            wrote_via_arrow = write_features_arrow_batch(layer, {"h3_index": h3_indexes}, geometries)
        except Exception as error:
            log_arrow_batch_fallback(f"h3_pyramid_utils._ensure_h3_level_table_scaffold[{table_name}]", error)

    if not wrote_via_arrow and parent_cells:
        layer.StartTransaction()
        try:
            for parent_cell in parent_cells:
                polygon_geometry = _parent_cell_polygon(parent_cell)
                if polygon_geometry is None:
                    continue

                feature = ogr.Feature(layer_defn)
                feature.SetField("h3_index", parent_cell)
                feature.SetGeometry(polygon_geometry)
                layer.CreateFeature(feature)
                feature = None
            layer.CommitTransaction()
        except Exception:
            layer.RollbackTransaction()
            raise

    _execute_sql_with_retry(
        ds,
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_h3index ON {table_name}(h3_index)",  # nosec B608
    )
    return table_name


def _ensure_h3_level_column(ds, table_name: str, sanitized_column: str) -> None:
    """Add a REAL column to an H3 level table if it doesn't already have one."""
    layer = ds.GetLayerByName(table_name)
    layer_defn = layer.GetLayerDefn()
    existing = {layer_defn.GetFieldDefn(i).GetName().lower() for i in range(layer_defn.GetFieldCount())}
    if sanitized_column.lower() not in existing:
        layer.CreateField(ogr.FieldDefn(sanitized_column, ogr.OFTReal))


def _sync_h3_level_table_columns(ds, table_name: str, source_table: str) -> None:
    """Add every score column that exists on source_table but is missing
    from table_name, so each H3 pyramid level stays a complete, scaled
    mirror of the layer below it - not just whichever columns have
    happened to be explicitly refresh_h3_pyramid_column()'d so far. A
    column a workflow hasn't run yet is simply NULL on both tables,
    exactly like the base grid itself. See the matching
    grid_pyramid_utils._sync_level_table_columns() for the square-grid
    equivalent of this same invariant.

    Called on every refresh, not just when a level table is first
    scaffolded, so a column added to study_area_grid after a level table
    already exists still gets picked up.
    """
    from geest.core.grid_pyramid_utils import OUT_OF_SCOPE_PYRAMID_COLUMNS

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


def _refresh_h3_level_column_values(
    ds, h3_module, table_name: str, source_table: str, sanitized_column: str, resolution: int
) -> None:
    """Recompute one column's values on one H3 pyramid level table from its finer source.

    Always fully recomputed (never incrementally patched), mirroring
    grid_pyramid_utils.refresh_pyramid_column(): a cell whose children
    became entirely NULL since the last build correctly reverts to NULL
    instead of lingering with a stale value.

    Args:
        ds: Open OGR DataSource for the GeoPackage.
        h3_module: The imported h3 library module.
        table_name: This level's wide table.
        source_table: The immediately finer table to aggregate from.
        sanitized_column: The already-sanitized column name.
        resolution: This level's H3 resolution, used to resolve each child
            cell's parent via h3.cell_to_parent().
    """
    quoted_column = _quote_sql_identifier(sanitized_column)

    # If every row of source_table already holds the exact same value (or
    # is uniformly NULL), this level's MIN is trivially that same value
    # too - skip reading every child row into Python and building
    # per-parent CASE-WHEN batches just to discover what a single
    # SELECT MIN/MAX already told us.
    is_uniform, uniform_value = _uniform_column_value(ds, source_table, sanitized_column)
    if is_uniform:
        literal = "NULL" if uniform_value is None else repr(float(uniform_value))
        _execute_sql_with_retry(ds, f"UPDATE {table_name} SET {quoted_column} = {literal}")  # nosec B608
        return

    result = _execute_sql_with_retry(ds, f"SELECT h3_index, {quoted_column} FROM {source_table}")  # nosec B608
    aggregated = {}
    if result is not None:
        feature = result.GetNextFeature()
        while feature is not None:
            child_index = feature.GetField("h3_index")
            value = feature.GetField(sanitized_column)
            feature = result.GetNextFeature()
            if not child_index or value is None:
                continue
            try:
                parent_cell = h3_module.cell_to_parent(child_index, resolution)
            except Exception as error:
                log_message(f"Could not resolve H3 parent for {child_index}: {error}", level=Qgis.Warning)
                continue
            if parent_cell not in aggregated or value < aggregated[parent_cell]:
                aggregated[parent_cell] = value
        ds.ReleaseResultSet(result)

    # Clear first so a parent with no non-null children any more reverts to
    # NULL rather than keeping a stale value from a previous build.
    _execute_sql_with_retry(ds, f"UPDATE {table_name} SET {quoted_column} = NULL")  # nosec B608

    items = list(aggregated.items())
    for start in range(0, len(items), H3_LEVEL_BATCH_SIZE):
        batch = items[start : start + H3_LEVEL_BATCH_SIZE]
        case_parts = [f"WHEN h3_index = {_quote_sql_literal(parent_cell)} THEN {value}" for parent_cell, value in batch]
        parent_list = ",".join(_quote_sql_literal(parent_cell) for parent_cell, _ in batch)
        sql = (
            f"UPDATE {table_name} "  # nosec B608
            f"SET {quoted_column} = CASE {' '.join(case_parts)} END "
            f"WHERE h3_index IN ({parent_list})"
        )
        _execute_sql_with_retry(ds, sql)


def refresh_h3_pyramid_column(
    gpkg_path: str,
    column_name: str,
    base_h3_resolution: Optional[int],
    clip_to_boundary: bool = False,
    analysis_scale: str = "national",
) -> bool:
    """(Re)populate one column across every H3 pyramid level table, cascading from the base grid.

    Idempotent and safe to call repeatedly, exactly like
    grid_pyramid_utils.refresh_pyramid_column() for the square-grid case.

    Args:
        gpkg_path: Path to the GeoPackage containing study_area_grid.
        column_name: The study_area_grid score column to pyramid.
        base_h3_resolution: The analysis grid's native H3 resolution.
        clip_to_boundary: If True, every level's edge cells are clipped to
            study_area_clip_polygons, matching the base grid's own
            clip_to_boundary behavior - see
            geest.core.grid_type_utils.get_h3_clip_to_boundary. Only
            meaningful the first time a level table is scaffolded; an
            already-built level table is never retroactively re-clipped.
        analysis_scale: "local" or "national" - picks which pyramid-depth
            setting to build down to (see h3_pyramid_steps()).

    Returns:
        True on success, False on failure.
    """
    if not os.path.exists(gpkg_path):
        log_message(f"GeoPackage not found: {gpkg_path}", level=Qgis.Warning)
        return False

    if base_h3_resolution is None:
        log_message("Cannot build H3 pyramid: no H3 resolution configured for this project", level=Qgis.Warning)
        return False

    try:
        import h3
    except ImportError:
        log_message(
            "H3 library not available. Install with: pip install h3",
            level=Qgis.Warning,
        )
        return False

    resolutions = compute_h3_level_resolutions(base_h3_resolution, steps=h3_pyramid_steps(analysis_scale))

    try:
        sanitized = _sanitize_column_name(column_name)

        ds = _open_gpkg_for_write(gpkg_path)
        if not ds:
            log_message(f"Could not open GeoPackage: {gpkg_path}", level=Qgis.Critical)
            return False

        grid_layer = ds.GetLayerByName("study_area_grid")
        if not grid_layer:
            log_message("study_area_grid layer not found", level=Qgis.Critical)
            ds = None
            return False

        grid_defn = grid_layer.GetLayerDefn()
        grid_fields = {grid_defn.GetFieldDefn(i).GetName().lower() for i in range(grid_defn.GetFieldCount())}

        if "h3_index" not in grid_fields:
            log_message(
                "Cannot build H3 pyramid: study_area_grid has no h3_index column",
                level=Qgis.Warning,
            )
            ds = None
            return False

        # A column that doesn't exist on study_area_grid must fail loudly,
        # not silently build a pyramid from garbage - see the matching
        # comment in grid_pyramid_utils.refresh_pyramid_column().
        if sanitized.lower() not in grid_fields:
            log_message(
                f"Cannot build pyramid: column '{sanitized}' does not exist on study_area_grid",
                level=Qgis.Warning,
            )
            ds = None
            return False

        srs = grid_layer.GetSpatialRef()
        target_epsg = _epsg_from_srs(srs)

        boundary_geom = _load_clip_boundary_geom(ds) if clip_to_boundary else None

        source_table = "study_area_grid"
        for resolution in resolutions[1:]:
            table_name = _ensure_h3_level_table_scaffold(
                ds, h3, resolution, source_table, srs, target_epsg, boundary_geom
            )
            if not table_name:
                ds = None
                return False
            _sync_h3_level_table_columns(ds, table_name, source_table)
            _ensure_h3_level_column(ds, table_name, sanitized)
            _refresh_h3_level_column_values(ds, h3, table_name, source_table, sanitized, resolution)
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
        log_message(f"Error refreshing H3 pyramid for column {column_name}: {error}", level=Qgis.Critical)
        return False


def build_h3_pyramid_scaffold(
    gpkg_path: str,
    base_h3_resolution: Optional[int],
    clip_to_boundary: bool = False,
    analysis_scale: str = "national",
) -> bool:
    """Build every H3 pyramid level's geometry scaffold, with no score columns yet.

    The scaffold (h3_index + geometry per level) only depends on the base
    grid's h3_index values - not on any particular indicator's score
    column - so there is no reason to wait until an indicator actually
    runs before building it. Call this once, right after the base grid is
    written during study area creation (see
    StudyAreaProcessingTask.run()), so every level table already exists by
    the time a user opens an indicator's properties dialog or a workflow
    finishes. refresh_h3_pyramid_column() then only has to add/populate one
    REAL column per level - plain SQL, fast - instead of also constructing
    geometry for potentially tens of thousands of cells on that first call.

    Idempotent: _ensure_h3_level_table_scaffold() skips any level table
    that already has rows, so calling this again (e.g. from
    refresh_h3_pyramid_column() for the first real column) is cheap.

    Args:
        gpkg_path: Path to the GeoPackage containing study_area_grid.
        base_h3_resolution: The analysis grid's native H3 resolution.
        clip_to_boundary: If True, edge cells at every level are clipped to
            study_area_clip_polygons - see
            geest.core.grid_type_utils.get_h3_clip_to_boundary.
        analysis_scale: "local" or "national" - picks which pyramid-depth
            setting to build down to (see h3_pyramid_steps()).

    Returns:
        True on success, False on failure.
    """
    if not os.path.exists(gpkg_path):
        log_message(f"GeoPackage not found: {gpkg_path}", level=Qgis.Warning)
        return False

    if base_h3_resolution is None:
        log_message(
            "Cannot build H3 pyramid scaffold: no H3 resolution configured for this project", level=Qgis.Warning
        )
        return False

    try:
        import h3
    except ImportError:
        log_message(
            "H3 library not available. Install with: pip install h3",
            level=Qgis.Warning,
        )
        return False

    resolutions = compute_h3_level_resolutions(base_h3_resolution, steps=h3_pyramid_steps(analysis_scale))

    try:
        ds = _open_gpkg_for_write(gpkg_path)
        if not ds:
            log_message(f"Could not open GeoPackage: {gpkg_path}", level=Qgis.Critical)
            return False

        grid_layer = ds.GetLayerByName("study_area_grid")
        if not grid_layer:
            log_message("study_area_grid layer not found", level=Qgis.Critical)
            ds = None
            return False

        srs = grid_layer.GetSpatialRef()
        target_epsg = _epsg_from_srs(srs)
        boundary_geom = _load_clip_boundary_geom(ds) if clip_to_boundary else None

        source_table = "study_area_grid"
        for resolution in resolutions[1:]:
            table_name = _ensure_h3_level_table_scaffold(
                ds, h3, resolution, source_table, srs, target_epsg, boundary_geom
            )
            if not table_name:
                ds = None
                return False
            source_table = table_name

        ds = None
        return True

    except Exception as error:
        log_message(f"Error building H3 pyramid scaffold: {error}", level=Qgis.Critical)
        return False


def get_exposed_h3_levels(
    gpkg_path: str, column_name: str, base_h3_resolution: Optional[int], analysis_scale: str = "national"
) -> List[Tuple[int, Optional[str]]]:
    """Return every built H3 pyramid level, finest first, for map visualization.

    Every level built by refresh_h3_pyramid_column() is exposed - there is
    no point building optimized scale-dependent levels and then hiding
    most of them from the actual scale-dependent visualization.

    Args:
        gpkg_path: Path to the GeoPackage containing study_area_grid (kept
            for signature symmetry with get_exposed_levels() - the level
            tables are column-agnostic and this never reads the file).
        column_name: The study_area_grid score column (same as above).
        base_h3_resolution: The analysis grid's native H3 resolution, or
            None, in which case this returns an empty list.
        analysis_scale: "local" or "national" - picks which pyramid-depth
            setting to expose (see h3_pyramid_steps()).

    Returns:
        List of (h3_resolution, table_name) tuples. table_name is None for
        the base level, meaning "use study_area_grid itself". Resolutions
        that clamp to the same value (once 0 is reached) are only exposed
        once, since they'd otherwise point at the same table twice.
    """
    _ = gpkg_path, column_name
    if base_h3_resolution is None:
        return []

    resolutions = compute_h3_level_resolutions(base_h3_resolution, steps=h3_pyramid_steps(analysis_scale))
    levels: List[Tuple[int, Optional[str]]] = [(resolutions[0], None)]
    seen_resolutions = {resolutions[0]}
    for resolution in resolutions[1:]:
        if resolution in seen_resolutions:
            continue
        levels.append((resolution, _h3_level_table_name(resolution)))
        seen_resolutions.add(resolution)
    return levels
