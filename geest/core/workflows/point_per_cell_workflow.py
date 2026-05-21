# -*- coding: utf-8 -*-
"""📦 Point Per Cell Workflow module.

This module contains functionality for point per cell workflow.

Supports grid-first mode where feature counts are written directly to
the study_area_grid column, then rasterized.
"""

import os
from typing import Optional
from urllib.parse import unquote

from qgis.core import (
    Qgis,
    QgsFeedback,
    QgsGeometry,
    QgsProcessingContext,
    QgsVectorLayer,
)

from geest.core import JsonTreeItem
from geest.core.grid_column_utils import (
    clear_grid_column,
    count_features_per_grid_cell,
    rasterize_grid_column,
)
from geest.utilities import log_message

from .workflow_base import WorkflowBase


class PointPerCellWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'use_point_per_cell' workflow.
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
        :param analysis_scale: Scale of the analysis, e.g., 'local', 'national'.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :param context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        :param working_directory: Folder containing study_area.gpkg and where the outputs will be placed. If not set will be taken from QSettings.
        """
        super().__init__(
            item, cell_size_m, analysis_scale, feedback, context, working_directory
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.workflow_name = "use_point_per_cell"
        layer_path = self.attributes.get("point_per_cell_shapefile", None)
        if layer_path:
            layer_path = unquote(layer_path)

        if not layer_path:
            layer_path = self.attributes.get("point_per_cell_layer_source", None)
            if not layer_path:
                error = "No point per cell layer provided."
                self.attributes["error"] = error
                # Raise an exception using our error message
                raise Exception(error)
        try:
            log_message(
                f"Loading point per cell layer: {layer_path}",
                tag="GeoE3",
                level=Qgis.Info,
            )
            self.features_layer = QgsVectorLayer(layer_path, "point_per_cell_layer", "ogr")
            if not self.features_layer.isValid():
                error = f"Point per cell layer is not valid: {layer_path}"
                self.attributes["error"] = error
                self.attributes["result"] = f"{self.workflow_name} Workflow Failed"
                raise Exception(error)
        except Exception as e:
            log_message(
                f"Error loading point per cell layer: {str(e)}",
                tag="GeoE3",
                level=Qgis.Critical,
            )
            error = f"Error loading point per cell layer: {str(e)}"
            self.attributes["error"] = error
            self.attributes["result"] = f"{self.workflow_name} Workflow Failed"

            raise Exception(error)
        self.feedback.setProgress(1.0)
        self.workflow_name = "point_per_cell"
        # Grid-first mode: write results to grid columns first, then rasterize
        self.use_grid_first = True
        # Track if we've cleared the column (only do once, not per area)
        self._column_cleared = False

    def _process_features_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
        area_name: Optional[str] = None,
    ) -> str:
        """
        Executes the actual workflow logic for a single area.

        Supports grid-first mode where counts are written directly to study_area_grid.

        :current_area: Current polygon from our study area.
        :current_bbox: Bounding box of the above area.
        :area_features: A vector layer of features to analyse.
        :index: Iteration / number of area being processed.
        :area_name: Name of the area being processed.

        :return: A raster layer file path if processing completes successfully.
        """
        area_features_count = area_features.featureCount()
        log_message(
            f"Features layer for area {index + 1} loaded with {area_features_count} features.",
            tag="GeoE3",
            level=Qgis.Info,
        )

        if self.use_grid_first:
            return self._process_grid_first(
                current_bbox=current_bbox,
                area_features=area_features,
                index=index,
                area_name=area_name,
            )
        else:
            return self._process_raster_first(
                current_bbox=current_bbox,
                area_features=area_features,
                index=index,
            )

    def _process_raster_first(
        self,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
    ) -> str:
        """Legacy raster-first processing using copied grid."""
        from geest.core.algorithms.features_per_cell_processor import (
            assign_values_to_grid,
            select_grid_cells_and_count_features,
        )

        output_path = os.path.join(self.workflow_directory, f"{self.layer_id}_grid_cells.gpkg")
        area_grid = select_grid_cells_and_count_features(self.grid_layer, area_features, output_path, self.feedback)
        grid = assign_values_to_grid(area_grid, self.feedback)
        raster_output = self._rasterize(
            grid,
            current_bbox,
            index,
            value_field="value",
            default_value=0,
        )
        return raster_output

    def _process_grid_first(
        self,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
        area_name: str,
    ) -> str:
        """Grid-first processing - writes directly to study_area_grid."""
        # Clear column once at the start (not per area)
        if not self._column_cleared:
            log_message(f"Clearing column {self.layer_id} before processing")
            clear_grid_column(self.gpkg_path, self.layer_id)
            self._column_cleared = True

        self.progressChanged.emit(10.0)

        # Count features and write to grid
        log_message(f"Counting features for column {self.layer_id}")
        count_features_per_grid_cell(
            gpkg_path=self.gpkg_path,
            column_name=self.layer_id,
            features_layer=area_features,
            feedback=self.feedback,
        )

        self.progressChanged.emit(50.0)

        # Rasterize from grid column
        output_path = os.path.join(
            self.workflow_directory,
            f"{self.layer_id}_{index}.tif",
        )

        rect = current_bbox.boundingBox()
        extent = (rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum())

        rasterize_grid_column(
            gpkg_path=self.gpkg_path,
            column_name=self.layer_id,
            output_raster_path=output_path,
            cell_size=self.cell_size_m,
            extent=extent,
            nodata=-9999.0,
            area_name=area_name,
        )

        self.progressChanged.emit(100.0)
        log_message(f"Rasterized grid column to {output_path}")
        return output_path

    # Default implementation of the abstract method - not used in this workflow
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
        pass

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
        area_name: str = None,
    ):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        pass
