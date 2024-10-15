from qgis.core import (
    QgsRasterLayer,
    QgsProcessingFeedback,
    QgsCoordinateReferenceSystem,
    QgsRectangle,
    QgsGeometry,
    QgsMessageLog,
    Qgis,
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
        reclassification_table,
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
            reclassification_table (list): List of reclassification rules.
            pixel_size (float): The pixel size for the output raster.
            gpkg_path (str): Path to the GeoPackage with study areas.
            grid_layer (QgsVectorLayer): The grid layer defining the extent and CRS.
            workflow_directory (str): Directory where intermediate files and the final VRT will be saved.
        """
        self.input_raster = input_raster
        self.output_vrt = output_vrt
        self.reclassification_table = reclassification_table
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
                reprojected_raster,
                index,
                reclass_table=self.reclassification_table,
                bbox=current_bbox,
            )
            temp_rasters.append(reclassified_raster)

        # Combine the reclassified rasters into a VRT
        self._combine_rasters_to_vrt(temp_rasters)

        QgsMessageLog.logMessage(
            f"Reclassification complete. VRT file saved to {self.output_vrt}",
            "RasterReclassificationProcessor",
            Qgis.Info,
        )

    def _reproject_and_clip_raster(
        self, raster_path: str, bbox: QgsGeometry, index: int
    ):
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

    def _apply_reclassification(
        self,
        input_raster: QgsRasterLayer,
        index: int,
        reclass_table,
        bbox: QgsGeometry,
    ):
        """
        Apply the reclassification using the raster calculator and save the output.
        """
        bbox = bbox.boundingBox()

        reclassified_raster = os.path.join(
            self.workflow_directory, f"reclassified_{index}.tif"
        )

        # Set up the reclassification using reclassifybytable
        params = {
            "INPUT_RASTER": input_raster,
            "RASTER_BAND": 1,  # Band number to apply the reclassification
            "TABLE": reclass_table,  # Reclassification table
            "NO_DATA": 255,  # NoData value
            "RANGE_BOUNDARIES": 0,  # Inclusive lower boundary
            "OUTPUT": "TEMPORARY_OUTPUT",
        }

        # Perform the reclassification using the raster calculator
        reclass = processing.run(
            "native:reclassifybytable", params, feedback=QgsProcessingFeedback()
        )["OUTPUT"]

        clip_params = {
            "INPUT": reclass,
            "MASK": self.grid_layer,
            "NODATA": 255,
            "CROP_TO_CUTLINE": True,
            "KEEP_RESOLUTION": True,
            "TARGET_EXTENT": f"{bbox.xMinimum()},{bbox.xMaximum()},{bbox.yMinimum()},{bbox.yMaximum()} [{self.crs.authid()}]",
            "OUTPUT": reclassified_raster,
        }

        processing.run(
            "gdal:cliprasterbymasklayer", clip_params, feedback=QgsProcessingFeedback()
        )
        QgsMessageLog.logMessage(
            f"Reclassification for area {index} complete. Saved to {reclassified_raster}",
            "RasterReclassificationProcessor",
            Qgis.Info,
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
