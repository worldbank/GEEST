# -*- coding: utf-8 -*-
"""📦 Index Score Workflow module.

This module contains functionality for index score workflow.

Supports grid-first mode where the index score is written directly to
the study_area_grid column, then optionally rasterized.
"""

import os
from typing import Optional

from qgis import processing  # noqa: F401 # QGIS processing toolbox
from qgis.core import (  # noqa: F401
    Qgis,
    QgsFeature,
    QgsFeedback,
    QgsField,
    QgsGeometry,
    QgsProcessingContext,
    QgsVectorFileWriter,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant

from geest.core import JsonTreeItem
from geest.core.grid_column_utils import (
    rasterize_grid_column,
    write_uniform_value_to_grid,
)
from geest.utilities import log_message

from .workflow_base import WorkflowBase


class DefaultIndexScoreWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'use_index_score' workflow.
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

        index_score = self.attributes.get("index_score", 0)
        log_message(f"Index score before rescaling to likert scale: {index_score}")
        self.index_score = (float(index_score) / 100) * 5
        log_message(f"Index score after rescaling to likert scale: {self.index_score}")

        self.features_layer = (
            True  # Normally we would set this to a QgsVectorLayer but in this workflow it is not needed
        )
        self.workflow_name = "index_score"
        # Grid-first mode: write results to grid columns first, then rasterize
        self.use_grid_first = True

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

        Supports both raster-first (legacy) and grid-first modes.

        Args:
            current_area: Current polygon from our study area.
            clip_area: Clipping polygon aligned to grid cells.
            current_bbox: Bounding box of the above area.
            area_features: A vector layer of features to analyse (unused for index_score).
            index: Iteration / number of area being processed.
            area_name: Name of the area being processed (for grid-first mode).

        Returns:
            Raster file path of the output.
        """
        _ = area_features  # unused
        log_message(f"Processing area {index} score workflow (grid_first={self.use_grid_first})")

        log_message(f"Index score: {self.index_score}")
        self.progressChanged.emit(10.0)

        if self.use_grid_first and area_name:
            return self._process_grid_first(
                current_bbox=current_bbox,
                index=index,
                area_name=area_name,
            )
        else:
            return self._process_raster_first(
                clip_area=clip_area,
                current_bbox=current_bbox,
                index=index,
            )

    def _process_raster_first(
        self,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
    ) -> str:
        """Legacy raster-first processing.

        Creates a polygon layer with the score and rasterizes it.
        """
        # Create a scored boundary layer filtered by current_area
        scored_layer = self.create_scored_boundary_layer(
            clip_area=clip_area,
            index=index,
        )
        self.progressChanged.emit(30.0)

        # Rasterize the scored layer
        raster_output = self._rasterize(
            scored_layer,
            current_bbox,
            index,
            value_field="score",
            default_value=255,
        )
        self.progressChanged.emit(100.0)

        log_message(f"Raster output: {raster_output}")
        log_message(f"Workflow completed for area {index}")
        return raster_output

    def _process_grid_first(
        self,
        current_bbox: QgsGeometry,
        index: int,
        area_name: str,
    ) -> str:
        """Grid-first processing.

        Writes the index score directly to the grid column, then rasterizes.
        """
        # Step 1: Write uniform value to grid
        self.progressChanged.emit(20.0)
        log_message(f"Writing index score {self.index_score} to grid column {self.layer_id} for area {area_name}")

        updated_count = write_uniform_value_to_grid(
            gpkg_path=self.gpkg_path,
            column_name=self.layer_id,
            value=self.index_score,
            area_name=area_name,
        )

        if updated_count < 0:
            log_message(f"Failed to write index score to grid for area {area_name}", level=Qgis.Warning)
            # Fall back to raster-first method
            return self._process_raster_first(
                clip_area=None,  # Not available in this path
                current_bbox=current_bbox,
                index=index,
            )

        log_message(f"Updated {updated_count} grid cells with index score {self.index_score}")
        self.progressChanged.emit(50.0)

        # Step 2: Rasterize from grid column
        output_path = os.path.join(
            self.workflow_directory,
            f"{self.layer_id}_{index}.tif",
        )

        rect = current_bbox.boundingBox()
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

        self.progressChanged.emit(100.0)

        if success:
            log_message(f"Rasterized grid column to {output_path}")
            return output_path
        else:
            log_message(f"Failed to rasterize grid column for area {area_name}", level=Qgis.Warning)
            return None

    def create_scored_boundary_layer(self, clip_area: QgsGeometry, index: int) -> QgsVectorLayer:
        """
        Create a scored boundary layer, filtering features by the current_area.

        :param index: The index of the current processing area.
        :return: A vector layer with a 'score' attribute.
        """
        output_prefix = f"{self.layer_id}_area_{index}"

        self.progressChanged.emit(20.0)  # We just use nominal intervals for progress updates
        # Create a new memory layer with the target CRS (EPSG:4326)
        subset_layer = QgsVectorLayer("Polygon", "subset", "memory")
        subset_layer.setCrs(self.target_crs)
        subset_layer_data = subset_layer.dataProvider()
        field = QgsField("score", QVariant.Double)
        fields = [field]
        # Add attributes (fields) from the point_layer
        subset_layer_data.addAttributes(fields)
        subset_layer.updateFields()
        self.progressChanged.emit(40.0)  # We just use nominal intervals for progress updates

        feature = QgsFeature(subset_layer.fields())
        feature.setGeometry(clip_area)
        score_field_index = subset_layer.fields().indexFromName("score")
        feature.setAttribute(score_field_index, self.index_score)
        features = [feature]
        # Add reprojected features to the new subset layer
        subset_layer_data.addFeatures(features)
        subset_layer.commitChanges()
        self.progressChanged.emit(60.0)  # We just use nominal intervals for progress updates

        shapefile_path = os.path.join(self.workflow_directory, f"{output_prefix}.shp")
        # Use QgsVectorFileWriter to save the layer to a shapefile
        QgsVectorFileWriter.writeAsVectorFormat(
            subset_layer,
            shapefile_path,
            "utf-8",
            subset_layer.crs(),
            "ESRI Shapefile",
        )
        layer = QgsVectorLayer(shapefile_path, "area_layer", "ogr")
        self.progressChanged.emit(80.0)  # We just use nominal intervals for progress updates

        return layer

    # Default implementation of the abstract method - not used in this workflow
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
