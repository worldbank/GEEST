# -*- coding: utf-8 -*-
"""Regression tests for TreePanel.on_item_clicked()'s unrun-indicator guard.

TreePanel is a heavy QWidget that needs a loaded .ui file and a full
JsonTreeModel to construct, so these tests call the unbound method against
a lightweight MagicMock stand-in instead of a real TreePanel, matching the
pattern in test_tree_panel_pyramid_migration.py.

Guards against clicking an indicator that has never actually run opening
the study area GeoPackage at all - there is no study_area_grid column, no
raster, nothing to show, so add_pyramid_layer_to_map()/add_to_map() must
never be called for it.
"""
import unittest
from unittest.mock import MagicMock, patch

from geest.gui.panels.tree_panel import TreePanel


def _make_item(role, attributes, enabled=True):
    item = MagicMock()
    item.role = role
    item.is_enabled.return_value = enabled
    item.attribute.side_effect = lambda key, default=None: attributes.get(key, default)
    return item


def _make_index(item):
    index = MagicMock()
    index.internalPointer.return_value = item
    return index


class TestOnItemClickedSkipsUnrunIndicators(unittest.TestCase):
    def setUp(self):
        self.panel = MagicMock()
        self.setting_patch = patch(
            "geest.gui.panels.tree_panel.setting",
            side_effect=lambda key, default=None: True if key == "show_layer_on_click" else False,
        )
        self.mock_setting = self.setting_patch.start()
        self.add_pyramid_patch = patch("geest.gui.panels.tree_panel.add_pyramid_layer_to_map")
        self.mock_add_pyramid = self.add_pyramid_patch.start()
        self.add_to_map_patch = patch("geest.gui.panels.tree_panel.add_to_map")
        self.mock_add_to_map = self.add_to_map_patch.start()
        self.add_grid_patch = patch("geest.gui.panels.tree_panel.add_grid_layer_to_map")
        self.mock_add_grid = self.add_grid_patch.start()

    def tearDown(self):
        self.setting_patch.stop()
        self.add_pyramid_patch.stop()
        self.add_to_map_patch.stop()
        self.add_grid_patch.stop()

    def test_never_run_indicator_does_not_touch_the_map(self):
        item = _make_item("indicator", {"id": "fire", "result": ""})
        index = _make_index(item)

        TreePanel.on_item_clicked(self.panel, index)

        self.mock_add_pyramid.assert_not_called()
        self.mock_add_to_map.assert_not_called()
        self.mock_add_grid.assert_not_called()

    def test_completed_indicator_adds_its_pyramid_layer(self):
        item = _make_item("indicator", {"id": "fire", "result": "Workflow Completed"})
        index = _make_index(item)

        TreePanel.on_item_clicked(self.panel, index)

        self.mock_add_pyramid.assert_called_once()
        self.mock_add_to_map.assert_not_called()

    def test_disabled_indicator_does_not_touch_the_map(self):
        item = _make_item("indicator", {"id": "fire", "result": "Workflow Completed"}, enabled=False)
        index = _make_index(item)

        TreePanel.on_item_clicked(self.panel, index)

        self.mock_add_pyramid.assert_not_called()

    def test_factor_is_unaffected_by_the_indicator_guard(self):
        # The guard is scoped to role == "indicator" - a factor's own
        # aggregate column may be meaningful even while individual
        # indicators underneath it haven't all run.
        item = _make_item("factor", {"id": "jobs"})
        index = _make_index(item)

        TreePanel.on_item_clicked(self.panel, index)

        self.mock_add_pyramid.assert_called_once()


if __name__ == "__main__":
    unittest.main()
