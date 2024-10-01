from qgis.core import QgsMessageLog, Qgis, QgsFeedback
from .workflow_base import WorkflowBase


class RasterLayerWorkflow(WorkflowBase):
    """
    Concrete implementation of a spatial analysis workflow.
    """

    def __init__(self, attributes: dict, feedback: QgsFeedback):
        """
        Initialize the TemporalAnalysisWorkflow with attributes and feedback.
        :param attributes: Dictionary containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        """
        super().__init__(attributes, feedback)

    def execute(self):
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
