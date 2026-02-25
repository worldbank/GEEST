# -*- coding: utf-8 -*-
"""📦 Safety Raster Workflow module.

This module contains functionality for safety raster workflow.
"""

import os
from urllib.parse import unquote

import numpy as np
from qgis import processing  # QGIS processing toolbox
from qgis.core import (
    Qgis,
    QgsFeedback,
    QgsGeometry,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsRasterLayer,
    QgsVectorLayer,
)

from geest.core import JsonTreeItem
from geest.core.jenks import jenks_natural_breaks
from geest.utilities import log_message

from .workflow_base import WorkflowBase


class SafetyRasterWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'use_nighttime_lights' workflow.
    """

    def __init__(
        self,
        item: JsonTreeItem,
        cell_size_m: float,
        analysis_scale: str,
        feedback: QgsFeedback,
        context: QgsProcessingContext,
        working_directory: str = None,
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param item: JsonTreeItem representing the analysis, dimension, or factor to process.
        :param cell_size_m: Cell size in meters
        :param analysis_scale: Scale of the analysis, e.g., 'local', 'national'.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :param context: QgsProcessingContext object for processing. This can be used to pass
            objects to the thread. e.g. the QgsProject Instance
        :param working_directory: Folder containing study_area.gpkg and where the outputs will
            be placed. If not set will be taken from QSettings.
        """
        super().__init__(
            item, cell_size_m, analysis_scale, feedback, context, working_directory
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.workflow_name = "use_nighttime_lights"
        layer_name = unquote(self.attributes.get("nighttime_lights_raster", None))

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
        self.raster_layer = QgsRasterLayer(layer_name, "Nighttime Lights Raster", "gdal")

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

        max_val, median, percentile_75, valid_data = self.calculate_raster_stats(area_raster)

        # Check if we got valid statistics
        if valid_data is None or len(valid_data) == 0:
            log_message(
                f"No valid data for area {index}, skipping reclassification",
                tag="Geest",
                level=1,
            )
            return None

        # Dynamically build the reclassification table using Jenks Natural Breaks
        reclass_table = self._build_reclassification_table(max_val, median, valid_data)
        log_message(
            f"Reclassification table for area {index}: {reclass_table}",
            tag="Geest",
            level=0,
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

        reclassified_raster = os.path.join(self.workflow_directory, f"{self.layer_id}_reclassified_{index}.tif")

        # Set up the reclassification using reclassifybytable
        params = {
            "INPUT_RASTER": input_raster,
            "RASTER_BAND": 1,  # Band number to apply the reclassification
            "TABLE": reclass_table,  # Reclassification table
            "RANGE_BOUNDARIES": 0,  # Inclusive lower boundary
            "NODATA_FOR_MISSING": False,
            "NO_DATA": 255,  # No data value
            "OUTPUT": reclassified_raster,
            "PROGRESS": self.feedback,
        }

        # Perform the reclassification using the raster calculator
        processing.run(
            "native:reclassifybytable",  # noqa F841
            params,  # noqa F841
            feedback=QgsProcessingFeedback(),  # noqa F841
        )["OUTPUT"]

        log_message(
            f"Reclassification for area {index} complete. Saved to {reclassified_raster}",
            tag="Geest",
            level=Qgis.Info,
        )

        return reclassified_raster

    def calculate_raster_stats(self, raster_path):
        """
        Calculate statistics from a QGIS raster layer using NumPy.

        Returns:
            Tuple of (max_value, median, percentile_75, valid_data)
            Returns (None, None, None, None) if raster cannot be read
        """
        raster_layer = QgsRasterLayer(raster_path, "Input Raster")

        # Check if the raster layer loaded successfully
        if not raster_layer.isValid():
            log_message("Raster layer failed to load", tag="Geest", level=1)
            return None, None, None, None

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
            log_message("Unsupported data type", tag="Geest", level=1)
            return None, None, None, None

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

            return max_value, median, percentile_75, valid_data
        else:
            # Handle case with no valid data
            log_message("No valid data in the raster", tag="Geest", level=1)
            return None, None, None, None

    def _build_reclassification_table(self, max_val: float, median: float, valid_data: np.ndarray) -> list:
        """
        Build a reclassification table using Jenks Natural Breaks algorithm.

        The table maps nighttime lights intensity values to 6 safety classes:
        - 0: No Access (very dark)
        - 1: Very Low
        - 2: Low
        - 3: Moderate
        - 4: High
        - 5: Very High (well-lit)

        Uses Jenks Natural Breaks for optimal data-driven classification.
        If Jenks cannot compute valid breaks (e.g., insufficient data variation),
        the workflow will fail with a descriptive error message.

        Args:
            max_val: Maximum value in the raster
            median: Median value in the raster
            valid_data: Array of all valid (non-NoData) raster values

        Returns:
            Reclassification table as list of [min, max, class, min, max, class, ...]
            formatted as strings for QGIS native:reclassifybytable algorithm

        Raises:
            ValueError: If Jenks Natural Breaks cannot compute valid classification breaks

        Example:
            >>> table = [0.0, 0.5, 0, 0.5, 1.2, 1, 1.2, 2.5, 2, ...]
            >>> # Means: [0.0-0.5] -> class 0, [0.5-1.2] -> class 1, etc.
        """
        n_classes = 6  # Fixed: 0=No Access, 1-5=Safety levels

        log_message(
            f"📊 Computing Jenks Natural Breaks classification (max={max_val:.6f}, "
            f"median={median:.6f}, n={len(valid_data)})",
            tag="Geest",
            level=0,
        )

        try:
            # Calculate Jenks breaks for n_classes
            # Returns: [break₁, break₂, break₃, break₄, break₅, max_value]
            breaks = jenks_natural_breaks(valid_data, n_classes=n_classes)

            # Build QGIS reclassification table format
            # Format: [min₁, max₁, class₁, min₂, max₂, class₂, ...]
            reclass_table = []

            # Class 0: From 0 to first break
            reclass_table.extend([0.0, breaks[0], 0])

            # Classes 1-5: Between consecutive breaks
            for i in range(len(breaks) - 1):
                class_num = i + 1
                min_val = breaks[i]
                max_val_class = breaks[i + 1]
                reclass_table.extend([min_val, max_val_class, class_num])

            # Convert all values to strings for QGIS processing
            reclass_table = list(map(str, reclass_table))

            # Calculate GVF for quality assessment
            from geest.core.jenks import calculate_goodness_of_variance_fit

            gvf = calculate_goodness_of_variance_fit(valid_data, breaks)

            log_message(
                f"✅ Jenks Natural Breaks computed:\n"
                f"   Class 0 (No Access):  0.000 - {breaks[0]:.3f}\n"
                f"   Class 1 (Very Low):   {breaks[0]:.3f} - {breaks[1]:.3f}\n"
                f"   Class 2 (Low):        {breaks[1]:.3f} - {breaks[2]:.3f}\n"
                f"   Class 3 (Moderate):   {breaks[2]:.3f} - {breaks[3]:.3f}\n"
                f"   Class 4 (High):       {breaks[3]:.3f} - {breaks[4]:.3f}\n"
                f"   Class 5 (Very High):  {breaks[4]:.3f} - {breaks[5]:.3f}\n"
                f"   Quality (GVF): {gvf:.4f}",
                tag="Geest",
                level=0,
            )

            return reclass_table

        except Exception as e:
            # Fail workflow with clear error message
            unique_count = len(np.unique(valid_data))
            error_msg = (
                f"❌ Jenks Natural Breaks classification failed: {e}\n"
                f"   Data characteristics:\n"
                f"     - Maximum value: {max_val:.6f}\n"
                f"     - Median value: {median:.6f}\n"
                f"     - Unique values: {unique_count}\n"
                f"     - Total values: {len(valid_data)}\n"
                f"   This may indicate insufficient data variation for meaningful classification.\n"
                f"   Please verify your nighttime lights raster has valid data with reasonable variation."
            )
            log_message(error_msg, tag="Geest", level=2)  # Critical
            raise ValueError(error_msg) from e

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
