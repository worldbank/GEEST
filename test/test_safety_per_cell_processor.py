import unittest
import os
from qgis.core import (
    QgsVectorLayer,
    QgsProcessingException,
    QgsRasterLayer,
    QgsRasterBandStats,
    QgsProcessingContext,
    QgsProject,
)
from geest.core.algorithms.safety_polygon_processor import (
    SafetyPerCellProcessor,
)


class TestSafetyPerCellProcessor(unittest.TestCase):
    def setUp(self):
        """
        Set up the environment for the test, loading the test data layers.
        """
        self.context = QgsProcessingContext()

        # Manually create a QgsProject instance and set it in the context
        self.project = QgsProject.instance()
        self.context.setProject(self.project)
        self.test_data_directory = os.path.join(os.path.dirname(__file__), "test_data")

        # Define paths to test layers
        self.safety_layer_path = os.path.join(
            self.test_data_directory, "safety", "safety.shp"
        )
        self.gpkg_path = os.path.join(
            self.test_data_directory, "study_area", "study_area.gpkg"
        )

        # Load the safety layer and check if it's valid
        self.safety_layer = QgsVectorLayer(
            self.safety_layer_path, "Safety Layer", "ogr"
        )
        if not self.safety_layer.isValid():
            raise QgsProcessingException(
                f"Failed to load safety layer from {self.safety_layer_path}"
            )

        # Define the workflow directory where output files will be saved
        self.workflow_directory = os.path.join(os.path.dirname(__file__), "output")

        # Create the output directory if it doesn't exist
        if not os.path.exists(self.workflow_directory):
            os.makedirs(self.workflow_directory)

        # Initialize the processor with test data
        self.processor = SafetyPerCellProcessor(
            output_prefix="test",
            safety_layer=self.safety_layer,
            safety_field="safety",
            cell_size_m=100.0,
            workflow_directory=self.workflow_directory,
            gpkg_path=self.gpkg_path,
            context=self.context,
        )

    def test_process_areas(self):
        """
        Test the main process_areas function to ensure that areas are processed correctly.
        """
        # Run the processor
        try:
            self.processor.process_areas()

            # Verify if the output raster and VRT files are created
            output_raster = os.path.join(
                self.workflow_directory, "test_safety_raster_0.tif"
            )
            output_vrt = os.path.join(
                self.workflow_directory, "test_safety_combined.vrt"
            )

            self.assertTrue(
                os.path.exists(output_raster), "Output raster was not created."
            )
            self.assertTrue(os.path.exists(output_vrt), "Output VRT was not created.")

            # Load the VRT file as a raster layer
            vrt_layer = QgsRasterLayer(output_vrt, "VRT Layer")

            if not vrt_layer.isValid():
                self.fail(f"Failed to load the VRT file from {output_vrt}")

            # Compute statistics from the raster layer
            stats = vrt_layer.dataProvider().bandStatistics(1, QgsRasterBandStats.All)

            # Check if the statistics are valid and contain expected values
            self.assertIsNotNone(stats, "Failed to compute statistics.")
            self.assertEqual(stats.minimumValue, 0, "Minimum value should be >= 0.")
            self.assertEqual(stats.maximumValue, 5, "Maximum value should be <= 5.")
            self.assertEqual(
                stats.mean, 2.4326080111367063, "Mean value should be > 0."
            )

        except QgsProcessingException as e:
            self.fail(f"Processing failed with exception: {str(e)}")


if __name__ == "__main__":
    unittest.main()
