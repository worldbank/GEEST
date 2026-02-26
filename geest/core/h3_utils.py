# coding=utf-8
"""H3 Hexagonal Grid Utilities.

This module provides utilities for H3 hexagonal grid generation,
used specifically for Regional scale analysis.

H3 Resolution Reference:
- Resolution 6: ~3.2km edge, ~36 km² area (Regional scale)
"""

from typing import List, Optional, Tuple

from osgeo import ogr, osr
from qgis.core import Qgis

from geest.utilities import log_message


def get_h3_resolution_for_scale(analysis_scale: str) -> Optional[int]:
    """Get H3 resolution for a given analysis scale.

    Args:
        analysis_scale: The analysis scale ("regional", "national", or "local")

    Returns:
        H3 resolution integer (6 for regional), or None if not applicable
    """
    if analysis_scale == "regional":
        return 6
    return None


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
    source_srs = osr.SpatialReference()
    source_srs.ImportFromEPSG(source_epsg)

    target_srs = osr.SpatialReference()
    target_srs.ImportFromEPSG(4326)

    transform = osr.CoordinateTransformation(source_srs, target_srs)

    # Transform all four corners
    points = [
        (xmin, ymin),
        (xmax, ymin),
        (xmax, ymax),
        (xmin, ymax),
    ]

    wgs84_points = []
    for px, py in points:
        lat, lon, _ = transform.TransformPoint(px, py)
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
    source_srs = osr.SpatialReference()
    source_srs.ImportFromEPSG(4326)

    target_srs = osr.SpatialReference()
    target_srs.ImportFromEPSG(target_epsg)

    transform = osr.CoordinateTransformation(source_srs, target_srs)
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

    # Get H3 boundary in WGS84 (lat/lon)
    boundary = h3.cell_to_boundary(h3_index)

    # Transform each point to target CRS
    transformed_points = []
    for lon, lat in boundary:
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
