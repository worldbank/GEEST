import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from qgis.core import (QgsFeature, QgsFeedback, QgsField, QgsGeometry,
                       QgsPointXY, QgsProcessingContext, QgsVectorLayer)
from qgis.PyQt.QtCore import QVariant
from utilities_for_testing import prepare_fixtures

from geest.core import JsonTreeItem
from geest.core.workflows import MultiBufferDistancesNativeWorkflow


class TestMultiBufferDistancesNativeWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up shared resources for the test suite."""

        cls.test_data_directory = prepare_fixtures()
        cls.working_directory = os.path.join(cls.test_data_directory, "wee_score")

        cls.context = QgsProcessingContext()
        cls.feedback = QgsFeedback()

    def setUp(self):
        self.study_area_gpkg_path = (
            f"{self.working_directory}/study_area/study_area.gpkg",
        )
        self.network_layer_path = os.path.join(
            os.path.dirname(__file__),
            "test_data",
            "network_analysis",
            "network_layer.shp",
        )
        self.points_layer_path = os.path.join(
            os.path.dirname(__file__),
            "test_data",
            "network_analysis",
            "points.shp",
        )

        self.analysis_item = JsonTreeItem(
            {"id": "analysis_1"}, role="analysis", parent=None
        )
        self.dimension_item = JsonTreeItem(
            {"id": "dimension_1"}, role="dimension", parent=self.analysis_item
        )
        self.factor_item = JsonTreeItem(
            {"id": "factor_1"}, role="factor", parent=self.dimension_item
        )
        self.test_data = [
            "Test Item TestMultiBufferDistancesNativeWorkflow",
            "Configured",
            1.0,
            {  # attributes dictionary
                "analysis_mode": "use_multibuffer_point",
                "default_factor_weighting": 1.0,
                "default_dimension_weighting": 1.0,
                "default_analysis_weighting": 1.0,
                "description": "Multibuffer Native Test",
                "factor_weighting": 1.0,
                "dimension_weighting": 1.0,
                "analysis_weighting": 1.0,
                "id": "street_crossings",
                "result": "Not Run",
                "multi_buffer_travel_distances": "1000,2000,3000",
                "multi_buffer_point_shapefile": self.points_layer_path,
                "multi_buffer_travel_mode": "Walking",
                "multi_buffer_travel_units": "Distance",
                "network_layer_path": self.network_layer_path,
            },
        ]
        self.indicator_item = JsonTreeItem(
            self.test_data,
            role="indicator",
            parent=self.factor_item,
        )

    def test_run(self):
        """Test creating a running the workflow."""

        # Assign the top-level item
        self.working_directory = self.working_directory
        self.workflow = MultiBufferDistancesNativeWorkflow(
            item=self.indicator_item,
            cell_size_m=10.0,
            feedback=self.feedback,
            context=self.context,
            working_directory=self.working_directory,
        )
        self.workflow.execute()


if __name__ == "__main__":
    unittest.main()
