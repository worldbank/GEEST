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

    def do_execute(self):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        if self.feedback.isCanceled():
            QgsMessageLog.logMessage(
                "Dont use workflow canceled.", tag="Geest", level=Qgis.Warning
            )
            return False

        QgsMessageLog.logMessage("Executing 'dont use'", tag="Geest", level=Qgis.Info)
        self.attributes["Result"] = "Dont use workflow completed"
        QgsMessageLog.logMessage(
            "Dont use workflow workflow completed", tag="Geest", level=Qgis.Info
        )
        return True
