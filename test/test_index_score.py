import unittest
import os
from qgis.core import (
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
    QgsRectangle,
    QgsApplication,
)
from qgis_gender_indicator_tool.jobs.index_score import RasterizeIndexScoreValue


class TestRasterizeIndexScoreValue(unittest.TestCase):
    """Test the Rasterizer Index Score class."""

    def test_generate_raster(self):
        """
        Test raster generation using a small sample boundary and score value.
        """
        # Prepare test data
        working_dir = os.path.dirname(__file__)
        boundary_path = os.path.join(working_dir, "data", "admin" "Admin0.shp")
        output_path = os.path.join(working_dir, "output", "test_raster.tif")

        # Ensure output directory exists
        os.makedirs(os.path.join(working_dir, "output"), exist_ok=True)

        # Load the country boundary layer
        country_boundary = QgsVectorLayer(boundary_path, "test_boundary", "ogr")
        self.assertTrue(country_boundary.isValid(), "The boundary layer is not valid.")

        # Define bbox and CRS
        bbox = country_boundary.extent()
        pixelSize = 100  # 100m grid
        crs = QgsCoordinateReferenceSystem("EPSG:32620")  # UTM Zone 20N
        index_value = 80  # Index value
        index_scale = 100

        # Create RasterizeIndexScoreValue instance and generate the raster
        raster_gen = RasterizeIndexScoreValue(
            bbox,
            country_boundary,
            pixelSize,
            output_path,
            crs,
            index_value,
            index_scale,
        )
        raster_layer = raster_gen.generate_raster()

        # Check that the raster file was created
        self.assertTrue(
            os.path.exists(output_path), "The raster output file was not created."
        )
        self.assertTrue(raster_layer.isValid(), "The raster layer is not valid.")

        # Verify the checksum of the generated raster
        checksum = raster_layer.dataProvider().checksum(
            1
        )  # Checksum for the first band
        expected_checksum = 4  # Expected checksum for the test data
        self.assertEqual(
            checksum,
            expected_checksum,
            f"Checksum {checksum} does not match expected {expected_checksum}.",
        )

        # Clean up generated raster
        if os.path.exists(output_path):
            os.remove(output_path)


if __name__ == "__main__":
    unittest.main()
