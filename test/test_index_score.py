import unittest
import os
from qgis.core import (
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
    QgsProcessingFeedback,
)
import processing
from geest.core.index_score import RasterizeIndexScoreValue


class TestRasterizeIndexScoreValue(unittest.TestCase):
    """Test the Rasterizer Index Score class."""

    def test_generate_raster(self):
        """
        Test raster generation using a small sample boundary and score value.
        """
        # Prepare test data
        working_dir = os.path.dirname(__file__)
        boundary_path = os.path.join(working_dir, "test_data", "admin", "Admin0.shp")
        output_path = os.path.join(working_dir, "output", "test_raster.tif")

        # Ensure output directory exists
        os.makedirs(os.path.join(working_dir, "output"), exist_ok=True)

        # Load the country boundary layer
        country_boundary = QgsVectorLayer(boundary_path, "test_boundary", "ogr")
        self.assertTrue(country_boundary.isValid(), "The boundary layer is not valid.")

        crs = QgsCoordinateReferenceSystem("EPSG:32620")  # UTM Zone 20N

        # Reproject the vector layer if necessary
        if country_boundary.crs() != crs:
            reprojected_result = processing.run(
                "native:reprojectlayer",
                {
                    "INPUT": country_boundary,
                    "TARGET_CRS": crs,
                    "OUTPUT": "memory:",
                },
                feedback=QgsProcessingFeedback(),
            )
            country_boundary = reprojected_result["OUTPUT"]

        # Define bbox and CRS
        bbox = country_boundary.extent()
        pixel_size = 100  # 100m grid
        crs = QgsCoordinateReferenceSystem("EPSG:32620")  # UTM Zone 20N
        index_value = 80  # Index value
        index_scale = 100

        # Create RasterizeIndexScoreValue instance and generate the raster
        raster_gen = RasterizeIndexScoreValue(
            bbox,
            country_boundary,
            pixel_size,
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
        stats = raster_layer.dataProvider().bandStatistics(
            1
        )  # Checksum for the first band
        # Assert the statistics match expected values
        expected_min = 4
        expected_max = 4
        expected_mean = 4

        self.assertAlmostEqual(
            stats.minimumValue,
            expected_min,
            msg=f"Minimum value does not match: {stats.minimumValue}",
        )
        self.assertAlmostEqual(
            stats.maximumValue,
            expected_max,
            msg=f"Maximum value does not match: {stats.maximumValue}",
        )
        self.assertAlmostEqual(
            stats.mean, expected_mean, msg=f"Mean value does not match: {stats.mean}"
        )


if __name__ == "__main__":
    unittest.main()
