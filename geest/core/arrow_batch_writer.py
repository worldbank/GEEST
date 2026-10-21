# -*- coding: utf-8 -*-
"""Optional pyarrow-accelerated bulk feature writes for OGR layers.

GDAL's Layer.WritePyArrow() hands a whole columnar batch to the driver in
one call, instead of one Python CreateFeature() call per feature. A
benchmark comparing both paths on GeoPackage/Shapefile/FlatGeobuf/
GeoParquet found the file format made almost no difference - the
bottleneck is the per-feature OGR/Python API call, not the on-disk
format - and switching to the batch API alone got ~2x faster writes and
~10x faster reads on the SAME GeoPackage files.

pyarrow is a large (~150MB+) compiled dependency, bundled by default on
Windows QGIS installs (OSGeo4W's qgis-full requires python3-pyarrow) but
not guaranteed elsewhere (Linux/macOS packages, older QGIS). So, matching
this codebase's existing convention for optional heavy deps (see the
lazy `import h3` inside try/except in geest.core.h3_utils), pyarrow is
imported lazily inside this function, not at module load time: every call
site keeps its original per-feature CreateFeature() loop as the fallback
path when this returns False.
"""
from typing import Dict, Optional, Sequence

from osgeo import ogr
from qgis.core import Qgis

from geest.utilities import log_message


def write_features_arrow_batch(
    layer,
    field_values: Dict[str, Sequence],
    geometries: Sequence[Optional["ogr.Geometry"]],
) -> bool:
    """Bulk-insert features into layer via GDAL's Arrow-batch API.

    Args:
        layer: An OGR Layer open for writing, with its fields already
            created (CreateField()) - this only inserts rows, it does not
            modify the schema.
        field_values: Attribute column name -> sequence of values, one
            per feature, in the same order as geometries. Every sequence
            must be the same length.
        geometries: One ogr.Geometry (or None for a null geometry) per
            feature, same order/length as each field_values sequence.

    Returns:
        True if the batch was written via the Arrow path. False if
        pyarrow is not installed - the caller should fall back to its own
        CreateFeature() loop in that case.

    Raises:
        RuntimeError: If pyarrow is available but GDAL's WritePyArrow()
            itself fails (e.g. a driver that doesn't support it). Not
            swallowed here - a caller that wants "try Arrow, else loop"
            should catch broadly around this call and fall back itself;
            silently discarding a real write failure would be worse than
            raising it.
    """
    try:
        import pyarrow as pa
    except ImportError:
        return False

    n = len(geometries)
    for name, values in field_values.items():
        if len(values) != n:
            raise ValueError(f"field_values[{name!r}] has {len(values)} values, expected {n}")

    geom_col = layer.GetGeometryColumn() or "wkb_geometry"
    columns = {name: pa.array(list(values)) for name, values in field_values.items()}
    wkb_values = [geom.ExportToIsoWkb() if geom is not None else None for geom in geometries]
    columns[geom_col] = pa.array(wkb_values, type=pa.binary())
    table = pa.table(columns)

    err = layer.WritePyArrow(table)
    if err != ogr.OGRERR_NONE:
        raise RuntimeError(f"WritePyArrow failed with OGRERR {err}")
    return True


def log_arrow_batch_fallback(context: str, error: Exception) -> None:
    """Shared log line for "Arrow batch write failed, falling back" call sites."""
    log_message(
        f"{context}: Arrow-batch write failed, falling back to per-feature write: {error}",
        level=Qgis.Warning,
    )
