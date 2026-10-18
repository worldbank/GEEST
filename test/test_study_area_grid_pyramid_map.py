# -*- coding: utf-8 -*-
"""Unit tests for geest.core.utilities.add_study_area_grid_pyramid_to_map().

Unlike add_pyramid_layer_to_map(), there is no score column to symbolize -
every level just shows the grid's own geometry. Covers the early-return
guards with lightweight fixtures, and the real layer-group construction
against a real GeoPackage with a real pyramid scaffold (via
build_pyramid_scaffold()), using the real QgsProject singleton the same
way test_download_all_resources.py's TestVectorResourceConfiguration does -
added layers are tracked and removed in tearDown so tests don't leak into
each other or into a real QGIS session.
"""
import json
import os
import shutil
import tempfile
import unittest

from osgeo import ogr, osr
from qgis.core import QgsProject

from geest.core.grid_pyramid_utils import build_pyramid_scaffold
from geest.core.utilities import add_study_area_grid_pyramid_to_map


def _build_base_grid(gpkg_path, cell_size=100.0, rows=4, cols=4, area_name="area1"):
    """A study_area_grid layer with just grid_id/area_name - the pyramid
    scaffold is column-agnostic, so no score column is needed here."""
    driver = ogr.GetDriverByName("GPKG")
    ds = driver.CreateDataSource(gpkg_path)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(32626)
    layer = ds.CreateLayer("study_area_grid", srs, geom_type=ogr.wkbPolygon)
    layer.CreateField(ogr.FieldDefn("grid_id", ogr.OFTInteger))
    layer.CreateField(ogr.FieldDefn("area_name", ogr.OFTString))

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
            feature.SetGeometry(ogr.CreateGeometryFromWkt(wkt))
            layer.CreateFeature(feature)
            feature = None
            grid_id += 1
    ds = None


class TestAddStudyAreaGridPyramidToMapGuards(unittest.TestCase):
    """Early-return guards that never touch QgsProject/the layer tree."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="test_study_area_grid_pyramid_map_")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_regional_scale_returns_false(self):
        result = add_study_area_grid_pyramid_to_map(self.tmp_dir, cell_size_m=100.0, analysis_scale="regional")
        self.assertFalse(result)

    def test_missing_working_directory_returns_false(self):
        result = add_study_area_grid_pyramid_to_map(None, cell_size_m=100.0, analysis_scale="national")
        self.assertFalse(result)

    def test_missing_geopackage_returns_false(self):
        result = add_study_area_grid_pyramid_to_map(self.tmp_dir, cell_size_m=100.0, analysis_scale="national")
        self.assertFalse(result)

    def test_h3_project_with_no_resolution_configured_returns_false(self):
        os.makedirs(os.path.join(self.tmp_dir, "study_area"))
        gpkg_path = os.path.join(self.tmp_dir, "study_area", "study_area.gpkg")
        _build_base_grid(gpkg_path)
        with open(os.path.join(self.tmp_dir, "model.json"), "w") as f:
            json.dump({"grid_type": "h3"}, f)

        result = add_study_area_grid_pyramid_to_map(self.tmp_dir, cell_size_m=100.0, analysis_scale="national")

        self.assertFalse(result)

    def test_no_pyramid_scaffold_built_yet_returns_false(self):
        """Only the base level exists (no build_pyramid_scaffold() call
        yet) - nothing coarser to show as a scale-dependent group."""
        os.makedirs(os.path.join(self.tmp_dir, "study_area"))
        gpkg_path = os.path.join(self.tmp_dir, "study_area", "study_area.gpkg")
        _build_base_grid(gpkg_path)

        result = add_study_area_grid_pyramid_to_map(self.tmp_dir, cell_size_m=100.0, analysis_scale="national")

        self.assertFalse(result)


class TestAddStudyAreaGridPyramidToMapRealLayers(unittest.TestCase):
    """Builds a real scaffolded GeoPackage and checks the real QgsLayerTreeGroup."""

    GROUP_NAME = "Test GeoE3 Study Area"

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="test_study_area_grid_pyramid_map_")
        os.makedirs(os.path.join(self.tmp_dir, "study_area"))
        self.gpkg_path = os.path.join(self.tmp_dir, "study_area", "study_area.gpkg")
        _build_base_grid(self.gpkg_path, cell_size=100.0, rows=4, cols=4)
        self.assertTrue(build_pyramid_scaffold(self.gpkg_path, 100.0))

        self.project = QgsProject.instance()
        self._added_layer_ids = []

    def tearDown(self):
        root = self.project.layerTreeRoot()
        group = root.findGroup(self.GROUP_NAME)
        if group is not None:
            layer_ids = [child.layerId() for child in group.children() if hasattr(child, "layerId")]
            if layer_ids:
                self.project.removeMapLayers(layer_ids)
            root.removeChildNode(group)
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_builds_a_scale_dependent_layer_group(self):
        result = add_study_area_grid_pyramid_to_map(
            self.tmp_dir, cell_size_m=100.0, analysis_scale="national", group=self.GROUP_NAME
        )

        self.assertTrue(result)

        root = self.project.layerTreeRoot()
        top_group = root.findGroup(self.GROUP_NAME)
        self.assertIsNotNone(top_group)

        output_group = top_group.findGroup("study_area_grid")
        self.assertIsNotNone(output_group)

        layer_nodes = [child for child in output_group.children() if hasattr(child, "layerId")]
        self.assertGreaterEqual(len(layer_nodes), 2, "expected at least the base level plus one coarser level")

        for node in layer_nodes:
            layer = node.layer()
            self.assertTrue(layer.hasScaleBasedVisibility())

    def test_finest_level_has_no_inner_scale_limit(self):
        add_study_area_grid_pyramid_to_map(
            self.tmp_dir, cell_size_m=100.0, analysis_scale="national", group=self.GROUP_NAME
        )

        root = self.project.layerTreeRoot()
        output_group = root.findGroup(self.GROUP_NAME).findGroup("study_area_grid")
        layer_nodes = [child for child in output_group.children() if hasattr(child, "layerId")]
        finest_layer = layer_nodes[0].layer()

        self.assertEqual(finest_layer.maximumScale(), 0)

    def test_rerunning_does_not_duplicate_layers(self):
        add_study_area_grid_pyramid_to_map(
            self.tmp_dir, cell_size_m=100.0, analysis_scale="national", group=self.GROUP_NAME
        )
        root = self.project.layerTreeRoot()
        output_group = root.findGroup(self.GROUP_NAME).findGroup("study_area_grid")
        first_run_count = len([child for child in output_group.children() if hasattr(child, "layerId")])

        add_study_area_grid_pyramid_to_map(
            self.tmp_dir, cell_size_m=100.0, analysis_scale="national", group=self.GROUP_NAME
        )
        output_group = root.findGroup(self.GROUP_NAME).findGroup("study_area_grid")
        layer_nodes = [child for child in output_group.children() if hasattr(child, "layerId")]

        self.assertEqual(len(layer_nodes), first_run_count)
        self.assertEqual(len(layer_nodes), len(set(n.layerId() for n in layer_nodes)))


if __name__ == "__main__":
    unittest.main()
