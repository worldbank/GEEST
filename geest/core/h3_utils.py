# coding=utf-8
"""H3 Hexagonal Grid Utilities.

This module provides utilities for H3 hexagonal grid generation,
used specifically for Regional scale analysis.

H3 Resolution Reference:
- Resolution 6: ~3.2km edge, ~36 km² area (Regional scale)
"""

import threading
from typing import List, Optional, Tuple

from osgeo import ogr, osr
from qgis.core import Qgis

from geest.utilities import log_message

# osr.CoordinateTransformation construction (SpatialReference setup +
# PROJ pipeline resolution) costs ~20x more than reusing an existing one -
# bbox_to_wgs84()/transform_wgs84_to_target() are called once per grid
# cell (H3 and square grids alike), so building a fresh transform on every
# call is a measured, significant chunk of total grid generation time.
# Thread-local, not a shared global: GDAL/PROJ transformation objects are
# not guaranteed safe for concurrent use from multiple threads at once,
# and grid generation already runs several of these calls in parallel via
# QThreadPool (see study_area_processing_task.py's ChunkRunnable).
_transform_cache_local = threading.local()


def _get_cached_transform(source_epsg: int, target_epsg: int) -> osr.CoordinateTransformation:
    """Return a thread-local, cached CoordinateTransformation for this EPSG pair."""
    cache = getattr(_transform_cache_local, "cache", None)
    if cache is None:
        cache = {}
        _transform_cache_local.cache = cache

    key = (source_epsg, target_epsg)
    transform = cache.get(key)
    if transform is None:
        source_srs = osr.SpatialReference()
        source_srs.ImportFromEPSG(source_epsg)
        source_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

        target_srs = osr.SpatialReference()
        target_srs.ImportFromEPSG(target_epsg)
        target_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

        transform = osr.CoordinateTransformation(source_srs, target_srs)
        cache[key] = transform
    return transform


# Fallback average H3 cell areas in km^2 (approximate)
H3_CELL_AREA_KM2 = {
    0: 4250546.848,
    1: 607220.978,
    2: 86745.854,
    3: 12392.265,
    4: 1770.323,
    5: 252.903,
    6: 36.129,
    7: 5.161,
    8: 0.737,
    9: 0.105,
    10: 0.015,
    11: 0.002,
    12: 0.00031,
    13: 0.000044,
    14: 0.000006,
    15: 0.0000009,
}


def get_h3_resolution_for_scale(analysis_scale: str, cell_size_m: Optional[float] = None) -> Optional[int]:
    """Get H3 resolution for a given analysis scale.

    Args:
        analysis_scale: The analysis scale ("regional", "national", or "local")
        cell_size_m: Optional target cell size in metres, used only for
            "local"/"national" scales that have opted into an H3 grid.
            Ignored for "regional", which always returns resolution 6.

    Returns:
        H3 resolution integer (6 for regional; derived from cell_size_m for
        local/national when provided), or None if not applicable.
    """
    if analysis_scale == "regional":
        return 6
    if analysis_scale in ("local", "national") and cell_size_m is not None:
        return get_h3_resolution_for_cell_size(cell_size_m)
    return None


def h3_cell_area_km2(h3_resolution: int) -> float:
    """Return average H3 cell area in km^2 for a resolution.

    Args:
        h3_resolution: H3 resolution level.

    Returns:
        Average hexagon area in square kilometers.
    """
    if h3_resolution < 0 or h3_resolution > 15:
        raise ValueError("H3 resolution must be between 0 and 15.")

    try:
        import h3

        return float(h3.average_hexagon_area(h3_resolution, unit="km^2"))
    except Exception:
        return H3_CELL_AREA_KM2[h3_resolution]


def get_h3_resolution_for_cell_size(cell_size_m: float) -> int:
    """Pick the H3 resolution whose average cell area best matches a target cell size.

    Area (not edge length) is the right equivalence metric: it is what
    directly determines cell density/count, which is what a square-grid
    cell_size_m is really standing in for here.

    Args:
        cell_size_m: Target (square) cell size in metres, e.g. an analysis
            grid's base cell size.

    Returns:
        H3 resolution (0-15) whose average hexagon area is closest to
        (cell_size_m / 1000)**2 square kilometres.
    """
    target_area_km2 = (cell_size_m / 1000.0) ** 2
    return min(range(16), key=lambda r: abs(h3_cell_area_km2(r) - target_area_km2))


def estimate_h3_cells_for_area(area_km2: float, h3_resolution: int) -> int:
    """Estimate H3 cell count needed for an area.

    Args:
        area_km2: Area in square kilometers.
        h3_resolution: H3 resolution level.

    Returns:
        Estimated number of cells.
    """
    if area_km2 <= 0:
        return 0

    cell_area = h3_cell_area_km2(h3_resolution)
    if cell_area <= 0:
        return 0

    return max(1, int(round(area_km2 / cell_area)))


def suggest_coarser_resolution(area_km2: float, max_cells: int, start_res: int) -> int:
    """Suggest a coarser resolution that stays under max cell count.

    Args:
        area_km2: Area in square kilometers.
        max_cells: Maximum allowed estimated cells.
        start_res: Starting resolution.

    Returns:
        Suggested resolution (0-15).
    """
    suggested = max(0, min(15, start_res))
    while suggested > 0 and estimate_h3_cells_for_area(area_km2, suggested) > max_cells:
        suggested -= 1
    return suggested


def suggest_finer_resolution(area_km2: float, min_cells: int, start_res: int) -> int:
    """Suggest a finer resolution that reaches minimum cell count.

    Args:
        area_km2: Area in square kilometers.
        min_cells: Minimum estimated cells.
        start_res: Starting resolution.

    Returns:
        Suggested resolution (0-15).
    """
    suggested = max(0, min(15, start_res))
    while suggested < 15 and estimate_h3_cells_for_area(area_km2, suggested) < min_cells:
        suggested += 1
    return suggested


def bbox_to_wgs84(
    xmin: float,
    xmax: float,
    ymin: float,
    ymax: float,
    source_epsg: int,
) -> Tuple[float, float, float, float]:
    """Transform bounding box from source CRS to WGS84.

    Args:
        xmin: Minimum x coordinate
        xmax: Maximum x coordinate
        ymin: Minimum y coordinate
        ymax: Maximum y coordinate
        source_epsg: EPSG code of source CRS

    Returns:
        Tuple of (xmin, xmax, ymin, ymax) in WGS84
    """
    transform = _get_cached_transform(source_epsg, 4326)

    # Transform all four corners
    points = [
        (xmin, ymin),
        (xmax, ymin),
        (xmax, ymax),
        (xmin, ymax),
    ]

    wgs84_points = []
    for px, py in points:
        lon, lat, _ = transform.TransformPoint(px, py)
        wgs84_points.append((lon, lat))

    wgs84_xmin = min(p[0] for p in wgs84_points)
    wgs84_xmax = max(p[0] for p in wgs84_points)
    wgs84_ymin = min(p[1] for p in wgs84_points)
    wgs84_ymax = max(p[1] for p in wgs84_points)

    return wgs84_xmin, wgs84_xmax, wgs84_ymin, wgs84_ymax


def transform_wgs84_to_target(
    x: float,
    y: float,
    target_epsg: int,
) -> Tuple[float, float]:
    """Transform a point from WGS84 to target CRS.

    Args:
        x: Longitude
        y: Latitude
        target_epsg: EPSG code of target CRS

    Returns:
        Tuple of (x, y) in target CRS
    """
    transform = _get_cached_transform(4326, target_epsg)
    tx, ty, _ = transform.TransformPoint(x, y)
    return tx, ty


def h3_cell_to_polygon_wkt(h3_index: str, target_epsg: int) -> str:
    """Convert H3 cell index to polygon WKT in target CRS.

    Args:
        h3_index: H3 cell index (e.g., "862a1072fffffff")
        target_epsg: EPSG code of target CRS

    Returns:
        Polygon WKT string in target CRS
    """
    try:
        import h3
    except ImportError:
        log_message(
            "H3 library not available. Install with: pip install h3",
            level=Qgis.Warning,
        )
        return ""

    # Get H3 boundary in WGS84 - h3-py returns (lat, lng) pairs
    boundary = h3.cell_to_boundary(h3_index)

    # Transform each point to target CRS
    transformed_points = []
    for lat, lon in boundary:
        tx, ty = transform_wgs84_to_target(lon, lat, target_epsg)
        transformed_points.append((tx, ty))

    # Create polygon WKT
    coords_str = ", ".join([f"{x} {y}" for x, y in transformed_points])
    wkt = f"POLYGON (({coords_str}))"

    return wkt


def generate_h3_indexes(
    bbox_wgs84: Tuple[float, float, float, float],
    h3_resolution: int,
) -> List[str]:
    """Generate H3 cell indexes for a bounding box.

    Args:
        bbox_wgs84: Tuple of (xmin, xmax, ymin, ymax) in WGS84
        h3_resolution: H3 resolution level (e.g., 6)

    Returns:
        List of H3 cell indexes
    """
    try:
        import h3
    except ImportError:
        log_message(
            "H3 library not available. Install with: pip install h3",
            level=Qgis.Warning,
        )
        return []

    xmin, xmax, ymin, ymax = bbox_wgs84

    # h3-py v4 uses LatLngPoly or h3shape_to_cells
    # Coordinates are [lat, lng] format (NOT [lng, lat])
    # Since we have bbox in [lng, lat] format, we need to swap
    outer = [
        (ymin, xmin),  # lat, lng
        (ymax, xmin),
        (ymax, xmax),
        (ymin, xmax),
        (ymin, xmin),
    ]

    try:
        poly = h3.LatLngPoly(outer)
        h3_indexes = h3.h3shape_to_cells(poly, res=h3_resolution)
    except Exception as e:
        log_message(f"Error generating H3 cells: {e}", level=Qgis.Warning)
        return []

    return list(h3_indexes)


def estimate_h3_cell_count(
    bbox_wgs84: Tuple[float, float, float, float],
    h3_resolution: int,
) -> int:
    """Estimate the number of H3 cells for a bounding box.

    Args:
        bbox_wgs84: Tuple of (xmin, xmax, ymin, ymax) in WGS84
        h3_resolution: H3 resolution level

    Returns:
        Estimated cell count
    """
    xmin, xmax, ymin, ymax = bbox_wgs84

    # Calculate approximate area in degrees
    width = xmax - xmin
    height = ymax - ymin

    # Average cell area at given resolution (in square degrees, approximate)
    # These are rough estimates based on H3 documentation
    cell_areas = {
        6: 0.01,  # ~36 km²
        7: 0.0015,  # ~5 km²
        9: 0.00005,  # ~0.1 km²
    }

    area = width * height
    cell_area = cell_areas.get(h3_resolution, 0.001)

    estimate = int(area / cell_area)
    return max(estimate, 1)


def create_h3_polygon_from_boundary(
    boundary_coords: List[Tuple[float, float]],
    target_epsg: int,
) -> ogr.Geometry:
    """Create OGR polygon geometry from H3 boundary coordinates.

    Args:
        boundary_coords: List of (x, y) tuples in WGS84
        target_epsg: EPSG code of target CRS

    Returns:
        OGR polygon geometry in target CRS
    """
    # Transform coordinates to target CRS
    transformed_coords = []
    for lon, lat in boundary_coords:
        tx, ty = transform_wgs84_to_target(lon, lat, target_epsg)
        transformed_coords.append((tx, ty))

    # Create ring
    ring = ogr.Geometry(ogr.wkbLinearRing)
    for x, y in transformed_coords:
        ring.AddPoint(x, y)
    ring.CloseRings()

    # Create polygon
    polygon = ogr.Geometry(ogr.wkbPolygon)
    polygon.AddGeometry(ring)

    return polygon
