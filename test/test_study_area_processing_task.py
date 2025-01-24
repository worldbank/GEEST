#!/usr/bin/env python
"""
Test suite for study_area.py

versionadded: 2025-01-24
"""

import os
import unittest
from osgeo import ogr, gdal
from study_area import StudyAreaProcessor


class TestStudyAreaProcessor(unittest.TestCase):
    """
    Comprehensive test suite for StudyAreaProcessor class.
    """

    @classmethod
    def setUpClass(cls):
        """
        Setup for the entire test suite.
        """
        cls.gpkg_path = "test_study_area.gpkg"
        cls.working_dir = "test_working_dir"
        cls.cell_size_m = 1000
        cls.target_spatial_ref = ogr.osr.SpatialReference()
        cls.target_spatial_ref.ImportFromEPSG(4326)  # WGS84

        cls.processor = StudyAreaProcessor(
            gpkg_path=cls.gpkg_path,
            working_dir=cls.working_dir,
            cell_size_m=cls.cell_size_m,
            target_spatial_ref=cls.target_spatial_ref,
        )

    @classmethod
    def tearDownClass(cls):
        """
        Cleanup after all tests.
        """
        if os.path.exists(cls.gpkg_path):
            os.remove(cls.gpkg_path)
        if os.path.exists(cls.working_dir):
            for root, dirs, files in os.walk(cls.working_dir):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    os.rmdir(os.path.join(root, dir))
            os.rmdir(cls.working_dir)

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
