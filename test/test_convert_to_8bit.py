import os
import unittest
from qgis.core import QgsApplication, QgsRasterLayer, Qgis
from geest.core.convert_to_8bit import RasterConverter


class TestRasterConverter(unittest.TestCase):

    @classmethod
    def setUpClass(self):

        # Define paths to input and output files
        self.input_raster = os.path.join(
            os.path.dirname(__file__), "test_data/rasters/raster.tif"
        )
        self.output_raster = os.path.join(
            os.path.dirname(__file__), "output/output_raster_8bit.tif"
        )

    def test_convert_to_8bit(self):
        """
        Test the convert_to_8bit method of the RasterConverter class.
        """
        # Create an instance of RasterConverter
        converter = RasterConverter()

        # Ensure input file exists before running the test
        self.assertTrue(
            os.path.exists(self.input_raster), "Input raster file does not exist"
        )

        # Check if the input image is 32-bit using QGIS API
        input_layer = QgsRasterLayer(self.input_raster, "Test Raster")
        self.assertTrue(input_layer.isValid(), "Raster layer is not valid")

        # Get the raster band data type
        input_provider = input_layer.dataProvider()
        input_band_data_type = input_provider.dataType(1)

        self.assertEqual(input_band_data_type, Qgis.Float32, "Input raster is 32-bit")

        # Run the conversion
        success = converter.convert_to_8bit(self.input_raster, self.output_raster)

        # Check if the conversion was successful
        self.assertTrue(success, "Raster conversion failed")

        # Check if the output image is 8-bit using QGIS API
        raster_layer = QgsRasterLayer(self.output_raster, "Test Raster")
        self.assertTrue(raster_layer.isValid(), "Raster layer is not valid")

        # Get the raster band data type
        provider = raster_layer.dataProvider()
        band_data_type = provider.dataType(1)

        # Assert if the raster data type is 8-bit
        self.assertEqual(band_data_type, Qgis.Byte, "Output raster is not 8-bit")


if __name__ == "__main__":
    unittest.main()
