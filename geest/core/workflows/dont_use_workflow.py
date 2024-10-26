import time
from qgis.core import QgsMessageLog, Qgis, QgsFeedback, QgsProcessingContext
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem


class DontUseWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'dont use' workflow.
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
        self.workflow_name = "Don't Use"
        self.attributes["Indicator Result File"] = ""
        self.attributes["Indicator Result"] = ""
        self.attributes["Result"] = "Don't Use Completed"

    def _process_area(self):
        pass

    def do_execute(self):
        pass
