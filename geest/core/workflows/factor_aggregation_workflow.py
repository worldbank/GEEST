import os
from qgis.core import QgsFeedback, QgsProcessingContext
from .aggregation_workflow_base import AggregationWorkflowBase
from geest.utilities import resources_path
from geest.core import JsonTreeItem


class FactorAggregationWorkflow(AggregationWorkflowBase):
    """
    Concrete implementation of a 'Factor Aggregation' workflow.

    It will aggregate the indicators within a factor to create a single raster output.
    """

    def __init__(
        self,
        item: dict,
        cell_size_m: float,
        feedback: QgsFeedback,
        context: QgsProcessingContext,
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param attributes: Item containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        """
        super().__init__(
            item, cell_size_m, feedback, context
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree

        self.aggregation_attributes = self.item.getFactorAttributes()
        self.id = self.aggregation_attributes[f"factor_id"].lower().replace(" ", "_")
        self.layers = self.aggregation_attributes.get(f"indicators", [])
        self.weight_key = "indicator_weighting"
        self.result_file_tag = "result_file"
        self.raster_path_key = "result_file"
        self.workflow_is_legacy = False
        self.layer_id = self.id
        self.workflow_name = "factor_aggregation"
