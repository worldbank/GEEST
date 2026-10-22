# -*- coding: utf-8 -*-
"""Regression test: _apply_grid_column_zero_fallback() must not wipe prior writes.

Several grid-first workflows (ContextualIndexScoreWorkflow, IndexScoreWorkflow,
AggregationWorkflowBase) write their whole column in one UPDATE covering every
row, before the per-area loop even starts. _apply_grid_column_zero_fallback()
is triggered later, for any area that produced zero matching study_area_grid
cells (e.g. a sliver too small to have been gridded) - and the first time it
runs per workflow instance, it used to unconditionally clear the entire
column (UPDATE study_area_grid SET col = NULL, no WHERE clause) before
filling that one area's cells with 0. For the workflows above, that clear ran
*after* their own full-column write had already succeeded, silently wiping
every other area's value - the real-world symptom was every value in
workplace_index/fac_*/dim_* ending up NULL despite the write itself
succeeding and being logged as such.

Each of those call sites now sets self._grid_column_cleared = True right
after its own successful full-column write, telling this fallback the clear
has already effectively happened. This test exercises the guard directly
against a real GeoPackage, without needing a fully-constructed workflow
instance (_apply_grid_column_zero_fallback only touches
self.gpkg_path/self.layer_id/self._grid_column_cleared).
"""
import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace

from osgeo import ogr

from geest.core.workflows.workflow_base import WorkflowBase


class TestApplyGridColumnZeroFallback(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_grid_zero_fallback_")
        self.gpkg_path = os.path.join(self.temp_dir, "study_area.gpkg")

        driver = ogr.GetDriverByName("GPKG")
        dataset = driver.CreateDataSource(self.gpkg_path)
        layer = dataset.CreateLayer("study_area_grid", geom_type=ogr.wkbPolygon)
        layer.CreateField(ogr.FieldDefn("area_name", ogr.OFTString))
        layer.CreateField(ogr.FieldDefn("test_col", ogr.OFTReal))
        layer_defn = layer.GetLayerDefn()
        # 3 cells already fully written (e.g. by write_uniform_value_to_grid)
        # for an area the per-area loop has already finished with.
        for _ in range(3):
            feature = ogr.Feature(layer_defn)
            feature.SetField("area_name", "area_a")
            feature.SetField("test_col", 7.0)
            layer.CreateFeature(feature)
        # "area_b" is the sliver: it has no rows at all, which is exactly
        # what makes rasterize_grid_column() fail and trigger this fallback.
        dataset = None

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _read_test_col_values(self):
        dataset = ogr.Open(self.gpkg_path, 0)
        layer = dataset.GetLayerByName("study_area_grid")
        values = [feature.GetField("test_col") for feature in layer]
        dataset = None
        return values

    def _fake_workflow(self, grid_column_cleared: bool) -> SimpleNamespace:
        return SimpleNamespace(
            gpkg_path=self.gpkg_path,
            layer_id="test_col",
            _grid_column_cleared=grid_column_cleared,
        )

    def test_does_not_clear_when_already_marked_cleared(self):
        fake_self = self._fake_workflow(grid_column_cleared=True)

        WorkflowBase._apply_grid_column_zero_fallback(fake_self, "area_b")

        values = self._read_test_col_values()
        self.assertTrue(
            all(v == 7.0 for v in values),
            f"area_a's values must survive a fallback for an unrelated area, got {values}",
        )
        self.assertTrue(fake_self._grid_column_cleared)

    def test_clears_on_first_call_when_not_yet_cleared(self):
        fake_self = self._fake_workflow(grid_column_cleared=False)

        WorkflowBase._apply_grid_column_zero_fallback(fake_self, "area_b")

        values = self._read_test_col_values()
        self.assertTrue(
            all(v is None for v in values),
            f"with the flag unset, the lazy clear-once-per-workflow path is expected to fire, got {values}",
        )
        self.assertTrue(fake_self._grid_column_cleared)


if __name__ == "__main__":
    unittest.main()
