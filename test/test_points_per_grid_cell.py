import unittest
import os
from qgis.core import (
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsRectangle,
)
from qgis_gender_indicator_tool.jobs.points_per_grid_cell import (
    RasterFromScore,
)  # Adjust the path to your class


class TestRasterFromScore(unittest.TestCase):
    """Test the RasterFromScore class."""

    def test_raster_from_score(self):
        """
        Test raster generation using the RasterFromScore class.
        """
        self.working_dir = os.path.dirname(__file__)
        self.test_data_dir = os.path.join(self.working_dir, "test_data")

        # Load the input data (points and country boundary layers)
        self.point_layer = QgsVectorLayer(
            os.path.join(self.test_data_dir, "points/points.shp"), "test_points", "ogr"
        )
        self.country_boundary = os.path.join(self.test_data_dir, "admin/Admin0.shp")

        self.assertTrue(self.point_layer.isValid(), "The point layer is not valid.")

        # Define output path for the generated raster
        self.output_path = os.path.join(
            self.working_dir, "output", "test_points_per_grid_cell.tif"
        )
        os.makedirs(os.path.join(self.working_dir, "output"), exist_ok=True)

        # Define CRS (for example UTM Zone 20N)
        self.crs = QgsCoordinateReferenceSystem("EPSG:32620")
        self.pixel_size = 100  # 100m grid

        # Create an instance of the RasterFromScore class
        rasterizer = RasterFromScore(
            country_boundary=self.country_boundary,
            pixel_size=self.pixel_size,
            output_path=self.output_path,
            crs=self.crs,
            input_points=self.point_layer,
        )

        # Run the raster_from_score method
        rasterizer.raster_from_score()

        # Load the generated raster layer to verify its validity
        # Verify that the raster file was created
        self.assertTrue(
            os.path.exists(self.output_path), "The raster output file was not created."
        )
        raster_layer = QgsVectorLayer(self.output_path, "test_raster", "gdal")
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
            3  # Update this with the actual expected value based on your data
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
