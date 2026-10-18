# -*- coding: utf-8 -*-
"""📦 Safety Raster Workflow module.
This module contains functionality for safety raster workflow.
"""
import os
from typing import Optional
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
from geest.core.grid_column_utils import write_joined_values_to_grid, write_spatial_join_to_grid
from geest.core.jenks import jenks_natural_breaks
from geest.utilities import log_message

from .workflow_base import WorkflowBase, WorkflowNotConfiguredError


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

        self.s2s_output_path = self.attributes.get("s2s_output_path", "")
        self.s2s_ntl_field = self.attributes.get("s2s_ntl_field", "")
        self.vector_source_path = unquote(self.attributes.get("nighttime_lights_vector", ""))
        self.vector_value_field = self.attributes.get("nighttime_lights_selected_field", "")
        self._use_s2s_grid_path = bool(
            self.analysis_scale == "regional" and self.s2s_output_path and self.s2s_ntl_field
        )
        self._use_vector_path = bool(self.vector_source_path and self.vector_value_field)

        if self._use_s2s_grid_path:
            self.features_layer = True
            self.use_grid_first = True
            self.raster_layer = None
            log_message(
                "Using regional S2S grid path for nighttime lights (direct raw value write).",
                tag="GeoE3",
                level=Qgis.Info,
            )
            return

        if self._use_vector_path:
            self.features_layer = QgsVectorLayer(self.vector_source_path, "Nighttime Lights Vector", "ogr")
            if not self.features_layer.isValid():
                log_message(
                    f"Invalid nighttime lights vector source: {self.vector_source_path}. Falling back to raster path.",
                    tag="GeoE3",
                    level=Qgis.Warning,
                )
                self.features_layer = None
            else:
                self.use_grid_first = True
                self.raster_layer = None
                log_message(
                    f"Using vector nighttime lights path with field '{self.vector_value_field}'.",
                    tag="GeoE3",
                    level=Qgis.Info,
                )
                return

        if self.analysis_scale == "regional":
            log_message(
                "Regional nighttime lights S2S data not configured; falling back to raster input path.",
                tag="GeoE3",
                level=Qgis.Warning,
            )

        layer_name = unquote(self.attributes.get("nighttime_lights_raster", None))
        if not layer_name:
            log_message(
                "Invalid raster found in nighttime_lights_raster, trying nighttime_lights_layer_source.",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            layer_name = self.attributes.get("nighttime_lights_layer_source", None)
            if not layer_name:
                log_message(
                    "No points layer found in nighttime_lights_layer_source.",
                    tag="GeoE3",
                    level=Qgis.Warning,
                )
                raise WorkflowNotConfiguredError("No night-time lights raster configured for this indicator")
        self.raster_layer = QgsRasterLayer(layer_name, "Nighttime Lights Raster", "gdal")

    def _process_raster_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_raster: str,
        index: int,
        area_name: str = None,
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
                tag="GeoE3",
                level=1,
            )
            return None
        # Dynamically build the reclassification table using Jenks Natural Breaks
        reclass_table = self._build_reclassification_table(max_val, median, valid_data)
        log_message(
            f"Reclassification table for area {index}: {reclass_table}",
            tag="GeoE3",
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

    def _process_features_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
        area_name: str = None,
    ) -> Optional[str]:
        """Process S2S regional nighttime lights by writing raw values to the H3 grid."""
        _ = current_area
        _ = clip_area
        _ = current_bbox
        _ = area_features

        if not self._use_s2s_grid_path and not self._use_vector_path:
            return None

        if not area_name:
            raise ValueError("area_name is required for regional S2S nighttime lights processing.")

        if self._use_s2s_grid_path:
            source_layer = os.path.splitext(os.path.basename(self.s2s_output_path))[0]
            updated_count = write_joined_values_to_grid(
                gpkg_path=self.gpkg_path,
                column_name=self.layer_id,
                source_gpkg=self.s2s_output_path,
                source_layer=source_layer,
                source_key_field="hex_id",
                target_key_field="h3_index",
                source_value_field=self.s2s_ntl_field,
                area_name=area_name,
            )

            if updated_count < 0:
                raise RuntimeError("Failed to write S2S nighttime lights values to study_area_grid.")

            mapped_count = self._apply_s2s_ntl_likert_mapping(area_name=area_name)
            if mapped_count < 0:
                raise RuntimeError("Failed to map S2S nighttime lights values to Likert scale.")

            log_message(
                f"Wrote {updated_count} regional S2S nighttime lights values and mapped {mapped_count} cells "
                f"to Likert scale in grid column {self.layer_id}",
                tag="GeoE3",
                level=Qgis.Info,
            )
        else:
            source_path = area_features.source()
            source_layer = os.path.splitext(os.path.basename(source_path))[0]
            updated_count = write_spatial_join_to_grid(
                gpkg_path=self.gpkg_path,
                column_name=self.layer_id,
                features_gpkg=source_path,
                features_layer=source_layer,
                score_expression=self.vector_value_field,
                area_name=area_name,
                aggregation_method="MAX",
                save_buffers=False,
                workflow_directory=self.workflow_directory,
            )

            if updated_count < 0:
                raise RuntimeError("Failed to write vector nighttime lights values to study_area_grid.")

            log_message(
                f"Wrote {updated_count} vector nighttime lights values to grid column {self.layer_id}",
                tag="GeoE3",
                level=Qgis.Info,
            )

        # Rasterization (when still needed - regional/H3, which has no
        # pyramid) is performed centrally by WorkflowBase.execute() from the
        # grid column this method just wrote; local/national visualization
        # comes from the pyramid instead, so this method's job ends here.
        return True

    def _apply_s2s_ntl_likert_mapping(self, area_name: str) -> int:
        """Map joined S2S NTL values to the same Likert scale as raster mode."""
        from geest.core.grid_column_utils import get_grid_column_values, reclassify_grid_column_with_table

        classification_mode = self.attributes.get("ntl_classification_mode", "jenks")
        if classification_mode == "noaa":
            reclass_table = self._build_noaa_table(max_val=0)
            return reclassify_grid_column_with_table(
                gpkg_path=self.gpkg_path,
                column_name=self.layer_id,
                reclassification_table=reclass_table,
                area_name=area_name,
                range_boundaries=0,
            )

        values = get_grid_column_values(self.gpkg_path, self.layer_id, area_name=area_name)
        if not values:
            return 0

        valid_data = np.asarray(values, dtype=float)
        breaks = jenks_natural_breaks(valid_data, n_classes=6)
        reclass_table = self._build_reclass_table_from_breaks(breaks)
        log_message(
            f"Dynamic NTL classification table for area {area_name}: {reclass_table}",
            tag="GeoE3",
            level=Qgis.Info,
        )
        return reclassify_grid_column_with_table(
            gpkg_path=self.gpkg_path,
            column_name=self.layer_id,
            reclassification_table=reclass_table,
            area_name=area_name,
            range_boundaries=0,
        )

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
            tag="GeoE3",
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
            log_message("Raster layer failed to load", tag="GeoE3", level=1)
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
            log_message("Unsupported data type", tag="GeoE3", level=1)
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
            log_message("No valid data in the raster", tag="GeoE3", level=1)
            return None, None, None, None

    def _build_noaa_table(self, max_val: float) -> list:
        """
        Build the NOAA threshold classification table.

        Uses the fixed Black Marble (NOAA) thresholds:
        - values in (0, 0.5]  map to class 1
        - values in (0.5, 1]  map to class 2
        - values in (1, 5]    map to class 3
        - values in (5, 50]   map to class 4
        - values > 50         map to class 5

        The table is interpreted with RANGE_BOUNDARIES = 0 (min < value <= max).

        Args:
            max_val: Maximum value in the raster data
        Returns:
            Reclassification table as list of strings
            Format: [min1, max1, class1, min2, max2, class2, ...]
        """
        _ = max_val
        reclass_table = [
            "-inf",
            "0.5",
            "1",
            "0.5",
            "1",
            "2",
            "1",
            "5",
            "3",
            "5",
            "50",
            "4",
            "50",
            "inf",
            "5",
        ]
        return list(map(str, reclass_table))

    def _build_reclassification_table(self, max_val: float, median: float, valid_data: np.ndarray) -> list:
        """
        Build reclassification table using the method chosen by the user in the configuration widget.

        Reads ``ntl_classification_mode`` from the item attributes:
        - ``"noaa"``     → 5 fixed threshold classes (scores 1-5)
        - otherwise      → 6 dynamic equal-count classes (default; also used when the
                           attribute is absent for backward compatibility with existing models)

        Args:
            max_val: Maximum value in the raster
            median: Median value in the raster
            valid_data: Array of all valid (non-NoData) raster values
        Returns:
            Reclassification table as list of [min, max, class, min, max, class, ...]
            formatted as strings for QGIS native:reclassifybytable algorithm
        """
        classification_mode = self.attributes.get("ntl_classification_mode", "jenks")
        use_noaa = classification_mode == "noaa"

        if use_noaa:
            log_message(
                f"🎯 NOAA threshold classification selected by user (max={max_val:.6f})",
                tag="GeoE3",
                level=0,
            )
            return self._build_noaa_table(max_val)

        # Dynamic min-max classification. Breaks are derived from the data's
        # own min-max range so that every value maps to a class (no missing).
        log_message(
            f"📊 Computing dynamic NTL classification (max={max_val:.6f}, "
            f"median={median:.6f}, n={len(valid_data)})",
            tag="GeoE3",
            level=0,
        )
        breaks = jenks_natural_breaks(valid_data, n_classes=6)
        reclass_table = self._build_reclass_table_from_breaks(breaks)
        log_message(
            f"✅ Dynamic NTL classification computed (6 equal-count classes spanning "
            f"data min-max, no missing values): {reclass_table}",
            tag="GeoE3",
            level=0,
        )
        return reclass_table

    @staticmethod
    def _build_reclass_table_from_breaks(breaks: list) -> list:
        """Build a reclassification table from class breaks.

        The first class extends from -inf (so every value maps to a class, no
        missing values) and the final boundary is the data maximum.

        Args:
            breaks: Class break points, last entry is the data maximum.

        Returns:
            Reclassification table as list of [min, max, class, ...] strings.
        """
        reclass_table = ["-inf", str(breaks[0]), "0"]
        for i in range(len(breaks) - 1):
            reclass_table.extend([str(breaks[i]), str(breaks[i + 1]), str(i + 1)])
        return reclass_table

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
        area_name: str = None,
    ):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        pass
