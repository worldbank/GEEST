from qgis.core import (
    QgsRasterLayer,
    QgsProcessingFeedback,
    QgsGeometry,
    Qgis,
    QgsProcessingContext,
    QgsVectorLayer,
)
import os
import processing
from .area_iterator import AreaIterator  # Import your area iterator
from geest.utilities import log_message


class RasterReclassificationProcessor:
    """
    A processor to reclassify raster values based on predefined rules for each area in a grid.
    The output is a VRT that combines all the reclassified raster tiles for each area.
    """

    def __init__(
        self,
        input_raster,
        output_prefix,
        reclassification_table,
        pixel_size,
        gpkg_path,
        workflow_directory,
        context: QgsProcessingContext,
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
        self.output_prefix = output_prefix
        self.reclassification_table = reclassification_table
        self.pixel_size = pixel_size
        self.gpkg_path = gpkg_path
        self.grid_layer = QgsVectorLayer(
            f"{self.gpkg_path}|layername=study_area_grid", "Grid Layer", "ogr"
        )
        self.workflow_directory = workflow_directory
        self.crs = self.grid_layer.crs()  # CRS is derived from the grid layer
        self.area_iterator = AreaIterator(gpkg_path)  # Initialize the area iterator
        self.context = (
            context  # Used to pass objects to the thread. e.g. the QgsProject Instance
        )

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
        output_vrt = self._combine_rasters_to_vrt(temp_rasters)

        log_message(
            f"Reclassification complete. VRT file saved to {output_vrt}",
            "RasterReclassificationProcessor",
            Qgis.Info,
        )
        return output_vrt

    def _reproject_and_clip_raster(
        self, raster_path: str, bbox: QgsGeometry, index: int
    ):
        """
        Reproject and clip the raster to the bounding box of the current area.
        """
        # Convert the bbox to QgsRectangle
        bbox = bbox.boundingBox()

        reprojected_raster = os.path.join(
            self.workflow_directory,
            f"temp_{self.output_prefix}_reprojected_{index}.tif",
        )

        params = {
            "INPUT": raster_path,
            "TARGET_CRS": self.crs,
            "RESAMPLING": 0,
            "TARGET_RESOLUTION": self.pixel_size,
            "NODATA": -9999,
            "OUTPUT": "TEMPORARY_OUTPUT",
            "TARGET_EXTENT": f"{bbox.xMinimum()},{bbox.xMaximum()},{bbox.yMinimum()},{bbox.yMaximum()} [{self.crs.authid()}]",
        }

        aoi = processing.run(
            "gdal:warpreproject", params, feedback=QgsProcessingFeedback()
        )["OUTPUT"]

        params = {
            "INPUT": aoi,
            "BAND": 1,
            "FILL_VALUE": 0,
            "OUTPUT": reprojected_raster,
        }

        processing.run("native:fillnodata", params)

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
            self.workflow_directory, f"{self.output_prefix}_reclassified_{index}.tif"
        )

        # Set up the reclassification using reclassifybytable
        params = {
            "INPUT_RASTER": input_raster,
            "RASTER_BAND": 1,  # Band number to apply the reclassification
            "TABLE": reclass_table,  # Reclassification table
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
            "CROP_TO_CUTLINE": True,
            "KEEP_RESOLUTION": False,
            "TARGET_EXTENT": f"{bbox.xMinimum()},{bbox.xMaximum()},{bbox.yMinimum()},{bbox.yMaximum()} [{self.crs.authid()}]",
            "OUTPUT": reclassified_raster,
        }

        processing.run(
            "gdal:cliprasterbymasklayer", clip_params, feedback=QgsProcessingFeedback()
        )
        log_message(
            f"Reclassification for area {index} complete. Saved to {reclassified_raster}",
            tag="Geest",
            level=Qgis.Info,
        )

        return reclassified_raster

    def _combine_rasters_to_vrt(self, rasters):
        """
        Combine the list of rasters into a single VRT file.
        """
        output_vrt = os.path.join(
            self.workflow_directory, f"{self.output_prefix}_reclassified_output.vrt"
        )
        params = {
            "INPUT": rasters,
            "RESOLUTION": 0,  # Use the highest resolution of input rasters
            "SEPARATE": False,
            "OUTPUT": output_vrt,
        }

        processing.run(
            "gdal:buildvirtualraster", params, feedback=QgsProcessingFeedback()
        )

        vrt_layer = QgsRasterLayer(output_vrt, f"{self.output_prefix}_reclass_output")
        if vrt_layer.isValid():
            # self.context.project().addMapLayer(vrt_layer)
            log_message("Added VRT layer to the map.", tag="Geest", level=Qgis.Info)
        else:
            log_message(
                "Failed to add VRT layer to the map.", tag="Geest", level=Qgis.Critical
            )
        return output_vrt
