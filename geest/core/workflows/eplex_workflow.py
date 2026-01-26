# -*- coding: utf-8 -*-
"""📦 EPLEX Workflow module.

This module contains functionality for EPLEX score workflow.
"""

import os

from qgis.core import (
    Qgis,
    QgsFeature,
    QgsFeedback,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsProcessingContext,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant

from geest.core import JsonTreeItem
from geest.utilities import log_message

from .workflow_base import WorkflowBase


class EPLEXWorkflow(WorkflowBase):
    """
    Concrete implementation of 'use_eplex_score' workflow.

    Creates a raster filled with the EPLEX score value for the study area.
    This is used when women considerations are disabled, providing a single
    contextual score based on Employment Protection Legislation Index.
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
        """Initialize the EPLEX workflow with attributes and feedback.

        Args:
            item: JsonTreeItem representing the indicator to process.
            cell_size_m: Cell size in meters for rasterization.
            analysis_scale: Scale of the analysis, e.g., 'local', 'national'.
            feedback: QgsFeedback object for progress reporting and cancellation.
            context: QgsProcessingContext object for processing.
            working_directory: Folder containing study_area.gpkg and outputs.
        """
        super().__init__(item, cell_size_m, analysis_scale, feedback, context, working_directory)

        # Get EPLEX score from attributes
        self.eplex_score = self.attributes.get("eplex_score", 0.0)
        log_message(
            f"EPLEX score from attributes: {self.eplex_score}",
            tag="Geest",
            level=Qgis.Info,
        )

        self.features_layer = True  # Not needed for this workflow
        self.workflow_name = "eplex_score"

    def _process_features_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_features,
        index: int,
    ) -> str:
        """Create a raster filled with EPLEX score for the study area.

        Uses the grid layer directly and rasterizes it with the EPLEX score value.

        Args:
            current_area: Current polygon from our study area.
            clip_area: Polygon to clip the raster to, aligned to cell edges.
            current_bbox: Bounding box of the above area.
            area_features: Not used in this workflow.
            index: Iteration / number of area being processed.

        Returns:
            Raster file path of the output.
        """
        log_message(f"Processing area {index} for EPLEX score workflow", tag="Geest", level=Qgis.Info)

        self.progressChanged.emit(10.0)

        # Create a memory layer with a single feature covering the clip area
        fields = QgsFields()
        fields.append(QgsField("value", QVariant.Double))

        eplex_layer = QgsVectorLayer(f"Polygon?crs={self.target_crs.authid()}", "eplex_temp", "memory")
        eplex_layer.dataProvider().addAttributes(fields)
        eplex_layer.updateFields()

        self.progressChanged.emit(30.0)

        # Create a single feature with the clip_area geometry and EPLEX score
        feature = QgsFeature(fields)
        feature.setGeometry(clip_area)
        feature.setAttribute("value", self.eplex_score)

        eplex_layer.dataProvider().addFeatures([feature])

        self.progressChanged.emit(50.0)

        # Rasterize this layer
        output_path = self._rasterize(
            eplex_layer,
            current_bbox,
            index,
            value_field="value",
            default_value=0,
        )

        self.progressChanged.emit(90.0)

        if output_path and os.path.exists(output_path):
            log_message(
                f"EPLEX raster created successfully: {output_path}",
                tag="Geest",
                level=Qgis.Info,
            )
        else:
            log_message(
                "Failed to create EPLEX raster",
                tag="Geest",
                level=Qgis.Critical,
            )
            return None

        self.progressChanged.emit(100.0)

        return output_path

    # Default implementations of abstract methods - not used in this workflow
    def _process_raster_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_raster: str,
        index: int,
    ):
        """Not used in EPLEX workflow.

        Args:
            current_area: Current polygon from study area.
            clip_area: Polygon to clip the raster to.
            current_bbox: Bounding box of the area.
            area_raster: Path to the raster file.
            index: Area index being processed.
        """
        pass

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
    ):
        """Not used in EPLEX workflow.

        Args:
            current_area: Current polygon from study area.
            clip_area: Polygon to clip the raster to.
            current_bbox: Bounding box of the area.
            index: Area index being processed.
        """
        pass
