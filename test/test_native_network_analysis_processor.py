# -*- coding: utf-8 -*-
"""Tests for NativeNetworkAnalysisProcessingTask.

Tests the QgsTask-based batch network analysis processor that generates
isochrones using QGIS native algorithms.
"""

import os
import tempfile
import unittest

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsVectorLayer,
)

from geest.core.algorithms.native_network_analysis_processor import (
    NativeNetworkAnalysisProcessingTask,
)


class TestNativeNetworkAnalysisProcessingTask(unittest.TestCase):
    """Test cases for NativeNetworkAnalysisProcessingTask."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a CRS for testing
        self.crs = QgsCoordinateReferenceSystem("EPSG:32632")

        # Create a point layer with test features
        self.point_layer = QgsVectorLayer("Point?crs=EPSG:32632", "test_points", "memory")
        provider = self.point_layer.dataProvider()

        # Add test points
        features = []
        for i, (x, y) in enumerate(
            [
                (643067.042, 3955294.999),
                (643100.0, 3955300.0),
                (643150.0, 3955350.0),
            ]
        ):
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
            features.append(feature)

        provider.addFeatures(features)
        self.point_layer.updateExtents()

        # Mock network layer path (would need actual test data)
        self.network_layer_path = os.path.join(
            os.path.dirname(__file__),
            "test_data",
            "network_analysis",
            "network_layer.shp",
        )

        # Distance values for isochrones
        self.distances = [1000, 2000, 3000]  # Distances in meters

        # Temporary directory for outputs
        self.working_directory = tempfile.mkdtemp()
        self.output_gpkg_path = os.path.join(self.working_directory, "test_isochrones.gpkg")

        print(f"Test working directory: {self.working_directory}")

    def tearDown(self):
        """Clean up after each test method."""
        # Clean up temporary files
        if os.path.exists(self.output_gpkg_path):
            os.remove(self.output_gpkg_path)
        if os.path.exists(self.working_directory):
            os.rmdir(self.working_directory)

    def test_initialization(self):
        """Test that the task initializes correctly with valid parameters."""
        task = NativeNetworkAnalysisProcessingTask(
            point_layer=self.point_layer,
            distances=self.distances,
            road_network_path=self.network_layer_path,
            output_gpkg_path=self.output_gpkg_path,
            target_crs=self.crs,
        )

        self.assertIsNotNone(task)
        self.assertEqual(task.point_layer, self.point_layer)
        self.assertEqual(task.distances, self.distances)
        self.assertEqual(task.road_network_path, self.network_layer_path)
        self.assertEqual(task.output_gpkg_path, self.output_gpkg_path)
        self.assertEqual(task.target_crs, self.crs)
        self.assertIsNone(task.result_path)
        self.assertIsNone(task.error_message)

    def test_initialization_empty_network_path(self):
        """Test that initialization fails with empty network path."""
        with self.assertRaises(ValueError) as context:
            NativeNetworkAnalysisProcessingTask(
                point_layer=self.point_layer,
                distances=self.distances,
                road_network_path="",
                output_gpkg_path=self.output_gpkg_path,
                target_crs=self.crs,
            )
        self.assertIn("road_network_path cannot be empty", str(context.exception))

    def test_initialization_empty_output_path(self):
        """Test that initialization fails with empty output path."""
        with self.assertRaises(ValueError) as context:
            NativeNetworkAnalysisProcessingTask(
                point_layer=self.point_layer,
                distances=self.distances,
                road_network_path=self.network_layer_path,
                output_gpkg_path="",
                target_crs=self.crs,
            )
        self.assertIn("output_gpkg_path cannot be empty", str(context.exception))

    def test_initialization_empty_distances(self):
        """Test that initialization fails with empty distances list."""
        with self.assertRaises(ValueError) as context:
            NativeNetworkAnalysisProcessingTask(
                point_layer=self.point_layer,
                distances=[],
                road_network_path=self.network_layer_path,
                output_gpkg_path=self.output_gpkg_path,
                target_crs=self.crs,
            )
        self.assertIn("distances list cannot be empty", str(context.exception))

    def test_task_description(self):
        """Test that the task has the correct description."""
        task = NativeNetworkAnalysisProcessingTask(
            point_layer=self.point_layer,
            distances=self.distances,
            road_network_path=self.network_layer_path,
            output_gpkg_path=self.output_gpkg_path,
            target_crs=self.crs,
        )
        self.assertEqual(task.description(), "Native Network Analysis (Batch Isochrones)")

    def test_task_can_cancel(self):
        """Test that the task is cancellable."""
        task = NativeNetworkAnalysisProcessingTask(
            point_layer=self.point_layer,
            distances=self.distances,
            road_network_path=self.network_layer_path,
            output_gpkg_path=self.output_gpkg_path,
            target_crs=self.crs,
        )
        # Task should be cancellable
        self.assertTrue(task.canCancel())

    def test_constants(self):
        """Test that hardcoded constants are set correctly."""
        self.assertEqual(NativeNetworkAnalysisProcessingTask.POINT_TOLERANCE, 50)
        self.assertEqual(NativeNetworkAnalysisProcessingTask.NETWORK_TOLERANCE, 50)
        self.assertEqual(NativeNetworkAnalysisProcessingTask.STRATEGY, 0)
        self.assertEqual(NativeNetworkAnalysisProcessingTask.DEFAULT_DIRECTION, 2)
        self.assertEqual(NativeNetworkAnalysisProcessingTask.DEFAULT_SPEED, 50)
        self.assertEqual(NativeNetworkAnalysisProcessingTask.INCLUDE_BOUNDS, False)
        self.assertEqual(NativeNetworkAnalysisProcessingTask.CONCAVE_HULL_ALPHA, 0.3)

    @unittest.expectedFailure  # Requires actual network data and QGIS processing environment
    def test_run_with_valid_network(self):
        """Test running the task with valid network data.

        This test is expected to fail in CI/test environments without proper
        network data and full QGIS processing setup.
        """
        # Skip if network layer doesn't exist
        if not os.path.exists(self.network_layer_path):
            self.skipTest("Network test data not available")

        task = NativeNetworkAnalysisProcessingTask(
            point_layer=self.point_layer,
            distances=self.distances,
            road_network_path=self.network_layer_path,
            output_gpkg_path=self.output_gpkg_path,
            target_crs=self.crs,
        )

        # Run the task synchronously
        success = task.run()

        # Verify success
        self.assertTrue(success)
        self.assertIsNotNone(task.result_path)
        self.assertEqual(task.result_path, self.output_gpkg_path)
        self.assertIsNone(task.error_message)

        # Verify output file was created
        self.assertTrue(os.path.exists(self.output_gpkg_path))

        # Verify the GeoPackage contains isochrones
        result_layer = QgsVectorLayer(f"{self.output_gpkg_path}|layername=isochrones", "result", "ogr")
        self.assertTrue(result_layer.isValid())

        # Should have features (3 points × 3 distances = up to 9 isochrones)
        # Some may be skipped if points are too far from network
        feature_count = result_layer.featureCount()
        self.assertGreater(feature_count, 0)
        self.assertLessEqual(feature_count, len(self.distances) * self.point_layer.featureCount())

        # Check that the layer has the expected field
        fields = result_layer.fields()
        self.assertTrue(fields.indexOf("value") >= 0)

        del result_layer

    def test_run_with_empty_point_layer(self):
        """Test that run() returns False with empty point layer."""
        empty_layer = QgsVectorLayer("Point?crs=EPSG:32632", "empty", "memory")

        task = NativeNetworkAnalysisProcessingTask(
            point_layer=empty_layer,
            distances=self.distances,
            road_network_path=self.network_layer_path,
            output_gpkg_path=self.output_gpkg_path,
            target_crs=self.crs,
        )

        success = task.run()

        # Should fail gracefully
        self.assertFalse(success)
        self.assertIsNotNone(task.error_message)
        self.assertIn("No point features", task.error_message)

    def test_cancel_during_processing(self):
        """Test that the task can be cancelled during processing."""
        task = NativeNetworkAnalysisProcessingTask(
            point_layer=self.point_layer,
            distances=self.distances,
            road_network_path=self.network_layer_path,
            output_gpkg_path=self.output_gpkg_path,
            target_crs=self.crs,
        )

        # Cancel immediately
        task.cancel()

        # Task should recognize it's cancelled
        self.assertTrue(task.isCanceled())


if __name__ == "__main__":
    unittest.main()
