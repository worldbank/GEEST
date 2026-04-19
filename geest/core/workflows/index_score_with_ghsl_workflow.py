# -*- coding: utf-8 -*-
"""📦 Index Score With Ghsl Workflow module.
This module contains functionality for index score with ghsl workflow.
"""
import os
from typing import Optional

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
    rasterize_grid_column,
    write_spatial_join_to_grid,
)
from geest.utilities import log_message

from .workflow_base import WorkflowBase


class IndexScoreWithGHSLException(Exception):
    """Custom exception for IndexScoreWithGHSLWorkflow errors."""

    pass


class IndexScoreWithGHSLWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'use_index_score_with_ghsl' workflow.
    This workflow scores areas using an index value, masked to GHSL settlement boundaries.
    Grid cells that intersect GHSL settlements get the index score; others stay NULL.
    Uses grid-first approach: spatial join directly to grid, then rasterize for VRT output.
    """

    def __init__(
        self,
        item: JsonTreeItem,
        cell_size_m: float,
        analysis_scale: str,
        feedback: QgsFeedback,
        context: QgsProcessingContext,
        working_directory: Optional[str] = None,
    ):
        """
        Initialize the workflow with attributes and feedback.
        Args:
            item: JsonTreeItem representing the analysis, dimension, or factor to process.
            cell_size_m: Cell size in meters for rasterization.
            analysis_scale: Scale of the analysis, e.g., 'local', 'national'
            feedback: QgsFeedback object for progress reporting and cancellation.
            context: QgsProcessingContext object for processing.
            working_directory: Folder containing study_area.gpkg and where the outputs will be placed.
        """
        log_message("\n\n\n\n")
        log_message("--------------------------------------------")
        log_message("Initializing Index Score with GHSL Workflow")
        log_message("--------------------------------------------")
        super().__init__(item, cell_size_m, analysis_scale, feedback, context, working_directory)
        index_score = self.attributes.get("index_score", 0)
        log_message(f"Index score before rescaling to likert scale: {index_score}")
        self.index_score = (float(index_score) / 100) * 5
        log_message(f"Index score after rescaling to likert scale: {self.index_score}")
        self.features_layer = True
        self.workflow_name = "index_score"
        self.use_grid_first = True
        self._column_cleared = False
        # Get the analysis extents
        self.study_area_bbox = self._study_area_bbox_4326()
        self.ghsl_layer_path = f"{self.gpkg_path}|layername=ghsl_settlements"
        # Check if GHSL layer exists, try to download if not
        if not self.ensure_ghsl_data():
            log_message(
                "GHSL data could not be obtained. Workflow will continue but may use full clip areas.",
                level="WARNING",
            )
        else:
            ghsl_layer = QgsVectorLayer(self.ghsl_layer_path, "ghsl_layer", "ogr")
            if not ghsl_layer.isValid():
                log_message(
                    "GHSL layer exists but is not valid. Workflow will continue but may use full clip areas.",
                    level="WARNING",
                )

    def _process_features_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
        area_name: str = None,
    ) -> str:
        """
        Score grid cells that intersect GHSL settlements, then rasterize from grid.
        Args:
            current_area: Current polygon from our study area.
            clip_area: Current area but expanded to coincide with grid cell boundaries.
            current_bbox: Bounding box of the above area.
            area_features: A vector layer of features to analyse (unused).
            index: Iteration / number of area being processed.
            area_name: Name of the current area.
        Returns:
            Raster file path of the output.
        """
        _ = area_features  # unused
        _ = current_area  # unused
        log_message(f"Processing area {index} with index score {self.index_score}")
        self.progressChanged.emit(10.0)

        # Clear grid column once at start
        if not self._column_cleared:
            clear_grid_column(self.gpkg_path, self.layer_id)
            self._column_cleared = True

        # Spatial join: set index_score for grid cells that intersect GHSL settlements
        score = self.index_score
        updated = write_spatial_join_to_grid(
            gpkg_path=self.gpkg_path,
            column_name=self.layer_id,
            features_gpkg=self.gpkg_path,
            features_layer="ghsl_settlements",
            score_expression=lambda feat: score,
            area_name=area_name,
            aggregation_method="MAX",
            save_buffers=False,
        )
        self.progressChanged.emit(60.0)

        if updated >= 0:
            log_message(f"Updated {updated} grid cells with GHSL-masked index score for area {area_name}")
        else:
            log_message(
                f"Failed to write GHSL-masked index score for area {area_name}",
                tag="GeoE3",
                level=Qgis.Warning,
            )

        # Rasterize from grid column for VRT output
        output_path = os.path.join(
            self.workflow_directory,
            f"{self.layer_id}_ghsl_scored_{index}.tif",
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
        """Not used in this workflow."""
        return None

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
        area_name: str = None,
    ):
        """Not used in this workflow."""
        return None
