#!/usr/bin/env python
"""
Test suite for study_area.py

versionadded: 2025-01-24
"""

import os
import unittest
import shutil

from osgeo import ogr, gdal
from qgis.core import QgsVectorLayer, QgsFeedback
from geest.core.tasks import StudyAreaProcessingTask
from utilities_for_testing import prepare_fixtures


class TestStudyAreaProcessor(unittest.TestCase):
    """
    Comprehensive test suite for StudyAreaProcessor class.
    """

    @classmethod
    def setUpClass(cls):
        """
        Setup for the entire test suite.
        """
        cls.cell_size_m = 1000
        cls.test_data_directory = prepare_fixtures()
        cls.input_admin_path = os.path.join(
            cls.test_data_directory, "admin", "Admin0.shp"
        )
        cls.layer = QgsVectorLayer(cls.input_admin_path, "Admin0", "ogr")
        cls.field_name = "Name"
        # Define working directories
        cls.working_dir = os.path.join(cls.test_data_directory, "output")
        cls.gpkg_path = os.path.join(cls.working_dir, "study_area", "study_area.gpkg")

    @classmethod
    def tearDownClass(cls):
        """
        Cleanup after all tests.
        """
        pass

    def setUp(self):
        """
        Set up the environment for the test, loading the test data layers.
        """
        # Create the output directory if it doesn't exist
        if not os.path.exists(self.working_dir):
            # print(f"Creating working directory {self.working_dir}")
            os.makedirs(self.working_dir)

        # Define paths to test layers
        self.processor = StudyAreaProcessingTask(
            layer=self.layer,
            field_name=self.field_name,
            working_dir=self.working_dir,
            cell_size_m=self.cell_size_m,
            crs=None,
        )

    def tearDown(self):
        # Recursively delete everything in the working_dir
        shutil.rmtree(self.working_dir)

    def test_create_layer_if_not_exists(self):
        """
        Test creating a layer if it does not exist.
        """
        layer_name = "test_layer"
        self.processor.create_layer_if_not_exists(layer_name)

        ds = ogr.Open(self.gpkg_path)
        layer = ds.GetLayerByName(layer_name)
        self.assertIsNotNone(layer, "Layer was not created.")
        ds = None

    @unittest.skip("Skipping test for now")
    def test_create_and_save_grid(self):
        """
        Test grid creation and saving.
        """
        bbox = (-10, 10, -10, 10)
        geom = ogr.Geometry(ogr.wkbPolygon)
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(-10, -10)
        ring.AddPoint(10, -10)
        ring.AddPoint(10, 10)
        ring.AddPoint(-10, 10)
        ring.AddPoint(-10, -10)
        geom.AddGeometry(ring)

        self.processor.create_and_save_grid("test_grid", geom, bbox)

        ds = ogr.Open(self.gpkg_path)
        layer = ds.GetLayerByName("study_area_grid")
        self.assertIsNotNone(layer, "Grid layer was not created.")
        self.assertGreater(layer.GetFeatureCount(), 0, "Grid layer has no features.")
        ds = None

    @unittest.skip("Skipping test for now")
    def test_create_raster_mask(self):
        """
        Test raster mask creation.
        """
        bbox = (-10, 10, -10, 10)
        geom = ogr.Geometry(ogr.wkbPolygon)
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(-10, -10)
        ring.AddPoint(10, -10)
        ring.AddPoint(10, 10)
        ring.AddPoint(-10, 10)
        ring.AddPoint(-10, -10)
        geom.AddGeometry(ring)

        mask_path = self.processor.create_raster_mask(geom, bbox, "test_mask")

        self.assertTrue(os.path.exists(mask_path), "Raster mask was not created.")

    def test_calculate_utm_zone(self):
        """
        Test UTM zone calculation.
        """
        bbox = (-10, 10, -10, 10)
        utm_code = self.processor.calculate_utm_zone(bbox)
        self.assertEqual(utm_code, 32631, "UTM zone calculation is incorrect.")

    def test_create_study_area_directory(self):
        """
        Test study area directory creation.
        """
        self.processor.create_study_area_directory(self.working_dir)

        self.assertTrue(
            os.path.exists(os.path.join(self.working_dir, "study_area")),
            "Study area directory was not created.",
        )

    def test_track_time(self):
        """
        Test the track_time helper method.
        """
        self.processor.metrics = {"test_metric": 0}
        start_time = 0
        self.processor.track_time("test_metric", start_time)
        self.assertIn("test_metric", self.processor.metrics, "Metric was not tracked.")

    @unittest.skip("Skipping test for now")
    def test_write_chunk(self):
        """
        Test the write_chunk method for layer writing.
        """
        # Create dummy layer and task
        self.processor.create_layer_if_not_exists("chunk_layer")
        ds = ogr.Open(self.gpkg_path, 1)
        layer = ds.GetLayerByName("chunk_layer")
        self.assertIsNotNone(layer, "Chunk layer creation failed.")
        task = type("DummyTask", (), {"features_out": [ogr.Geometry(ogr.wkbPolygon)]})()
        task.features_out[0].AddGeometry(ogr.Geometry(ogr.wkbLinearRing))
        self.processor.write_chunk(layer, task, "test_chunk")
        self.assertGreater(layer.GetFeatureCount(), 0, "Chunk writing failed.")

    @unittest.skip("Skipping test for now")
    def test_create_raster_vrt(self):
        """
        Test VRT creation.
        """
        vrt_name = "test_vrt.vrt"
        self.processor.create_raster_vrt(output_vrt_name=vrt_name)
        self.assertTrue(
            os.path.exists(os.path.join(self.working_dir, "study_area", vrt_name)),
            "VRT file was not created.",
        )

    @unittest.skip("Skipping test for now")
    def test_create_clip_polygon(self):
        """
        Test clip polygon creation.
        """
        bbox = (-10, 10, -10, 10)
        aligned_box = (-12, 12, -12, 12)

        # Create a test geometry
        geom = ogr.Geometry(ogr.wkbPolygon)
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(-10, -10)
        ring.AddPoint(10, -10)
        ring.AddPoint(10, 10)
        ring.AddPoint(-10, 10)
        ring.AddPoint(-10, -10)
        geom.AddGeometry(ring)

        # Call create_clip_polygon
        self.processor.create_clip_polygon(geom, aligned_box, "test_clip")

        ds = ogr.Open(self.gpkg_path)
        layer = ds.GetLayerByName("study_area_clip_polygons")
        self.assertIsNotNone(layer, "Clip polygon layer was not created.")
        self.assertGreater(
            layer.GetFeatureCount(), 0, "Clip polygon layer has no features."
        )


if __name__ == "__main__":
    unittest.main()
