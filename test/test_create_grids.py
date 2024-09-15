import unittest
import os
from qgis.core import (
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
    QgsApplication,
    QgsRectangle,
)
from qgis.analysis import QgsNativeAlgorithms
from processing.core.Processing import Processing
from qgis_processing_test.grid_creator import GridCreator
from qgis_processing_test.extents import Extents


class TestGridCreator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Sets up the QGIS environment before all tests."""
        cls.qgs = QgsApplication([], False)
        cls.qgs.initQgis()
        Processing.initialize()
        QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())

    @classmethod
    def tearDownClass(cls):
        """Cleans up the QGIS environment after all tests."""
        cls.qgs.exitQgis()

    def setUp(self):
        # Setup parameters for the GridCreator class
        self.vector_layer_path = os.path.join(
            os.path.dirname(__file__), "data/polygon/polygon_layer.shp"
        )
        self.output_dir = os.path.join(os.path.dirname(__file__), "output")
        self.merged_output_path = os.path.join(self.output_dir, "merged_grid.gpkg")
        self.utm_crs = QgsCoordinateReferenceSystem("EPSG:32633")  # UTM Zone 33N
        self.h_spacing = 100
        self.v_spacing = 100

        # Create the output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

    def test_create_grids(self):
        """Test the create_grids method with real data to ensure the grid creation process works."""
        # Load the vector layer
        layer = QgsVectorLayer(self.vector_layer_path, "polygon_layer", "ogr")
        self.assertTrue(layer.isValid(), "The vector layer is not valid")

        # Initialize the GridCreator class with the real parameters
        grid_creator = GridCreator(h_spacing=self.h_spacing, v_spacing=self.v_spacing)

        # Run the grid creation process
        merged_grid = grid_creator.create_grids(
            layer, self.output_dir, self.utm_crs, self.merged_output_path
        )

        # Check that the merged grid output file was created
        self.assertTrue(
            os.path.exists(self.merged_output_path),
            "Merged grid output file does not exist",
        )

    def tearDown(self):
        # Clean up after tests by removing the output directory and its contents
        if os.path.exists(self.merged_output_path):
            os.remove(self.merged_output_path)

        if os.path.exists(self.output_dir) and not os.listdir(self.output_dir):
            os.rmdir(self.output_dir)


if __name__ == "__main__":
    unittest.main()
