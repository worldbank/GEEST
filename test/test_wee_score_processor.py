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
from geest.core.algorithms import WEEByPopulationScoreProcessingTask


class TestWEEScoreProcessingTask(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up shared resources for the test suite."""

        cls.test_data_directory = prepare_fixtures()
        cls.working_directory = os.path.join(cls.test_data_directory, "wee_score")

        cls.context = QgsProcessingContext()
        cls.feedback = QgsFeedback()

    def setUp(self):
        self.task = WEEByPopulationScoreProcessingTask(
            # geest_raster_path=f"{self.working_directory}/wee_masked_0.tif",
            # pop_raster_path=f"{self.working_directory}/population/reclassified_0.tif",
            study_area_gpkg_path=f"{self.working_directory}/study_area/study_area.gpkg",
            working_directory=f"{self.working_directory}",
            target_crs=None,
            force_clear=True,
        )

    def test_initialization(self):
        self.assertTrue(
            self.task.output_dir.endswith("wee_by_population_score"),
            msg=f"Output directory is {self.task.output_dir}",
        )
        self.assertEqual(self.task.target_crs.authid(), "EPSG:32620")

    def test_run_task(self):
        result = self.task.run()
        self.assertTrue(result, msg=f"Wee score failed in {self.working_directory}")
