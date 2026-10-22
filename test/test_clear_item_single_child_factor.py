# -*- coding: utf-8 -*-
"""Unit tests for TreePanel.clear_item()'s handling of a single-child factor.

JsonTreeModel.data() hides a factor with exactly one child indicator from
the tree view, promoting that indicator's row to display in the factor's
place (labeled with the factor's name) - see treeview.py's
toggle_single_child_factors_visibility()/data(). So the one row a user sees
and right-clicks ("Workplace Discrimination") really represents TWO tree
items (the factor and its indicator) sharing a single visible row;
index.internalPointer() for that row returns the INDICATOR, not the factor.

Before this fix, clear_item() only cleared whichever item was actually
selected - so clearing that fused row cleared the indicator's own grid
column/outputs but left the factor's own column/rasters/layer completely
untouched, even though the user believed the whole "Workplace
Discrimination" row had been cleared (worldbank/GeoE3 field report,
2026-10-22: dimension cleared correctly, but all three single-indicator
factors kept their stale "Completed" column values after being "cleared").
"""
import os
import shutil
import tempfile
import types
import unittest
from unittest.mock import MagicMock

from osgeo import ogr

from geest.core import JsonTreeItem
from geest.gui.panels.tree_panel import TreePanel

ogr.UseExceptions()


def build_tree(hide_factor):
    dimension = JsonTreeItem(["Contextual", "Configured", 1.0, {"id": "contextual"}], role="dimension", parent=None)
    factor = JsonTreeItem(
        ["Workplace Discrimination", "Configured", 1.0, {"id": "workplace_discrimination"}],
        role="factor",
        parent=dimension,
    )
    indicator = JsonTreeItem(
        ["Workplace Index", "Configured", 1.0, {"id": "Workplace_Index"}],
        role="indicator",
        parent=factor,
    )
    factor.appendChild(indicator)
    dimension.appendChild(factor)
    factor.set_visibility(not hide_factor)
    return dimension, factor, indicator


class TestClearItemSingleChildFactor(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_clear_item_single_child_")
        self.gpkg_path = os.path.join(self.temp_dir, "study_area", "study_area.gpkg")
        os.makedirs(os.path.dirname(self.gpkg_path))
        driver = ogr.GetDriverByName("GPKG")
        dataset = driver.CreateDataSource(self.gpkg_path)
        layer = dataset.CreateLayer("study_area_grid", geom_type=ogr.wkbPolygon)
        layer.CreateField(ogr.FieldDefn("fac_workplace_discrimination", ogr.OFTReal))
        layer.CreateField(ogr.FieldDefn("workplace_index", ogr.OFTReal))
        layer_defn = layer.GetLayerDefn()
        for _ in range(3):
            feature = ogr.Feature(layer_defn)
            feature.SetField("fac_workplace_discrimination", 2.0)
            feature.SetField("workplace_index", 2.0)
            layer.CreateFeature(feature)
        dataset = None

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _read_column(self, column_name):
        dataset = ogr.Open(self.gpkg_path, 0)
        layer = dataset.GetLayerByName("study_area_grid")
        values = [feature.GetField(column_name) for feature in layer]
        dataset = None
        return values

    def _clear_via_panel(self, selected_item):
        panel = MagicMock()
        panel.working_directory = self.temp_dir
        panel.save_json_to_working_directory = MagicMock()
        # clear_item() calls self._clear_single_item_outputs(...) - on a
        # bare MagicMock that resolves to an auto-generated no-op mock, not
        # the real method. Bind the real unbound method so it actually runs.
        panel._clear_single_item_outputs = types.MethodType(TreePanel._clear_single_item_outputs, panel)
        index = MagicMock()
        index.internalPointer.return_value = selected_item
        panel.treeView.currentIndex.return_value = index
        TreePanel.clear_item(panel)

    def test_clearing_the_fused_row_clears_both_factor_and_indicator(self):
        _dimension, factor, indicator = build_tree(hide_factor=True)
        self.assertFalse(factor.is_visible())

        # The row the user actually clicks resolves to the indicator -
        # exactly what JsonTreeModel.data()/index.internalPointer() return
        # for that visible row.
        self._clear_via_panel(indicator)

        self.assertTrue(
            all(v is None for v in self._read_column("fac_workplace_discrimination")),
            "the hidden parent factor's own column must be cleared too",
        )
        self.assertTrue(all(v is None for v in self._read_column("workplace_index")))
        self.assertEqual(factor.attribute("result"), "Not Run")
        self.assertEqual(indicator.attribute("result"), "Not Run")

    def test_clearing_a_visible_factor_does_not_touch_its_child(self):
        """A factor with multiple children (or visible for any other
        reason) is a real, independently-selectable row - clearing it must
        NOT reach into its child, same as before this fix."""
        _dimension, factor, indicator = build_tree(hide_factor=False)
        self.assertTrue(factor.is_visible())

        self._clear_via_panel(factor)

        self.assertTrue(all(v is None for v in self._read_column("fac_workplace_discrimination")))
        self.assertTrue(
            all(v == 2.0 for v in self._read_column("workplace_index")),
            "a visible (independently selectable) factor's clear must not reach into its child",
        )
        self.assertEqual(factor.attribute("result"), "Not Run")
        self.assertNotEqual(indicator.attribute("result"), "Not Run")


if __name__ == "__main__":
    unittest.main()
