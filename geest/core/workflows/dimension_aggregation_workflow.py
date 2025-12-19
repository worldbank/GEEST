# -*- coding: utf-8 -*-
"""📦 Dimension Aggregation Workflow module.

This module contains functionality for dimension aggregation workflow.
"""
import json
import os

from qgis.core import Qgis, QgsFeedback, QgsGeometry, QgsProcessingContext

from geest.core import JsonTreeItem
from geest.core.algorithms import create_eplex_raster
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
            # Load model.json to check women considerations setting
            model_path = os.path.join(self.working_directory, "model.json")
            if os.path.exists(model_path):
                try:
                    with open(model_path, "r") as f:
                        model_data = json.load(f)

                    women_considerations_enabled = model_data.get("women_considerations_enabled", True)
                    eplex_score = model_data.get("eplex_score", 0.0)

                    if not women_considerations_enabled:
                        log_message(
                            f"Using EPLEX score ({eplex_score}) for Contextual dimension (women considerations disabled)",
                            tag="Geest",
                            level=Qgis.Info,
                        )
                        # Find a template raster and create EPLEX raster
                        template_path = self._find_template_raster(index)
                        if template_path:
                            output_path = os.path.join(
                                self.workflow_directory,
                                os.path.basename(self.workflow_directory),
                                f"contextual_masked_{index}.tif",
                            )
                            return create_eplex_raster(eplex_score, template_path, output_path)
                        else:
                            log_message(
                                "Could not create EPLEX raster: no template raster found",
                                tag="Geest",
                                level=Qgis.Warning,
                            )
                            return None
                except Exception as e:
                    log_message(
                        f"Error reading model.json for EPLEX check: {e}",
                        tag="Geest",
                        level=Qgis.Warning,
                    )

        # Otherwise, use the standard aggregation process
        return super()._process_aggregate_for_area(current_area, clip_area, current_bbox, index)

    def _find_template_raster(self, index: int) -> str:
        """
        Find a template raster from the child factors to use for EPLEX raster creation.

        Args:
            index: The area index

        Returns:
            Path to a template raster file, or None if not found
        """
        # Try to find any raster from the child factors to use as a template
        for guid in self.guids:
            item = self.item.getItemByGuid(guid)
            if item and item.attribute(self.result_file_key, ""):
                template_path = item.attribute(self.result_file_key, "")
                layer_folder = os.path.dirname(template_path)
                template_full_path = os.path.join(
                    self.workflow_directory,
                    layer_folder,
                    f"{item.attribute('id').lower()}_masked_{index}.tif",
                )

                if os.path.exists(template_full_path):
                    log_message(
                        f"Found template raster for EPLEX: {template_full_path}",
                        tag="Geest",
                        level=Qgis.Info,
                    )
                    return template_full_path

        return None
