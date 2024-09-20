from qgis.core import QgsMessageLog, Qgis, QgsFeedback
from .workflow_base import WorkflowBase

class DontUseWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'dont use' workflow.
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
        QgsMessageLog.logMessage("Executing 'dont use'", 'Custom Workflows', Qgis.Info)

        steps = 10
        for i in range(steps):
            if self._feedback.isCanceled():
                QgsMessageLog.logMessage("Dont use workflow canceled.", 'Custom Workflows', Qgis.Warning)
                return False

            # Simulate progress and work
            self._attributes['progress'] = f"Dont use workflow Step {i + 1} completed"
            self._feedback.setProgress((i + 1) / steps * 100)  # Report progress in percentage
            time.sleep(1)  # Simulate a task

        self._attributes['result'] = 'Dont use workflow completed'
        QgsMessageLog.logMessage("Dont use workflow workflow completed", 'Custom Workflows', Qgis.Info)
        return True
