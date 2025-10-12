# -*- coding: utf-8 -*-
"""
Copyright (c) 2025. All rights reserved.
Original Author: [Your Name]

Comprehensive Unit Tests for GHSLProcessor Class
"""
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from qgis.core import QgsRectangle

from geest.core.algorithms.ghsl_processor import GHSLProcessor


class TestGHSLProcessor(unittest.TestCase):
    def setUp(self):
        # Initialize any required variables or objects here
        test_data_path = os.path.join(os.path.dirname(__file__), "test_data")
        # check if test_data_path exists, if not raise an error
        if not os.path.exists(test_data_path):
            raise FileNotFoundError(f"Test data path does not exist: {test_data_path}")

        self.raster1 = os.path.join(test_data_path, "ghsl", "GHS_SMOD_E2030_GLOBE_R2023A_54009_1000_V2_0_R5_C19.tif")
        self.raster2 = os.path.join(test_data_path, "ghsl", "GHS_SMOD_E2030_GLOBE_R2023A_54009_1000_V2_0_R5_C20.tif")
        self.raster_paths = [self.raster1, self.raster2]

        # Create temp directory for test outputs
        self.temp_dir = tempfile.mkdtemp(prefix="test_ghsl_")

        # Only initialize processor if test rasters exist
        if os.path.exists(self.raster1) and os.path.exists(self.raster2):
            self.processor = GHSLProcessor(self.raster_paths)
        else:
            self.processor = None

    def test_initialization(self):
        # Test if the processor initializes correctly
        if self.processor:
            self.assertIsInstance(self.processor, GHSLProcessor)
            self.assertEqual(len(self.processor.input_raster_layers), 2)
            self.assertEqual(self.processor.input_raster_layers, self.raster_paths)
        else:
            self.skipTest("Test rasters not available")

    def test_initialization_empty_list(self):
        # Test initialization with empty raster list
        with self.assertRaises(ValueError):
            GHSLProcessor([])

    def test_initialization_invalid_paths(self):
        # Test initialization with invalid file paths
        invalid_paths = ["/invalid/path1.tif", "/invalid/path2.tif"]
        with self.assertRaises(ValueError):
            GHSLProcessor(invalid_paths)

    def test_create_virtual_raster(self):
        # Test virtual raster creation
        if not self.processor:
            self.skipTest("Test rasters not available")

        output_path = os.path.join(self.temp_dir, "test_virtual.vrt")

        # Mock GDAL BuildVRT to avoid actual file operations in tests
        with patch("geest.core.algorithms.ghsl_processor.gdal.BuildVRT") as mock_build_vrt:
            mock_dataset = MagicMock()
            mock_build_vrt.return_value = mock_dataset

            result = self.processor.create_virtual_raster(output_path)

            self.assertEqual(result, output_path)
            self.assertEqual(self.processor.virtual_raster_path, output_path)
            mock_build_vrt.assert_called_once()

    def test_create_virtual_raster_failure(self):
        # Test virtual raster creation failure
        if not self.processor:
            self.skipTest("Test rasters not available")

        output_path = os.path.join(self.temp_dir, "test_virtual_fail.vrt")

        with patch("geest.core.algorithms.ghsl_processor.gdal.BuildVRT") as mock_build_vrt:
            mock_build_vrt.return_value = None  # Simulate failure

            with self.assertRaises(RuntimeError):
                self.processor.create_virtual_raster(output_path)

    def test_reclassify_rasters(self):
        # Test raster reclassification
        if not self.processor:
            self.skipTest("Test rasters not available")

        # Mock GDAL operations for reclassification
        with patch("geest.core.algorithms.ghsl_processor.gdal.Open") as mock_open, patch(
            "geest.core.algorithms.ghsl_processor.gdal.GetDriverByName"
        ) as mock_driver:

            # Mock input dataset
            mock_input_dataset = MagicMock()
            mock_input_band = MagicMock()
            mock_input_dataset.GetRasterBand.return_value = mock_input_band
            mock_input_dataset.RasterXSize = 100
            mock_input_dataset.RasterYSize = 100
            mock_input_dataset.GetGeoTransform.return_value = (0, 1, 0, 0, 0, -1)
            mock_input_dataset.GetProjection.return_value = "EPSG:4326"
            mock_input_band.ReadAsArray.return_value = [[10, 11, 20], [30, 10, 40]]

            mock_open.return_value = mock_input_dataset

            # Mock output driver and dataset
            mock_output_driver = MagicMock()
            mock_output_dataset = MagicMock()
            mock_output_band = MagicMock()
            mock_output_dataset.GetRasterBand.return_value = mock_output_band
            mock_output_driver.Create.return_value = mock_output_dataset
            mock_driver.return_value = mock_output_driver

            result = self.processor.reclassify_rasters("test_suffix")

            self.assertIsInstance(result, list)
            self.assertEqual(len(result), len(self.raster_paths))

    def test_clean_raster_for_polygonization(self):
        # Test raster cleaning for polygonization
        if not self.processor:
            self.skipTest("Test rasters not available")

        input_raster = os.path.join(self.temp_dir, "test_input.tif")

        with patch("geest.core.algorithms.ghsl_processor.gdal.Open") as mock_open, patch(
            "geest.core.algorithms.ghsl_processor.gdal.GetDriverByName"
        ) as mock_driver:

            # Mock input dataset
            mock_input_dataset = MagicMock()
            mock_input_band = MagicMock()
            mock_input_dataset.GetRasterBand.return_value = mock_input_band
            mock_input_dataset.RasterXSize = 10
            mock_input_dataset.RasterYSize = 10
            mock_input_dataset.GetGeoTransform.return_value = (0, 1, 0, 0, 0, -1)
            mock_input_dataset.GetProjection.return_value = "EPSG:4326"
            mock_input_band.ReadAsArray.return_value = [[0, 1, 0], [1, 0, 1]]

            mock_open.return_value = mock_input_dataset

            # Mock output driver and dataset
            mock_output_driver = MagicMock()
            mock_output_dataset = MagicMock()
            mock_output_band = MagicMock()
            mock_output_dataset.GetRasterBand.return_value = mock_output_band
            mock_output_driver.Create.return_value = mock_output_dataset
            mock_driver.return_value = mock_output_driver

            result = self.processor.clean_raster_for_polygonization(input_raster)

            self.assertTrue(result.endswith("_cleaned.tif"))

    def test_polygonize_rasters(self):
        # Test raster polygonization
        if not self.processor:
            self.skipTest("Test rasters not available")

        input_rasters = [os.path.join(self.temp_dir, "test_raster1.tif")]

        with patch.object(self.processor, "clean_raster_for_polygonization") as mock_clean, patch(
            "geest.core.algorithms.ghsl_processor.gdal.Open"
        ) as mock_open, patch("geest.core.algorithms.ghsl_processor.ogr.GetDriverByName") as mock_driver, patch(
            "geest.core.algorithms.ghsl_processor.gdal.Polygonize"
        ) as mock_polygonize:

            mock_clean.return_value = input_rasters[0].replace(".tif", "_cleaned.tif")

            # Mock raster dataset
            mock_raster_dataset = MagicMock()
            mock_raster_band = MagicMock()
            mock_raster_dataset.GetRasterBand.return_value = mock_raster_band
            mock_raster_dataset.GetProjection.return_value = "EPSG:4326"
            mock_open.return_value = mock_raster_dataset

            # Mock vector driver and datasource
            mock_vector_driver = MagicMock()
            mock_vector_datasource = MagicMock()
            mock_vector_layer = MagicMock()
            mock_vector_layer.GetFeatureCount.return_value = 5
            mock_vector_datasource.CreateLayer.return_value = mock_vector_layer
            mock_vector_driver.CreateDataSource.return_value = mock_vector_datasource
            mock_driver.return_value = mock_vector_driver

            # Mock polygonize success
            mock_polygonize.return_value = 0

            # Mock Path.exists to return True
            with patch("geest.core.algorithms.ghsl_processor.Path") as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path_instance.stat.return_value.st_size = 1000
                mock_path.return_value = mock_path_instance

                result = self.processor.polygonize_rasters(input_rasters)

            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 1)

    def test_combine_vectors(self):
        # Test vector combination
        if not self.processor:
            self.skipTest("Test rasters not available")

        input_vectors = [os.path.join(self.temp_dir, "vector1.parquet"), os.path.join(self.temp_dir, "vector2.parquet")]
        output_vector = os.path.join(self.temp_dir, "combined.parquet")
        extent = QgsRectangle(0, 0, 100, 100)

        with patch("geest.core.algorithms.ghsl_processor.ogr.Open") as mock_open, patch(
            "geest.core.algorithms.ghsl_processor.ogr.GetDriverByName"
        ) as mock_driver:

            # Mock input datasources and layers
            mock_input_datasource = MagicMock()
            mock_input_layer = MagicMock()
            mock_input_layer.GetExtent.return_value = (10, 90, 10, 90)  # (minX, maxX, minY, maxY)
            mock_input_layer.GetSpatialRef.return_value = MagicMock()
            mock_input_layer.GetLayerDefn.return_value = MagicMock()
            mock_input_layer.GetLayerDefn.return_value.GetFieldCount.return_value = 1
            mock_input_layer.__iter__ = lambda x: iter([])  # Empty feature list for simplicity
            mock_input_datasource.GetLayer.return_value = mock_input_layer
            mock_open.return_value = mock_input_datasource

            # Mock output driver and datasource
            mock_output_driver = MagicMock()
            mock_output_datasource = MagicMock()
            mock_output_layer = MagicMock()
            mock_output_layer.GetFeatureCount.return_value = 0
            mock_output_datasource.CreateLayer.return_value = mock_output_layer
            mock_output_driver.CreateDataSource.return_value = mock_output_datasource
            mock_driver.return_value = mock_output_driver

            result = self.processor.combine_vectors(input_vectors, output_vector, extent)

            self.assertTrue(result)

    def test_spatial_join_with_filter(self):
        # Test spatial join with filtering
        if not self.processor:
            self.skipTest("Test rasters not available")

        input_vector = os.path.join(self.temp_dir, "input_vector.gpkg")
        polygonized_vector = os.path.join(self.temp_dir, "polygonized.gpkg")
        output_vector = os.path.join(self.temp_dir, "joined.gpkg")

        with patch("geest.core.algorithms.ghsl_processor.ogr.Open") as mock_open, patch(
            "geest.core.algorithms.ghsl_processor.ogr.GetDriverByName"
        ) as mock_driver:

            # Mock input and polygonized datasources
            mock_datasource = MagicMock()
            mock_layer = MagicMock()
            mock_layer.GetLayerDefn.return_value = MagicMock()
            mock_layer.GetLayerDefn.return_value.GetFieldCount.return_value = 1
            mock_layer.GetSpatialRef.return_value = MagicMock()
            mock_layer.GetGeomType.return_value = 3  # wkbPolygon
            mock_layer.__iter__ = lambda x: iter([])  # Empty feature list
            mock_datasource.GetLayer.return_value = mock_layer
            mock_datasource.GetLayerCount.return_value = 1
            mock_open.return_value = mock_datasource

            # Mock output driver
            mock_output_driver = MagicMock()
            mock_output_datasource = MagicMock()
            mock_output_layer = MagicMock()
            mock_output_datasource.CreateLayer.return_value = mock_output_layer
            mock_output_driver.CreateDataSource.return_value = mock_output_datasource
            mock_driver.return_value = mock_output_driver

            result = self.processor.spatial_join_with_filter(input_vector, polygonized_vector, output_vector)

            self.assertEqual(result, output_vector)
            self.assertEqual(self.processor.joined_vector_path, output_vector)

    def test_process_full_workflow(self):
        # Test the complete workflow
        if not self.processor:
            self.skipTest("Test rasters not available")

        virtual_output = os.path.join(self.temp_dir, "virtual.vrt")
        reclassified_output = os.path.join(self.temp_dir, "reclassified.tif")
        polygonized_output = os.path.join(self.temp_dir, "polygonized.gpkg")
        input_vector = os.path.join(self.temp_dir, "input.gpkg")
        joined_output = os.path.join(self.temp_dir, "joined.gpkg")

        with patch.object(self.processor, "create_virtual_raster") as mock_create_vrt, patch.object(
            self.processor, "reclassify_raster"
        ) as mock_reclassify, patch.object(self.processor, "polygonize_raster") as mock_polygonize, patch.object(
            self.processor, "spatial_join_with_filter"
        ) as mock_spatial_join:

            mock_create_vrt.return_value = virtual_output
            mock_reclassify.return_value = reclassified_output
            mock_polygonize.return_value = polygonized_output
            mock_spatial_join.return_value = joined_output

            result = self.processor.process_full_workflow(
                virtual_output, reclassified_output, polygonized_output, input_vector, joined_output
            )

            self.assertIsInstance(result, dict)
            self.assertIn("virtual_raster", result)
            self.assertIn("reclassified_raster", result)
            self.assertIn("polygonized_vector", result)
            self.assertIn("joined_vector", result)

    def tearDown(self):
        # Clean up temporary directory
        import shutil

        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
