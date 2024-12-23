import os
import unittest
from qgis.core import (
    QgsVectorLayer,
    QgsProcessingContext,
    QgsFeedback,
)
from geest.core.tasks import (
    StudyAreaProcessingTask,
)  # Adjust the import path as necessary
from utilities_for_testing import prepare_fixtures
from geest.core.algorithms import SubnationalAggregationProcessingTask


class TestSubnationalAggregationProcessingTask(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up shared resources for the test suite."""

        cls.test_data_directory = prepare_fixtures()
        cls.working_directory = os.path.join(
            cls.test_data_directory, "subnational_aggregation"
        )

        cls.context = QgsProcessingContext()
        cls.feedback = QgsFeedback()

    def setUp(self):
        self.task = SubnationalAggregationProcessingTask(
            # geest_raster_path=f"{self.working_directory}/wee_masked_0.tif",
            # pop_raster_path=f"{self.working_directory}/population/reclassified_0.tif",
            study_area_gpkg_path=f"{self.working_directory}/study_area/study_area.gpkg",
            aggregation_areas_path=f"{self.working_directory}/aggregation/boundaries.gpkg|layername=boundaries",
            working_directory=f"{self.working_directory}",
            target_crs=None,
            force_clear=True,
        )

    def test_initialization(self):
        self.assertTrue(self.task.output_dir.endswith("wee_score"))
        self.assertEqual(self.task.target_crs.authid(), "EPSG:32620")

    def test_run_task(self):
        result = self.task.run()
        self.assertTrue(
            result, msg=f"Subnational Aggregation failed in {self.working_directory}"
        )
