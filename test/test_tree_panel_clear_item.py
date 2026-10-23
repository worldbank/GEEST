# -*- coding: utf-8 -*-
"""Regression test for TreePanel.clear_item() ancestor invalidation.

TreePanel is a heavy QWidget that needs a loaded .ui file and a full
JsonTreeModel to construct, so this test calls the unbound method against
a lightweight MagicMock stand-in instead of a real TreePanel, matching the
pattern in test_tree_panel_download_all_resources.py.

Guards against a real production bug: clearing a single indicator deleted
its own result but left its parent factor, grandparent dimension, and
great-grandparent analysis all still reporting "Completed successfully"
with aggregate values computed from the now-deleted child - clear_item()
never told any ancestor it was now stale.
"""
import unittest
from unittest.mock import MagicMock

from geest.core.json_tree_item import JsonTreeItem
from geest.gui.panels.tree_panel import TreePanel


def _make_item(name, role, parent=None):
    data = [name, "Configured", 1.0, {"id": name, "result": "Completed successfully"}]
    item = JsonTreeItem(data, role=role, parent=parent)
    if parent is not None:
        parent.appendChild(item)
    return item


class TestClearItemInvalidatesAncestors(unittest.TestCase):
    def setUp(self):
        self.analysis = _make_item("Analysis", "analysis")
        self.dimension = _make_item("Accessibility", "dimension", parent=self.analysis)
        self.factor = _make_item("Womens Travel Patterns", "factor", parent=self.dimension)
        self.indicator = _make_item("Womens Travel Patterns Indicator", "indicator", parent=self.factor)

        self.panel = MagicMock()
        self.panel.working_directory = None
        index = MagicMock()
        index.internalPointer.return_value = self.indicator
        self.panel.treeView.currentIndex.return_value = index
        # self.panel is a MagicMock, so without this clear_item()'s call to
        # self._clear_single_item_outputs(item) would hit an auto-mocked
        # attribute instead of the real method under test.
        self.panel._clear_single_item_outputs.side_effect = lambda item: TreePanel._clear_single_item_outputs(
            self.panel, item
        )

    def test_clearing_an_indicator_invalidates_factor_dimension_and_analysis(self):
        TreePanel.clear_item(self.panel)

        self.assertEqual(self.indicator.attributes()["result"], "Not Run")
        for ancestor in (self.factor, self.dimension, self.analysis):
            self.assertEqual(ancestor.attributes()["result"], "")
            self.assertEqual(ancestor.attributes()["result_file"], "")

    def test_clearing_an_indicator_still_saves_the_model(self):
        TreePanel.clear_item(self.panel)

        self.panel.save_json_to_working_directory.assert_called_once()


if __name__ == "__main__":
    unittest.main()
