import unittest
import os
from qgis.core import QgsVectorLayer, QgsCoordinateReferenceSystem, QgsApplication, QgsRectangle
from qgis.analysis import QgsNativeAlgorithms
from processing.core.Processing import Processing
from qgis.core import QgsProcessingFeedback
from qgis_gender_indicator_tool.jobs.extents import Extents


class TestExtents(unittest.TestCase):
    """Test the Extents class."""

    def test_get_extent(self):
        """Test the get_country_extent method to ensure extent calculation is correct."""
        
        # Setup parameters for the Extents class
        self.workingDir = os.path.join(os.path.dirname(__file__))
        self.vector_layer_path = os.path.join(
            os.path.dirname(__file__), "data/admin/Admin0.shp"
        )
        self.utm_crs = QgsCoordinateReferenceSystem("EPSG:32620")  # UTM Zone 20N
        self.pixel_size = 100
        
        # Initialize the Extents class
        extents_processor = Extents(
            self.workingDir, self.vector_layer_path, self.pixel_size, self.utm_crs
        )

        # Get the extent of the vector layer
        country_extent = extents_processor.get_country_extent()

        # Check that the extent is a valid QgsRectangle
        self.assertIsInstance(
            country_extent, QgsRectangle, "The extent is not a valid QgsRectangle"
        )
        self.assertGreater(
            country_extent.width(), 0, "Extent width is not greater than zero"
        )
        self.assertGreater(
            country_extent.height(), 0, "Extent height is not greater than zero"
        )


if __name__ == "__main__":
    unittest.main()
