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
        item: JsonTreeItem,
        cell_size_m: float,
        feedback: QgsFeedback,
        context: QgsProcessingContext,
        working_directory: str = None,
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param attributes: Item containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        :working_directory: Folder containing study_area.gpkg and where the outputs will be placed. If not set will be taken from QSettings.
        """
        super().__init__(
            item, cell_size_m, feedback, context, working_directory
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree

        self.guids = (
            self.item.getFactorIndicatorGuids()
        )  # get a list of the items to aggregate
        self.id = (
            self.item.attribute("id").lower().replace(" ", "_")
        )  # should not be needed any more
        self.weight_key = "factor_weighting"
        self.workflow_name = "factor_aggregation"
