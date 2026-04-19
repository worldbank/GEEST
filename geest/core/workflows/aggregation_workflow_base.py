# -*- coding: utf-8 -*-
"""📦 Aggregation Workflow Base module.

This module contains functionality for aggregation workflow base.

Supports both raster-first (legacy) and grid-first aggregation approaches.
The grid-first approach writes aggregated values directly to study_area_grid
columns, then optionally rasterizes from the grid.
"""

import os
from typing import Dict, Optional

from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from qgis.core import (
    Qgis,
    QgsFeedback,
    QgsGeometry,
    QgsProcessingContext,
    QgsRasterLayer,
)

from geest.core import JsonTreeItem
from geest.core.grid_column_utils import (
    clear_grid_column,
    rasterize_grid_column,
    write_aggregation_to_grid,
)
from geest.utilities import log_message

from .workflow_base import WorkflowBase


class AggregationWorkflowBase(WorkflowBase):
    """
    Base class for all aggregation workflows (factor, dimension, analysis)
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
        :param cell_size_m: Cell size in meters for rasterization.
        :param analysis_scale: Scale of the analysis, e.g., 'local', 'national'
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :param context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        :param working_directory: Folder containing study_area.gpkg and where the outputs will be placed. If not set will be taken from QSettings.
        """
        super().__init__(
            item, cell_size_m, analysis_scale, feedback, context, working_directory
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.guids = None  # This should be set by the child class - a list of guids of JSONTreeItems to aggregate
        self.id = None  # This should be set by the child class
        self.weight_key = None  # This should be set by the child class
        self.aggregation = True
        # Grid-first mode: write results to grid columns first, then rasterize
        # Set to True to use the new grid-first approach
        self.use_grid_first = True
        self.feedback.setProgress(10.0)

    def aggregate(self, input_files: list, index: int) -> str:
        """
        Perform weighted raster aggregation on the found raster files.

        :param input_files: dict of raster file paths to aggregate and their weights.
        :param index: The index of the area being processed.

        :return: Path to the aggregated raster file.
        """
        if len(input_files) == 0:
            log_message(
                "Error: Found no Input files. Cannot proceed with aggregation.",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            return None

        # Load the layers
        raster_layers = [QgsRasterLayer(vf, f"raster_{i}") for i, vf in enumerate(input_files.keys())]

        # Ensure all raster layers are valid and print filenames of invalid layers
        invalid_layers = [layer.source() for layer in raster_layers if not layer.isValid()]
        if invalid_layers:
            log_message(
                f"Invalid raster layers found: {', '.join(invalid_layers)}",
                tag="GeoE3",
                level=Qgis.Critical,
            )
        layer_count = len(raster_layers) - len(invalid_layers)
        # Create QgsRasterCalculatorEntries for each raster layer
        entries = []
        ref_names = []
        expression = ""
        sum_of_weights = 0
        for i, raster_layer in enumerate(raster_layers):
            if raster_layer.source() in invalid_layers:
                continue
            log_message(
                f"Adding raster layer {i + 1} to the raster calculator. {raster_layer.source()}",
                tag="GeoE3",
                level=Qgis.Info,
            )
            entry = QgsRasterCalculatorEntry()
            ref_name = os.path.basename(raster_layer.source()).split(".")[0]
            entry.ref = f"{ref_name}_{i + 1}@1"  # Reference the first band
            # entry.ref = f"layer_{i+1}@1"  # layer_1@1, layer_2@1, etc.
            entry.raster = raster_layer
            entry.bandNumber = 1
            entries.append(entry)
            ref_names.append(f"{ref_name}_{i + 1}")
            # input_files[raster_layer.source() returns the weight for the given layer
            weight = input_files[raster_layer.source()]
            if i == 0:
                expression = f"({weight} * {ref_names[i]}@1)"
            else:
                expression += f"+ ({weight} * {ref_names[i]}@1)"
            sum_of_weights += weight

            self.feedback.setProgress((i / layer_count) * 100.0)

        # I believe these are wrong and should be removed since the total weight
        # of the aggregate layers should already be 1.0 - Tim
        # Number of raster layers
        # layer_count = len(input_files) - len(invalid_layers)

        # Wrap the weighted sum and divide by the sum of weights
        # expression = f"({expression}) / {layer_count}"

        aggregation_output = os.path.join(self.workflow_directory, f"{self.id}_aggregated_{index}.tif")

        log_message(
            f"Aggregating {len(input_files)} raster layers to {aggregation_output}",
            tag="GeoE3",
            level=Qgis.Info,
        )
        log_message(f"Aggregation Expression: {expression}")
        # Set up the raster calculator
        calc = QgsRasterCalculator(
            expression,
            aggregation_output,
            "GTiff",  # Output format
            raster_layers[0].extent(),  # Assuming all layers have the same extent
            raster_layers[0].width(),
            raster_layers[0].height(),
            entries,
        )

        # Run the calculation
        result = calc.processCalculation()
        log_message(f"Calculator errors: {calc.lastError()}")
        if result != 0:
            log_message(
                "Raster aggregation completed successfully.",
                tag="GeoE3",
                level=Qgis.Info,
            )
            return None

        # Write the output path to the attributes
        # That will get passed back to the json model
        self.attributes[self.result_file_key] = aggregation_output

        return aggregation_output

    def get_raster_dict(self, index) -> list:
        """
        Get the list of rasters from the attributes that will be aggregated.

        (Factor Aggregation, Dimension Aggregation, Analysis).

        Parameters:
            index (int): The index of the area being processed.

        Returns:
            dict: dict of found raster file paths and their weights.
        """
        raster_files = {}
        if self.guids is None:
            raise ValueError("No GUIDs provided for aggregation")

        for guid in self.guids:

            item = self.item.getItemByGuid(guid)
            status = item.getStatus() == "Completed successfully"
            mode = item.attributes().get("analysis_mode", "Do Not Use") == "Do Not Use"
            excluded = item.getStatus() == "Excluded from analysis"
            disabled = not item.is_enabled()
            id = item.attribute("id").lower().replace(" ", "_")
            if not status and not mode and not excluded and not disabled:
                raise ValueError(
                    f"{id} is not completed successfully and is not set to 'Do Not Use' or 'Excluded from analysis'"
                )

            if mode:
                log_message(
                    f"Skipping {item.attribute('id')} as it is set to 'Do Not Use'",
                    tag="GeoE3",
                    level=Qgis.Info,
                )
                continue
            if excluded:
                log_message(
                    f"Skipping {item.attribute('id')} as it is excluded from analysis",
                    tag="GeoE3",
                    level=Qgis.Info,
                )
                continue
            if disabled:
                log_message(
                    f"Skipping {item.attribute('id')} as it is disabled (women considerations)",
                    tag="GeoE3",
                    level=Qgis.Info,
                )
                continue
            if not item.attribute(self.result_file_key, ""):
                log_message(
                    f"Skipping {id} as it has no result file",
                    tag="GeoE3",
                    level=Qgis.Info,
                )
                raise ValueError(f"{id} has no result file")

            layer_folder = os.path.dirname(item.attribute(self.result_file_key, ""))
            path = os.path.join(self.workflow_directory, layer_folder, f"{id}_masked_{index}.tif")
            log_message(
                f"Checking for masked raster: {path}",
                tag="GeoE3",
                level=Qgis.Info,
            )
            if os.path.exists(path):

                weight = item.attribute(self.weight_key, "")
                try:
                    weight = float(weight)
                except (ValueError, TypeError):
                    weight = 1.0  # Default fallback to 1.0 if weight is invalid

                raster_files[path] = weight

                log_message(f"Adding raster: {path} with weight: {weight}")
            else:
                log_message(
                    f"Masked raster not found at: {path}",
                    tag="GeoE3",
                    level=Qgis.Warning,
                )

        log_message(
            f"Total raster files found: {len(raster_files)}",
            tag="GeoE3",
            level=Qgis.Info,
        )
        return raster_files

    def get_grid_columns_and_weights(self) -> Dict[str, float]:
        """Get the list of grid columns and weights for aggregation.

        This is the grid-first alternative to get_raster_dict(). Instead of
        returning raster file paths, it returns column names from study_area_grid.

        Returns:
            Dict mapping column names to their weights.
            Example: {"indicator1": 0.3, "indicator2": 0.3, "indicator3": 0.4}
        """
        columns_weights = {}
        if self.guids is None:
            raise ValueError("No GUIDs provided for aggregation")

        for guid in self.guids:
            item = self.item.getItemByGuid(guid)
            status = item.getStatus() == "Completed successfully"
            mode = item.attributes().get("analysis_mode", "Do Not Use") == "Do Not Use"
            excluded = item.getStatus() == "Excluded from analysis"
            disabled = not item.is_enabled()
            raw_id = item.attribute("id").lower().replace(" ", "_").replace("-", "_")
            # Add prefix based on item role to match column naming
            item_role = item.role if hasattr(item, "role") else ""
            if item_role == "dimension":
                item_id = f"dim_{raw_id}"
            elif item_role == "factor":
                item_id = f"fac_{raw_id}"
            else:
                item_id = raw_id  # indicators keep raw ID

            if not status and not mode and not excluded and not disabled:
                raise ValueError(
                    f"{item_id} is not completed successfully and is not set to 'Do Not Use' or 'Excluded from analysis'"
                )

            if mode:
                log_message(
                    f"Skipping {item.attribute('id')} as it is set to 'Do Not Use'",
                    tag="GeoE3",
                    level=Qgis.Info,
                )
                continue
            if excluded:
                log_message(
                    f"Skipping {item.attribute('id')} as it is excluded from analysis",
                    tag="GeoE3",
                    level=Qgis.Info,
                )
                continue
            if disabled:
                log_message(
                    f"Skipping {item.attribute('id')} as it is disabled (women considerations)",
                    tag="GeoE3",
                    level=Qgis.Info,
                )
                continue

            # Get weight for this item
            weight = item.attribute(self.weight_key, "")
            try:
                weight = float(weight)
            except (ValueError, TypeError):
                weight = 1.0  # Default fallback to 1.0 if weight is invalid

            # Column name is the sanitized item ID
            column_name = item_id[:63]  # Match sanitization in grid_column_utils
            columns_weights[column_name] = weight

            log_message(f"Adding column: {column_name} with weight: {weight}")

        log_message(
            f"Total columns found for aggregation: {len(columns_weights)}",
            tag="GeoE3",
            level=Qgis.Info,
        )
        return columns_weights

    def aggregate_grid(self, area_name: str) -> int:
        """Perform weighted aggregation directly on grid columns.

        This is the grid-first alternative to aggregate(). Instead of using
        QgsRasterCalculator on raster files, it uses SQL to aggregate values
        directly in the study_area_grid table.

        Args:
            area_name: The name of the area being processed.

        Returns:
            Number of cells updated, or -1 on error.
        """
        columns_weights = self.get_grid_columns_and_weights()

        if not columns_weights:
            log_message(
                "Error: Found no columns to aggregate.",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            return -1

        log_message(
            f"Aggregating {len(columns_weights)} columns into {self.layer_id} for area {area_name}",
            tag="GeoE3",
            level=Qgis.Info,
        )

        # Clear stale values before writing new aggregation
        clear_grid_column(self.gpkg_path, self.layer_id)

        # Use the grid-first aggregation function
        updated_count = write_aggregation_to_grid(
            gpkg_path=self.gpkg_path,
            target_column=self.layer_id,
            source_columns_weights=columns_weights,
            area_name=area_name,
            use_coalesce=True,
        )

        if updated_count >= 0:
            log_message(
                f"Grid aggregation completed: updated {updated_count} cells for {self.layer_id}",
                tag="GeoE3",
                level=Qgis.Info,
            )
        else:
            log_message(
                f"Grid aggregation failed for {self.layer_id}",
                tag="GeoE3",
                level=Qgis.Warning,
            )

        return updated_count

    def rasterize_from_grid(
        self,
        area_name: str,
        bbox: QgsGeometry,
        index: int,
    ) -> Optional[str]:
        """Rasterize the grid column to create a raster output.

        This creates a raster from the aggregated grid column using gdal_rasterize.

        Args:
            area_name: The name of the area being processed.
            bbox: Bounding box geometry for the output raster extent.
            index: The index of the area being processed.

        Returns:
            Path to the output raster, or None on error.
        """
        output_path = os.path.join(
            self.workflow_directory,
            f"{self.layer_id}_aggregated_{index}.tif",
        )

        # Get extent from bbox
        rect = bbox.boundingBox()
        extent = (rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum())

        success = rasterize_grid_column(
            gpkg_path=self.gpkg_path,
            column_name=self.layer_id,
            output_raster_path=output_path,
            cell_size=self.cell_size_m,
            extent=extent,
            nodata=-9999.0,
            area_name=area_name,
        )

        if success:
            log_message(
                f"Rasterized grid column {self.layer_id} to {output_path}",
                tag="GeoE3",
                level=Qgis.Info,
            )
            # Write the output path to attributes
            self.attributes[self.result_file_key] = output_path
            return output_path
        else:
            log_message(
                f"Failed to rasterize grid column {self.layer_id}",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            return None

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
        area_name: Optional[str] = None,
    ):
        """Execute aggregation workflow for a single area.

        Supports both raster-first (legacy) and grid-first aggregation modes.
        The mode is controlled by self.use_grid_first flag.

        Args:
            current_area: Current polygon from our study area.
            clip_area: Polygon to clip the raster to which is aligned to cell edges.
            current_bbox: Bounding box of the above area.
            index: Index of the current area.
            area_name: Name of the area being processed (for grid-first mode).

        Returns:
            Path to the aggregated raster file, or None on error.
        """
        # Log the execution
        log_message(
            f"Executing {self.analysis_mode} Aggregation Workflow (grid_first={self.use_grid_first})",
            tag="GeoE3",
            level=Qgis.Info,
        )

        if self.use_grid_first:
            # Grid-first mode: aggregate directly in grid columns
            return self._process_aggregate_grid_first(
                current_area=current_area,
                clip_area=clip_area,
                current_bbox=current_bbox,
                index=index,
                area_name=area_name,
            )
        else:
            # Legacy raster-first mode
            return self._process_aggregate_raster_first(
                current_area=current_area,
                clip_area=clip_area,
                current_bbox=current_bbox,
                index=index,
            )

    def _process_aggregate_raster_first(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
    ) -> Optional[str]:
        """Legacy raster-first aggregation.

        Uses QgsRasterCalculator to aggregate raster files.
        """
        _ = current_area  # Unused
        _ = clip_area  # Unused
        _ = current_bbox  # Unused

        raster_files = self.get_raster_dict(index)

        if not raster_files or not isinstance(raster_files, dict):
            error = f"No valid raster files found in '{self.guids}'. Cannot proceed with aggregation (likely all factors disabled or excluded)."
            log_message(
                error,
                tag="GeoE3",
                level=Qgis.Warning,
            )
            self.attributes[self.result_key] = f"{self.analysis_mode} Aggregation Workflow Skipped"
            self.attributes["error"] = error
            return None

        log_message(
            f"Found {len(raster_files)} raster files in 'Result File'. Proceeding with raster aggregation.",
            tag="GeoE3",
            level=Qgis.Info,
        )

        # Perform aggregation using raster calculator
        result_file = self.aggregate(raster_files, index)
        return result_file

    def _process_aggregate_grid_first(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
        area_name: Optional[str] = None,
    ) -> Optional[str]:
        """Grid-first aggregation.

        Aggregates values directly in grid columns using SQL, then
        optionally rasterizes from the grid.
        """
        _ = current_area  # Unused

        # Step 1: Aggregate grid columns
        try:
            columns_weights = self.get_grid_columns_and_weights()
        except ValueError as e:
            error = str(e)
            log_message(
                error,
                tag="GeoE3",
                level=Qgis.Warning,
            )
            self.attributes[self.result_key] = f"{self.analysis_mode} Aggregation Workflow Skipped"
            self.attributes["error"] = error
            return None

        if not columns_weights:
            error = "No valid columns found for aggregation. Cannot proceed (likely all factors disabled or excluded)."
            log_message(
                error,
                tag="GeoE3",
                level=Qgis.Warning,
            )
            self.attributes[self.result_key] = f"{self.analysis_mode} Aggregation Workflow Skipped"
            self.attributes["error"] = error
            return None

        log_message(
            f"Found {len(columns_weights)} columns for grid aggregation: {list(columns_weights.keys())}",
            tag="GeoE3",
            level=Qgis.Info,
        )

        # Perform SQL aggregation on grid
        updated_count = self.aggregate_grid(area_name)
        if updated_count < 0:
            log_message(
                f"Grid aggregation failed for area {area_name}",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            return None

        # Step 2: Rasterize from grid column for VRT generation
        result_file = self.rasterize_from_grid(
            area_name=area_name,
            bbox=current_bbox,
            index=index,
        )

        return result_file

    def _process_features_for_area(self):
        pass

    def _process_raster_for_area(self):
        pass
