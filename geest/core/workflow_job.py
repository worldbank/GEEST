from qgis.core import QgsTask, QgsMessageLog, QgsFeedback, Qgis
from PyQt5.QtCore import QObject, pyqtSignal
from .workflow_factory import WorkflowFactory


class WorkflowJob(QgsTask):
    """
    Represents an individual workflow task. Uses QgsFeedback for progress reporting
    and cancellation, and the WorkflowFactory to create the appropriate workflow.
    """

    # Custom signal to emit when the job is finished
    job_finished = pyqtSignal(bool, dict)

    def __init__(self, description: str, attributes: dict):
        """
        Initialize the workflow job.
        :param description: Task description
        :param attributes: A dictionary of task attributes
        """
        super().__init__(description)
        self._attributes = attributes
        self._feedback = QgsFeedback()  # Feedback object for progress and cancellation
        workflow_factory = WorkflowFactory()
        self._workflow = workflow_factory.create_workflow(
            attributes, self._feedback
        )  # Create the workflow

    def run(self) -> bool:
        """
        Executes the workflow created by the WorkflowFactory. Uses the QgsFeedback
        object for progress reporting and cancellation.
        :return: True if the task was successful, False otherwise
        """
        if not self._workflow:
            QgsMessageLog.logMessage(
                f"Error: No workflow assigned to {self.description()}",
                tag="Geest",
                level=Qgis.Critical,
            )
            return False

        try:
            QgsMessageLog.logMessage(
                f"Running workflow: {self.description()}", tag="Geest", level=Qgis.Info
            )

            result = self._workflow.execute()

            if result:
                QgsMessageLog.logMessage(
                    f"Workflow {self.description()} completed.",
                    tag="Geest",
                    level=Qgis.Info,
                )
                return True
            else:
                QgsMessageLog.logMessage(
                    f"Workflow {self.description()} did not complete successfully.",
                    tag="Geest",
                    level=Qgis.Info,
                )
                return False

        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error during task execution: {e}", tag="Geest", level=Qgis.Critical
            )
            return False

    def feedback(self) -> QgsFeedback:
        """
        Returns the feedback object, allowing external systems to monitor progress and cancellation.
        :return: QgsFeedback object
        """
        return self._feedback

    def finished(self, success: bool) -> None:
        """
        Override the finished method to emit a custom signal when the task is finished.
        :param success: True if the task was completed successfully, False otherwise
        """
        # Emit the custom signal job_finished with the success state and the updated attributes
        self.job_finished.emit(success, self._attributes)
