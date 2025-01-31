import os
import unittest
from qgis.core import (
    QgsProcessingContext,
    QgsFeedback,
)
from geest.core.tasks import (
    StudyAreaProcessingTask,
)  # Adjust the import path as necessary
from utilities_for_testing import prepare_fixtures
from geest.core.algorithms import OpportunitiesMaskProcessor
from geest.core.json_tree_item import JsonTreeItem


@unittest.skip("Skip this test for now")
class TestPolygonOpportunitiesMask(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up shared resources for the test suite."""

        cls.working_directory = os.path.join(prepare_fixtures(), "wee_score")
        cls.context = QgsProcessingContext()
        cls.feedback = QgsFeedback()
        cls.mask_areas_path = os.path.join(
            cls.working_directory, "masks", "polygon_mask.gpkg|layername=polygon_mask"
        )
        cls.study_area_gpkg_path = os.path.join(
            cls.working_directory, "study_area", "study_area.gpkg"
        )

    def setUp(self):
        self.test_data = [
            "Test Item",
            "Configured",
            1.0,
            {
                "name": "polygon_mask",
                "type": "mask",
                "path": self.mask_areas_path,
                "aggregation_layer": None,
                "aggregation_layer_crs": "EPSG:32620",
                "aggregation_layer_id": "admin_2681a7d2_5c5d_4d41_8a0f_74b02334723d",
                "aggregation_layer_name": "admin",
                "aggregation_layer_provider_type": "ogr",
                "aggregation_layer_source": "",
                "aggregation_layer_wkb_type": 6,
                "aggregation_shapefile": "",
                "analysis_cell_size_m": 1000,
                "analysis_mode": "analysis_aggregation",
                "analysis_name": "Women's Economic Empowerment - wee_score",
                "buffer_distance_m": 100,
                "description": "No Description",
                "error": "",
                "error_file": None,
                "execution_end_time": "2025-01-05T09:15:52.503123",
                "execution_start_time": "2025-01-05T09:15:51.664475",
                "mask_mode": "point",
                "opportunities_mask_result": "",
                "opportunities_mask_result_file": "",
                "output_filename": "WEE_Score",
                "point_mask_layer": None,
                "point_mask_layer_crs": "EPSG:32620",
                "point_mask_layer_id": "fake_childcare_6a120423_4837_409e_893c_cc06dd1bde8f",
                "point_mask_layer_name": "fake_childcare",
                "point_mask_layer_provider_type": "ogr",
                "point_mask_layer_source": "",
                "point_mask_layer_wkb_type": 1,
                "point_mask_shapefile": "",
                "polygon_mask_layer": None,
                "polygon_mask_layer_crs": "",
                "polygon_mask_layer_id": "",
                "polygon_mask_layer_name": "",
                "polygon_mask_layer_provider_type": "",
                "polygon_mask_layer_source": "",
                "polygon_mask_layer_wkb_type": "",
                "polygon_mask_shapefile": "",
                "population_layer": None,
                "population_layer_crs": "EPSG:32620",
                "population_layer_id": "reclassified_population_bba75c81_028b_4221_b33f_78c8c31e5e46",
                "population_layer_name": "reclassified_population",
                "population_layer_provider_type": "gdal",
                "population_layer_source": "",
                "population_layer_wkb_type": "",
                "population_shapefile": "",
                "raster_mask_layer": None,
                "raster_mask_layer_crs": "",
                "raster_mask_layer_id": "",
                "raster_mask_layer_name": "",
                "raster_mask_layer_provider_type": "",
                "raster_mask_layer_source": "",
                "raster_mask_layer_wkb_type": "",
                "raster_mask_raster": "",
                "result": "analysis_aggregation Workflow Completed",
                "result_file": "",
                "wee_by_population": "",
                "working_folder": "",
            },
        ]
        self.item = JsonTreeItem(
            self.test_data,
            role="analysis",
        )

        self.task = OpportunitiesMaskProcessor(
            item=self.item,
            study_area_gpkg_path=self.study_area_gpkg_path,
            working_directory=self.working_directory,
            force_clear=True,
            cell_size_m=1000,
        )

    def test_initialization(self):
        self.assertTrue(
            self.task.output_dir.endswith("opportunity_masks"),
            msg=f"Output directory is {self.task.output_dir}",
        )
        self.assertEqual(self.task.target_crs.authid(), "EPSG:32620")

    def test_run_task(self):
        result = self.task.run()
        self.assertTrue(
            result,
            msg=f"Polygon Opportunities Mask Aggregation failed in {self.working_directory}",
        )
