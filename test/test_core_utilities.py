import unittest
from unittest.mock import MagicMock, patch
from qgis.core import (
    QgsVectorLayer,
    QgsRasterLayer,
    QgsLayerTreeGroup,
    QgsLayerTreeLayer,
)
from geest.core.utilities import (
    get_or_create_group,
    traverse_and_create_subgroups,
    create_layer,
    find_existing_layer,
    add_layer_to_group,
    ensure_visibility,
)
from geest.core.json_tree_item import JsonTreeItem


class TestUtilities(unittest.TestCase):
    @patch("geest.core.utilities.QgsProject")
    def setUp(self, mock_qgs_project):
        """Set up a mocked QGIS project for each test."""
        self.mock_project = MagicMock()
        self.mock_root = MagicMock()
        self.mock_project.layerTreeRoot.return_value = self.mock_root
        mock_qgs_project.instance.return_value = self.mock_project

    def test_get_or_create_group(self):
        """Test get_or_create_group creates or retrieves a group."""
        group_name = "TestGroup"
        mock_group = MagicMock()
        self.mock_root.findGroup.return_value = None
        self.mock_root.insertGroup.return_value = mock_group

        group = get_or_create_group(group_name)
        self.assertEqual(group, mock_group)
        self.mock_root.insertGroup.assert_called_once_with(0, group_name)

        # Test retrieving the same group
        self.mock_root.findGroup.return_value = mock_group
        same_group = get_or_create_group(group_name)
        self.assertEqual(group, same_group)

    def test_traverse_and_create_subgroups(self):
        """Test traverse_and_create_subgroups creates subgroups."""
        parent_group = MagicMock()
        mock_subgroup = MagicMock()
        parent_group.findGroup.return_value = None
        parent_group.addGroup.return_value = mock_subgroup

        item = JsonTreeItem("Layer1", 0)
        item.getPaths = lambda: ["ParentGroup", "Subgroup1", "Layer1"]

        subgroup = traverse_and_create_subgroups(parent_group, item)
        self.assertEqual(subgroup, mock_subgroup)
        parent_group.addGroup.assert_called_with("Subgroup1")

    @patch("geest.core.utilities.QgsVectorLayer")
    @patch("geest.core.utilities.QgsRasterLayer")
    def test_create_layer(self, mock_raster_layer, mock_vector_layer):
        """Test create_layer creates a valid layer."""
        mock_vector_layer.return_value.isValid.return_value = True
        mock_raster_layer.return_value.isValid.return_value = True

        # Test vector layer creation
        vector_layer = create_layer("mock.gpkg", "Vector Layer", None, None)
        self.assertEqual(vector_layer, mock_vector_layer.return_value)
        mock_vector_layer.assert_called_once_with("mock.gpkg", "Vector Layer", "ogr")

        # Test raster layer creation
        raster_layer = create_layer("mock.tif", "Raster Layer", None, None)
        self.assertEqual(raster_layer, mock_raster_layer.return_value)
        mock_raster_layer.assert_called_once_with("mock.tif", "Raster Layer")

    def test_find_existing_layer(self):
        """Test find_existing_layer finds an existing layer."""
        parent_group = MagicMock()
        mock_layer = MagicMock()
        mock_tree_layer = MagicMock()
        mock_tree_layer.layer.return_value = mock_layer
        parent_group.children.return_value = [mock_tree_layer]

        layer, tree_layer = find_existing_layer(parent_group, "mock_layer_uri")
        self.assertEqual(layer, mock_layer)
        self.assertEqual(tree_layer, mock_tree_layer)

    def test_add_layer_to_group(self):
        """Test add_layer_to_group adds a layer to the group."""
        parent_group = MagicMock()
        mock_layer = MagicMock()
        mock_tree_layer = MagicMock()
        parent_group.addLayer.return_value = mock_tree_layer

        add_layer_to_group(mock_layer, parent_group, "mock_layer_uri")
        parent_group.addLayer.assert_called_once_with(mock_layer)

    def test_ensure_visibility(self):
        """Test ensure_visibility makes layers and groups visible."""
        parent_group = MagicMock()
        mock_tree_layer = MagicMock()

        ensure_visibility(mock_tree_layer, parent_group)
        parent_group.setExpanded.assert_called_with(True)
        parent_group.setItemVisibilityChecked.assert_called_with(True)
        mock_tree_layer.setItemVisibilityChecked.assert_called_with(True)


if __name__ == "__main__":
    unittest.main()
