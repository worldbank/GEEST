import unittest
import os
from qgis.core import (
    QgsVectorLayer,
    QgsRasterLayer,
    QgsCoordinateReferenceSystem,
)
from geest.core.polygons_per_grid_cell import (
    RasterPolygonGridScore,
)  # Adjust the path to your class


class TestRasterPolygonGridScore(unittest.TestCase):
    """Test the RasterPolygonGridScore class."""

    def test_raster_polygon_grid_score(self):
        """
        Test raster generation using the RasterPolygonGridScore class.
        """
        self.working_dir = os.path.dirname(__file__)
        self.test_data_dir = os.path.join(self.working_dir, "test_data")
        os.chdir(self.working_dir)

        # Load the input data (polygons and country boundary layers)
        self.polygon_layer = QgsVectorLayer(
            os.path.join(self.test_data_dir, "polygons/blocks.shp"),
            "test_polygons",
            "ogr",
        )
        self.country_boundary = os.path.join(self.test_data_dir, "admin/Admin0.shp")

        self.assertTrue(self.polygon_layer.isValid(), "The polygon layer is not valid.")

        # Define output path for the generated raster
        self.output_path = os.path.join(
            self.working_dir, "output", "test_polygons_per_grid_cell.tif"
        )
        os.makedirs(os.path.join(self.working_dir, "output"), exist_ok=True)

        # Define CRS (for example UTM Zone 20N)
        self.crs = QgsCoordinateReferenceSystem("EPSG:32620")
        self.pixel_size = 100  # 100m grid

        # Create an instance of the RasterPolygonGridScore class
        rasterizer = RasterPolygonGridScore(
            country_boundary=self.country_boundary,
            pixel_size=self.pixel_size,
            output_path=self.output_path,
            crs=self.crs,
            input_polygons=self.polygon_layer,
        )

        # Run the raster_polygon_grid_score method
        rasterizer.raster_polygon_grid_score()

        # Load the generated raster layer to verify its validity
        # Verify that the raster file was created
        self.assertTrue(
            os.path.exists(self.output_path), "The raster output file was not created."
        )
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
