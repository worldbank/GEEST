from qgis.core import (
    QgsRasterLayer,
    QgsProcessingFeedback,
    QgsGeometry,
    QgsMessageLog,
    Qgis,
    QgsProcessingContext,
)
import os
import numpy as np
import processing
from .area_iterator import AreaIterator


class SafetyRasterReclassificationProcessor:
    """
    A processor to reclassify raster values based on predefined safety rules for each area in a grid.
    The output is a VRT that combines all the reclassified raster tiles for each area.
    """

    def __init__(
        self,
        output_prefix,
        input_raster,
        pixel_size,
        gpkg_path,
        grid_layer,
        workflow_directory,
        context: QgsProcessingContext,
    ):
        """
        Initialize the SafetyRasterReclassificationProcessor.

        Args:
            input_raster (str): Path to the input raster file.
            output_vrt (str): Path to save the final VRT file.
            pixel_size (float): The pixel size for the output raster.
            gpkg_path (str): Path to the GeoPackage with study areas.
            grid_layer (QgsVectorLayer): The grid layer defining the extent and CRS.
            workflow_directory (str): Directory where intermediate files and the final VRT will be saved.
        """
        self.output_prefix = output_prefix
        self.input_raster = input_raster
        self.pixel_size = pixel_size
        self.gpkg_path = gpkg_path
        self.grid_layer = grid_layer
        self.workflow_directory = workflow_directory
        self.crs = grid_layer.crs()  # CRS is derived from the grid layer
        self.area_iterator = AreaIterator(gpkg_path)  # Initialize the area iterator
        self.context = (
            context  # Used to pass objects to the thread. e.g. the QgsProject Instance
        )

    def process_areas(self):
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

            max_val, median, percentile_75 = self.calculate_raster_stats(
                reprojected_raster
            )

            # Dynamically build the reclassification table using the max value
            reclass_table = self._build_reclassification_table(
                max_val, median, percentile_75
            )
            QgsMessageLog.logMessage(
                f"Reclassification table for area {index}: {reclass_table}",
                "Geest",
                Qgis.Info,
            )

            # Apply the reclassification rules
            reclassified_raster = self._apply_reclassification(
                reprojected_raster,
                index,
                reclass_table=reclass_table,
                bbox=current_bbox,
            )
            temp_rasters.append(reclassified_raster)

        # Combine the reclassified rasters into a VRT
        vrt_path = self._combine_rasters_to_vrt(temp_rasters)

        QgsMessageLog.logMessage(
            f"Reclassification complete. VRT file saved to {vrt_path}",
            "Geest",
            Qgis.Info,
        )

    def calculate_raster_stats(self, raster_path):
        """
        Calculate statistics (max, median, 75th percentile) from a QGIS raster layer using as_numpy.
        """
        raster_layer = QgsRasterLayer(raster_path, "Input Raster")
        provider = raster_layer.dataProvider()
        extent = raster_layer.extent()
        width = raster_layer.width()
        height = raster_layer.height()

        # Fetch the raster data for band 1
        block = provider.block(1, extent, width, height)

        byte_array = block.data()  # This returns a QByteArray

        # Convert list to a numpy array
        raster_array = np.frombuffer(byte_array, dtype=np.float32).reshape(
            (height, width)
        )

        # Filter out NoData values (assumes NoData is represented by some large value like 3.4e+38 or negative values)
        no_data_value = provider.sourceNoDataValue(1)
        valid_data = raster_array[raster_array != no_data_value]

        if valid_data.size > 0:
            # Compute statistics
            max_value = np.max(valid_data).astype(np.float32)
            median = np.median(valid_data).astype(np.float32)
            percentile_75 = np.percentile(valid_data, 75).astype(np.float32)

            return max_value, median, percentile_75

        else:
            return None, None, None

    def _build_reclassification_table(
        self, max_val: float, median: float, percentile_75: float
    ):
        """
        Build a reclassification table dynamically using the max value from the raster.
        """
        # Low NTL Classification Scheme
        if max_val < 0.05:
            reclass_table = [
                0,
                0,
                0,  # No Light
                0.01,
                max_val * 0.2,
                1,  # Very Low
                max_val * 0.2 + 0.01,
                max_val * 0.4,
                2,  # Low
                max_val * 0.4 + 0.01,
                max_val * 0.6,
                3,  # Moderate
                max_val * 0.6 + 0.01,
                max_val * 0.8,
                4,  # High
                max_val * 0.8 + 0.01,
                max_val,
                5,  # Highest
            ]
            reclass_table = list(map(str, reclass_table))
            return reclass_table
        else:
            # Standard Classification Scheme
            quarter_median = round(0.25 * median, 2)
            half_median = round(0.5 * median, 2)
            reclass_table = [
                0.00,
                0.05,
                0,  # No Access
                0.05,
                quarter_median,
                1,  # Very Low
                quarter_median,
                half_median,
                2,  # Low
                half_median,
                median,
                3,  # Moderate
                median,
                percentile_75,
                4,  # High
                percentile_75,
                "inf",
                5,  # Very High
            ]
            reclass_table = list(map(str, reclass_table))
            return reclass_table

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
            "DATA_TYPE": 0,  # Byte
            "OUTPUT": reprojected_raster,
            "TARGET_EXTENT": f"{bbox.xMinimum()},{bbox.xMaximum()},{bbox.yMinimum()},{bbox.yMaximum()} [{self.crs.authid()}]",
        }

        processing.run("gdal:warpreproject", params, feedback=QgsProcessingFeedback())

        return reprojected_raster

    def _apply_reclassification(
        self,
        input_raster: QgsRasterLayer,
        index: int,
        reclass_table: list,
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
            "NODATA_FOR_MISSING": False,
            "NO_DATA": 255,  # No data value
            "OUTPUT": reclassified_raster,
        }

        # Perform the reclassification using the raster calculator
        reclass = processing.run(
            "native:reclassifybytable", params, feedback=QgsProcessingFeedback()
        )["OUTPUT"]

        QgsMessageLog.logMessage(
            f"Reclassification for area {index} complete. Saved to {reclassified_raster}",
            "Geest",
            Qgis.Info,
        )

        return reclassified_raster

    def _combine_rasters_to_vrt(self, rasters):
        """
        Combine the list of rasters into a single VRT file.
        """
        output_vrt = os.path.join(
            self.workflow_directory, f"{self.output_prefix}_reclass_output.vrt"
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
            self.context.project().addMapLayer(vrt_layer)
            QgsMessageLog.logMessage(
                "Added VRT layer to the map.", tag="Geest", level=Qgis.Info
            )
        else:
            QgsMessageLog.logMessage(
                "Failed to add VRT layer to the map.", tag="Geest", level=Qgis.Critical
            )
        return output_vrt
