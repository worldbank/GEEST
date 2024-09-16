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
from qgis_gender_indicator_tool.jobs.create_grids import GridCreator


class TestGridCreator(unittest.TestCase):
    """Test the GridCreator class."""

    def test_create_grids(self):
        """Test the create_grids method with real data to ensure the grid creation process works."""
        
        # Setup parameters for the GridCreator class
        self.vector_layer_path = os.path.join(
            os.path.dirname(__file__), "data/admin/Admin0.shp"
        )
        self.output_dir = os.path.join(os.path.dirname(__file__), "output")
        self.merged_output_path = os.path.join(self.output_dir, "merged_grid.gpkg")
        self.utm_crs = QgsCoordinateReferenceSystem("EPSG:32620")  # UTM Zone 20N
        self.h_spacing = 100
        self.v_spacing = 100

        # Create the output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
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


if __name__ == "__main__":
    unittest.main()
