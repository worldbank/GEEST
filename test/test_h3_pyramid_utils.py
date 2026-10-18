# -*- coding: utf-8 -*-
"""Unit tests for geest.core.h3_pyramid_utils.

Exercises the real H3 pyramid engine end to end (unlike
test_tree_panel_pyramid_migration.py's `_fake_h3_pyramid_utils`, which
stands in for this module to test TreePanel's own wiring in isolation).
Mirrors test_grid_pyramid_utils.py's structure/coverage for the
square-grid pyramid, but against real H3 hexagons generated with h3-py.
"""
import os
import shutil
import tempfile
import unittest

from osgeo import ogr, osr

from geest.core.grid_pyramid_utils import invalidate_pyramid, is_pyramid_fresh
from geest.core.h3_pyramid_utils import (
    compute_h3_level_resolutions,
    get_exposed_h3_levels,
    h3_effective_cell_size_m,
    has_h3_pyramid_structure,
    refresh_h3_pyramid_column,
)


def _build_h3_grid(gpkg_path, h3_resolution=9, score_fields=(), bbox_wgs84=(36.80, -1.30, 36.82, -1.28)):
    """Create a minimal H3-indexed study_area_grid with the given REAL (scored) fields.

    Cells are real H3 hexagons (h3-py v4's h3shape_to_cells) covering a
    small WGS84 bounding box, with an "h3_index" text column matching the
    field study_area_processing_task.py writes for H3-grid projects.

    Args:
        gpkg_path: Destination path for the study_area.gpkg fixture.
        h3_resolution: H3 resolution to generate cells at.
        score_fields: REAL (scored) column names to add and populate, each
            cell getting a distinct value (its 0-based index) so MAX
            aggregation across a coarser cell's children is distinguishable.
        bbox_wgs84: (min_lon, min_lat, max_lon, max_lat), kept small so the
            generated cell count stays low and tests run fast.

    Returns:
        The number of base cells created.
    """
    import h3

    driver = ogr.GetDriverByName("GPKG")
    ds = driver.CreateDataSource(gpkg_path)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    layer = ds.CreateLayer("study_area_grid", srs, geom_type=ogr.wkbPolygon)
    layer.CreateField(ogr.FieldDefn("grid_id", ogr.OFTInteger))
    h3_field = ogr.FieldDefn("h3_index", ogr.OFTString)
    h3_field.SetWidth(16)
    layer.CreateField(h3_field)
    for field in score_fields:
        layer.CreateField(ogr.FieldDefn(field, ogr.OFTReal))

    min_lon, min_lat, max_lon, max_lat = bbox_wgs84
    shape = h3.LatLngPoly([(min_lat, min_lon), (min_lat, max_lon), (max_lat, max_lon), (max_lat, min_lon)])
    cells = list(h3.h3shape_to_cells(shape, h3_resolution))
    if not cells:
        raise RuntimeError("No H3 cells generated for the test bbox - widen bbox_wgs84.")

    for grid_id, cell in enumerate(cells):
        boundary = h3.cell_to_boundary(cell)  # [(lat, lon), ...]
        ring = ogr.Geometry(ogr.wkbLinearRing)
        for lat, lon in boundary:
            ring.AddPoint(lon, lat)
        ring.CloseRings()
        polygon = ogr.Geometry(ogr.wkbPolygon)
        polygon.AddGeometry(ring)

        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField("grid_id", grid_id)
        feature.SetField("h3_index", cell)
        for field in score_fields:
            feature.SetField(field, float(grid_id))
        feature.SetGeometry(polygon)
        layer.CreateFeature(feature)
        feature = None
    ds = None
    return len(cells)


class TestComputeH3LevelResolutions(unittest.TestCase):
    """Tests for compute_h3_level_resolutions()."""

    def test_steps_down_by_one_each_level(self):
        self.assertEqual(compute_h3_level_resolutions(9), [9, 8, 7, 6, 5])

    def test_clamps_at_zero(self):
        self.assertEqual(compute_h3_level_resolutions(2), [2, 1, 0, 0, 0])

    def test_custom_step_count(self):
        self.assertEqual(compute_h3_level_resolutions(9, steps=2), [9, 8, 7])


class TestH3EffectiveCellSizeM(unittest.TestCase):
    """Tests for h3_effective_cell_size_m()."""

    def test_coarser_resolution_is_larger(self):
        self.assertGreater(h3_effective_cell_size_m(5), h3_effective_cell_size_m(9))

    def test_positive_for_every_valid_resolution(self):
        for resolution in range(16):
            self.assertGreater(h3_effective_cell_size_m(resolution), 0)


class TestH3PyramidEndToEnd(unittest.TestCase):
    """End-to-end tests against a real H3 grid GeoPackage."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_h3_pyramid_")
        self.gpkg_path = os.path.join(self.temp_dir, "study_area.gpkg")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_has_structure_false_before_build(self):
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=("jobs",))
        self.assertFalse(has_h3_pyramid_structure(self.gpkg_path, "jobs", 9))

    def test_has_structure_none_resolution_returns_false(self):
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=("jobs",))
        self.assertFalse(has_h3_pyramid_structure(self.gpkg_path, "jobs", None))

    def test_refresh_builds_structure_and_marks_fresh(self):
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=("jobs",))

        self.assertTrue(refresh_h3_pyramid_column(self.gpkg_path, "jobs", 9))
        self.assertTrue(has_h3_pyramid_structure(self.gpkg_path, "jobs", 9))
        self.assertTrue(is_pyramid_fresh(self.gpkg_path, "jobs"))

    def test_refresh_missing_column_fails_cleanly(self):
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=())
        self.assertFalse(refresh_h3_pyramid_column(self.gpkg_path, "nonexistent", 9))

    def test_refresh_none_resolution_fails_cleanly(self):
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=("jobs",))
        self.assertFalse(refresh_h3_pyramid_column(self.gpkg_path, "jobs", None))

    def test_refresh_missing_gpkg_fails_cleanly(self):
        self.assertFalse(refresh_h3_pyramid_column(os.path.join(self.temp_dir, "nope.gpkg"), "jobs", 9))

    def test_aggregated_value_is_max_of_children(self):
        import h3

        n_cells = _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=("jobs",))
        self.assertGreater(n_cells, 1, "Test bbox must yield more than one base H3 cell to exercise aggregation.")

        self.assertTrue(refresh_h3_pyramid_column(self.gpkg_path, "jobs", 9))

        # Independently recompute the expected MAX-per-parent at resolution 8
        # straight from the base grid, then compare against what got built.
        ds = ogr.Open(self.gpkg_path, 0)
        base_layer = ds.GetLayerByName("study_area_grid")
        expected = {}
        for feature in base_layer:
            parent = h3.cell_to_parent(feature.GetField("h3_index"), 8)
            value = feature.GetField("jobs")
            if value is None:
                continue
            expected[parent] = max(expected.get(parent, value), value)

        level_layer = ds.GetLayerByName("study_area_grid_h3_res8")
        self.assertIsNotNone(level_layer, "Expected level table study_area_grid_h3_res8 to exist.")
        actual = {}
        for feature in level_layer:
            actual[feature.GetField("h3_index")] = feature.GetField("jobs")
        ds = None

        self.assertEqual(actual, expected)

    def test_refresh_is_idempotent(self):
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=("jobs",))
        self.assertTrue(refresh_h3_pyramid_column(self.gpkg_path, "jobs", 9))
        self.assertTrue(refresh_h3_pyramid_column(self.gpkg_path, "jobs", 9))
        self.assertTrue(has_h3_pyramid_structure(self.gpkg_path, "jobs", 9))

    def test_refresh_reverts_to_null_when_children_become_null(self):
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=("jobs",))
        self.assertTrue(refresh_h3_pyramid_column(self.gpkg_path, "jobs", 9))

        ds = ogr.Open(self.gpkg_path, 1)
        base_layer = ds.GetLayerByName("study_area_grid")
        for feature in base_layer:
            feature.SetFieldNull("jobs")
            base_layer.SetFeature(feature)
        ds = None

        self.assertTrue(refresh_h3_pyramid_column(self.gpkg_path, "jobs", 9))

        ds = ogr.Open(self.gpkg_path, 0)
        level_layer = ds.GetLayerByName("study_area_grid_h3_res8")
        values = [feature.GetField("jobs") for feature in level_layer]
        ds = None
        self.assertTrue(all(value is None for value in values))

    def test_invalidate_pyramid_clears_freshness_not_structure(self):
        # Shared bookkeeping (grid_pyramid_utils.invalidate_pyramid()) must
        # work for the H3 path too - see the matching TreePanel regression
        # test in test_tree_panel_pyramid_migration.py.
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=("jobs",))
        self.assertTrue(refresh_h3_pyramid_column(self.gpkg_path, "jobs", 9))

        invalidate_pyramid(self.gpkg_path, "jobs")

        self.assertFalse(is_pyramid_fresh(self.gpkg_path, "jobs"))
        self.assertTrue(has_h3_pyramid_structure(self.gpkg_path, "jobs", 9))


class TestGetExposedH3Levels(unittest.TestCase):
    """Tests for get_exposed_h3_levels()."""

    def test_base_level_has_no_table(self):
        levels = get_exposed_h3_levels("unused.gpkg", "jobs", 9)
        self.assertEqual(levels[0], (9, None))

    def test_returns_three_levels_when_resolution_is_high_enough(self):
        levels = get_exposed_h3_levels("unused.gpkg", "jobs", 9)
        self.assertEqual([res for res, _table in levels], [9, 7, 5])
        self.assertEqual([table for _res, table in levels][1:], ["study_area_grid_h3_res7", "study_area_grid_h3_res5"])

    def test_deduplicates_once_resolution_clamps_to_zero(self):
        levels = get_exposed_h3_levels("unused.gpkg", "jobs", 1)
        # resolution 1 -> steps 0,2,4 give [1, max(0,-1)=0, max(0,-3)=0];
        # the two clamped-to-0 levels must collapse into a single entry.
        self.assertEqual(levels, [(1, None), (0, "study_area_grid_h3_res0")])

    def test_none_resolution_returns_empty_list(self):
        self.assertEqual(get_exposed_h3_levels("unused.gpkg", "jobs", None), [])


if __name__ == "__main__":
    unittest.main()
