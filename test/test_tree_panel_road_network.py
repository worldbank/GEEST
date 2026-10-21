# -*- coding: utf-8 -*-
"""Unit tests for TreePanel.set_road_network_layer_path.

TreePanel is a heavy QWidget that needs a loaded .ui file and a full
JsonTreeModel to construct, so these tests call the unbound method
against a lightweight stand-in object instead of a real TreePanel.
"""
import tempfile
import unittest
from unittest.mock import MagicMock

from geest.gui.panels.tree_panel import TreePanel


class TestSetRoadNetworkLayerPath(unittest.TestCase):
    def setUp(self):
        self.analysis_item = MagicMock()
        panel = MagicMock()
        panel.model.rootItem.child.return_value = self.analysis_item
        self.panel = panel

    def test_missing_file_is_rejected_and_not_stored(self):
        TreePanel.set_road_network_layer_path(self.panel, "/no/such/file.gpkg")

        self.analysis_item.setAttribute.assert_not_called()
        self.panel.show_validation_error.assert_called_once()
        self.assertIn("Road Network Issue", self.panel.show_validation_error.call_args[0][0])

    def test_existing_file_is_stored(self):
        with tempfile.NamedTemporaryFile(suffix=".gpkg") as tmp:
            TreePanel.set_road_network_layer_path(self.panel, tmp.name)

        self.analysis_item.setAttribute.assert_called_once_with("road_network_layer_path", tmp.name)
        self.panel.save_json_to_working_directory.assert_called_once()
        self.panel.show_validation_error.assert_not_called()

    def test_existing_file_with_layername_suffix_is_stored(self):
        with tempfile.NamedTemporaryFile(suffix=".gpkg") as tmp:
            layer_path = f"{tmp.name}|layername=network"
            TreePanel.set_road_network_layer_path(self.panel, layer_path)

        self.analysis_item.setAttribute.assert_called_once_with("road_network_layer_path", layer_path)
        self.panel.show_validation_error.assert_not_called()

    def test_empty_path_clears_stored_value(self):
        TreePanel.set_road_network_layer_path(self.panel, "")

        self.analysis_item.setAttribute.assert_called_once_with("road_network_layer_path", "")
        self.panel.save_json_to_working_directory.assert_called_once()
        self.panel.show_validation_error.assert_not_called()

    def test_none_path_clears_stored_value(self):
        TreePanel.set_road_network_layer_path(self.panel, None)

        self.analysis_item.setAttribute.assert_called_once_with("road_network_layer_path", "")


if __name__ == "__main__":
    unittest.main()
