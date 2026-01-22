# -*- coding: utf-8 -*-
"""📦 Factor Aggregation Workflow module.

This module contains functionality for factor aggregation workflow.
"""

from qgis.core import QgsFeedback, QgsProcessingContext

from geest.core import JsonTreeItem

from .aggregation_workflow_base import AggregationWorkflowBase


class FactorAggregationWorkflow(AggregationWorkflowBase):
    """
    Concrete implementation of a 'Factor Aggregation' workflow.

    It will aggregate the indicators within a factor to create a single raster output.
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

        self.guids = self.item.getFactorIndicatorGuids()  # get a list of the items to aggregate
        self.id = self.item.attribute("id").lower().replace(" ", "_")  # should not be needed any more
        self.weight_key = "factor_weighting"
        self.workflow_name = "factor_aggregation"
