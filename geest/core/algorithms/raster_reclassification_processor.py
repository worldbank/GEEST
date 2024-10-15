from qgis.core import (
    QgsRasterLayer,
    QgsProcessingFeedback,
    QgsCoordinateReferenceSystem,
    QgsRectangle,
)
from qgis.analysis import QgsRasterCalculatorEntry
import os
import processing
from .area_iterator import AreaIterator  # Import your area iterator


class RasterReclassificationProcessor:
    """
    A processor to reclassify raster values based on predefined rules for each area in a grid.
    The output is a VRT that combines all the reclassified raster tiles for each area.
    """

    def __init__(
        self,
        input_raster,
        output_vrt,
        reclassification_rules,
        pixel_size,
        gpkg_path,
        grid_layer,
        workflow_directory,
    ):
        """
        Initialize the RasterReclassificationProcessor.

        Args:
            input_raster (str): Path to the input raster file.
            output_vrt (str): Path to save the final VRT file.
            reclassification_rules (dict): Dictionary of reclassification rules.
            pixel_size (float): The pixel size for the output raster.
            gpkg_path (str): Path to the GeoPackage with study areas.
            grid_layer (QgsVectorLayer): The grid layer defining the extent and CRS.
            workflow_directory (str): Directory where intermediate files and the final VRT will be saved.
        """
        self.input_raster = input_raster
        self.output_vrt = output_vrt
        self.reclassification_rules = reclassification_rules
        self.pixel_size = pixel_size
        self.gpkg_path = gpkg_path
        self.grid_layer = grid_layer
        self.workflow_directory = workflow_directory
        self.crs = grid_layer.crs()  # CRS is derived from the grid layer
        self.area_iterator = AreaIterator(gpkg_path)  # Initialize the area iterator

    def reclassify(self):
        """
        Reclassify the input raster for each area and combine the results into a VRT.
        """
        feedback = QgsProcessingFeedback()
        temp_rasters = []

        # Iterate over each area from the AreaIterator
        for index, (current_area, current_bbox, progress) in enumerate(
            self.area_iterator
        ):
            feedback.pushInfo(
                f"Processing area {index + 1} with progress {progress:.2f}%"
            )

            # Use the current_bbox (bounding box of the area) for reclassification
            reprojected_raster = self._reproject_and_clip_raster(
                self.input_raster, current_bbox, index
            )

            # Apply the reclassification rules
            reclassified_raster = self._apply_reclassification(
                reprojected_raster, index
            )
            temp_rasters.append(reclassified_raster)

        # Combine the reclassified rasters into a VRT
        self._combine_rasters_to_vrt(temp_rasters)

        print(f"Reclassified VRT saved to: {self.output_vrt}")

    def _reproject_and_clip_raster(self, raster_path, bbox, index):
        """
        Reproject and clip the raster to the bounding box of the current area.
        """
        # Convert the bbox to QgsRectangle
        bbox = bbox.boundingBox()

        reprojected_raster = os.path.join(
            self.workflow_directory, f"temp_reprojected_{index}.tif"
        )

        params = {
            "INPUT": raster_path,
            "TARGET_CRS": self.crs,
            "RESAMPLING": 0,
            "NODATA": 255,
            "TARGET_RESOLUTION": self.pixel_size,
            "OUTPUT": reprojected_raster,
            "TARGET_EXTENT": f"{bbox.xMinimum()},{bbox.xMaximum()},{bbox.yMinimum()},{bbox.yMaximum()} [{self.crs.authid()}]",
        }

        processing.run("gdal:warpreproject", params, feedback=QgsProcessingFeedback())

        return reprojected_raster

    def _build_reclassification_expression(self, input_raster):
        """
        Build the raster calculator expression based on the reclassification rules.
        """
        # Get the file name without extension
        file_name = os.path.splitext(os.path.basename(input_raster))[0]

        expression_parts = []

        for (
            lower_bound,
            upper_bound,
        ), new_value in self.reclassification_rules.items():
            expression_parts.append(
                f"({file_name}@1 >= {lower_bound} AND {file_name}@1 <= {upper_bound}) * {new_value}"
            )

        reclass_expression = " + ".join(expression_parts)
        return reclass_expression

    def _apply_reclassification(self, input_raster, index):
        """
        Apply the reclassification using the raster calculator and save the output.
        """

        # Build the reclassification expression
        expression = self._build_reclassification_expression(input_raster)

        reclassified_raster = os.path.join(
            self.workflow_directory, f"reclassified_{index}.tif"
        )

        # Define the input raster layer
        raster_layer = QgsRasterLayer(input_raster, f"Reprojected Raster {index}")

        if not raster_layer.isValid():
            raise Exception(f"Failed to load raster: {input_raster}")

        # Define the raster calculator entries
        raster_entry = QgsRasterCalculatorEntry()
        raster_entry.ref = f"{os.path.splitext(os.path.basename(input_raster))[0]}@1"
        raster_entry.raster = raster_layer
        raster_entry.bandNumber = 1

        # Set up the raster calculator
        params = {
            "EXPRESSION": expression,
            "LAYERS": [raster_entry.raster],
            "CELLSIZE": self.pixel_size,
            "EXTENT": raster_layer.extent(),
            "CRS": self.crs.toWkt(),
            "OUTPUT": reclassified_raster,
        }
        extent = raster_layer.extent()
        # Print extent and expression for debugging
        print(f"Extent: {extent}")
        print(f"Expression: {expression}")

        # Perform the reclassification using the raster calculator
        processing.run(
            "gdal:rastercalculator", params, feedback=QgsProcessingFeedback()
        )

        return reclassified_raster

    def _combine_rasters_to_vrt(self, rasters):
        """
        Combine the list of rasters into a single VRT file.
        """
        params = {
            "INPUT": rasters,
            "RESOLUTION": 0,  # Use the highest resolution of input rasters
            "SEPARATE": False,
            "OUTPUT": self.output_vrt,
        }

        processing.run(
            "gdal:buildvirtualraster", params, feedback=QgsProcessingFeedback()
        )

        print(f"VRT created at {self.output_vrt}")
