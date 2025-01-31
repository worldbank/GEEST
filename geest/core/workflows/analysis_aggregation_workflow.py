import os
from qgis.core import QgsFeedback, QgsProcessingContext
from .aggregation_workflow_base import AggregationWorkflowBase
from geest.core import JsonTreeItem


class AnalysisAggregationWorkflow(AggregationWorkflowBase):
    """
    Concrete implementation of an 'Analysis Aggregation' workflow.

    It will generate the WEE Score product. Further processing is required to generate the WEE x Population Score.
    The logic for the latter is implemented in tree_panel.py : calculate_analysis_insights method.
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
            self.item.getAnalysisDimensionGuids()
        )  # get a list of the items to aggregate
        self.id = (
            self.item.attribute("analysis_name")
            .lower()
            .replace(" ", "_")
            .replace("'", "")
        )  # should not be needed any more
        self.layer_id = "wee"
        self.weight_key = "analysis_weighting"
        self.workflow_name = "analysis_aggregation"
        # Override the default working directory defined in the base class
        self.workflow_directory = os.path.join(self.working_directory, "wee_score")
        if not os.path.exists(self.workflow_directory):
            os.makedirs(self.workflow_directory, exist_ok=True)
