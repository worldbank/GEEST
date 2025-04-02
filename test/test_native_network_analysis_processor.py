import unittest
from unittest.mock import MagicMock, patch
from qgis.core import QgsFeature, QgsCoordinateReferenceSystem
from geest.core.algorithms.native_network_analysis_processor import (
    NativeNetworkAnalysisProcessor,
)


class TestNativeNetworkAnalysisProcessor(unittest.TestCase):
    def setUp(self):
        # Mock QgsFeature
        self.mock_feature = MagicMock(spec=QgsFeature)
        self.mock_feature.id.return_value = 1

        # Mock CRS
        self.mock_crs = MagicMock(spec=QgsCoordinateReferenceSystem)
        self.mock_crs.authid.return_value = "4326"

        # Mock parameters
        self.network_layer_path = "/path/to/network_layer.gpkg"
        self.mode = "distance"
        self.value = 3000  # 3km
        self.working_directory = "/path/to/working_directory"

        # Create an instance of the processor
        self.processor = NativeNetworkAnalysisProcessor(
            network_layer_path=self.network_layer_path,
            feature=self.mock_feature,
            crs=self.mock_crs,
            mode=self.mode,
            value=self.value,
            working_directory=self.working_directory,
        )

    def test_initialization(self):
        self.assertEqual(self.processor.network_layer_path, self.network_layer_path)
        self.assertEqual(self.processor.feature, self.mock_feature)
        self.assertEqual(self.processor.crs, self.mock_crs)
        self.assertEqual(self.processor.mode, self.mode)
        self.assertEqual(self.processor.value, self.value)
        self.assertEqual(self.processor.working_directory, self.working_directory)

    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            NativeNetworkAnalysisProcessor(
                network_layer_path=self.network_layer_path,
                feature=self.mock_feature,
                crs=self.mock_crs,
                mode="invalid_mode",
                value=self.value,
                working_directory=self.working_directory,
            )

    def test_invalid_value(self):
        with self.assertRaises(ValueError):
            NativeNetworkAnalysisProcessor(
                network_layer_path=self.network_layer_path,
                feature=self.mock_feature,
                crs=self.mock_crs,
                mode=self.mode,
                value=-10,
                working_directory=self.working_directory,
            )

    @patch("geest.core.algorithms.native_network_analysis_processor.processing.run")
    def test_calculate_network(self, mock_processing_run):
        # Mock processing.run outputs
        mock_processing_run.side_effect = [
            {"OUTPUT": "service_area_output"},
            {"OUTPUT": "multipart_output"},
            {
                "OUTPUT": MagicMock(
                    featureCount=MagicMock(return_value=1),
                    getFeature=MagicMock(return_value="mock_feature"),
                )
            },
        ]

        self.processor.calculate_network()

        # Check if processing.run was called three times
        self.assertEqual(mock_processing_run.call_count, 3)

        # Check if the service area was set
        self.assertEqual(self.processor.service_area, "mock_feature")

    @patch("geest.core.algorithms.native_network_analysis_processor.log_message")
    def test_run_success(self, mock_log_message):
        with patch.object(self.processor, "calculate_network", return_value=None):
            result = self.processor.run()
            self.assertTrue(result)
            mock_log_message.assert_any_call(
                "Initialized Native Network Analysis Processing Task"
            )

    @patch("geest.core.algorithms.native_network_analysis_processor.log_message")
    def test_run_failure(self, mock_log_message):
        with patch.object(
            self.processor, "calculate_network", side_effect=Exception("Test exception")
        ):
            result = self.processor.run()
            self.assertFalse(result)
            mock_log_message.assert_any_call("Task failed: Test exception")

    @patch("geest.core.algorithms.native_network_analysis_processor.log_message")
    def test_finished_success(self, mock_log_message):
        self.processor.finished(True)
        mock_log_message.assert_any_call(
            "Native Network Analysis Processing Task calculation completed successfully."
            "Access the service area feature using the 'service_area' attribute."
        )

    @patch("geest.core.algorithms.native_network_analysis_processor.log_message")
    def test_finished_failure(self, mock_log_message):
        self.processor.finished(False)
        mock_log_message.assert_any_call(
            "Native Network Analysis Processing Task calculation failed."
        )


if __name__ == "__main__":
    unittest.main()
