import os
import unittest
import unittest
import os
from qgis.core import QgsProcessingContext, QgsProject, QgsCoordinateReferenceSystem
from geest.core.algorithms import PopulationRasterProcessingTask
from utilities_for_testing import prepare_fixtures


class TestPopulationRasterProcessingTask(unittest.TestCase):
    def setUp(self):
        """
        Set up the environment for the test, loading the test data layers.
        """
        self.context = QgsProcessingContext()
        # Manually create a QgsProject instance and set it in the context
        self.project = QgsProject.instance()
        self.context.setProject(self.project)

        # Define working directories
        self.test_data_directory = prepare_fixtures()
        self.output_directory = os.path.join(self.test_data_directory, "output")

        # Create the output directory if it doesn't exist
        if not os.path.exists(self.output_directory):
            os.makedirs(self.output_directory)

        # Define paths to test layers
        self.input_raster_path = os.path.join(
            self.test_data_directory, "population", "population.tif"
        )
        self.gpkg_path = os.path.join(
            self.test_data_directory, "study_area", "study_area.gpkg"
        )

    @unittest.skip("Skip this test for now")
    def test_population_raster_processing(self):
        """
        Tests the PopulationRasterProcessingTask for expected behavior.
        """
        task = PopulationRasterProcessingTask(
            population_raster_path=self.input_raster_path,
            study_area_gpkg_path=self.gpkg_path,
            working_directory=self.output_directory,
            force_clear=True,
            cell_size_m=100,
        )

        result = task.run()
        self.assertTrue(result, "Task did not complete successfully.")

        # Check that output files exist
        output_files = os.listdir(os.path.join(self.output_directory, "population"))
        self.assertTrue(
            any(f.startswith("clipped_") for f in output_files),
            "Clipped rasters not created.",
        )
        self.assertTrue(
            any(f.startswith("reclassified_") for f in output_files),
            "Reclassified rasters not created.",
        )
        self.assertTrue(
            "clipped_population.vrt" in output_files, "Clipped VRT not created."
        )
        self.assertTrue(
            "reclassified_population.vrt" in output_files,
            "Reclassified VRT not created.",
        )

        # Verify global min and max
        self.assertLess(
            task.global_min,
            task.global_max,
            "Global min should be less than global max.",
        )


if __name__ == "__main__":
    unittest.main()
