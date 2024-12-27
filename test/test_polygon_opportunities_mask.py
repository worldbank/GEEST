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
from geest.core.algorithms import OpportunitiesPolygonMaskProcessingTask


class TestPolygonOpportunitiesMask(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up shared resources for the test suite."""

        cls.working_directory = os.path.join(prepare_fixtures(), "wee_score")
        cls.context = QgsProcessingContext()
        cls.feedback = QgsFeedback()
        cls.mask_areas_path = os.path.join(
            cls.working_directory, "mask", "mask.gpkg|layername=mask"
        )
        cls.study_area_gpkg_path = os.path.join(
            cls.working_directory, "study_area", "study_area.gpkg"
        )

    def setUp(self):
        self.task = OpportunitiesPolygonMaskProcessingTask(
            # geest_raster_path=f"{self.working_directory}/wee_masked_0.tif",
            # pop_raster_path=f"{self.working_directory}/population/reclassified_0.tif",
            study_area_gpkg_path=self.study_area_gpkg_path,
            mask_areas_path=self.mask_areas_path,
            working_directory=self.working_directory,
            target_crs=None,
            force_clear=True,
        )

    def test_initialization(self):
        self.assertTrue(
            self.task.output_dir.endswith("wee_masks"),
            msg=f"Output directory is {self.task.output_dir}",
        )
        self.assertEqual(self.task.target_crs.authid(), "EPSG:32620")

    def test_run_task(self):
        result = self.task.run()
        self.assertTrue(
            result,
            msg=f"Polygon Opportunities Mask Aggregation failed in {self.working_directory}",
        )
