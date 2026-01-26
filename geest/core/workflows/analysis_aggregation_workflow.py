# -*- coding: utf-8 -*-
"""📦 Analysis Aggregation Workflow module.

This module contains functionality for analysis aggregation workflow.
"""

import os

from qgis.core import QgsFeedback, QgsProcessingContext

from geest.core import JsonTreeItem

from .aggregation_workflow_base import AggregationWorkflowBase


class AnalysisAggregationWorkflow(AggregationWorkflowBase):
    """
    Concrete implementation of an 'Analysis Aggregation' workflow.

    It will generate the GeoE3 Score product. Further processing is required to generate the GeoE3 x Population Score.
    The logic for the latter is implemented in tree_panel.py : calculate_analysis_insights method.
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
        """Initialize the workflow with attributes and feedback.

        Args:
            item: JsonTreeItem representing the analysis, dimension, or factor to process.
            cell_size_m: Cell size in meters for rasterization.
            analysis_scale: Scale of the analysis, e.g., 'local', 'national'.
            feedback: QgsFeedback object for progress reporting and cancellation.
            context: QgsProcessingContext object for processing.
            working_directory: Folder containing study_area.gpkg and outputs.
        """
        super().__init__(
            item, cell_size_m, analysis_scale, feedback, context, working_directory
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.guids = self.item.getAnalysisDimensionGuids()  # get a list of the items to aggregate
        self.id = (
            self.item.attribute("analysis_name").lower().replace(" ", "_").replace("'", "")
        )  # should not be needed any more
        self.layer_id = "geoe3"
        self.weight_key = "analysis_weighting"
        self.workflow_name = "analysis_aggregation"
        # Override the default working directory defined in the base class
        self.workflow_directory = os.path.join(self.working_directory, "geoe3_score")
        if not os.path.exists(self.workflow_directory):
            os.makedirs(self.workflow_directory, exist_ok=True)
