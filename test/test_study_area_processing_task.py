import os
import unittest
from qgis.core import (
    QgsVectorLayer,
    QgsFeedback,
)
from geest.core.tasks import (
    StudyAreaProcessingTask,
)  # Adjust the import path as necessary
from utilities_for_testing import prepare_fixtures


class TestStudyAreaProcessingTask(unittest.TestCase):
    """Test suite for the StudyAreaProcessingTask class."""

    @classmethod
    def setUpClass(cls):
        """Set up shared resources for the test suite."""

        cls.test_data_directory = prepare_fixtures()
        cls.working_directory = os.path.join(cls.test_data_directory, "output")

        # Create the output directory if it doesn't exist
        if not os.path.exists(cls.working_directory):
            os.makedirs(cls.working_directory)

        cls.layer_path = os.path.join(
            cls.test_data_directory, "admin", "fake_admin0.gpkg"
        )
        cls.field_name = "Name"
        cls.cell_size_m = 100
        cls.feedback = QgsFeedback()

        # Ensure the working directory exists
        if not os.path.exists(cls.working_directory):
            os.makedirs(cls.working_directory)

        # Load the test layer
        cls.layer = QgsVectorLayer(cls.layer_path, "Test Layer", "ogr")
        if not cls.layer.isValid():
            raise RuntimeError(f"Failed to load test layer from {cls.layer_path}")

    def setUp(self):
        """Set up test-specific resources."""
        # Clean up the output directory before each test
        for filename in os.listdir(self.working_directory):
            file_path = os.path.join(self.working_directory, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

    def test_initialization(self):
        """Test initialization of the task."""
        task = StudyAreaProcessingTask(
            layer=self.layer,
            field_name=self.field_name,
            cell_size_m=self.cell_size_m,
            working_dir=self.working_directory,
            parent_job_feedback=self.feedback,
        )

        self.assertEqual(task.layer, self.layer)
        self.assertEqual(task.field_name, self.field_name)
        self.assertEqual(task.cell_size_m, self.cell_size_m)
        self.assertEqual(task.working_dir, self.working_directory)
        self.assertTrue(
            os.path.exists(os.path.join(self.working_directory, "study_area"))
        )

    def test_calculate_utm_zone(self):
        """Test UTM zone calculation."""
        task = StudyAreaProcessingTask(
            layer=self.layer,
            field_name=self.field_name,
            cell_size_m=self.cell_size_m,
            working_dir=self.working_directory,
            parent_job_feedback=self.feedback,
        )

        bbox = self.layer.extent()
        utm_zone = task.calculate_utm_zone(bbox)

        # Validate the calculated UTM zone (adjust based on test data location)
        self.assertTrue(utm_zone >= 32600 or utm_zone >= 32700)

    def test_process_study_area(self):
        """Test processing of study area features."""
        task = StudyAreaProcessingTask(
            layer=self.layer,
            field_name=self.field_name,
            cell_size_m=self.cell_size_m,
            working_dir=self.working_directory,
            parent_job_feedback=self.feedback,
        )

        result = task.process_study_area()
        self.assertTrue(result)

        # Validate output GeoPackage
        gpkg_path = os.path.join(
            self.working_directory, "study_area", "study_area.gpkg"
        )
        self.assertTrue(
            os.path.exists(gpkg_path),
            msg=f"GeoPackage not created in {self.working_directory}",
        )

    def test_process_singlepart_geometry(self):
        """Test processing of singlepart geometry."""
        task = StudyAreaProcessingTask(
            layer=self.layer,
            field_name=self.field_name,
            cell_size_m=self.cell_size_m,
            working_dir=self.working_directory,
            parent_job_feedback=self.feedback,
        )

        feature = next(self.layer.getFeatures())
        task.process_singlepart_geometry(feature.geometry(), "test_area", "Test Area")

        # Validate GeoPackage outputs
        gpkg_path = os.path.join(
            self.working_directory, "study_area", "study_area.gpkg"
        )
        self.assertTrue(
            os.path.exists(gpkg_path),
            msg=f"GeoPackage not created in {self.working_directory}",
        )
        # Validate mask is a valid file
        mask_path = os.path.join(
            self.working_directory, "study_area", "saint_lucia_part0.tif"
        )
        self.assertTrue(
            os.path.exists(mask_path),
            msg=f"mask saint_lucia_part0.tif not created in {mask_path}",
        )

    def test_grid_aligned_bbox(self):
        """Test grid alignment of bounding boxes."""
        task = StudyAreaProcessingTask(
            layer=self.layer,
            field_name=self.field_name,
            cell_size_m=self.cell_size_m,
            working_dir=self.working_directory,
            parent_job_feedback=self.feedback,
        )

        bbox = self.layer.extent()
        aligned_bbox = task.grid_aligned_bbox(bbox)

        # Validate grid alignment
        self.assertAlmostEqual(
            (aligned_bbox.xMaximum() - aligned_bbox.xMinimum()) % self.cell_size_m, 0
        )
        self.assertAlmostEqual(
            (aligned_bbox.yMaximum() - aligned_bbox.yMinimum()) % self.cell_size_m, 0
        )

    def test_create_raster_vrt(self):
        """Test creation of a VRT from raster masks."""
        task = StudyAreaProcessingTask(
            layer=self.layer,
            field_name=self.field_name,
            cell_size_m=self.cell_size_m,
            working_dir=self.working_directory,
            parent_job_feedback=self.feedback,
        )

        # Generate raster masks
        task.process_study_area()

        # Create VRT
        task.create_raster_vrt()

        # Validate VRT file
        vrt_path = os.path.join(
            self.working_directory, "study_area", "combined_mask.vrt"
        )
        self.assertTrue(
            os.path.exists(vrt_path),
            msg=f"VRT file not created in {self.working_directory}",
        )

    @classmethod
    def tearDownClass(cls):
        """Clean up shared resources."""
        cleanup = False
        if os.path.exists(cls.working_directory) and cleanup:
            for root, dirs, files in os.walk(cls.working_directory, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))


if __name__ == "__main__":
    unittest.main()
