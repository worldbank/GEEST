import unittest
import os
from qgis.core import QgsVectorLayer, QgsCoordinateReferenceSystem, QgsApplication
from qgis.analysis import QgsNativeAlgorithms
from processing.core.Processing import Processing
from qgis.core import QgsProcessingFeedback
from qgis_gender_indicator_tool.jobs.rasterization import Rasterizer


class TestRasterizer(unittest.TestCase):
    """Test the Rasterizer class."""

    def setUp(self):
        # Setup real parameters for the Rasterizer class
        self.vector_layer_path = os.path.join(
            os.path.dirname(__file__), "data/admin/Admin0.shp"
        )
        self.output_dir = os.path.join(os.path.dirname(__file__), "output")
        self.pixel_size = 100
        self.utm_crs = QgsCoordinateReferenceSystem("EPSG:32620")  # UTM Zone 20N
        self.field = "score"
        self.dimension = "Contextual"

        # Create the output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

    def test_rasterize_vector_layer(self):
        """
        Test the rasterize_vector_layer method with real data to ensure the rasterization process works.
        """
        # Initialize the Rasterizer class with real parameters
        rasterizer = Rasterizer(
            vector_layer_path=self.vector_layer_path,
            output_dir=self.output_dir,
            pixel_size=self.pixel_size,
            utm_crs=self.utm_crs,
            field=self.field,
            dimension=self.dimension,
        )

        # Load the vector layer and check if it is valid
        rasterizer._load_and_preprocess_vector_layer()  # Assuming this method exists to load the layer
        self.assertTrue(
            rasterizer.vector_layer.isValid(), "The vector layer is not valid"
        )

        # Run the real rasterization process
        rasterizer.rasterize_vector_layer()

        # Check that the rasterized output file was created
        rasterized_output = rasterizer.get_rasterized_layer_path()
        self.assertTrue(
            os.path.exists(rasterized_output), "Rasterized output file does not exist"
        )


if __name__ == "__main__":
    unittest.main()
