import unittest
import os
from qgis.core import (
    QgsVectorLayer,
    QgsRasterLayer,
    QgsCoordinateReferenceSystem,
)
from geest.core.polylines_per_grid_cell import (
    RasterPolylineGridScore,
)


class TestRasterPolylineGridScore(unittest.TestCase):
    """Test the RasterPolylineGridScore class."""

    def test_raster_polyline_grid_score(self):
        """
        Test raster generation using the RasterPolylineGridScore class.
        """
        self.working_dir = os.path.dirname(__file__)
        self.test_data_dir = os.path.join(self.working_dir, "test_data")
        os.chdir(self.working_dir)

        # Load the input data (polylines and country boundary layers)
        self.polyline_layer = QgsVectorLayer(
            os.path.join(self.test_data_dir, "polylines", "polylines.shp"),
            "test_polylines",
            "ogr",
        )
        self.country_boundary = os.path.join(self.test_data_dir, "admin", "Admin0.shp")

        self.assertTrue(
            self.polyline_layer.isValid(), "The polyline layer is not valid."
        )

        # Define output path for the generated raster
        self.output_path = os.path.join(
            self.working_dir, "output", "rasterized_grid.tif"
        )
        os.makedirs(os.path.join(self.working_dir, "output"), exist_ok=True)

        # Define CRS (for example UTM Zone 20N)
        self.crs = QgsCoordinateReferenceSystem("EPSG:32620")
        self.pixel_size = 100  # 100m grid

        # Create an instance of the RasterPolylineGridScore class
        rasterizer = RasterPolylineGridScore(
            country_boundary=self.country_boundary,
            pixel_size=self.pixel_size,
            working_dir=self.test_data_dir,
            crs=self.crs,
            input_polylines=self.polyline_layer,
            output_path=self.output_path,
        )

        # Run the raster_polyline_grid_score method
        rasterizer.raster_polyline_grid_score()

        # Load the generated raster layer to verify its validity
        self.assertTrue(
            os.path.exists(self.output_path), "The raster output file was not created."
        )
        # self.clipped_output_path = os.path.join(
        #    self.working_dir, "output", "clipped_rasterized_grid.tif"
        # )
        raster_layer = QgsRasterLayer(self.output_path, "test_raster", "gdal")
        self.assertTrue(
            raster_layer.isValid(), "The generated raster layer is not valid."
        )

        # Verify raster statistics (e.g., minimum, maximum, mean)
        stats = raster_layer.dataProvider().bandStatistics(
            1
        )  # Get statistics for the first band
        expected_min = (
            0  # Update this with the actual expected value based on your data
        )
        expected_max = (
            5  # Update this with the actual expected value based on your data
        )

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


if __name__ == "__main__":
    unittest.main()
