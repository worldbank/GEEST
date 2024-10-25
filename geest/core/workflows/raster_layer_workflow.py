from qgis.core import QgsMessageLog, Qgis, QgsFeedback, QgsProcessingContext
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem


class RasterLayerWorkflow(WorkflowBase):
    """
    Concrete implementation of a spatial analysis workflow.
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

    def do_execute(self):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        QgsMessageLog.logMessage(
            "Executing spatial analysis workflow", "Custom Workflows", Qgis.Info
        )

        steps = 10
        for i in range(steps):
            if self._feedback.isCanceled():
                QgsMessageLog.logMessage(
                    "Spatial analysis workflow canceled.",
                    "Custom Workflows",
                    Qgis.Warning,
                )
                return False

            # Simulate progress and work
            self._attributes["progress"] = f"Spatial Analysis Step {i + 1} completed"
            self._feedback.setProgress(
                (i + 1) / steps * 100
            )  # Report progress in percentage
            pass

        self._attributes["Result"] = "Spatial analysis completed"
        QgsMessageLog.logMessage(
            "Spatial analysis workflow completed", "Custom Workflows", Qgis.Info
        )
        return True

    def _process_area(self):
        pass
