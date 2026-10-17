# -*- coding: utf-8 -*-
"""Grid column utilities for model-based columns.

This module provides utilities for extracting IDs from the JSON model
and managing grid columns for indicators, factors, dimensions, and aggregate scores.

The module supports a grid-first architecture where workflow results are written
directly to study_area_grid columns, then optionally rasterized using gdal_rasterize.
"""

import json
import os
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from osgeo import gdal, ogr
from qgis.core import Qgis, QgsFeedback, QgsVectorLayer

from geest.utilities import log_message

SQLITE_WRITE_BUSY_TIMEOUT_MS = 10000
SQLITE_WRITE_MAX_RETRIES = 3
SQLITE_WRITE_RETRY_DELAY_SECONDS = 0.2


def _open_gpkg_for_write(gpkg_path: str):
    """Open GeoPackage with safer SQLite write pragmas applied."""
    ds = ogr.Open(gpkg_path, 1)
    if not ds:
        return None

    try:
        ds.ExecuteSQL(f"PRAGMA busy_timeout={SQLITE_WRITE_BUSY_TIMEOUT_MS}")
        ds.ExecuteSQL("PRAGMA journal_mode=WAL")
        ds.ExecuteSQL("PRAGMA synchronous=NORMAL")
    except Exception as error:
        log_message(f"Failed to apply SQLite write pragmas: {error}", level=Qgis.Warning)
    return ds


def _is_lock_error(error: Exception) -> bool:
    """Return True if exception indicates SQLite lock contention."""
    text = str(error).lower()
    return "database is locked" in text or "database table is locked" in text or "busy" in text


def _execute_sql_with_retry(ds, sql: str, dialect: Optional[str] = None):
    """Execute SQL with bounded retries for lock/busy errors."""
    last_error = None
    for attempt in range(SQLITE_WRITE_MAX_RETRIES):
        try:
            if dialect:
                return ds.ExecuteSQL(sql, dialect=dialect)
            return ds.ExecuteSQL(sql)
        except Exception as error:
            last_error = error
            if _is_lock_error(error) and attempt < SQLITE_WRITE_MAX_RETRIES - 1:
                time.sleep(SQLITE_WRITE_RETRY_DELAY_SECONDS * (attempt + 1))
                continue
            raise

    if last_error:
        raise last_error
    return None


def grid_cell_count(gpkg_path: str) -> int:
    """Return the number of analysis grid cells, or -1 when unreadable.

    An empty grid means every grid-first workflow would 'succeed' while
    scoring nothing — callers use this to fail loudly instead.
    """
    import sqlite3

    try:
        connection = sqlite3.connect(gpkg_path)
        try:
            return connection.execute("SELECT COUNT(*) FROM study_area_grid").fetchone()[0]
        finally:
            connection.close()
    except sqlite3.Error as error:
        log_message(f"Could not count analysis grid cells: {error}", level=Qgis.Warning)
        return -1


def _checkpoint_wal(ds) -> None:
    """Force a WAL checkpoint on a GeoPackage dataset before closing.

    When multiple OGR write connections open the same GeoPackage in WAL mode,
    uncheckpointed WAL data can cause QGIS's OGR provider to return stale
    metadata (including empty CRS).  A TRUNCATE checkpoint flushes all WAL
    content back into the main database file and removes the WAL/SHM files,
    ensuring subsequent readers see the full, up-to-date database.

    Delegates to gpkg_doctor so every checkpoint in the process shares one
    lock (two connections must never interleave checkpoints on one file).
    """
    from geest.core.gpkg_doctor import checkpoint_dataset

    checkpoint_dataset(ds)


def _ensure_column_exists(gpkg_path: str, column_name: str) -> bool:
    """Ensure a column exists in study_area_grid, creating it if needed.

    This is a safety net for Windows where add_model_columns_to_grid() may fail
    due to file locking. Each write function can call this before writing to
    guarantee the target column exists.

    Args:
        gpkg_path: Path to the GeoPackage containing study_area_grid.
        column_name: Name of the column to ensure exists.

    Returns:
        True if the column exists (or was created), False on failure.
    """
    sanitized = _sanitize_column_name(column_name)
    for attempt in range(SQLITE_WRITE_MAX_RETRIES):
        ds = _open_gpkg_for_write(gpkg_path)
        if not ds:
            if attempt < SQLITE_WRITE_MAX_RETRIES - 1:
                time.sleep(SQLITE_WRITE_RETRY_DELAY_SECONDS * (attempt + 1))
                continue
            return False

        try:
            layer = ds.GetLayerByName("study_area_grid")
            if not layer:
                ds = None
                return False

            layer_defn = layer.GetLayerDefn()
            for i in range(layer_defn.GetFieldCount()):
                if layer_defn.GetFieldDefn(i).GetName().lower() == sanitized.lower():
                    return True  # Already exists

            # Column doesn't exist — create it
            field_defn = ogr.FieldDefn(sanitized, ogr.OFTReal)
            if layer.CreateField(field_defn) == 0:
                log_message(
                    f"Lazily created grid column: {sanitized}",
                    tag="GeoE3",
                    level=Qgis.Info,
                )
                _checkpoint_wal(ds)
                return True

            if attempt < SQLITE_WRITE_MAX_RETRIES - 1:
                log_message(
                    f"Failed to create column '{sanitized}' (attempt {attempt + 1}), retrying...",
                    tag="GeoE3",
                    level=Qgis.Warning,
                )
                time.sleep(SQLITE_WRITE_RETRY_DELAY_SECONDS * (attempt + 1))
        finally:
            ds = None

    log_message(
        f"Could not create grid column '{sanitized}' after {SQLITE_WRITE_MAX_RETRIES} attempts",
        tag="GeoE3",
        level=Qgis.Critical,
    )
    return False


def extract_model_ids(model_path: str) -> Dict[str, List[str]]:
    """Extract all IDs from the model JSON file.

    Traverses the model structure and extracts IDs for dimensions,
    factors, and indicators. Prefixes are added to avoid namespace collisions:
    - Dimensions: dim_<id>
    - Factors: fac_<id>
    - Indicators: <id> (no prefix, most commonly referenced)

    Args:
        model_path: Path to the model.json file.

    Returns:
        Dictionary with keys 'dimensions', 'factors', 'indicators' containing
        lists of prefixed IDs for each category.
    """
    ids = {
        "dimensions": [],
        "factors": [],
        "indicators": [],
    }

    if not os.path.exists(model_path):
        log_message(f"Model file not found: {model_path}", level=Qgis.Warning)
        return ids

    try:
        with open(model_path, "r", encoding="utf-8") as f:
            model = json.load(f)

        for dimension in model.get("dimensions", []):
            dim_id = dimension.get("id", "")
            if dim_id:
                ids["dimensions"].append(f"dim_{dim_id.lower()}")

            for factor in dimension.get("factors", []):
                factor_id = factor.get("id", "")
                if factor_id:
                    ids["factors"].append(f"fac_{factor_id.lower()}")

                for indicator in factor.get("indicators", []):
                    indicator_id = indicator.get("id", "")
                    if indicator_id:
                        ids["indicators"].append(indicator_id.lower())

    except Exception as e:
        log_message(f"Error extracting model IDs: {e}", level=Qgis.Critical)

    return ids


def get_aggregate_column_names() -> List[str]:
    """Get the list of aggregate score column names.

    Returns:
        List of column names for aggregate scores (WEE score, WEE by population, etc.)
    """
    return [
        "geoe3",
        "geoe3_by_population",  # GeoE3 × Population bivariate score (1-15)
        "geoe3_masked",  # GeoE3 score masked by opportunities/GHSL
        "geoe3_by_population_masked",  # GeoE3 by population masked by opportunities
        "opportunities_mask",  # Binary mask for job opportunities
        "contextual_score",
        "accessibility_score",
        "place_characterization_score",
    ]


def get_all_column_names(model_path: str) -> List[str]:
    """Get all column names to be added to the grid layer.

    Args:
        model_path: Path to the model.json file.

    Returns:
        List of all column names (indicators, factors, dimensions, and aggregates).
    """
    ids = extract_model_ids(model_path)
    columns = []

    # Add indicator columns
    columns.extend(ids["indicators"])

    # Add factor columns
    columns.extend(ids["factors"])

    # Add dimension columns
    columns.extend(ids["dimensions"])

    # Add aggregate columns
    columns.extend(get_aggregate_column_names())

    return columns


def add_model_columns_to_grid(gpkg_path: str, model_path: str) -> bool:
    """Add model-based columns to the study_area_grid layer.

    Adds one Real/Float column for each indicator, factor, dimension, and aggregate
    score based on the IDs from the model.json file.

    Args:
        gpkg_path: Path to the GeoPackage containing study_area_grid.
        model_path: Path to the model.json file.

    Returns:
        True if columns were added successfully, False otherwise.
    """
    column_names = get_all_column_names(model_path)

    if not column_names:
        log_message("No columns to add to grid layer", level=Qgis.Warning)
        return False

    try:
        # Get existing field names to avoid duplicates
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
        existing_fields = set()
        for i in range(layer_defn.GetFieldCount()):
            existing_fields.add(layer_defn.GetFieldDefn(i).GetName().lower())

        # Add new columns as Real/Float type
        added_count = 0
        failed_columns = []
        for col_name in column_names:
            sanitized_name = col_name.replace(" ", "_").replace("-", "_")[:63]

            if sanitized_name.lower() in existing_fields:
                continue

            field_defn = ogr.FieldDefn(sanitized_name, ogr.OFTReal)
            created = False
            for attempt in range(SQLITE_WRITE_MAX_RETRIES):
                if layer.CreateField(field_defn) == 0:
                    added_count += 1
                    created = True
                    break
                if attempt < SQLITE_WRITE_MAX_RETRIES - 1:
                    log_message(
                        f"Failed to create field '{sanitized_name}' (attempt {attempt + 1}), retrying...",
                        tag="GeoE3",
                        level=Qgis.Warning,
                    )
                    time.sleep(SQLITE_WRITE_RETRY_DELAY_SECONDS * (attempt + 1))
                    # Reopen dataset on retry — Windows may need a fresh connection
                    ds = None
                    ds = _open_gpkg_for_write(gpkg_path)
                    if not ds:
                        continue
                    layer = ds.GetLayerByName("study_area_grid")
                    if not layer:
                        continue

            if not created:
                failed_columns.append(sanitized_name)
                log_message(f"Failed to create field: {sanitized_name}", level=Qgis.Warning)

        _checkpoint_wal(ds)
        ds.FlushCache()
        ds = None

        if failed_columns:
            log_message(
                f"Added {added_count} columns, but {len(failed_columns)} failed: {failed_columns}",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            # Return True if at least some columns were added; lazy creation handles the rest
            return added_count > 0

        log_message(f"Added {added_count} model columns to study_area_grid")
        return True

    except Exception as e:
        log_message(f"Error adding model columns to grid: {e}", level=Qgis.Critical)
        return False


def write_raster_values_to_grid(
    gpkg_path: str,
    raster_path: str,
    column_name: str,
    area_name: Optional[str] = None,
) -> int:
    """Sample raster values at grid cell centroids and write to grid column.

    Uses the raster's extent to spatially filter grid cells, then samples
    only those cells that fall within the raster bounds. Skips nodata values.

    Args:
        gpkg_path: Path to the GeoPackage containing study_area_grid.
        raster_path: Path to the raster file to sample.
        column_name: Name of the column to write values to.
        area_name: Optional area name to filter grid cells. If None, processes all cells.

    Returns:
        Number of cells updated, or -1 on error.
    """
    if not os.path.exists(raster_path):
        log_message(f"Raster file not found: {raster_path}", level=Qgis.Warning)
        return -1

    try:
        # Open the raster
        raster_ds = gdal.Open(raster_path)
        if not raster_ds:
            log_message(f"Could not open raster: {raster_path}", level=Qgis.Critical)
            return -1

        band = raster_ds.GetRasterBand(1)
        nodata = band.GetNoDataValue()
        gt = raster_ds.GetGeoTransform()

        # Calculate raster extent for spatial filtering
        xmin = gt[0]
        ymax = gt[3]
        xmax = gt[0] + gt[1] * raster_ds.RasterXSize
        ymin = gt[3] + gt[5] * raster_ds.RasterYSize

        # Open the GeoPackage for updating
        ds = _open_gpkg_for_write(gpkg_path)
        if not ds:
            log_message(f"Could not open GeoPackage: {gpkg_path}", level=Qgis.Critical)
            raster_ds = None
            return -1

        # Get layer and ensure column exists (create if missing)
        layer, field_idx = _get_grid_layer_and_field_index(ds, column_name, create_if_missing=True)
        if layer is None or field_idx < 0:
            ds = None
            raster_ds = None
            return -1

        sanitized_column = _sanitize_column_name(column_name)

        # Set spatial filter to raster extent (only process cells within raster bounds)
        layer.SetSpatialFilterRect(xmin, ymin, xmax, ymax)

        # Set attribute filter if area_name is provided
        if area_name:
            layer.SetAttributeFilter(f"area_name = '{area_name}'")

        # Collect FIDs and values first, then batch update
        fid_values = {}
        for feature in layer:
            geom = feature.GetGeometryRef()
            if not geom:
                continue

            # Get centroid
            centroid = geom.Centroid()
            x = centroid.GetX()
            y = centroid.GetY()

            # Convert to pixel coordinates
            px = int((x - gt[0]) / gt[1])
            py = int((y - gt[3]) / gt[5])

            # Check bounds (should be within due to spatial filter, but double-check)
            if px < 0 or px >= raster_ds.RasterXSize or py < 0 or py >= raster_ds.RasterYSize:
                continue

            # Read pixel value
            try:
                pixel_value = band.ReadAsArray(px, py, 1, 1)
                if pixel_value is not None:
                    value = float(pixel_value[0, 0])
                    # Skip nodata values
                    if nodata is not None and value == nodata:
                        continue
                    fid_values[feature.GetFID()] = value
            except (RuntimeError, ValueError, IndexError):
                # Skip cells where pixel read fails
                continue

        log_message(f"Found {len(fid_values)} grid cells with valid raster values")

        # Reset filters before updating
        layer.SetSpatialFilter(None)
        layer.SetAttributeFilter(None)
        layer.ResetReading()

        # Batch update using SQL for efficiency
        updated_count = 0
        batch_size = 500
        fids = list(fid_values.keys())

        for batch_start in range(0, len(fids), batch_size):
            batch_fids = fids[batch_start : batch_start + batch_size]

            # Build CASE statement for this batch
            case_parts = []
            for fid in batch_fids:
                value = fid_values[fid]
                case_parts.append(f"WHEN fid = {fid} THEN {value}")

            if case_parts:
                fid_list = ",".join(str(f) for f in batch_fids)
                sql = (
                    f"UPDATE study_area_grid "  # nosec B608
                    f'SET "{sanitized_column}" = CASE {" ".join(case_parts)} END '
                    f"WHERE fid IN ({fid_list})"
                )
                _execute_sql_with_retry(ds, sql)
                updated_count += len(batch_fids)

        ds = None
        raster_ds = None

        log_message(f"Updated {updated_count} grid cells for column {sanitized_column}")
        return updated_count

    except Exception as e:
        log_message(f"Error in write_raster_values_to_grid: {e}", level=Qgis.Critical)
        return -1


def _sanitize_column_name(column_name: str) -> str:
    """Sanitize a column name for use in SQL and as a field name.

    Args:
        column_name: The column name to sanitize.

    Returns:
        Sanitized column name (lowercase, underscores, max 63 chars).
    """
    return column_name.replace(" ", "_").replace("-", "_")[:63].lower()


def _quote_sql_identifier(identifier: str) -> str:
    """Quote and validate an SQL identifier for SQLite usage.

    Args:
        identifier: The identifier to validate and quote.

    Returns:
        Safely quoted identifier string.

    Raises:
        ValueError: If identifier contains unsupported characters.
    """
    if not identifier:
        raise ValueError("SQL identifier cannot be empty")

    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier}")

    return f'"{identifier}"'


def _quote_sql_literal(value: str) -> str:
    """Quote a string literal for SQLite usage."""
    return "'" + value.replace("'", "''") + "'"


def _parse_reclass_boundary(boundary: Any) -> float:
    """Parse a reclassification table boundary value into float."""
    if isinstance(boundary, str):
        token = boundary.strip().lower()
        if token in {"inf", "+inf", "infinity", "+infinity"}:
            return float("inf")
        if token in {"-inf", "-infinity"}:
            return float("-inf")
        return float(token)
    return float(boundary)


def _value_matches_range(value: float, minimum: float, maximum: float, range_boundaries: int) -> bool:
    """Check whether a value falls into a reclassification range."""
    if range_boundaries == 0:
        return minimum < value <= maximum
    if range_boundaries == 1:
        return minimum <= value < maximum
    if range_boundaries == 2:
        return minimum <= value <= maximum
    if range_boundaries == 3:
        return minimum < value < maximum
    return minimum < value <= maximum


def get_grid_column_values(gpkg_path: str, column_name: str, area_name: Optional[str] = None) -> List[float]:
    """Read non-null values from a grid column, optionally filtered by area."""
    if not os.path.exists(gpkg_path):
        return []

    values: List[float] = []
    try:
        ds = ogr.Open(gpkg_path, 0)
        if not ds:
            return values

        layer, field_idx = _get_grid_layer_and_field_index(ds, column_name, create_if_missing=False)
        if layer is None or field_idx < 0:
            ds = None
            return values

        sanitized_column = _sanitize_column_name(column_name)
        if area_name:
            layer.SetAttributeFilter(f"area_name = '{area_name}'")

        for feature in layer:
            value = feature.GetField(sanitized_column)
            if value is None:
                continue
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                continue

        layer.SetAttributeFilter(None)
        ds = None
        return values
    except Exception as error:
        log_message(f"Error reading grid column values: {error}", level=Qgis.Warning)
        return []


def reclassify_grid_column_with_table(
    gpkg_path: str,
    column_name: str,
    reclassification_table: List[Any],
    area_name: Optional[str] = None,
    range_boundaries: int = 0,
) -> int:
    """Apply a QGIS-style reclassification table directly to a grid column.

    The table format must be [min1, max1, class1, min2, max2, class2, ...].
    """
    if len(reclassification_table) % 3 != 0:
        log_message("Invalid reclassification table length", level=Qgis.Warning)
        return -1

    if not os.path.exists(gpkg_path):
        log_message(f"GeoPackage not found: {gpkg_path}", level=Qgis.Warning)
        return -1

    try:
        parsed_ranges: List[Tuple[float, float, float]] = []
        for index in range(0, len(reclassification_table), 3):
            minimum = _parse_reclass_boundary(reclassification_table[index])
            maximum = _parse_reclass_boundary(reclassification_table[index + 1])
            output_value = float(reclassification_table[index + 2])
            parsed_ranges.append((minimum, maximum, output_value))
    except Exception as error:
        log_message(f"Failed to parse reclassification table: {error}", level=Qgis.Critical)
        return -1

    try:
        ds = _open_gpkg_for_write(gpkg_path)
        if not ds:
            log_message(f"Could not open GeoPackage: {gpkg_path}", level=Qgis.Critical)
            return -1

        layer, field_idx = _get_grid_layer_and_field_index(ds, column_name, create_if_missing=False)
        if layer is None or field_idx < 0:
            ds = None
            return -1

        sanitized_column = _sanitize_column_name(column_name)
        if area_name:
            layer.SetAttributeFilter(f"area_name = '{area_name}'")

        updated_count = 0
        layer.StartTransaction()
        try:
            for feature in layer:
                value = feature.GetField(sanitized_column)
                if value is None:
                    continue

                numeric_value = float(value)
                mapped_value = None
                for minimum, maximum, output_value in parsed_ranges:
                    if _value_matches_range(numeric_value, minimum, maximum, range_boundaries):
                        mapped_value = output_value
                        break

                if mapped_value is None:
                    continue

                feature.SetField(sanitized_column, mapped_value)
                if layer.SetFeature(feature) == 0:
                    updated_count += 1

            layer.CommitTransaction()
        except Exception:
            layer.RollbackTransaction()
            raise

        layer.SetAttributeFilter(None)
        ds = None
        return updated_count
    except Exception as error:
        log_message(f"Error reclassifying grid column: {error}", level=Qgis.Critical)
        return -1


def _get_grid_layer_and_field_index(
    ds: ogr.DataSource,
    column_name: str,
    create_if_missing: bool = True,
) -> Tuple[Optional[ogr.Layer], int]:
    """Get the study_area_grid layer and field index for a column.

    Args:
        ds: Open OGR DataSource for the GeoPackage.
        column_name: The column name to look up.
        create_if_missing: If True, create the column as Real/Float if it doesn't exist.

    Returns:
        Tuple of (layer, field_index) or (None, -1) if not found.
    """
    layer = ds.GetLayerByName("study_area_grid")
    if not layer:
        log_message("study_area_grid layer not found", level=Qgis.Critical)
        return None, -1

    sanitized_column = _sanitize_column_name(column_name)
    layer_defn = layer.GetLayerDefn()
    field_idx = layer_defn.GetFieldIndex(sanitized_column)

    if field_idx < 0:
        if create_if_missing:
            # Create the column as Real/Float type
            field_defn = ogr.FieldDefn(sanitized_column, ogr.OFTReal)
            if layer.CreateField(field_defn) != 0:
                log_message(f"Failed to create column {sanitized_column}", level=Qgis.Warning)
                return layer, -1
            log_message(f"Created column {sanitized_column} in grid layer")
            # Re-fetch the field index after creation
            layer_defn = layer.GetLayerDefn()
            field_idx = layer_defn.GetFieldIndex(sanitized_column)
        else:
            log_message(f"Column {sanitized_column} not found in grid layer", level=Qgis.Warning)
            return layer, -1

    return layer, field_idx


def write_joined_values_to_grid(
    gpkg_path: str,
    column_name: str,
    source_gpkg: str,
    source_layer: str,
    source_key_field: str,
    target_key_field: str,
    source_value_field: str,
    area_name: Optional[str] = None,
) -> int:
    """Write values to study_area_grid via key-based join.

    This function joins `study_area_grid` in the target GeoPackage with an external
    source layer and writes matched values to a target grid column.

    Typical usage for regional S2S:
      - target_key_field: h3_index
      - source_key_field: hex_id

    Args:
        gpkg_path: Path to the GeoPackage containing study_area_grid.
        column_name: Target grid column to write values into.
        source_gpkg: Path to source GeoPackage containing source_layer.
        source_layer: Source layer name in source_gpkg.
        source_key_field: Source key field name (e.g. hex_id).
        target_key_field: Grid key field name (e.g. h3_index).
        source_value_field: Source value field name to copy.
        area_name: Optional area_name filter for grid rows.

    Returns:
        Number of matched grid rows updated, or -1 on error.
    """
    if not os.path.exists(gpkg_path):
        log_message(f"GeoPackage not found: {gpkg_path}", level=Qgis.Warning)
        return -1

    if not os.path.exists(source_gpkg):
        log_message(f"Source GeoPackage not found: {source_gpkg}", level=Qgis.Warning)
        return -1

    try:
        # Ensure the target column exists in study_area_grid.
        ds = _open_gpkg_for_write(gpkg_path)
        if not ds:
            log_message(f"Could not open GeoPackage: {gpkg_path}", level=Qgis.Critical)
            return -1

        layer, field_idx = _get_grid_layer_and_field_index(ds, column_name, create_if_missing=True)
        ds = None
        if layer is None or field_idx < 0:
            return -1

        sanitized_column = _sanitize_column_name(column_name)

        target_col_sql = _quote_sql_identifier(sanitized_column)
        target_key_sql = _quote_sql_identifier(target_key_field)
        source_key_sql = _quote_sql_identifier(source_key_field)
        source_value_sql = _quote_sql_identifier(source_value_field)
        source_layer_sql = _quote_sql_identifier(source_layer)

        area_predicate = ""
        if area_name:
            area_predicate = f"AND g.area_name = {_quote_sql_literal(area_name)}"

        source_gpkg_literal = _quote_sql_literal(source_gpkg)
        source_layer_literal = _quote_sql_literal(source_layer)

        ds = _open_gpkg_for_write(gpkg_path)
        if not ds:
            log_message(f"Could not open GeoPackage: {gpkg_path}", level=Qgis.Critical)
            return -1

        _execute_sql_with_retry(ds, f"ATTACH DATABASE {source_gpkg_literal} AS src", dialect="SQLite")  # nosec B608

        try:
            # Validate source layer exists.
            source_exists_result = _execute_sql_with_retry(
                ds,
                (
                    "SELECT 1 AS exists_flag "  # nosec B608
                    "FROM src.sqlite_master "
                    "WHERE type IN ('table', 'view') "
                    f"AND name = {source_layer_literal} "
                    "LIMIT 1"
                ),
                dialect="SQLite",
            )
            source_exists = False
            if source_exists_result is not None:
                feature = source_exists_result.GetNextFeature()
                source_exists = feature is not None
                ds.ReleaseResultSet(source_exists_result)

            if not source_exists:
                log_message(f"Source layer not found in source GeoPackage: {source_layer}", level=Qgis.Warning)
                return -1

            # Validate source_value_field exists in source layer schema
            schema_sql = f"PRAGMA table_info({source_layer_sql})"  # nosec B608
            schema_result = _execute_sql_with_retry(ds, schema_sql, dialect="SQLite")
            available_columns = []
            if schema_result is not None:
                feat = schema_result.GetNextFeature()
                while feat:
                    col_name = feat.GetField("name")
                    if col_name:
                        available_columns.append(col_name)
                    feat = schema_result.GetNextFeature()
                ds.ReleaseResultSet(schema_result)

            if source_value_field not in available_columns:
                log_message(
                    f"Column '{source_value_field}' not found in source layer '{source_layer}'. "
                    f"Available columns: {available_columns}",
                    level=Qgis.Critical,
                )
                return -1

            # Clear existing values to preserve NULL semantics for unmatched keys.
            clear_sql = f"UPDATE study_area_grid SET {target_col_sql} = NULL"  # nosec B608
            if area_name:
                clear_sql += f" WHERE area_name = {_quote_sql_literal(area_name)}"
            _execute_sql_with_retry(ds, clear_sql, dialect="SQLite")  # nosec B608

            update_sql = (
                f"UPDATE study_area_grid AS g "  # nosec B608
                f"SET {target_col_sql} = ("
                f"SELECT CAST(s.{source_value_sql} AS REAL) "
                f"FROM src.{source_layer_sql} AS s "
                f"WHERE s.{source_key_sql} = g.{target_key_sql} "
                f"LIMIT 1"
                f") "
                f"WHERE EXISTS ("
                f"SELECT 1 FROM src.{source_layer_sql} AS s "
                f"WHERE s.{source_key_sql} = g.{target_key_sql}"
                f") {area_predicate}"
            )
            _execute_sql_with_retry(ds, update_sql, dialect="SQLite")  # nosec B608

            count_sql = (
                f"SELECT COUNT(*) AS matched_count "  # nosec B608
                f"FROM study_area_grid AS g "
                f"JOIN src.{source_layer_sql} AS s "
                f"ON s.{source_key_sql} = g.{target_key_sql} "
                f"WHERE 1=1 {area_predicate}"
            )
            count_result = _execute_sql_with_retry(ds, count_sql, dialect="SQLite")
            matched_count = 0
            if count_result is not None:
                feature = count_result.GetNextFeature()
                if feature is not None:
                    matched_count = feature.GetField("matched_count") or 0
                ds.ReleaseResultSet(count_result)
        finally:
            _execute_sql_with_retry(ds, "DETACH DATABASE src", dialect="SQLite")
            ds = None

        log_message(
            f"Updated {matched_count} grid rows in {sanitized_column} using key join "
            f"({target_key_field} <- {source_key_field})"
        )
        return int(matched_count)

    except Exception as e:
        log_message(f"Error in write_joined_values_to_grid: {e}", level=Qgis.Critical)
        return -1


def write_uniform_value_to_grid(
    gpkg_path: str,
    column_name: str,
    value: float,
    area_name: Optional[str] = None,
    clip_geometry: Optional[ogr.Geometry] = None,
) -> int:
    """Write a constant value to all cells in an area using SQL UPDATE.

    This is useful for index_score workflows where a single value applies
    to all grid cells in an area.

    Args:
        gpkg_path: Path to the GeoPackage containing study_area_grid.
        column_name: Name of the column to write values to.
        value: The constant value to write to all matching cells.
        area_name: Optional area name to filter grid cells.
        clip_geometry: Optional geometry to spatially filter cells (not used in SQL mode).

    Returns:
        Number of cells updated, or -1 on error.
    """
    _ = clip_geometry  # Not used in SQL mode

    if not os.path.exists(gpkg_path):
        log_message(f"GeoPackage not found: {gpkg_path}", level=Qgis.Warning)
        return -1

    sanitized_column = _sanitize_column_name(column_name)

    try:
        ds = _open_gpkg_for_write(gpkg_path)
        if not ds:
            log_message(f"Could not open GeoPackage: {gpkg_path}", level=Qgis.Critical)
            return -1

        # Verify column exists, create if missing
        layer, field_idx = _get_grid_layer_and_field_index(ds, column_name, create_if_missing=True)
        if layer is None or field_idx < 0:
            ds = None
            return -1

        # Simple SQL UPDATE - no area_name filter, update ALL cells
        sql = f'UPDATE study_area_grid SET "{sanitized_column}" = {value}'  # nosec B608
        log_message(f"Executing: {sql}")
        _execute_sql_with_retry(ds, sql)  # nosec B608
        ds = None

        return 0

    except Exception as e:
        log_message(f"Error in write_uniform_value_to_grid: {e}", level=Qgis.Critical)
        return -1


def clear_grid_column(gpkg_path: str, column_name: str) -> bool:
    """Set all values in a grid column to NULL.

    Should be called before populating a column to ensure clean state.

    Args:
        gpkg_path: Path to the GeoPackage containing study_area_grid.
        column_name: Name of the column to clear.

    Returns:
        True if successful, False otherwise.
    """
    if not os.path.exists(gpkg_path):
        log_message(f"GeoPackage not found: {gpkg_path}", level=Qgis.Warning)
        return False

    sanitized_column = _sanitize_column_name(column_name)

    # Ensure column exists — Windows can fail during add_model_columns_to_grid
    _ensure_column_exists(gpkg_path, sanitized_column)

    try:
        ds = _open_gpkg_for_write(gpkg_path)
        if not ds:
            log_message(f"Could not open GeoPackage: {gpkg_path}", level=Qgis.Critical)
            return False

        sql = f'UPDATE study_area_grid SET "{sanitized_column}" = NULL'  # nosec B608
        log_message(f"Clearing column: {sql}")
        _execute_sql_with_retry(ds, sql)  # nosec B608
        ds = None
        return True

    except Exception as e:
        log_message(f"Error clearing grid column: {e}", level=Qgis.Critical)
        return False


def fill_grid_column_zero_for_area(
    gpkg_path: str,
    column_name: str,
    area_name: str,
) -> bool:
    """Set all NULL values to 0 in a grid column for a specific area.

    Used when a workflow produces no features for an area (e.g. OSM points
    outside the AOI).  Score 0 ("not enabling") is a meaningful result and
    must be persisted so the grid renders correctly instead of showing
    transparent/nodata cells.

    Args:
        gpkg_path: Path to the GeoPackage containing study_area_grid.
        column_name: Name of the column to fill.
        area_name: The area_name value identifying which cells to update.

    Returns:
        True if successful, False otherwise.
    """
    if not os.path.exists(gpkg_path):
        log_message(f"GeoPackage not found: {gpkg_path}", level=Qgis.Warning)
        return False

    sanitized_column = _sanitize_column_name(column_name)

    try:
        ds = _open_gpkg_for_write(gpkg_path)
        if not ds:
            log_message(f"Could not open GeoPackage for write: {gpkg_path}", level=Qgis.Critical)
            return False

        sql = (
            f'UPDATE study_area_grid SET "{sanitized_column}" = 0 '  # nosec B608
            f"WHERE area_name = '{area_name}' AND \"{sanitized_column}\" IS NULL"
        )
        _execute_sql_with_retry(ds, sql)
        ds = None
        log_message(
            f"Set score 0 for NULL cells in column {sanitized_column} for area {area_name}",
        )
        return True

    except Exception as e:
        log_message(
            f"Error filling grid column zero for area: {e}",
            level=Qgis.Critical,
        )
        return False


def count_features_per_grid_cell(
    gpkg_path: str,
    column_name: str,
    features_layer: QgsVectorLayer,
    feedback: QgsFeedback = None,
) -> int:
    """Count features intersecting each grid cell and assign scores.

    Writes directly to study_area_grid without creating copies.
    Score mapping: 0 features = NULL, 1 feature = 3, 2+ features = 5

    Args:
        gpkg_path: Path to the GeoPackage containing study_area_grid.
        column_name: Name of the column to write values to.
        features_layer: QgsVectorLayer containing features to count.
        feedback: Optional feedback for progress reporting.

    Returns:
        Number of cells updated, or -1 on error.
    """
    from qgis.core import QgsFeatureRequest, QgsSpatialIndex

    if not os.path.exists(gpkg_path):
        log_message(f"GeoPackage not found: {gpkg_path}", level=Qgis.Warning)
        return -1

    sanitized_column = _sanitize_column_name(column_name)

    # Ensure column exists — Windows can fail during add_model_columns_to_grid
    _ensure_column_exists(gpkg_path, sanitized_column)

    try:
        # Load grid layer
        grid_layer = QgsVectorLayer(f"{gpkg_path}|layername=study_area_grid", "grid", "ogr")
        if not grid_layer.isValid():
            log_message("Could not load study_area_grid layer", level=Qgis.Critical)
            return -1

        # Create spatial index for grid
        grid_index = QgsSpatialIndex(grid_layer.getFeatures())

        # Count features per cell
        grid_feature_counts = {}
        feature_count = features_layer.featureCount()
        log_message(f"Counting {feature_count} features against grid cells")

        for i, feature in enumerate(features_layer.getFeatures()):
            geom = feature.geometry()
            if geom.isEmpty():
                continue

            # Find intersecting grid cells
            intersecting_ids = grid_index.intersects(geom.boundingBox())

            # Refine with actual intersection test for non-point geometries
            if geom.type() != 0:  # Not point
                request = QgsFeatureRequest().setFilterFids(intersecting_ids)
                intersecting_ids = [f.id() for f in grid_layer.getFeatures(request) if f.geometry().intersects(geom)]

            for grid_id in intersecting_ids:
                grid_feature_counts[grid_id] = grid_feature_counts.get(grid_id, 0) + 1

            if feedback and i % 1000 == 0:
                feedback.setProgress((i / feature_count) * 50)

        log_message(f"Found {len(grid_feature_counts)} grid cells with features")

        # Build SQL CASE statement for batch update
        ds = _open_gpkg_for_write(gpkg_path)
        if not ds:
            log_message(f"Could not open GeoPackage: {gpkg_path}", level=Qgis.Critical)
            return -1

        # Update in batches using SQL
        # First, get the fid field name (usually 'fid' for GeoPackage)
        updated_count = 0
        batch_size = 500
        fids = list(grid_feature_counts.keys())

        for batch_start in range(0, len(fids), batch_size):
            batch_fids = fids[batch_start : batch_start + batch_size]

            # Build CASE statement for this batch
            case_parts = []
            for fid in batch_fids:
                count = grid_feature_counts[fid]
                score = 3 if count == 1 else 5
                case_parts.append(f"WHEN fid = {fid} THEN {score}")

            if case_parts:
                fid_list = ",".join(str(f) for f in batch_fids)
                sql = (
                    f"UPDATE study_area_grid "  # nosec B608
                    f'SET "{sanitized_column}" = CASE {" ".join(case_parts)} END '
                    f"WHERE fid IN ({fid_list})"
                )
                _execute_sql_with_retry(ds, sql)
                updated_count += len(batch_fids)

            if feedback:
                progress = 50 + (batch_start / len(fids)) * 50
                feedback.setProgress(progress)

        ds = None
        log_message(f"Updated {updated_count} grid cells with feature counts")

        # Set score 0 for all cells with no intersecting features.
        # "No features nearby" is a meaningful result (no access) and should
        # render as score 0 (not enabling), not as transparent nodata.
        ds = _open_gpkg_for_write(gpkg_path)
        if ds:
            sql = (
                f"UPDATE study_area_grid "  # nosec B608
                f'SET "{sanitized_column}" = 0 '
                f'WHERE "{sanitized_column}" IS NULL'
            )
            _execute_sql_with_retry(ds, sql)
            ds = None
            log_message(f"Set score 0 for cells with no features in column {sanitized_column}")

        return updated_count

    except Exception as e:
        log_message(f"Error in count_features_per_grid_cell: {e}", level=Qgis.Critical)
        return -1


def write_spatial_join_to_grid(
    gpkg_path: str,
    column_name: str,
    features_gpkg: str,
    features_layer: str,
    score_expression: Union[str, Callable[[ogr.Feature], float]],
    area_name: Optional[str] = None,
    aggregation_method: str = "MAX",
    save_buffers: bool = True,
    workflow_directory: Optional[str] = None,
) -> int:
    """Write scores to grid cells based on spatial intersection with features.

    This function performs a spatial join between grid cells and input features,
    applying an aggregation method (MAX, MIN, AVG, SUM) to determine the final
    score for each cell.

    Args:
        gpkg_path: Path to the GeoPackage containing study_area_grid.
        column_name: Name of the column to write values to.
        features_gpkg: Path to the GeoPackage containing the features to join.
        features_layer: Name of the layer containing features (e.g., buffer polygons).
        score_expression: Either a field name containing scores, or a callable
            that takes a feature and returns a score.
        area_name: Optional area name to filter grid cells.
        aggregation_method: How to combine multiple intersecting features
            (MAX, MIN, AVG, SUM, COUNT). Defaults to MAX.
        save_buffers: If True, save intermediate buffer table for review.
        workflow_directory: Directory to save intermediate files.

    Returns:
        Number of cells updated, or -1 on error.
    """
    from qgis.core import (
        QgsCoordinateTransform,
        QgsFeature,
        QgsFeatureRequest,
        QgsGeometry,
        QgsProject,
        QgsSpatialIndex,
    )

    if not os.path.exists(gpkg_path):
        log_message(f"GeoPackage not found: {gpkg_path}", level=Qgis.Warning)
        return -1

    if not os.path.exists(features_gpkg):
        log_message(f"Features GeoPackage not found: {features_gpkg}", level=Qgis.Warning)
        return -1

    sanitized_column = _sanitize_column_name(column_name)
    _ensure_column_exists(gpkg_path, sanitized_column)

    try:
        grid_layer = QgsVectorLayer(f"{gpkg_path}|layername=study_area_grid", "grid", "ogr")
        if not grid_layer.isValid():
            log_message("Could not load study_area_grid layer", level=Qgis.Critical)
            return -1

        features_qlayer = QgsVectorLayer(f"{features_gpkg}|layername={features_layer}", features_layer, "ogr")
        if not features_qlayer.isValid():
            log_message(f"Features layer not found: {features_layer} in {features_gpkg}", level=Qgis.Critical)
            return -1

        # Reproject features on the fly when their CRS differs from the grid -
        # a silent mismatch would otherwise intersect nothing.
        transform = None
        if features_qlayer.crs().isValid() and grid_layer.crs() != features_qlayer.crs():
            log_message(
                f"Features layer CRS {features_qlayer.crs().authid()} differs from grid CRS "
                f"{grid_layer.crs().authid()} — reprojecting features on the fly",
                level=Qgis.Warning,
            )
            transform = QgsCoordinateTransform(features_qlayer.crs(), grid_layer.crs(), QgsProject.instance())

        is_callable_score = callable(score_expression)

        # Normalise features once: reproject, repair invalid geometries, and
        # resolve each feature's score up front.
        feature_geoms = {}
        feature_scores = {}
        repaired = 0
        for feature in features_qlayer.getFeatures():
            geometry = QgsGeometry(feature.geometry())
            if geometry.isEmpty():
                continue
            if transform is not None:
                geometry.transform(transform)
            if not geometry.isGeosValid():
                geometry = geometry.makeValid()
                repaired += 1
                if geometry.isEmpty():
                    continue

            score = score_expression(feature) if is_callable_score else feature.attribute(score_expression)
            if score is None:
                continue

            feature_geoms[feature.id()] = geometry
            feature_scores[feature.id()] = float(score)
        if repaired:
            log_message(f"Repaired {repaired} invalid geometries before spatial join scoring")

        if save_buffers and workflow_directory:
            try:
                from qgis.core import QgsVectorFileWriter

                buffer_output = os.path.join(workflow_directory, f"{features_layer}_buffers.gpkg")
                if os.path.exists(buffer_output):
                    os.remove(buffer_output)
                QgsVectorFileWriter.writeAsVectorFormat(
                    features_qlayer, buffer_output, "UTF-8", features_qlayer.crs(), "GPKG"
                )
                log_message(f"Saved intermediate buffers to {buffer_output}")
            except Exception as e:
                log_message(f"Could not save intermediate buffers: {e}", level=Qgis.Warning)

        if not feature_geoms:
            log_message(f"No usable scored features found in {features_layer}", level=Qgis.Warning)
            return 0

        # Build the spatial index once over the (typically much smaller)
        # features layer, then do one indexed lookup per grid cell - rather
        # than re-querying the features layer with SetSpatialFilter for every
        # one of up to hundreds of thousands of grid cells.
        feature_index = QgsSpatialIndex()
        for fid, geometry in feature_geoms.items():
            index_feature = QgsFeature(fid)
            index_feature.setGeometry(geometry)
            feature_index.addFeature(index_feature)

        request = QgsFeatureRequest()
        if area_name:
            request.setFilterExpression(f"area_name = '{area_name}'")

        grid_scores = {}
        for grid_feature in grid_layer.getFeatures(request):
            grid_geom = grid_feature.geometry()
            if grid_geom.isEmpty():
                continue

            candidate_ids = feature_index.intersects(grid_geom.boundingBox())
            if not candidate_ids:
                continue

            scores = []
            for candidate_id in candidate_ids:
                feature_geom = feature_geoms.get(candidate_id)
                if feature_geom is not None and feature_geom.intersects(grid_geom):
                    scores.append(feature_scores[candidate_id])

            if scores:
                if aggregation_method == "MAX":
                    final_score = max(scores)
                elif aggregation_method == "MIN":
                    final_score = min(scores)
                elif aggregation_method == "AVG":
                    final_score = sum(scores) / len(scores)
                elif aggregation_method == "SUM":
                    final_score = sum(scores)
                elif aggregation_method == "COUNT":
                    final_score = float(len(scores))
                else:
                    final_score = max(scores)

                grid_scores[grid_feature.id()] = final_score

        log_message(f"Found {len(grid_scores)} grid cells with intersecting features for spatial join")

        ds = _open_gpkg_for_write(gpkg_path)
        if not ds:
            log_message(f"Could not open GeoPackage: {gpkg_path}", level=Qgis.Critical)
            return -1

        updated_count = 0
        batch_size = 500
        fids = list(grid_scores.keys())

        for batch_start in range(0, len(fids), batch_size):
            batch_fids = fids[batch_start : batch_start + batch_size]
            case_parts = [f"WHEN fid = {fid} THEN {grid_scores[fid]}" for fid in batch_fids]
            fid_list = ",".join(str(f) for f in batch_fids)
            sql = (
                f"UPDATE study_area_grid "  # nosec B608
                f'SET "{sanitized_column}" = CASE {" ".join(case_parts)} END '
                f"WHERE fid IN ({fid_list})"
            )
            _execute_sql_with_retry(ds, sql)
            updated_count += len(batch_fids)

        ds = None

        log_message(f"Updated {updated_count} grid cells via spatial join for column {sanitized_column}")
        return updated_count

    except Exception as e:
        log_message(f"Error in write_spatial_join_to_grid: {e}", level=Qgis.Critical)
        return -1


def write_aggregation_to_grid(
    gpkg_path: str,
    target_column: str,
    source_columns_weights: Dict[str, float],
    area_name: Optional[str] = None,
    use_coalesce: bool = True,
) -> int:
    """Perform weighted aggregation of grid columns using SQL UPDATE.

    This replaces the raster-based QgsRasterCalculator approach for
    factor, dimension, and analysis aggregations.

    Uses a single SQL UPDATE statement:
    UPDATE study_area_grid SET target = (w1*COALESCE(c1,0) + w2*COALESCE(c2,0) + ...)

    Args:
        gpkg_path: Path to the GeoPackage containing study_area_grid.
        target_column: Name of the column to write aggregated values to.
        source_columns_weights: Dict mapping source column names to their weights.
            Example: {"indicator1": 0.3, "indicator2": 0.3, "indicator3": 0.4}
        area_name: Optional area name to filter grid cells (not used - aggregates all).
        use_coalesce: If True, use COALESCE(col, 0) to handle NULL values.
            Defaults to True.

    Returns:
        0 on success, or -1 on error.
    """
    _ = area_name  # Not used - we aggregate all cells

    if not source_columns_weights:
        log_message("No source columns provided for aggregation", level=Qgis.Warning)
        return -1

    if not os.path.exists(gpkg_path):
        log_message(f"GeoPackage not found: {gpkg_path}", level=Qgis.Warning)
        return -1

    try:
        ds = _open_gpkg_for_write(gpkg_path)
        if not ds:
            log_message(f"Could not open GeoPackage: {gpkg_path}", level=Qgis.Critical)
            return -1

        layer, field_idx = _get_grid_layer_and_field_index(ds, target_column, create_if_missing=True)
        if layer is None or field_idx < 0:
            ds = None
            return -1

        sanitized_target = _sanitize_column_name(target_column)

        # Verify all source columns exist
        layer_defn = layer.GetLayerDefn()
        created_missing_columns = []
        for source_col in source_columns_weights.keys():
            sanitized_source = _sanitize_column_name(source_col)
            if layer_defn.GetFieldIndex(sanitized_source) < 0:
                field_defn = ogr.FieldDefn(sanitized_source, ogr.OFTReal)
                if layer.CreateField(field_defn) != 0:
                    log_message(f"Source column {sanitized_source} not found in grid layer", level=Qgis.Warning)
                    ds = None
                    return -1
                created_missing_columns.append(sanitized_source)
                layer_defn = layer.GetLayerDefn()

        if created_missing_columns:
            log_message(
                f"Created missing aggregation source columns with NULL defaults: {', '.join(created_missing_columns)}",
                level=Qgis.Warning,
            )

        # Build the weighted sum expression
        # Example: (0.3 * COALESCE("indicator1", 0) + 0.4 * COALESCE("indicator2", 0))
        terms = []
        for source_col, weight in source_columns_weights.items():
            sanitized_source = _sanitize_column_name(source_col)
            if use_coalesce:
                terms.append(f'({weight} * COALESCE("{sanitized_source}", 0))')
            else:
                terms.append(f'({weight} * "{sanitized_source}")')

        expression = " + ".join(terms)

        # Build and execute SQL UPDATE
        sql = f'UPDATE study_area_grid SET "{sanitized_target}" = ({expression})'  # nosec B608
        log_message(f"Executing aggregation SQL: {sql[:200]}...")
        _execute_sql_with_retry(ds, sql)  # nosec B608
        ds = None

        log_message(f"Aggregated {len(source_columns_weights)} columns into {sanitized_target}")
        return 0

    except Exception as e:
        log_message(f"Error in write_aggregation_to_grid: {e}", level=Qgis.Critical)
        return -1


def rasterize_grid_column(
    gpkg_path: str,
    column_name: str,
    output_raster_path: str,
    cell_size: float,
    extent: Optional[Tuple[float, float, float, float]] = None,
    nodata: float = -9999.0,
    area_name: Optional[str] = None,
    output_type: int = gdal.GDT_Float32,
) -> bool:
    """Convert a grid column to a raster using gdal_rasterize.

    This function creates a raster from the study_area_grid layer,
    burning values from the specified column into the output raster.

    Args:
        gpkg_path: Path to the GeoPackage containing study_area_grid.
        column_name: Name of the column to rasterize.
        output_raster_path: Path for the output raster file.
        cell_size: Cell size in map units (meters for projected CRS).
        extent: Optional tuple of (xmin, ymin, xmax, ymax). If None,
            computed from the grid layer extent.
        nodata: NoData value for the output raster. Defaults to -9999.
        area_name: Optional area name to filter grid cells.
        output_type: GDAL data type for output. Defaults to GDT_Float32.

    Returns:
        True if rasterization succeeded, False otherwise.
    """
    if not os.path.exists(gpkg_path):
        log_message(f"GeoPackage not found: {gpkg_path}", level=Qgis.Warning)
        return False

    sanitized_column = _sanitize_column_name(column_name)

    # Build the layer specification with optional attribute filter
    if area_name:
        layer_spec = "study_area_grid"
        where_clause = f"area_name = '{area_name}'"
    else:
        layer_spec = "study_area_grid"
        where_clause = None

    try:
        # Open the GeoPackage to get extent and CRS info
        ds = ogr.Open(gpkg_path, 0)
        if not ds:
            log_message(f"Could not open GeoPackage: {gpkg_path}", level=Qgis.Critical)
            return False

        layer = ds.GetLayerByName("study_area_grid")
        if not layer:
            log_message("study_area_grid layer not found", level=Qgis.Critical)
            ds = None
            return False

        # Apply filter to get correct extent
        if area_name:
            layer.SetAttributeFilter(f"area_name = '{area_name}'")
            matched = layer.GetFeatureCount()
            if matched == 0:
                # Some study areas never populate area_name on their grid rows
                # at all (a single, un-partitioned area) - there, the filter
                # matching nothing is expected, not a sign of a missing area.
                # Only bail out when OTHER rows in this grid do carry a real
                # area_name, which means this specific area's cells are
                # genuinely missing (e.g. a sliver too small to have been
                # gridded) rather than area_name simply being unused here.
                layer.SetAttributeFilter("area_name IS NOT NULL")
                area_partitioning_in_use = layer.GetFeatureCount() > 0
                layer.SetAttributeFilter(f"area_name = '{area_name}'")
                if area_partitioning_in_use:
                    log_message(
                        f"No study_area_grid cells found for area '{area_name}'; "
                        "skipping rasterization rather than burning an empty/placeholder raster.",
                        level=Qgis.Warning,
                    )
                    ds = None
                    return False
                layer.SetAttributeFilter(None)

        # Get extent if not provided
        if extent is None:
            layer_extent = layer.GetExtent()
            extent = (layer_extent[0], layer_extent[2], layer_extent[1], layer_extent[3])
            # extent is (xmin, ymin, xmax, ymax)

        # Get spatial reference
        srs = layer.GetSpatialRef()
        srs_wkt = srs.ExportToWkt() if srs else None

        # Reset filter
        layer.SetAttributeFilter(None)
        ds = None

        # Calculate raster dimensions
        xmin, ymin, xmax, ymax = extent
        width = int((xmax - xmin) / cell_size)
        height = int((ymax - ymin) / cell_size)

        if width <= 0 or height <= 0:
            log_message(f"Invalid raster dimensions: {width}x{height}", level=Qgis.Critical)
            return False

        # Build gdal_rasterize options
        rasterize_options = gdal.RasterizeOptions(
            format="GTiff",
            outputType=output_type,
            width=width,
            height=height,
            outputBounds=[xmin, ymin, xmax, ymax],
            noData=nodata,
            initValues=[nodata],
            attribute=sanitized_column,
            layers=[layer_spec],
            where=where_clause,
            creationOptions=["COMPRESS=LZW", "TILED=YES"],
        )

        # Run rasterization
        result = gdal.Rasterize(
            output_raster_path,
            gpkg_path,
            options=rasterize_options,
        )

        if result is None:
            log_message(f"gdal_rasterize failed for column {sanitized_column}", level=Qgis.Critical)
            return False

        # Set spatial reference on output
        if srs_wkt:
            result.SetProjection(srs_wkt)

        # Ensure data is written
        result.FlushCache()
        result = None

        log_message(f"Rasterized column {sanitized_column} to {output_raster_path}")
        return True

    except Exception as e:
        log_message(f"Error in rasterize_grid_column: {e}", level=Qgis.Critical)
        return False


def write_buffer_values_to_grid(
    gpkg_path: str,
    column_name: str,
    buffer_layer: QgsVectorLayer,
    value_field: str = "value",
    aggregation_method: str = "MAX",
    feedback: QgsFeedback = None,
) -> int:
    """Write buffer polygon scores to intersecting grid cells.

    For each grid cell, finds intersecting buffer polygons and aggregates
    their scores (using MAX by default) to determine the cell's value.

    Args:
        gpkg_path: Path to the GeoPackage containing study_area_grid.
        column_name: Name of the column to write values to.
        buffer_layer: QgsVectorLayer containing buffer polygons with scores.
        value_field: Name of the field containing scores in buffer_layer.
        aggregation_method: How to combine multiple intersecting buffers
            (MAX, MIN, AVG). Defaults to MAX.
        feedback: Optional feedback for progress reporting.

    Returns:
        Number of cells updated, or -1 on error.
    """
    from qgis.core import (
        QgsCoordinateTransform,
        QgsFeature,
        QgsGeometry,
        QgsProject,
        QgsRectangle,
        QgsSpatialIndex,
    )

    if not os.path.exists(gpkg_path):
        log_message(f"GeoPackage not found: {gpkg_path}", level=Qgis.Warning)
        return -1

    if not buffer_layer or not buffer_layer.isValid():
        log_message("Invalid buffer layer provided", level=Qgis.Warning)
        return -1

    sanitized_column = _sanitize_column_name(column_name)

    # Ensure column exists — Windows can fail during add_model_columns_to_grid
    _ensure_column_exists(gpkg_path, sanitized_column)

    try:
        # Load grid layer
        grid_layer = QgsVectorLayer(f"{gpkg_path}|layername=study_area_grid", "grid", "ogr")
        if not grid_layer.isValid():
            log_message("Could not load study_area_grid layer", level=Qgis.Critical)
            return -1

        # Normalise the buffer features once: reproject when the CRS differs
        # from the grid (previously a mismatch silently intersected nothing)
        # and repair invalid geometries (network-analysis concave hulls are
        # frequently self-intersecting; GEOS intersects() silently returns
        # False for invalid inputs on stricter builds).
        transform = None
        if buffer_layer.crs() != grid_layer.crs():
            log_message(
                f"Buffer layer CRS {buffer_layer.crs().authid()} differs from grid CRS "
                f"{grid_layer.crs().authid()} — reprojecting buffers on the fly",
                level=Qgis.Warning,
            )
            transform = QgsCoordinateTransform(buffer_layer.crs(), grid_layer.crs(), QgsProject.instance())

        buffer_geoms = {}
        buffer_scores = {}
        repaired = 0
        for buffer_feature in buffer_layer.getFeatures():
            geometry = QgsGeometry(buffer_feature.geometry())
            if geometry.isEmpty():
                continue
            if transform is not None:
                geometry.transform(transform)
            if not geometry.isGeosValid():
                geometry = geometry.makeValid()
                repaired += 1
                if geometry.isEmpty():
                    continue
            buffer_geoms[buffer_feature.id()] = geometry
            buffer_scores[buffer_feature.id()] = buffer_feature.attribute(value_field)
        if repaired:
            log_message(f"Repaired {repaired} invalid buffer geometries before grid scoring")

        # Create spatial index over the normalised geometries
        buffer_index = QgsSpatialIndex()
        for fid, geometry in buffer_geoms.items():
            index_feature = QgsFeature(fid)
            index_feature.setGeometry(geometry)
            buffer_index.addFeature(index_feature)

        # Collect scores per grid cell
        grid_scores = {}
        total_features = grid_layer.featureCount()
        log_message(f"Processing {total_features} grid cells against buffer layer")
        if total_features == 0:
            log_message(
                "study_area_grid contains no cells — nothing can be scored. "
                "The study area needs to be re-created to regenerate the grid.",
                level=Qgis.Critical,
            )
            return -1

        for i, grid_feature in enumerate(grid_layer.getFeatures()):
            grid_geom = grid_feature.geometry()
            if grid_geom.isEmpty():
                continue

            grid_fid = grid_feature.id()

            # Find intersecting buffer polygons
            candidate_ids = buffer_index.intersects(grid_geom.boundingBox())
            if not candidate_ids:
                continue

            # Get actual intersecting features and their scores
            scores = []
            for candidate_id in candidate_ids:
                buffer_geom = buffer_geoms.get(candidate_id)
                if buffer_geom is not None and buffer_geom.intersects(grid_geom):
                    score = buffer_scores.get(candidate_id)
                    if score is not None:
                        scores.append(float(score))

            # Aggregate scores
            if scores:
                if aggregation_method == "MAX":
                    final_score = max(scores)
                elif aggregation_method == "MIN":
                    final_score = min(scores)
                elif aggregation_method == "AVG":
                    final_score = sum(scores) / len(scores)
                else:
                    final_score = max(scores)

                grid_scores[grid_fid] = final_score

            if feedback and i % 1000 == 0:
                feedback.setProgress((i / total_features) * 50)

        log_message(f"Found {len(grid_scores)} grid cells with intersecting buffers")
        if not grid_scores and buffer_geoms:
            # Zero intersections with real buffers present is almost always a
            # spatial/validity problem — leave forensics in the log.
            buffer_extent = QgsRectangle()
            for geometry in buffer_geoms.values():
                buffer_extent.combineExtentWith(geometry.boundingBox())
            log_message(
                "No grid cells intersect any buffer. "
                f"Grid extent: {grid_layer.extent().toString(0)} | "
                f"Buffer extent: {buffer_extent.toString(0)} | "
                f"Buffers: {len(buffer_geoms)} (repaired: {repaired}) | "
                f"Buffer CRS: {buffer_layer.crs().authid()} | Grid CRS: {grid_layer.crs().authid()}",
                level=Qgis.Warning,
            )

        # Update grid using SQL batched updates
        ds = _open_gpkg_for_write(gpkg_path)
        if not ds:
            log_message(f"Could not open GeoPackage: {gpkg_path}", level=Qgis.Critical)
            return -1

        updated_count = 0
        batch_size = 500
        fids = list(grid_scores.keys())

        for batch_start in range(0, len(fids), batch_size):
            batch_fids = fids[batch_start : batch_start + batch_size]

            # Build CASE statement for this batch
            case_parts = []
            for fid in batch_fids:
                score = grid_scores[fid]
                case_parts.append(f"WHEN fid = {fid} THEN {score}")

            if case_parts:
                fid_list = ",".join(str(f) for f in batch_fids)
                sql = (
                    f"UPDATE study_area_grid "  # nosec B608
                    f'SET "{sanitized_column}" = CASE {" ".join(case_parts)} END '
                    f"WHERE fid IN ({fid_list})"
                )
                _execute_sql_with_retry(ds, sql)
                updated_count += len(batch_fids)

            if feedback:
                progress = 50 + (batch_start / max(len(fids), 1)) * 50
                feedback.setProgress(progress)

        ds = None
        log_message(f"Updated {updated_count} grid cells with buffer scores")

        # Set score 0 for all cells outside every buffer (no access).
        # "No buffer coverage" is a meaningful result and should render as
        # score 0 (not enabling), not as transparent nodata.
        ds = _open_gpkg_for_write(gpkg_path)
        if ds:
            sql = (
                f"UPDATE study_area_grid "  # nosec B608
                f'SET "{sanitized_column}" = 0 '
                f'WHERE "{sanitized_column}" IS NULL'
            )
            _execute_sql_with_retry(ds, sql)
            ds = None
            log_message(f"Set score 0 for cells outside all buffers in column {sanitized_column}")

        return updated_count

    except Exception as e:
        log_message(f"Error in write_buffer_values_to_grid: {e}", level=Qgis.Critical)
        return -1


def write_percentage_scores_to_grid(
    gpkg_path: str,
    column_name: str,
    buffer_layer: QgsVectorLayer,
    percentage_scores: Dict[int, int],
    feedback: QgsFeedback = None,
) -> int:
    """Score grid cells by % of hexagon area covered by dissolved POI buffers.

    All buffer polygons are dissolved (unioned) first so that overlapping
    buffers from nearby POIs are not double-counted.  Each hexagon's score is
    then determined by what fraction of its own area falls inside the merged
    buffer, mapped to a 0–5 class via *percentage_scores*.

    Args:
        gpkg_path: Path to the GeoPackage containing study_area_grid.
        column_name: Name of the column to write values to.
        buffer_layer: QgsVectorLayer containing buffer polygons (geometry only).
        percentage_scores: Mapping of lower-bound percentage → score, e.g.
            ``{0: 0, 6: 1, 12: 2, 18: 3, 24: 4, 100: 5}``.
        feedback: Optional feedback for progress reporting.

    Returns:
        Number of cells updated, or -1 on error.
    """
    from qgis.core import (
        QgsCoordinateTransform,
        QgsGeometry,
        QgsProject,
    )

    if not os.path.exists(gpkg_path):
        log_message(f"GeoPackage not found: {gpkg_path}", level=Qgis.Warning)
        return -1

    if not buffer_layer or not buffer_layer.isValid():
        log_message("Invalid buffer layer provided", level=Qgis.Warning)
        return -1

    if not percentage_scores:
        log_message("No percentage_scores provided", level=Qgis.Warning)
        return -1

    sanitized_column = _sanitize_column_name(column_name)
    _ensure_column_exists(gpkg_path, sanitized_column)

    try:
        grid_layer = QgsVectorLayer(f"{gpkg_path}|layername=study_area_grid", "grid", "ogr")
        if not grid_layer.isValid():
            log_message("Could not load study_area_grid layer", level=Qgis.Critical)
            return -1

        transform = None
        if buffer_layer.crs() != grid_layer.crs():
            log_message(
                f"Buffer layer CRS {buffer_layer.crs().authid()} differs from grid CRS "
                f"{grid_layer.crs().authid()} — reprojecting buffers on the fly",
                level=Qgis.Warning,
            )
            transform = QgsCoordinateTransform(buffer_layer.crs(), grid_layer.crs(), QgsProject.instance())

        buffer_geoms = []
        repaired = 0
        for buffer_feature in buffer_layer.getFeatures():
            geometry = QgsGeometry(buffer_feature.geometry())
            if geometry.isEmpty():
                continue
            if transform is not None:
                geometry.transform(transform)
            if not geometry.isGeosValid():
                geometry = geometry.makeValid()
                repaired += 1
                if geometry.isEmpty():
                    continue
            buffer_geoms.append(geometry)
        if repaired:
            log_message(f"Repaired {repaired} invalid buffer geometries before dissolving")

        if not buffer_geoms:
            log_message("No valid buffer geometries to dissolve", level=Qgis.Warning)
            return 0

        dissolved = QgsGeometry.unaryUnion(buffer_geoms)
        if dissolved.isNull() or dissolved.isEmpty():
            log_message("Dissolved buffer is empty", level=Qgis.Warning)
            return 0
        if not dissolved.isGeosValid():
            dissolved = dissolved.makeValid()

        log_message(f"Dissolved {len(buffer_geoms)} buffers into unified polygon")
        dissolved_bbox = dissolved.boundingBox()

        sorted_thresholds = sorted(percentage_scores.items())

        def _score_for_percent(pct: float) -> int:
            for max_pct, s in sorted_thresholds:
                if pct <= max_pct:
                    return s
            return sorted_thresholds[-1][1]

        grid_scores = {}
        total_features = grid_layer.featureCount()
        log_message(f"Scoring {total_features} grid cells by percentage intersection")
        if total_features == 0:
            log_message(
                "study_area_grid contains no cells — nothing can be scored.",
                level=Qgis.Critical,
            )
            return -1

        for i, grid_feature in enumerate(grid_layer.getFeatures()):
            grid_geom = grid_feature.geometry()
            if grid_geom.isEmpty():
                continue

            grid_area = grid_geom.area()
            if grid_area == 0:
                continue

            # Cheap bbox reject before the expensive exact GEOS intersection -
            # most cells are nowhere near any buffer (buffers cluster around
            # POIs, leaving large gaps), and this is the dominant cost when
            # the grid has hundreds of thousands of cells (local scale).
            if not grid_geom.boundingBox().intersects(dissolved_bbox):
                continue

            intersection = grid_geom.intersection(dissolved)
            if intersection.isNull() or intersection.area() == 0:
                continue

            overlap_percent = (intersection.area() / grid_area) * 100
            score = _score_for_percent(overlap_percent)
            if score > 0:
                grid_scores[grid_feature.id()] = score

            if feedback and i % 1000 == 0:
                feedback.setProgress((i / total_features) * 80)

        log_message(f"Found {len(grid_scores)} grid cells with buffer coverage")

        ds = _open_gpkg_for_write(gpkg_path)
        if not ds:
            log_message(f"Could not open GeoPackage: {gpkg_path}", level=Qgis.Critical)
            return -1

        updated_count = 0
        batch_size = 500
        fids = list(grid_scores.keys())

        for batch_start in range(0, len(fids), batch_size):
            batch_fids = fids[batch_start : batch_start + batch_size]

            case_parts = []
            for fid in batch_fids:
                score = grid_scores[fid]
                case_parts.append(f"WHEN fid = {fid} THEN {score}")

            if case_parts:
                fid_list = ",".join(str(f) for f in batch_fids)
                sql = (
                    f"UPDATE study_area_grid "  # nosec B608
                    f'SET "{sanitized_column}" = CASE {" ".join(case_parts)} END '
                    f"WHERE fid IN ({fid_list})"
                )
                _execute_sql_with_retry(ds, sql)
                updated_count += len(batch_fids)

            if feedback:
                progress = 80 + (batch_start / max(len(fids), 1)) * 20
                feedback.setProgress(progress)

        ds = None
        log_message(f"Updated {updated_count} grid cells with percentage-based scores")

        ds = _open_gpkg_for_write(gpkg_path)
        if ds:
            sql = (
                f"UPDATE study_area_grid "  # nosec B608
                f'SET "{sanitized_column}" = 0 '
                f'WHERE "{sanitized_column}" IS NULL'
            )
            _execute_sql_with_retry(ds, sql)
            ds = None
            log_message(f"Set score 0 for cells outside all buffers in column {sanitized_column}")

        return updated_count

    except Exception as e:
        log_message(f"Error in write_percentage_scores_to_grid: {e}", level=Qgis.Critical)
        return -1


def get_grid_column_statistics(
    gpkg_path: str,
    column_name: str,
    area_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate statistics for a grid column.

    Args:
        gpkg_path: Path to the GeoPackage containing study_area_grid.
        column_name: Name of the column to analyze.
        area_name: Optional area name to filter grid cells.

    Returns:
        Dict with keys: count, min, max, mean, sum, null_count.
        Returns empty dict on error.
    """
    if not os.path.exists(gpkg_path):
        log_message(f"GeoPackage not found: {gpkg_path}", level=Qgis.Warning)
        return {}

    try:
        ds = ogr.Open(gpkg_path, 0)
        if not ds:
            log_message(f"Could not open GeoPackage: {gpkg_path}", level=Qgis.Critical)
            return {}

        layer, field_idx = _get_grid_layer_and_field_index(ds, column_name)
        if layer is None or field_idx < 0:
            ds = None
            return {}

        sanitized_column = _sanitize_column_name(column_name)

        # Set attribute filter
        if area_name:
            layer.SetAttributeFilter(f"area_name = '{area_name}'")

        # Calculate statistics
        values = []
        null_count = 0

        for feature in layer:
            value = feature.GetField(sanitized_column)
            if value is None:
                null_count += 1
            else:
                values.append(float(value))

        layer.SetAttributeFilter(None)
        ds = None

        if not values:
            return {
                "count": 0,
                "min": None,
                "max": None,
                "mean": None,
                "sum": None,
                "null_count": null_count,
            }

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "sum": sum(values),
            "null_count": null_count,
        }

    except Exception as e:
        log_message(f"Error in get_grid_column_statistics: {e}", level=Qgis.Critical)
        return {}
