import unittest
from unittest.mock import MagicMock, patch
from qgis.core import QgsFeature, QgsCoordinateReferenceSystem, QgsPointXY

from geest.core.algorithms.native_network_analysis_processor import (
    NativeNetworkAnalysisProcessor,
)
import os
import tempfile


class TestNativeNetworkAnalysisProcessor(unittest.TestCase):
    def setUp(self):
        # Mock QgsFeature
        # Create an actual QgsFeature
        self.feature = QgsFeature()
        self.feature.setGeometry(
            QgsFeature().geometry().fromPointXY(QgsPointXY(643067.042, 3955294.999))
        )

        # Create an actual CRS
        self.crs = QgsCoordinateReferenceSystem("EPSG:32632")

        # Mock parameters
        self.network_layer_path = os.path.join(
            os.path.dirname(__file__),
            "test_data",
            "network_analysis",
            "network_layer.shp",
        )
        self.mode = "distance"
        self.values = [1000, 2000, 3000]  # Distances in meters
        self.working_directory = tempfile.mkdtemp()
        self.isochrone_layer_path = os.path.join(
            self.working_directory, "isochrone_layer.gpkg"
        )
        # self.addCleanup(lambda: os.rmdir(self.working_directory))
        print(f"Native Network Analysis Working directory: {self.working_directory}")
        # Create an instance of the processor
        self.processor = NativeNetworkAnalysisProcessor(
            network_layer_path=self.network_layer_path,
            isochrone_layer_path=self.isochrone_layer_path,
            area_index=1,
            point_feature=self.feature,
            crs=self.crs,
            mode=self.mode,
            values=self.values,
            working_directory=self.working_directory,
        )

    def test_initialization(self):
        self.assertEqual(self.processor.network_layer_path, self.network_layer_path)
        self.assertEqual(self.processor.feature, self.feature)
        self.assertEqual(self.processor.crs, self.crs)
        self.assertEqual(self.processor.mode, self.mode)
        self.assertEqual(self.processor.values, self.values)
        self.assertEqual(self.processor.working_directory, self.working_directory)

    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            NativeNetworkAnalysisProcessor(
                network_layer_path=self.network_layer_path,
                isochrone_layer_path=self.isochrone_layer_path,
                area_index=1,
                point_feature=self.feature,
                crs=self.crs,
                mode="invalid_mode",
                values=self.values,
                working_directory=self.working_directory,
            )

    def test_invalid_values(self):
        with self.assertRaises(ValueError):
            NativeNetworkAnalysisProcessor(
                network_layer_path=self.network_layer_path,
                isochrone_layer_path=self.isochrone_layer_path,
                area_index=1,
                point_feature=self.feature,
                crs=self.crs,
                mode=self.mode,
                values=[-10, 2000],  # Negative value
                working_directory=self.working_directory,
            )

        with self.assertRaises(ValueError):
            NativeNetworkAnalysisProcessor(
                network_layer_path=self.network_layer_path,
                isochrone_layer_path=self.isochrone_layer_path,
                area_index=1,
                point_feature=self.feature,
                crs=self.crs,
                mode=self.mode,
                values=["1000", 2000],  # Non-integer value
                working_directory=self.working_directory,
            )

    def test_calculate_network(self):
        # Ensure the network layer exists
        self.assertTrue(os.path.exists(self.network_layer_path))

        # Call the actual calculate_network method
        self.processor.calculate_network()

        # Check if the service areas were set correctly
        # There should be one per isochrone distance
        self.assertEqual(
            self.processor.isochrone_feature_count(),
            len(self.values),
        )


if __name__ == "__main__":
    unittest.main()
