import unittest
from geest.core.algorithms import Pop


class TestPopulationRasterProcessingTask(unittest.TestCase):
    def test_population_raster_processing(self):
        """
        Tests the PopulationRasterProcessingTask for expected behavior.
        """
        task = PopulationRasterProcessingTask(
            name="Test Population Raster Processing",
            population_raster_path="test_population.tif",
            study_area_gpkg_path="test_study_area.gpkg",
            output_dir="test_output",
            force_clear=True,
        )

        result = task.run()
        self.assertTrue(result, "Task did not complete successfully.")

        # Check that output files exist
        output_files = os.listdir(os.path.join("test_output", "population"))
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
