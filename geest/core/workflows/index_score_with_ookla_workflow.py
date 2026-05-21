# -*- coding: utf-8 -*-
"""📦 Index Score With Ookla Workflow module.
This module contains functionality for index score with ookla workflow.
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
from geest.core.algorithms.ookla_downloader import OoklaDownloader
from geest.core.grid_column_utils import (
    clear_grid_column,
    rasterize_grid_column,
    write_spatial_join_to_grid,
)
from geest.utilities import log_message

from .workflow_base import WorkflowBase


class ProgressBridgeFeedback(QgsFeedback):
    """
    A feedback wrapper that bridges progress updates to the workflow's progressChanged signal.
    This ensures OOKLA download progress is visible in the UI.
    """

    def __init__(self, workflow, base_feedback):
        super().__init__()
        self.workflow = workflow
        self.base_feedback = base_feedback

    def setProgress(self, progress):
        """Override to emit workflow progress signal."""
        super().setProgress(progress)
        if self.base_feedback:
            self.base_feedback.setProgress(progress)
        self.workflow.progressChanged.emit(float(progress))

    def isCanceled(self):
        """Check if operation should be canceled."""
        if self.base_feedback:
            return self.base_feedback.isCanceled()
        return super().isCanceled()


class IndexScoreWithOoklaWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'use_index_score_with_ookla' workflow.
    This workflow scores areas using an index value, masked to Ookla broadband coverage.
    Grid cells that intersect Ookla coverage tiles get the index score; others stay NULL.
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
        :param item: JsonTreeItem representing the analysis, dimension, or factor to process.
        :param cell_size_m: Cell size in meters for rasterization.
        :param analysis_scale: Scale of the analysis, e.g., 'local', 'national'
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :param context: QgsProcessingContext object for processing.
        :param working_directory: Folder containing study_area.gpkg and outputs.
        """
        log_message("\n\n\n\n")
        log_message("--------------------------------------------")
        log_message("Initializing Index Score with Ookla Workflow")
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
        # Lazy load OOKLA data during execute to avoid blocking __init__
        self.ookla_layer_path = None
        self.ookla_downloaded = False

    def _download_ookla_data(self):
        """
        Download OOKLA data if not already downloaded.
        This is called during execute() to prevent blocking __init__.
        """
        if self.ookla_downloaded:
            return
        log_message("Downloading Ookla data (this may take several minutes)...")
        self.updateStatus("Downloading Ookla data — this may take several minutes...")
        self.progressChanged.emit(1.0)
        bridge_feedback = ProgressBridgeFeedback(self, self.feedback)
        ookla_layer_path = os.path.join(self.working_directory, "study_area")
        log_message(f"Ookla output will be saved to: {ookla_layer_path}")
        downloader = OoklaDownloader(
            extents=self.study_area_bbox,
            output_path=ookla_layer_path,
            filename_prefix="ookla",
            use_cache=True,
            delete_existing=True,
            feedback=bridge_feedback,
        )
        self.updateStatus("Ookla: fetching broadband data (may take several minutes)...")
        try:
            downloader.extract_data(output_crs=self.target_crs)
        except Exception as e:
            error_msg = f"Ookla download failed: {e}"
            log_message(error_msg, level=Qgis.Critical)
            self.updateStatus(error_msg)
            raise
        self.ookla_layer_path = os.path.join(ookla_layer_path, "ookla_combined.gpkg")
        self.ookla_downloaded = True
        log_message("Ookla data download complete")
        self.updateStatus("Ookla download complete")

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
        Score grid cells that intersect Ookla coverage, then rasterize from grid.
        :current_area: Current polygon from our study area.
        :current_bbox: Bounding box of the above area.
        :area_features: A vector layer of features to analyse (unused).
        :index: Iteration / number of area being processed.
        :area_name: Name of the current area.
        :return: Raster file path of the output.
        """
        _ = area_features  # unused
        _ = current_area  # unused

        # Download OOKLA data on first area
        if index == 0:
            self._download_ookla_data()
        log_message(f"Index score: {self.index_score}")
        self.progressChanged.emit(10.0)

        # Clear grid column once at start
        if not self._column_cleared:
            clear_grid_column(self.gpkg_path, self.layer_id)
            self._column_cleared = True

        # Spatial join: set index_score for grid cells that intersect Ookla coverage
        score = self.index_score
        updated = write_spatial_join_to_grid(
            gpkg_path=self.gpkg_path,
            column_name=self.layer_id,
            features_gpkg=self.ookla_layer_path,
            features_layer="ookla_combined",
            score_expression=lambda feat: score,
            area_name=area_name,
            aggregation_method="MAX",
            save_buffers=False,
        )
        self.progressChanged.emit(60.0)

        if updated >= 0:
            log_message(f"Updated {updated} grid cells with Ookla-masked index score for area {area_name}")
        else:
            log_message(
                f"Failed to write Ookla-masked index score for area {area_name}",
                tag="GeoE3",
                level=Qgis.Warning,
            )

        # Rasterize from grid column for VRT output
        output_path = os.path.join(
            self.workflow_directory,
            f"{self.layer_id}_ookla_scored_{index}.tif",
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
        pass

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
        area_name: str = None,
    ):
        """Not used in this workflow."""
        pass
