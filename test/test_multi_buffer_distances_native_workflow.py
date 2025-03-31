import unittest
from qgis.core import QgsVectorLayer, QgsGeometry, QgsPointXY, QgsFeature, QgsField
from qgis.PyQt.QtCore import QVariant
from geest.core.workflows import MultiBufferDistancesNativeWorkflow
from unittest.mock import MagicMock, patch
from geest.core import JsonTreeItem


class TestMultiBufferDistancesNativeWorkflow(unittest.TestCase):
    def setUp(self):

        self.test_data = [
            "Test Item",
            "Configured",
            1.0,
            {  # Attributes dictionary
                "analysis_mode": "use_multibuffer_point",
                "default_factor_weighting": 1.0,
                "default_dimension_weighting": 2.0,
                "default_analysis_weighting": 3.0,
                "description": "Multibuffer Native Test",
                "factor_weighting": 1.0,
                "dimension_weighting": 2.0,
                "analysis_weighting": 3.0,
                "id": "street_crossings",
                "result": "Not Run",
                "multi_buffer_travel_distances": "100,200,300",
                "multi_buffer_shapefile": "/path/to/valid/shapefile.shp",
                "multi_buffer_travel_mode": "Walking",
                "multi_buffer_travel_units": "Distance",
            },
        ]

    def test_creation(self):
        """Test creating a JsonTreeItem instance."""
        # Create JsonTreeItem instances for each level and add children
        analysis_item = JsonTreeItem({"id": "analysis_1"}, "analysis")
        dimension_item = JsonTreeItem({"id": "dimension_1"}, "dimension")
        factor_item = JsonTreeItem({"id": "factor_1"}, "factor")
        indicator_item = JsonTreeItem(
            {
                "id": "indicator_1",
                "role": "indicator",
                "name": "Test Item",
                "status": "Configured",
                "value": 1.0,
                "attributes": {
                    "analysis_mode": "use_multibuffer_point",
                    "default_factor_weighting": 1.0,
                    "default_dimension_weighting": 2.0,
                    "default_analysis_weighting": 3.0,
                    "description": "Multibuffer Native Test",
                    "factor_weighting": 1.0,
                    "dimension_weighting": 2.0,
                    "analysis_weighting": 3.0,
                    "id": "street_crossings",
                    "result": "Not Run",
                    "multi_buffer_travel_distances": "100,200,300",
                    "multi_buffer_shapefile": "/path/to/valid/shapefile.shp",
                    "multi_buffer_travel_mode": "Walking",
                    "multi_buffer_travel_units": "Distance",
                },
            },
            "indicator",
        )

        # Build the tree structure
        factor_item.appendChild(indicator_item)
        dimension_item.appendChild(factor_item)
        analysis_item.appendChild(dimension_item)

        # Assign the top-level item
        self.mock_item = indicator_item
        self.mock_feedback = MagicMock()
        self.mock_context = MagicMock()
        self.mock_working_directory = "/path/to/working/directory"
        self.workflow = MultiBufferDistancesNativeWorkflow(
            item=self.mock_item,
            cell_size_m=10.0,
            feedback=self.mock_feedback,
            context=self.mock_context,
            working_directory=self.mock_working_directory,
        )

    @patch("geest.core.workflows.multi_buffer_distances_native_workflow.QgsVectorLayer")
    def test_create_multibuffers(self, mock_vector_layer):
        # Mock the point layer
        mock_point_layer = MagicMock(spec=QgsVectorLayer)
        mock_point_layer.getFeatures.return_value = [
            QgsFeature(QgsGeometry.fromPointXY(QgsPointXY(0, 0))),
            QgsFeature(QgsGeometry.fromPointXY(QgsPointXY(1, 1))),
        ]
        mock_vector_layer.return_value = mock_point_layer

        # Call the method
        result = self.workflow.create_multibuffers(mock_point_layer)

        # Assert that the result is not False
        self.assertIsNot(result, False)

    @patch("geest.core.workflows.multi_buffer_distances_native_workflow.processing.run")
    def test_merge_layers(self, mock_processing_run):
        # Mock the processing.run output
        mock_processing_run.return_value = {"OUTPUT": "/path/to/merged/layer.shp"}

        # Call the method
        result = self.workflow._merge_layers(layers=[], index=0)

        # Assert that the result is a QgsVectorLayer
        self.assertIsInstance(result, QgsVectorLayer)

    def test_assign_scores(self):
        # Create a mock layer
        mock_layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "test_layer", "memory")
        provider = mock_layer.dataProvider()
        provider.addAttributes([QgsField("distance", QVariant.Int)])
        mock_layer.updateFields()

        # Add mock features
        feature1 = QgsFeature()
        feature1.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(0, 0)))
        feature1.setAttributes([100])
        feature2 = QgsFeature()
        feature2.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(1, 1)))
        feature2.setAttributes([200])
        provider.addFeatures([feature1, feature2])

        # Call the method
        result_layer = self.workflow._assign_scores(mock_layer)

        # Assert that the "value" field is added and populated correctly
        value_index = result_layer.fields().indexFromName("value")
        self.assertNotEqual(value_index, -1)
        for feature in result_layer.getFeatures():
            self.assertIsNotNone(feature["value"])


if __name__ == "__main__":
    unittest.main()
