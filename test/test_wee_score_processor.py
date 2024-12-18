import unittest
from geest.core.algorithms import WEEScoreProcessingTask


class TestWEEScoreProcessingTask(unittest.TestCase):
    def setUp(self):
        self.task = WEEScoreProcessingTask(
            geest_raster_path="test_data/wee_score/wee_masked_0.tif",
            pop_raster_path="test_data/wee_score/reclassified_0.tif",
            study_area_gpkg_path="test_data/wee_score/study_area/study_area.gpkg",
            working_directory="/tmp",
            target_crs=None,
            force_clear=True,
        )

    def test_initialization(self):
        self.assertTrue(self.task.output_dir.endswith("wee_score"))
        self.assertEqual(self.task.target_crs.authid(), "EPSG:4326")

    def test_run_task(self):
        result = self.task.run()
        self.assertTrue(result)
