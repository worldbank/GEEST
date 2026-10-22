# -*- coding: utf-8 -*-
"""Unit tests for geest.core.utilities.remove_from_map.

Uses a real QgsProject/layer tree (mirroring test_download_all_resources.py's
TestVectorResourceConfiguration pattern) rather than mocking QGIS objects,
since the whole point is to verify the real group-traversal/layer-removal
round trip against the same tree shape add_to_map()/add_grid_layer_to_map()
build.
"""
import unittest

from qgis.core import QgsProject, QgsVectorLayer

from geest.core import JsonTreeItem
from geest.core.utilities import remove_from_map


def _memory_layer(name):
    layer = QgsVectorLayer("Point?crs=EPSG:4326", name, "memory")
    assert layer.isValid()
    return layer


def build_tree():
    """dim1 -> fac1 -> ind1, matching the shape add_to_map()/getPaths() expect."""
    dimension = JsonTreeItem(["Dimension", "Configured", 1.0, {"id": "dim1"}], role="dimension", parent=None)
    factor = JsonTreeItem(["Factor", "Configured", 1.0, {"id": "fac1"}], role="factor", parent=dimension)
    indicator = JsonTreeItem(["Indicator", "Configured", 1.0, {"id": "ind1"}], role="indicator", parent=factor)
    factor.appendChild(indicator)
    dimension.appendChild(factor)
    return dimension, factor, indicator


class TestRemoveFromMap(unittest.TestCase):
    def setUp(self):
        self.project = QgsProject.instance()
        self.project.clear()
        self.dimension, self.factor, self.indicator = build_tree()

    def tearDown(self):
        self.project.clear()

    def _build_layer_tree(self):
        """GeoE3 / dim1 (factor's own group) / fac1 (indicator's own group).

        Mirrors what add_to_map()/add_grid_layer_to_map() build: an item's
        own layer lives in the group named by getPaths()[:-1], i.e. one
        level *above* the subgroup that holds its children.
        """
        root = self.project.layerTreeRoot()
        geoe3_group = root.insertGroup(0, "GeoE3")
        dim1_group = geoe3_group.addGroup("dim1")  # factor's own group
        fac1_group = dim1_group.addGroup("fac1")  # indicator's own group

        factor_layer = _memory_layer("Factor")
        indicator_layer = _memory_layer("Indicator")
        self.project.addMapLayer(factor_layer, False)
        self.project.addMapLayer(indicator_layer, False)
        dim1_group.addLayer(factor_layer)
        fac1_group.addLayer(indicator_layer)
        return factor_layer, indicator_layer, dim1_group, fac1_group

    def test_removes_only_this_items_own_layer(self):
        factor_layer, indicator_layer, dim1_group, fac1_group = self._build_layer_tree()
        # Capture ids before removal - removeMapLayer deletes the underlying
        # C++ object, so the Python wrapper can't be queried afterward.
        factor_layer_id = factor_layer.id()
        indicator_layer_id = indicator_layer.id()

        remove_from_map(self.factor)

        self.assertIsNone(self.project.mapLayer(factor_layer_id))
        self.assertIsNotNone(self.project.mapLayer(indicator_layer_id))

    def test_does_not_prune_the_childrens_group(self):
        factor_layer, indicator_layer, dim1_group, fac1_group = self._build_layer_tree()

        remove_from_map(self.factor)

        root = self.project.layerTreeRoot()
        self.assertIsNotNone(root.findGroup("GeoE3").findGroup("dim1"))
        self.assertIsNotNone(root.findGroup("GeoE3").findGroup("dim1").findGroup("fac1"))
        self.assertIsNotNone(fac1_group.findLayer(indicator_layer.id()))

    def test_removes_grid_variant_layer_too(self):
        root = self.project.layerTreeRoot()
        geoe3_group = root.insertGroup(0, "GeoE3")
        dim1_group = geoe3_group.addGroup("dim1")

        grid_layer = _memory_layer("Factor (Grid)")
        self.project.addMapLayer(grid_layer, False)
        dim1_group.addLayer(grid_layer)
        grid_layer_id = grid_layer.id()

        remove_from_map(self.factor)

        self.assertIsNone(self.project.mapLayer(grid_layer_id))

    def test_no_group_is_a_silent_noop(self):
        # No "GeoE3" group exists at all - must not raise.
        remove_from_map(self.indicator)

    def test_item_never_added_is_a_silent_noop(self):
        root = self.project.layerTreeRoot()
        root.insertGroup(0, "GeoE3")
        # "GeoE3" exists but none of this item's path subgroups do.
        remove_from_map(self.indicator)


if __name__ == "__main__":
    unittest.main()
