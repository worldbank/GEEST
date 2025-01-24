#!/usr/bin/env python
"""
Test suite for grid_from_bbox.py.
This test suite uses pytest to validate the functionality of the grid generation utility.

Version Added: 2025-01-24
"""

import pytest
from grid_from_bbox import create_grid_from_bbox
from qgis.core import QgsRectangle, QgsCoordinateReferenceSystem


@pytest.fixture
def example_bbox() -> QgsRectangle:
    """Fixture for a standard bounding box."""
    return QgsRectangle(0, 0, 100, 100)


@pytest.fixture
def example_crs() -> QgsCoordinateReferenceSystem:
    """Fixture for the Coordinate Reference System."""
    return QgsCoordinateReferenceSystem("EPSG:4326")


@pytest.mark.parametrize(
    "cell_width, cell_height",
    [
        (10, 10),
        (5, 5),
        (20, 20),
    ],
)
def test_create_grid_from_bbox_standard(
    example_bbox, example_crs, cell_width, cell_height
):
    """Test grid generation with standard parameters."""
    grid = create_grid_from_bbox(
        bbox=example_bbox,
        cell_width=cell_width,
        cell_height=cell_height,
        crs=example_crs,
    )

    assert grid is not None, "Grid creation failed to return a valid result."
    assert grid.isValid(), "Generated grid is not valid."
    assert grid.featureCount() > 0, "Grid should contain at least one feature."


def test_create_grid_from_bbox_edge_cases(example_crs):
    """Test edge cases for bounding boxes."""
    # Zero-area bbox
    zero_area_bbox = QgsRectangle(10, 10, 10, 10)
    grid = create_grid_from_bbox(
        bbox=zero_area_bbox, cell_width=5, cell_height=5, crs=example_crs
    )
    assert grid.featureCount() == 0, "Grid for zero-area bbox should have no features."

    # Inverted bbox
    inverted_bbox = QgsRectangle(100, 100, 0, 0)
    with pytest.raises(ValueError, match="Invalid bounding box dimensions"):
        create_grid_from_bbox(
            bbox=inverted_bbox, cell_width=10, cell_height=10, crs=example_crs
        )


def test_invalid_cell_dimensions(example_bbox, example_crs):
    """Test invalid cell dimensions."""
    # Negative cell dimensions
    with pytest.raises(ValueError, match="Cell dimensions must be positive"):
        create_grid_from_bbox(
            bbox=example_bbox, cell_width=-10, cell_height=10, crs=example_crs
        )

    with pytest.raises(ValueError, match="Cell dimensions must be positive"):
        create_grid_from_bbox(
            bbox=example_bbox, cell_width=10, cell_height=-10, crs=example_crs
        )

    # Zero cell dimensions
    with pytest.raises(ValueError, match="Cell dimensions must be positive"):
        create_grid_from_bbox(
            bbox=example_bbox, cell_width=0, cell_height=10, crs=example_crs
        )


def test_large_bbox(example_crs):
    """Test handling of a large bounding box."""
    large_bbox = QgsRectangle(-180, -90, 180, 90)
    grid = create_grid_from_bbox(
        bbox=large_bbox, cell_width=1, cell_height=1, crs=example_crs
    )

    assert (
        grid.featureCount() > 10000
    ), "Large bounding box should generate a substantial number of features."


def test_crs_mismatch():
    """Test behavior when CRS is mismatched or invalid."""
    bbox = QgsRectangle(0, 0, 100, 100)
    invalid_crs = QgsCoordinateReferenceSystem()

    with pytest.raises(ValueError, match="Invalid CRS provided"):
        create_grid_from_bbox(bbox=bbox, cell_width=10, cell_height=10, crs=invalid_crs)

    mismatched_crs = QgsCoordinateReferenceSystem("EPSG:3857")
    result = create_grid_from_bbox(
        bbox=bbox, cell_width=10, cell_height=10, crs=mismatched_crs
    )

    assert result.isValid(), "Grid generation should handle CRS mismatches gracefully."
