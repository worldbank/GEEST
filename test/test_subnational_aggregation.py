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


@unittest.skip("Skip this test for now")
class TestSubnationalAggregationProcessingTask(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up shared resources for the test suite."""

        cls.working_directory = os.path.join(prepare_fixtures(), "wee_score")
        cls.context = QgsProcessingContext()
        cls.feedback = QgsFeedback()
        cls.aggregation_areas_path = os.path.join(
            cls.working_directory,
            "subnational_aggregation",
            "subnational_aggregation.gpkg|layername=subnational_aggregation",
        )
        cls.study_area_gpkg_path = os.path.join(
            cls.working_directory, "study_area", "study_area.gpkg"
        )

    def setUp(self):
        self.task = SubnationalAggregationProcessingTask(
            # geest_raster_path=f"{self.working_directory}/wee_masked_0.tif",
            # pop_raster_path=f"{self.working_directory}/population/reclassified_0.tif",
            study_area_gpkg_path=self.study_area_gpkg_path,
            aggregation_areas_path=self.aggregation_areas_path,
            working_directory=self.working_directory,
            target_crs=None,
            force_clear=True,
        )

    def test_initialization(self):
        self.assertTrue(
            self.task.output_dir.endswith("subnational_aggregation"),
            msg=f"Output directory is {self.task.output_dir}",
        )
        self.assertEqual(self.task.target_crs.authid(), "EPSG:32620")

    def test_run_task(self):
        result = self.task.run()
        self.assertTrue(
            result, msg=f"Subnational Aggregation failed in {self.working_directory}"
        )
