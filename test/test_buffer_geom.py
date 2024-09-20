import unittest
import os
from qgis.core import QgsVectorLayer, QgsCoordinateReferenceSystem
from geest.core.buffering import SinglePointBuffer


class TestSinglePointBuffer(unittest.TestCase):
    """Test the SinglePointBuffer class."""

    def test_create_point_buffer(self):
        """
        Test the buffer creation with CRS check and reprojection.
        """
        # Prepare test data
        working_dir = os.path.dirname(__file__)
        input_layer_path = os.path.join(
            working_dir, "test_data", "points", "points.shp"
        )
        output_path = os.path.join(working_dir, "output", "buffered_layer.shp")

        # Ensure output directory exists
        os.makedirs(os.path.join(working_dir, "output"), exist_ok=True)

        # Load the input layer
        input_layer = QgsVectorLayer(input_layer_path, "test_polygon", "ogr")
        self.assertTrue(input_layer.isValid(), "The input layer is not valid.")

        # Define buffer parameters
        buffer_distance = 100  # Buffer distance in CRS units
        expected_crs = QgsCoordinateReferenceSystem("EPSG:32620")  # UTM Zone 20N

        # Create SinglePointBuffer instance and generate the buffer
        buffer_gen = SinglePointBuffer(
            input_layer, buffer_distance, output_path, expected_crs
        )
        buffered_layer = buffer_gen.create_buffer()

        # Check that the buffered layer file was created
        self.assertTrue(
            os.path.exists(output_path), "The buffered output file was not created."
        )
        self.assertTrue(buffered_layer.isValid(), "The buffered layer is not valid.")

        # Clean up generated output
        if os.path.exists(output_path):
            os.remove(output_path)


if __name__ == "__main__":
    unittest.main()
