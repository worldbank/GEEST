# -*- coding: utf-8 -*-
"""📦 Dimension Aggregation Workflow module.

This module contains functionality for dimension aggregation workflow.
"""
import json
import os

from qgis.core import Qgis, QgsFeedback, QgsGeometry, QgsProcessingContext, QgsField, QgsVectorLayer
from qgis.PyQt.QtCore import QVariant

from geest.core import JsonTreeItem
from geest.utilities import log_message

from .aggregation_workflow_base import AggregationWorkflowBase


class DimensionAggregationWorkflow(AggregationWorkflowBase):
    """
    Concrete implementation of a 'Dimension Aggregation' workflow.

    It will aggregate the factors within a dimension to create a single raster output.

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

        # get a list of the items to aggregate
        self.guids = self.item.getDimensionFactorGuids()
        self.id = self.item.attribute("id").lower().replace(" ", "_")  # should not be needed any more
        self.weight_key = "dimension_weighting"
        self.workflow_name = "dimension_aggregation"

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
    ):
        """
        Override to handle EPLEX score for Contextual dimension when women considerations is disabled.

        If this is the Contextual dimension and women_considerations_enabled is False,
        create a raster filled with the EPLEX score value instead of aggregating factors.
        """
        # Check if this is the Contextual dimension
        if self.id == "contextual":
            # Read configuration from item attributes (proper architecture)
            women_considerations_enabled = self.item.attribute("women_considerations_enabled", True)
            eplex_score = self.item.attribute("eplex_score", 0.0)

            if not women_considerations_enabled:
                log_message(
                    f"Using EPLEX score ({eplex_score}) for Contextual dimension (women considerations disabled)",
                    tag="Geest",
                    level=Qgis.Info,
                )
                # Create EPLEX raster directly from grid using the eplex_score
                return self._create_eplex_raster_from_grid(eplex_score, current_bbox, index)

        # Otherwise, use the standard aggregation process
        return super()._process_aggregate_for_area(current_area, clip_area, current_bbox, index)

    def _create_eplex_raster_from_grid(self, eplex_score: float, bbox: QgsGeometry, index: int) -> str:
        """
        Create a raster filled with the EPLEX score directly from the grid layer.

        This method creates the raster without needing a template from other factors,
        by rasterizing the grid layer with a constant EPLEX score value.

        Args:
            eplex_score: The EPLEX score value to fill the raster with (0-5 range)
            bbox: Bounding box geometry for the current area
            index: The area index

        Returns:
            Path to the created raster file, or None if creation failed
        """
        try:
            # Create a temporary copy of the grid layer with the EPLEX score as a field
            grid_layer_copy = QgsVectorLayer(
                f"{self.gpkg_path}|layername=study_area_grid", "grid_temp", "ogr"
            )

            if not grid_layer_copy.isValid():
                log_message("Failed to load grid layer for EPLEX raster creation", tag="Geest", level=Qgis.Warning)
                return None

            # Add a temporary field for the EPLEX score
            grid_layer_copy.startEditing()

            # Check if 'value' field exists, if not add it
            field_index = grid_layer_copy.fields().indexOf("value")
            if field_index == -1:
                field = QgsField("value", QVariant.Double, "double", 10, 2)
                grid_layer_copy.dataProvider().addAttributes([field])
                grid_layer_copy.updateFields()

            # Set all features to have the EPLEX score
            for feature in grid_layer_copy.getFeatures():
                grid_layer_copy.changeAttributeValue(
                    feature.id(), grid_layer_copy.fields().indexOf("value"), eplex_score
                )

            grid_layer_copy.commitChanges()

            # Use the base class _rasterize method to create the raster
            output_raster = self._rasterize(
                input_layer=grid_layer_copy,
                bbox=bbox,
                index=index,
                value_field="value",
                default_value=0,
            )

            log_message(f"Created EPLEX raster: {output_raster}", tag="Geest", level=Qgis.Info)
            return output_raster

        except Exception as e:
            log_message(f"Error creating EPLEX raster from grid: {e}", tag="Geest", level=Qgis.Critical)
            return None
