import os
from qgis.core import QgsFeedback, QgsProcessingContext
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from .aggregation_workflow_base import AggregationWorkflowBase
from geest.utilities import resources_path
from geest.core import JsonTreeItem


class AnalysisAggregationWorkflow(AggregationWorkflowBase):
    """
    Concrete implementation of an 'Analysis Aggregation' workflow.

    It will aggregate the dimensions within an analysis to create a single raster output.
    """

    def __init__(
        self, item: JsonTreeItem, feedback: QgsFeedback, context: QgsProcessingContext
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param attributes: Item containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        """
        super().__init__(
            item, feedback, context
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.id = "geest_analysis"
        self.aggregation_attributes = self.item.getAnalysisAttributes()
        self.layers = self.aggregation_attributes.get(f"Dimensions", [])
        self.weight_key = "dimension_weighting"
        self.result_file_tag = "Analysis Result File"
        self.raster_path_key = "Dimension Result File"
