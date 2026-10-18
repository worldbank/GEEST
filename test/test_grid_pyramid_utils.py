# -*- coding: utf-8 -*-
"""Unit tests for the multi-resolution vector grid pyramid utilities.

Schema under test: ONE wide table per pyramid level (study_area_grid_200,
study_area_grid_400, ...), mirroring study_area_grid itself - many score
columns share the same table at each level, added lazily like the base
grid - never one table per (level, column) pair.
"""

import os
import shutil
import tempfile
import unittest

from osgeo import ogr, osr
from qgis.core import QgsVectorLayer

from geest.core.grid_pyramid_utils import (
    build_pyramid_scaffold,
    compute_level_cell_sizes,
    get_exposed_levels,
    invalidate_pyramid,
    is_pyramid_fresh,
    refresh_pyramid_column,
    scale_denominator_for_cell_size,
)


def _build_grid(gpkg_path, cell_size=100.0, rows=4, cols=4, area_name="area1", hole=None):
    """Create a study_area_grid layer with a 'score' column for testing.

    Args:
        hole: Optional set of (row, col) pairs to leave NULL.
    """
    driver = ogr.GetDriverByName("GPKG")
    ds = driver.CreateDataSource(gpkg_path)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(32626)
    layer = ds.CreateLayer("study_area_grid", srs, geom_type=ogr.wkbPolygon)
    layer.CreateField(ogr.FieldDefn("grid_id", ogr.OFTInteger))
    layer.CreateField(ogr.FieldDefn("area_name", ogr.OFTString))
    layer.CreateField(ogr.FieldDefn("score", ogr.OFTReal))

    hole = hole or set()
    grid_id = 0
    for row in range(rows):
        for col in range(cols):
            xmin, ymin = col * cell_size, row * cell_size
            wkt = (
                f"POLYGON(({xmin} {ymin},{xmin + cell_size} {ymin},"
                f"{xmin + cell_size} {ymin + cell_size},{xmin} {ymin + cell_size},{xmin} {ymin}))"
            )
            feature = ogr.Feature(layer.GetLayerDefn())
            feature.SetField("grid_id", grid_id)
            feature.SetField("area_name", area_name)
            if (row, col) not in hole:
                feature.SetField("score", float(row + col))
            feature.SetGeometry(ogr.CreateGeometryFromWkt(wkt))
            layer.CreateFeature(feature)
            feature = None
            grid_id += 1
    ds = None


def _table_names(gpkg_path):
    ds = ogr.Open(gpkg_path, 0)
    names = {ds.GetLayer(i).GetName() for i in range(ds.GetLayerCount())}
    ds = None
    return names


class TestComputeLevelCellSizes(unittest.TestCase):
    """Tests for compute_level_cell_sizes()."""

    def test_doubles_each_level(self):
        self.assertEqual(compute_level_cell_sizes(100.0), [100.0, 200.0, 400.0, 800.0, 1600.0])

    def test_non_default_base(self):
        self.assertEqual(compute_level_cell_sizes(30.0, doublings=2), [30.0, 60.0, 120.0])


class TestScaleDenominatorForCellSize(unittest.TestCase):
    """Tests for scale_denominator_for_cell_size()."""

    def test_scales_linearly_with_cell_size(self):
        base = scale_denominator_for_cell_size(100.0)
        self.assertAlmostEqual(scale_denominator_for_cell_size(400.0), base * 4)
        self.assertAlmostEqual(scale_denominator_for_cell_size(1600.0), base * 16)


class TestBuildPyramidScaffold(unittest.TestCase):
    """Tests for build_pyramid_scaffold() - the geometry-only, column-agnostic build.

    This is what StudyAreaProcessingTask calls right after writing the base
    grid, so every level table already exists before any indicator has
    ever run - see the matching call site in study_area_processing_task.py.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_grid_pyramid_scaffold_")
        self.gpkg_path = os.path.join(self.temp_dir, "study_area.gpkg")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_builds_every_level_table_with_no_score_columns(self):
        _build_grid(self.gpkg_path, rows=16, cols=16)

        self.assertTrue(build_pyramid_scaffold(self.gpkg_path, 100.0))

        tables = _table_names(self.gpkg_path)
        self.assertEqual(
            tables,
            {
                "study_area_grid",
                "study_area_grid_200",
                "study_area_grid_400",
                "study_area_grid_800",
                "study_area_grid_1600",
            },
        )
        ds = ogr.Open(self.gpkg_path, 0)
        level_layer = ds.GetLayerByName("study_area_grid_200")
        self.assertGreater(level_layer.GetFeatureCount(), 0)
        layer_defn = level_layer.GetLayerDefn()
        field_names = {layer_defn.GetFieldDefn(i).GetName().lower() for i in range(layer_defn.GetFieldCount())}
        self.assertEqual(field_names, {"row_index", "col_index"})
        ds = None

    def test_a_later_refresh_for_a_real_column_does_not_duplicate_rows(self):
        _build_grid(self.gpkg_path, rows=16, cols=16)
        self.assertTrue(build_pyramid_scaffold(self.gpkg_path, 100.0))

        ds = ogr.Open(self.gpkg_path, 0)
        scaffold_count = ds.GetLayerByName("study_area_grid_200").GetFeatureCount()
        ds = None

        self.assertTrue(refresh_pyramid_column(self.gpkg_path, "score", 100.0))

        ds = ogr.Open(self.gpkg_path, 0)
        after_refresh_count = ds.GetLayerByName("study_area_grid_200").GetFeatureCount()
        ds = None
        self.assertEqual(scaffold_count, after_refresh_count)


class TestRefreshPyramidColumn(unittest.TestCase):
    """Tests for refresh_pyramid_column() and its supporting functions."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_grid_pyramid_")
        self.gpkg_path = os.path.join(self.temp_dir, "study_area.gpkg")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _level_layer(self, cell_size, table_name, filter_column=None):
        uri = f"{self.gpkg_path}|layername={table_name or 'study_area_grid'}"
        layer = QgsVectorLayer(uri, "x", "ogr")
        if filter_column:
            layer.setSubsetString(f'"{filter_column}" IS NOT NULL')
        return layer

    def test_is_pyramid_fresh_false_before_build(self):
        _build_grid(self.gpkg_path, rows=4, cols=4)
        self.assertFalse(is_pyramid_fresh(self.gpkg_path, "score"))

    def test_one_table_per_level_not_per_column(self):
        # The whole point of this schema: N columns share the SAME level
        # tables, never N tables.
        _build_grid(self.gpkg_path, rows=16, cols=16)
        ds = ogr.Open(self.gpkg_path, 1)
        ds.ExecuteSQL("ALTER TABLE study_area_grid ADD COLUMN other_score REAL")
        ds.ExecuteSQL('UPDATE study_area_grid SET other_score = "score" * 2')
        ds = None

        self.assertTrue(refresh_pyramid_column(self.gpkg_path, "score", 100.0))
        self.assertTrue(refresh_pyramid_column(self.gpkg_path, "other_score", 100.0))

        tables = _table_names(self.gpkg_path)
        self.assertEqual(
            tables,
            {
                "pyr_meta",
                "study_area_grid",
                "study_area_grid_200",
                "study_area_grid_400",
                "study_area_grid_800",
                "study_area_grid_1600",
            },
        )

        mid_layer = self._level_layer(400.0, "study_area_grid_400")
        field_names = {f.name() for f in mid_layer.fields()}
        self.assertIn("score", field_names)
        self.assertIn("other_score", field_names)

    def test_level_tables_mirror_every_base_column_even_if_never_refreshed(self):
        # Each level must be a complete, scaled mirror of the base grid's
        # current column set - not a sparse table that only grows the
        # columns someone happened to explicitly refresh_pyramid_column().
        # A column whose indicator hasn't run yet is NULL on both the base
        # grid and every level, exactly the same as a column that HAS run.
        _build_grid(self.gpkg_path, rows=16, cols=16)
        ds = ogr.Open(self.gpkg_path, 1)
        # never_refreshed is added to the base grid but refresh_pyramid_column
        # is deliberately never called for it below.
        ds.ExecuteSQL("ALTER TABLE study_area_grid ADD COLUMN never_refreshed REAL")
        ds = None

        self.assertTrue(refresh_pyramid_column(self.gpkg_path, "score", 100.0))

        ds = ogr.Open(self.gpkg_path, 0)
        for table_name in (
            "study_area_grid_200",
            "study_area_grid_400",
            "study_area_grid_800",
            "study_area_grid_1600",
        ):
            layer = ds.GetLayer(table_name)
            layer_defn = layer.GetLayerDefn()
            field_names = {layer_defn.GetFieldDefn(i).GetName() for i in range(layer_defn.GetFieldCount())}
            self.assertIn(
                "never_refreshed",
                field_names,
                f"{table_name} must mirror every base-grid score column, including ones never explicitly refreshed",
            )
        ds = None

    def test_refresh_builds_correct_max_scores(self):
        _build_grid(self.gpkg_path, rows=16, cols=16)
        self.assertTrue(refresh_pyramid_column(self.gpkg_path, "score", 100.0))
        self.assertTrue(is_pyramid_fresh(self.gpkg_path, "score"))

        levels = get_exposed_levels(self.gpkg_path, "score", 100.0)
        # Every built level is exposed, not a curated subset.
        self.assertEqual([cs for cs, _ in levels], [100.0, 200.0, 400.0, 800.0, 1600.0])
        tables_by_size = dict(levels)

        # Base level still goes through study_area_grid itself.
        self.assertIsNone(tables_by_size[100.0])

        # Mid level (400m) takes the max over a 4x4 block of base cells -> 16 rows total.
        mid_layer = self._level_layer(400.0, tables_by_size[400.0])
        self.assertTrue(mid_layer.isValid())
        self.assertEqual(mid_layer.featureCount(), 16)
        values_by_cell = {(f["row_index"], f["col_index"]): f["score"] for f in mid_layer.getFeatures()}
        # Block (0,0) covers base rows/cols 0-3; max of row+col over that block.
        expected = max(r + c for r in range(4) for c in range(4))
        self.assertAlmostEqual(values_by_cell[(0, 0)], expected)

        # Coarse level (1600m) collapses the whole 16x16 grid to one row.
        coarse_layer = self._level_layer(1600.0, tables_by_size[1600.0])
        self.assertTrue(coarse_layer.isValid())
        self.assertEqual(coarse_layer.featureCount(), 1)
        overall_expected = max(r + c for r in range(16) for c in range(16))
        self.assertAlmostEqual(next(coarse_layer.getFeatures())["score"], overall_expected)

    def test_partial_children_max_ignores_null(self):
        # A 2x2 hole (4 NULL base cells) inside a 4x4 block that feeds one
        # 400m cell: that cell must take the max of only the 12 remaining
        # children, not treat the hole as zero or propagate NULL. The hole
        # covers the block's highest-value corner, so the max necessarily
        # shifts if (and only if) NULLs are correctly excluded.
        _build_grid(self.gpkg_path, rows=16, cols=16, hole={(3, 3), (3, 2), (2, 3), (2, 2)})
        self.assertTrue(refresh_pyramid_column(self.gpkg_path, "score", 100.0))

        levels = get_exposed_levels(self.gpkg_path, "score", 100.0)
        tables_by_size = dict(levels)
        mid_layer = self._level_layer(400.0, tables_by_size[400.0])
        values_by_cell = {(f["row_index"], f["col_index"]): f["score"] for f in mid_layer.getFeatures()}

        remaining = [r + c for r in range(4) for c in range(4) if (r, c) not in {(3, 3), (3, 2), (2, 3), (2, 2)}]
        self.assertAlmostEqual(values_by_cell[(0, 0)], max(remaining))

    def test_rebuild_reverts_stale_cells_to_null_not_deleted(self):
        # When children become entirely NULL since the last build, the
        # coarse cell's VALUE must revert to NULL - but the ROW (geometry)
        # persists, since it reflects cell existence, not any one column.
        _build_grid(self.gpkg_path, rows=4, cols=4)
        self.assertTrue(refresh_pyramid_column(self.gpkg_path, "score", 100.0))
        levels = get_exposed_levels(self.gpkg_path, "score", 100.0)
        coarse_table = dict(levels)[1600.0]
        coarse_layer = self._level_layer(1600.0, coarse_table)
        self.assertEqual(coarse_layer.featureCount(), 1)

        ds = ogr.Open(self.gpkg_path, 1)
        ds.ExecuteSQL('UPDATE study_area_grid SET "score" = NULL')
        ds = None
        invalidate_pyramid(self.gpkg_path, "score")

        self.assertTrue(refresh_pyramid_column(self.gpkg_path, "score", 100.0))
        coarse_layer_after_filtered = self._level_layer(1600.0, coarse_table, filter_column="score")
        self.assertEqual(coarse_layer_after_filtered.featureCount(), 0)
        coarse_layer_after_unfiltered = self._level_layer(1600.0, coarse_table)
        self.assertEqual(coarse_layer_after_unfiltered.featureCount(), 1)

    def test_rerun_is_idempotent_no_duplicate_rows(self):
        _build_grid(self.gpkg_path, rows=16, cols=16)
        self.assertTrue(refresh_pyramid_column(self.gpkg_path, "score", 100.0))
        self.assertTrue(refresh_pyramid_column(self.gpkg_path, "score", 100.0))

        levels = get_exposed_levels(self.gpkg_path, "score", 100.0)
        for cell_size, table in levels[1:]:
            layer = self._level_layer(cell_size, table)
            expected = (1600 // int(cell_size)) ** 2
            self.assertEqual(layer.featureCount(), expected)

    def test_missing_column_fails_cleanly_instead_of_fabricating_values(self):
        # A column that does not exist on study_area_grid must not silently
        # build a plausible pyramid from garbage (SQLite's double-quoted-
        # identifier fallback would otherwise evaluate MAX("missing") as the
        # literal string "missing" for every row instead of raising).
        _build_grid(self.gpkg_path, rows=4, cols=4)
        self.assertFalse(refresh_pyramid_column(self.gpkg_path, "does_not_exist", 100.0))
        self.assertFalse(is_pyramid_fresh(self.gpkg_path, "does_not_exist"))

    def test_invalid_identifier_characters_fail_cleanly(self):
        # Indicator/factor ids come straight from a spreadsheet column with
        # no slugify, so a name with characters _quote_sql_identifier
        # rejects must return False, not raise an uncaught ValueError.
        _build_grid(self.gpkg_path, rows=4, cols=4)
        self.assertFalse(refresh_pyramid_column(self.gpkg_path, "women's safety", 100.0))

    def test_all_null_column_builds_rows_with_null_value(self):
        # Uses the project's own WAL-mode write helper (not a raw ogr.Open)
        # for this ALTER TABLE: switching journal modes between a plain
        # ogr.Open and _open_gpkg_for_write's WAL mode immediately
        # afterwards is a real race in this GDAL/SQLite combination, not
        # something specific to the pyramid logic under test here.
        from geest.core.grid_column_utils import _execute_sql_with_retry, _open_gpkg_for_write

        _build_grid(self.gpkg_path, rows=4, cols=4)
        ds = _open_gpkg_for_write(self.gpkg_path)
        _execute_sql_with_retry(ds, "ALTER TABLE study_area_grid ADD COLUMN empty_col REAL")
        ds = None

        self.assertTrue(refresh_pyramid_column(self.gpkg_path, "empty_col", 100.0))
        levels = get_exposed_levels(self.gpkg_path, "empty_col", 100.0)
        for cell_size, table in levels[1:]:
            layer = self._level_layer(cell_size, table, filter_column="empty_col")
            self.assertTrue(layer.isValid())
            self.assertEqual(layer.featureCount(), 0)

    def test_invalidate_then_is_pyramid_fresh_false(self):
        _build_grid(self.gpkg_path, rows=4, cols=4)
        self.assertTrue(refresh_pyramid_column(self.gpkg_path, "score", 100.0))
        self.assertTrue(is_pyramid_fresh(self.gpkg_path, "score"))
        invalidate_pyramid(self.gpkg_path, "score")
        self.assertFalse(is_pyramid_fresh(self.gpkg_path, "score"))

    def test_sliver_area_with_fewer_cells_than_one_block(self):
        # A single-cell "sliver" study area: deeper levels legitimately end
        # up with exactly one row, but nothing should crash.
        _build_grid(self.gpkg_path, rows=1, cols=1)
        self.assertTrue(refresh_pyramid_column(self.gpkg_path, "score", 100.0))
        levels = get_exposed_levels(self.gpkg_path, "score", 100.0)
        mid_layer = self._level_layer(400.0, dict(levels)[400.0])
        self.assertTrue(mid_layer.isValid())
        self.assertEqual(mid_layer.featureCount(), 1)
        self.assertAlmostEqual(next(mid_layer.getFeatures())["score"], 0.0)

    def test_archipelago_two_areas_share_a_coarse_cell(self):
        # Two areas placed so their cells fall in the same row/col bucket at
        # a coarser level must blend spatially, not drop either area.
        driver = ogr.GetDriverByName("GPKG")
        ds = driver.CreateDataSource(self.gpkg_path)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(32626)
        layer = ds.CreateLayer("study_area_grid", srs, geom_type=ogr.wkbPolygon)
        layer.CreateField(ogr.FieldDefn("grid_id", ogr.OFTInteger))
        layer.CreateField(ogr.FieldDefn("area_name", ogr.OFTString))
        layer.CreateField(ogr.FieldDefn("score", ogr.OFTReal))
        cells = [
            (0, 0, "area_a", 10.0),
            (0, 1, "area_a", 20.0),
            (1, 0, "area_b", 30.0),
            (1, 1, "area_b", 40.0),
        ]
        for grid_id, (row, col, area, value) in enumerate(cells):
            xmin, ymin = col * 100.0, row * 100.0
            wkt = (
                f"POLYGON(({xmin} {ymin},{xmin + 100} {ymin},{xmin + 100} {ymin + 100},"
                f"{xmin} {ymin + 100},{xmin} {ymin}))"
            )
            feature = ogr.Feature(layer.GetLayerDefn())
            feature.SetField("grid_id", grid_id)
            feature.SetField("area_name", area)
            feature.SetField("score", value)
            feature.SetGeometry(ogr.CreateGeometryFromWkt(wkt))
            layer.CreateFeature(feature)
            feature = None
        ds = None

        self.assertTrue(refresh_pyramid_column(self.gpkg_path, "score", 100.0))
        levels = get_exposed_levels(self.gpkg_path, "score", 100.0)
        mid_layer = self._level_layer(400.0, dict(levels)[400.0])
        self.assertEqual(mid_layer.featureCount(), 1)
        self.assertAlmostEqual(next(mid_layer.getFeatures())["score"], 40.0)  # max of all 4, both areas


if __name__ == "__main__":
    unittest.main()
