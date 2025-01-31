import unittest
import os
from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsProcessingContext, QgsProject

# from geest.core.algorithms import SafetyRasterReclassificationProcessor
from utilities_for_testing import prepare_fixtures


@unittest.skip("Skip the test for now")
class TestRasterReclassificationProcessor(unittest.TestCase):
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
            self.test_data_directory, "rasters", "NTL.tif"
        )
        self.gpkg_path = os.path.join(
            self.test_data_directory, "study_area", "study_area.gpkg"
        )

        # Load the input raster and grid layer
        self.input_raster = QgsRasterLayer(self.input_raster_path, "Input Raster")
        self.grid_layer = QgsVectorLayer(
            f"{self.gpkg_path}|layername=study_area_grid", "Grid Layer", "ogr"
        )

        # Ensure the input layers are valid
        self.assertTrue(self.input_raster.isValid(), "Failed to load input raster.")
        self.assertTrue(self.grid_layer.isValid(), "Failed to load grid layer.")

        # Set the output VRT path
        self.output_vrt = os.path.join(
            self.output_directory, "safety_reclass_output.vrt"
        )

        # Set the pixel size (example: 100 meters)
        self.pixel_size = 100.0

        # Initialize the processor with test data
        self.processor = SafetyRasterReclassificationProcessor(
            output_prefix="safety",
            input_raster=self.input_raster_path,
            pixel_size=self.pixel_size,
            gpkg_path=self.gpkg_path,
            grid_layer=self.grid_layer,
            workflow_directory=self.output_directory,
            context=self.context,
        )

    def test_reclassify(self):
        """
        Test the main reclassify function to ensure that the raster is reclassified
        and the VRT output is generated correctly.
        """
        # Run the processor
        self.processor.process_areas()

        # Check if the VRT output file was created
        self.assertTrue(
            os.path.exists(self.output_vrt), "The VRT output was not created."
        )

        # Verify the content of the output VRT (ensure it's a valid VRT)
        vrt_layer = QgsRasterLayer(self.output_vrt, "Reclassified VRT")
        self.assertTrue(vrt_layer.isValid(), "The generated VRT is invalid.")


if __name__ == "__main__":
    unittest.main()
