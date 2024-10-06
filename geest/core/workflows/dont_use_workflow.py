import time
from qgis.core import QgsMessageLog, Qgis, QgsFeedback
from .workflow_base import WorkflowBase
from geest.gui.treeview import JsonTreeItem


class DontUseWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'dont use' workflow.
    """

    def __init__(self, item: JsonTreeItem, feedback: QgsFeedback):
        """
        Initialize the TemporalAnalysisWorkflow with attributes and feedback.

        ⭐️ Item is a reference - whatever you change in this item will directly update the tree

        :param item: JsonTreeItem containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        """
        super().__init__(item, feedback)
        self.attributes = self.item.data(3)

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

        steps = 10
        for i in range(steps):
            if self.feedback.isCanceled():
                QgsMessageLog.logMessage(
                    "Dont use workflow canceled.", tag="Geest", level=Qgis.Warning
                )
                return False

            # Simulate progress and work
            self.attributes["progress"] = f"Dont use workflow Step {i + 1} completed"
            self.feedback.setProgress(
                (i + 1) / steps * 100
            )  # Report progress in percentage
            pass

        self.attributes["Result"] = "Dont use workflow completed"
        QgsMessageLog.logMessage(
            "Dont use workflow workflow completed", tag="Geest", level=Qgis.Info
        )
        return True
