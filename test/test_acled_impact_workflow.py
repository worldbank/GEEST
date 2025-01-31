import unittest
import os
from unittest.mock import patch, MagicMock, mock_open
from qgis.core import QgsVectorLayer
from geest.core import JsonTreeItem
from geest.core.workflows import AcledImpactWorkflow
from utilities_for_testing import prepare_fixtures


class TestAcledImpactWorkflow(unittest.TestCase):
    """Tests for the AcledImpactWorkflow class."""

    def setUp(self):
        """Set up test data."""
        # Mock JsonTreeItem with required attributes
        self.mock_item = MagicMock(spec=JsonTreeItem)
        self.mock_item.attributes = {
            "use_csv_to_point_layer_csv_file": "mock_csv_file.csv",
            "id": "TestLayer",
        }

        # Mock QgsProcessingContext and QgsFeedback
        self.mock_context = MagicMock()
        self.mock_feedback = MagicMock()

        # Define working directories
        self.test_data_directory = prepare_fixtures()
        self.working_directory = os.path.join(self.test_data_directory, "output")

        # Create the output directory if it doesn't exist
        if not os.path.exists(self.working_directory):
            os.makedirs(self.working_directory)

    @unittest.skip("This test is not ready")
    @patch("geest.workflow.AcledImpactWorkflow._load_csv_as_point_layer")
    def test_workflow_initialization_valid_csv(self, mock_load_csv):
        """Test initialization with a valid CSV file."""
        mock_layer = MagicMock(spec=QgsVectorLayer)
        mock_layer.isValid.return_value = True
        mock_load_csv.return_value = mock_layer

        workflow = AcledImpactWorkflow(
            self.mock_item,
            cell_size_m=1000,
            feedback=self.mock_feedback,
            context=self.mock_context,
            working_directory=self.working_directory,
        )

        self.assertEqual(workflow.csv_file, "mock_csv_file.csv")
        self.assertTrue(workflow.features_layer.isValid())
        mock_load_csv.assert_called_once()

    @unittest.skip("This test is not ready")
    @patch("geest.workflow.AcledImpactWorkflow._load_csv_as_point_layer")
    def test_workflow_initialization_invalid_csv(self, mock_load_csv):
        """Test initialization with an invalid CSV file."""
        mock_layer = MagicMock(spec=QgsVectorLayer)
        mock_layer.isValid.return_value = False
        mock_load_csv.return_value = mock_layer

        with self.assertRaises(Exception) as cm:
            AcledImpactWorkflow(
                self.mock_item,
                cell_size_m=1000,
                feedback=self.mock_feedback,
                context=self.mock_context,
                working_directory=self.working_directory,
            )

        self.assertIn("ACLED CSV layer is not valid", str(cm.exception))

    @unittest.skip("This test is not ready")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="latitude,longitude,event_type\n0,0,TestEvent",
    )
    @patch("qgis.core.QgsVectorFileWriter.writeAsVectorFormat")
    @patch("qgis.core.QgsCoordinateTransform.transform")
    def test_load_csv_as_point_layer(self, mock_transform, mock_writer, mock_open_file):
        """Test the loading of CSV as a point layer."""
        # Mock CRS and transform
        mock_transform.return_value = MagicMock()

        # Mock context.project().transformContext()
        self.mock_context.project().transformContext.return_value = MagicMock()

        # Create workflow and call _load_csv_as_point_layer
        workflow = AcledImpactWorkflow(
            self.mock_item,
            cell_size_m=1000,
            feedback=self.mock_feedback,
            context=self.mock_context,
            working_directory=self.working_directory,
        )

        with patch.object(
            workflow, "target_crs", MagicMock(authid=lambda: "EPSG:4326")
        ):
            layer = workflow._load_csv_as_point_layer()

        self.assertIsInstance(layer, QgsVectorLayer)
        mock_open_file.assert_called_once_with(
            "mock_csv_file.csv", newline="", encoding="utf-8"
        )
        mock_writer.assert_called_once()

    @unittest.skip("This test is not ready")
    @patch("geest.workflow.AcledImpactWorkflow._buffer_features")
    @patch("geest.workflow.AcledImpactWorkflow._assign_scores")
    @patch("geest.workflow.AcledImpactWorkflow._overlay_analysis")
    @patch("geest.workflow.AcledImpactWorkflow._rasterize")
    def test_process_features_for_area(
        self, mock_rasterize, mock_overlay, mock_scores, mock_buffer
    ):
        """Test the processing of features for an area."""
        mock_geometry = MagicMock()
        mock_layer = MagicMock(spec=QgsVectorLayer)
        mock_buffer.return_value = mock_layer
        mock_scores.return_value = mock_layer
        mock_overlay.return_value = mock_layer
        mock_rasterize.return_value = "mock_raster.tif"

        workflow = AcledImpactWorkflow(
            self.mock_item,
            cell_size_m=1000,
            feedback=self.mock_feedback,
            context=self.mock_context,
            working_directory=self.working_directoryConfigured,
        )

        result = workflow._process_features_for_area(
            mock_geometry, mock_geometry, mock_layer, 0
        )
        self.assertEqual(result, "mock_raster.tif")
        mock_buffer.assert_called_once()
        mock_scores.assert_called_once()
        mock_overlay.assert_called_once()
        mock_rasterize.assert_called_once()

    @unittest.skip("This test is not ready")
    def test_workflow_fails_without_csv(self):
        """Test initialization without a CSV file."""
        self.mock_item.attributes.pop("use_csv_to_point_layer_csv_file")

        with self.assertRaises(Exception) as cm:
            AcledImpactWorkflow(
                self.mock_item,
                cell_size_m=1000,
                feedback=self.mock_feedback,
                context=self.mock_context,
                working_directory=self.working_directory,
            )
        self.assertIn("No CSV file provided.", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
