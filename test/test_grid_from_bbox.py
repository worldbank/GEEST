#!/usr/bin/env python
"""
Test suite for grid_from_bbox.py.

Version Changed: 2025-01-24
"""

from geest.core.tasks import GridFromBbox
from qgis.core import QgsRectangle, QgsCoordinateReferenceSystem


def example_bbox():
    """Returns a standard bounding box."""
    return QgsRectangle(0, 0, 100, 100)


def example_crs():
    """Returns the Coordinate Reference System."""
    return QgsCoordinateReferenceSystem("EPSG:4326")


def test_create_grid_from_bbox_standard():
    """Test grid generation with standard parameters."""
    bbox = example_bbox()
    crs = example_crs()

    for cell_width, cell_height in [(10, 10), (5, 5), (20, 20)]:
        grid = GridFromBbox(
            bbox=bbox, cell_width=cell_width, cell_height=cell_height, crs=crs
        )

        assert grid is not None, "Grid creation failed to return a valid result."
        assert grid.isValid(), "Generated grid is not valid."
        assert grid.featureCount() > 0, "Grid should contain at least one feature."


def test_create_grid_from_bbox_edge_cases():
    """Test edge cases for bounding boxes."""
    crs = example_crs()

    # Zero-area bbox
    zero_area_bbox = QgsRectangle(10, 10, 10, 10)
    grid = GridFromBbox(bbox=zero_area_bbox, cell_width=5, cell_height=5, crs=crs)
    assert grid.featureCount() == 0, "Grid for zero-area bbox should have no features."

    # Inverted bbox
    inverted_bbox = QgsRectangle(100, 100, 0, 0)
    try:
        GridFromBbox(bbox=inverted_bbox, cell_width=10, cell_height=10, crs=crs)
        assert False, "Expected ValueError for inverted bbox, but none was raised."
    except ValueError as e:
        assert "Invalid bounding box dimensions" in str(
            e
        ), f"Unexpected error message: {e}"


def test_invalid_cell_dimensions():
    """Test invalid cell dimensions."""
    bbox = example_bbox()
    crs = example_crs()

    # Negative cell dimensions
    try:
        GridFromBbox(bbox=bbox, cell_width=-10, cell_height=10, crs=crs)
        assert (
            False
        ), "Expected ValueError for negative cell width, but none was raised."
    except ValueError as e:
        assert "Cell dimensions must be positive" in str(
            e
        ), f"Unexpected error message: {e}"

    try:
        GridFromBbox(bbox=bbox, cell_width=10, cell_height=-10, crs=crs)
        assert (
            False
        ), "Expected ValueError for negative cell height, but none was raised."
    except ValueError as e:
        assert "Cell dimensions must be positive" in str(
            e
        ), f"Unexpected error message: {e}"

    # Zero cell dimensions
    try:
        GridFromBbox(bbox=bbox, cell_width=0, cell_height=10, crs=crs)
        assert False, "Expected ValueError for zero cell width, but none was raised."
    except ValueError as e:
        assert "Cell dimensions must be positive" in str(
            e
        ), f"Unexpected error message: {e}"


def test_large_bbox():
    """Test handling of a large bounding box."""
    crs = example_crs()
    large_bbox = QgsRectangle(-180, -90, 180, 90)
    grid = GridFromBbox(bbox=large_bbox, cell_width=1, cell_height=1, crs=crs)

    assert (
        grid.featureCount() > 10000
    ), "Large bounding box should generate a substantial number of features."


def test_crs_mismatch():
    """Test behavior when CRS is mismatched or invalid."""
    bbox = QgsRectangle(0, 0, 100, 100)

    invalid_crs = QgsCoordinateReferenceSystem()
    try:
        GridFromBbox(bbox=bbox, cell_width=10, cell_height=10, crs=invalid_crs)
        assert False, "Expected ValueError for invalid CRS, but none was raised."
    except ValueError as e:
        assert "Invalid CRS provided" in str(e), f"Unexpected error message: {e}"

    mismatched_crs = QgsCoordinateReferenceSystem("EPSG:3857")
    result = GridFromBbox(bbox=bbox, cell_width=10, cell_height=10, crs=mismatched_crs)

    assert result.isValid(), "Grid generation should handle CRS mismatches gracefully."


def run_tests():
    """Runs all tests sequentially."""
    test_create_grid_from_bbox_standard()
    print("test_create_grid_from_bbox_standard passed.")

    test_create_grid_from_bbox_edge_cases()
    print("test_create_grid_from_bbox_edge_cases passed.")

    test_invalid_cell_dimensions()
    print("test_invalid_cell_dimensions passed.")

    test_large_bbox()
    print("test_large_bbox passed.")

    test_crs_mismatch()
    print("test_crs_mismatch passed.")


if __name__ == "__main__":
    run_tests()
