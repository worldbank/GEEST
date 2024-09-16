import os
from qgis.core import (
    QgsRasterLayer,
    QgsProcessingFeedback,
    QgsRectangle,
    QgsCoordinateReferenceSystem,
)
import processing


class RasterizeIndexScoreValue:
    def __init__(
        self,
        bbox,
        country_boundary,
        pixelSize,
        output_path,
        crs,
        index_value,
        index_scale=100,
    ):
        """
        Initializes the RasterizeIndexScoreValue class.

        Args:
            bbox (QgsRectangle): The bounding box for the analysis area.
            country_boundary (QgsVectorLayer): A polygon layer defining the country boundary.
            pixelSize (int): The size of each cell in the raster (e.g., 100m).
            output_path (str): Path where the output raster should be saved.
            crs (QgsCoordinateReferenceSystem): CRS for the raster (e.g., UTM).
            index_value (float): The score value to assign to each pixel inside the boundary.
            index_scale (float, optional): The scale factor for the index value. Defaults to 100.
        """
        self.bbox = bbox
        self.country_boundary = country_boundary
        self.pixelSize = pixelSize
        self.output_path = output_path
        self.crs = crs
        self.index_value = index_value
        self.index_scale = index_scale

    def generate_raster(self):
        """
        Generates a raster from the score value within the country boundary.

        Returns:
            QgsRasterLayer: The resulting raster layer.
        """
        # Check if the output file already exists and delete it if necessary
        if os.path.exists(self.output_path):
            print(
                f"Warning: {self.output_path} already exists. It will be overwritten."
            )
            os.remove(self.output_path)

        # Calculate the raster value based on index_value and index_scale
        raster_value = int(self.index_value / self.index_scale) * 5

        # Create a temporary raster filled with the raster_value
        extent_str = f"{self.bbox.xMinimum()},{self.bbox.xMaximum()},{self.bbox.yMinimum()},{self.bbox.yMaximum()}"
        temp_raster_path = os.path.join(
            os.path.dirname(self.output_path), "temp_raster.tif"
        )

        # Use QGIS processing tool 'gdal:rasterize' to create the grid
        processing.run(
            "gdal:rasterize",
            {
                "INPUT": self.country_boundary,
                "FIELD": None,
                "BURN": raster_value,  # Burn the score value
                "UNITS": 1,  # Pixel size in CRS units
                "WIDTH": self.pixelSize,
                "HEIGHT": self.pixelSize,
                "EXTENT": extent_str,
                "NODATA": -9999,  # NoData value for non-land pixels
                "DATA_TYPE": 5,  # Float32
                "OUTPUT": temp_raster_path,
                "CRS": self.crs,
            },
            feedback=QgsProcessingFeedback(),
        )

        # Load the output raster as a QgsRasterLayer
        raster_layer = QgsRasterLayer(temp_raster_path, "generated_raster")

        if not raster_layer.isValid():
            raise ValueError("Raster layer creation failed.")

        return raster_layer
