import unittest
import os
from qgis.core import QgsVectorLayer, QgsCoordinateReferenceSystem
from geest.core.crs_converter import CRSConverter


class TestCRSConverter(unittest.TestCase):

    def setUp(self):
        """
        Setup method that runs before each test. It prepares the environment.
        """
        # Define paths for test data
        self.working_dir = os.path.dirname(__file__)
        self.test_data_dir = os.path.join(self.working_dir, "test_data")

        # Load a test layer from the test data directory
        self.layer = QgsVectorLayer(
            os.path.join(self.test_data_dir, "admin/Admin0.shp"), "test_layer", "ogr"
        )
        self.assertTrue(self.layer.isValid(), "Layer failed to load!")

    def test_crs_conversion(self):
        """
        Test CRS conversion to a different CRS.
        """
        # Create an instance of CRSConverter with the test layer
        converter = CRSConverter(self.layer)

        # Convert the layer to a different CRS (EPSG:3857 "Web Mercator")
        target_epsg = 3857
        reprojected_layer = converter.convert_to_crs(target_epsg)

        # Get the new CRS of the reprojected layer
        new_crs = reprojected_layer.crs()

        # Check if the CRS was converted correctly
        expected_crs = QgsCoordinateReferenceSystem(target_epsg)
        self.assertEqual(
            new_crs.authid(), expected_crs.authid(), "CRS conversion failed!"
        )

    def test_no_conversion_needed(self):
        """
        Test if no conversion is performed when the layer is already in the target CRS.
        """
        # Create an instance of CRSConverter with the test layer
        converter = CRSConverter(self.layer)

        # Convert to the same CRS (EPSG:4326)
        target_epsg = 4326
        reprojected_layer = converter.convert_to_crs(target_epsg)

        # Check that the CRS remains the same
        self.assertEqual(
            reprojected_layer.crs().authid(),
            "EPSG:4326",
            "Layer CRS should remain unchanged!",
        )


if __name__ == "__main__":
    unittest.main()
