import os
import numpy as np
from qgis.core import (
    Qgis,
    QgsFeedback,
    QgsGeometry,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsRasterLayer,
    QgsVectorLayer,
)
import processing  # QGIS processing toolbox
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem
from geest.utilities import log_message


class SafetyRasterWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'use_nighttime_lights' workflow.
    """

    def __init__(
        self,
        item: JsonTreeItem,
        cell_size_m: float,
        feedback: QgsFeedback,
        context: QgsProcessingContext,
        working_directory: str = None,
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param attributes: Item containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        :working_directory: Folder containing study_area.gpkg and where the outputs will be placed. If not set will be taken from QSettings.
        """
        super().__init__(
            item, cell_size_m, feedback, context, working_directory
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.workflow_name = "use_nighttime_lights"
        layer_name = self.attributes.get("nighttime_lights_raster", None)

        if not layer_name:
            log_message(
                "Invalid raster found in nighttime_lights_raster, trying nighttime_lights_layer_source.",
                tag="Geest",
                level=Qgis.Warning,
            )
            layer_name = self.attributes.get("nighttime_lights_layer_source", None)
            if not layer_name:
                log_message(
                    "No points layer found in nighttime_lights_layer_source.",
                    tag="Geest",
                    level=Qgis.Warning,
                )
                return False
        self.raster_layer = QgsRasterLayer(
            layer_name, "Nighttime Lights Raster", "gdal"
        )

    def _process_raster_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_raster: str,
        index: int,
    ):
        """
        Executes the actual workflow logic for a single area using a raster.

        :current_area: Current polygon from our study area.
        :clip_area: Polygon to clip the raster to which is aligned to cell edges.
        :current_bbox: Bounding box of the above area.
        :area_raster: A raster layer of features to analyse that includes only bbox pixels in the study area.
        :index: Index of the current area.

        :return: Path to the reclassified raster.
        """
        _ = current_area  # Unused in this analysis

        max_val, median, percentile_75 = self.calculate_raster_stats(area_raster)

        # Dynamically build the reclassification table using the max value
        reclass_table = self._build_reclassification_table(
            max_val, median, percentile_75
        )
        log_message(
            f"Reclassification table for area {index}: {reclass_table}",
            tag="Geest",
            level=Qgis.Info,
        )

        # Apply the reclassification rules
        reclassified_raster = self._apply_reclassification(
            area_raster,
            index,
            reclass_table=reclass_table,
            bbox=current_bbox,
        )
        return reclassified_raster

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
            self.workflow_directory, f"{self.layer_id}_reclassified_{index}.tif"
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

        log_message(
            f"Reclassification for area {index} complete. Saved to {reclassified_raster}",
            tag="Geest",
            level=Qgis.Info,
        )

        return reclassified_raster

    def calculate_raster_stats(self, raster_path):
        """
        Calculate statistics (max, median, 75th percentile) from a QGIS raster layer using as_numpy.
        """
        raster_layer = QgsRasterLayer(raster_path, "Input Raster")

        # Check if the raster layer loaded successfully
        if not raster_layer.isValid():
            log_message("Raster layer failed to load", "Geest", level=Qgis.Warning)
            return None, None, None

        provider = raster_layer.dataProvider()
        extent = raster_layer.extent()
        width = raster_layer.width()
        height = raster_layer.height()

        # Fetch the raster data for band 1
        block = provider.block(1, extent, width, height)
        byte_array = block.data()  # This returns a QByteArray

        # Determine the correct dtype based on the provider's data type
        data_type = provider.dataType(1)
        dtype = None
        if data_type == 6:  # Float32
            dtype = np.float32
        elif data_type == 3:  # Int16
            dtype = np.int16
        elif data_type == 2:  # UInt16
            dtype = np.uint16
        elif data_type == 5:  # Int32
            dtype = np.int32
        elif data_type == 4:  # UInt32
            dtype = np.uint32
        elif data_type == 1:  # Byte
            dtype = np.uint8

        if dtype is None:
            log_message("Unsupported data type", "Geest", level=Qgis.Warning)
            return None, None, None

        # Convert QByteArray to a numpy array with the correct dtype
        raster_array = np.frombuffer(byte_array, dtype=dtype).reshape((height, width))

        # Filter out NoData values
        no_data_value = provider.sourceNoDataValue(1)
        valid_data = raster_array[raster_array != no_data_value]

        if valid_data.size > 0:
            # Compute statistics
            max_value = np.max(valid_data).astype(dtype)
            median = np.median(valid_data).astype(dtype)
            percentile_75 = np.percentile(valid_data, 75).astype(dtype)

            return max_value, median, percentile_75
        else:
            # Handle case with no valid data
            log_message("No valid data in the raster", "Geest", level=Qgis.Warning)
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
            quarter_median = 0.25 * median
            half_median = 0.5 * median

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

    # Not used in this workflow since we work with rasters
    def _process_features_for_area(
        self,
        current_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
    ) -> str:
        """
        Executes the actual workflow logic for a single area
        Must be implemented by subclasses.

        :current_area: Current polygon from our study area.
        :current_bbox: Bounding box of the above area.
        :area_features: A vector layer of features to analyse that includes only features in the study area.
        :index: Iteration / number of area being processed.

        :return: A raster layer file path if processing completes successfully, False if canceled or failed.
        """
        pass

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
    ):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        pass
