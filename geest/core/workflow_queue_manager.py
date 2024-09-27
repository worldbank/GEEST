from PyQt5.QtCore import QObject
from qgis.core import QgsMessageLog, Qgis
from .workflow_queue import WorkflowQueue
from .workflow_job import WorkflowJob


class WorkflowQueueManager(QObject):
    """
    Manages the overall workflow queue system. Delegates task management
    to the WorkflowQueue, which handles concurrent task execution.
    """

    def __init__(self, pool_size: int, parent=None):
        """
        Initialize the WorkflowQueueManager with a thread pool size and a workflow factory.
        :param pool_size: Maximum number of concurrent tasks
        :param parent: Optional parent QObject
        """
        super().__init__(parent=parent)
        self.workflow_queue = WorkflowQueue(pool_size)

        # Connect signals to manage task updates
        self.workflow_queue.status_changed.connect(self.update_status)
        self.workflow_queue.processing_completed.connect(self.on_processing_completed)
        self.workflow_queue.status_message.connect(self.log_status_message)

    def add_task(self, attributes: dict) -> None:
        """
        Add a task to the WorkflowQueue for processing using the attributes provided.
        Internally uses the WorkflowFactory to create the appropriate workflow.
        :param attributes: A dictionary of task attributes
        """
        task = WorkflowJob(description="Workflow Task", attributes=attributes)
        self.workflow_queue.add_job(task)
        QgsMessageLog.logMessage(
            f"Task added: {task.description()}", tag="Geest", level=Qgis.Info
        )

    def start_processing(self) -> None:
        """Start processing the tasks in the WorkflowQueue."""
        QgsMessageLog.logMessage(
            "Starting workflow queue processing...", tag="Geest", level=Qgis.Info
        )
        self.workflow_queue.start_processing()

    def cancel_processing(self) -> None:
        """Cancels all tasks in the WorkflowQueue."""
        QgsMessageLog.logMessage(
            "Cancelling workflow queue...", tag="Geest", level=Qgis.Info
        )
        self.workflow_queue.cancel_processing()

    def update_status(self) -> None:
        """Update the status of the workflow queue (for UI updates, etc.)."""
        QgsMessageLog.logMessage(
            "Workflow queue status updated.", tag="Geest", level=Qgis.Info
        )

    def on_processing_completed(self, success: bool) -> None:
        """
        Handle when all tasks in the queue have completed.
        :param success: Indicates whether all tasks completed successfully
        """
        if success:
            QgsMessageLog.logMessage(
                "All workflow tasks completed successfully.", tag="Geest", level=Qgis.Info)
        else:
            QgsMessageLog.logMessage(
                "Workflow processing was canceled.", tag="Geest", level=Qgis.Info
            )

    def log_status_message(self, message: str) -> None:
        """
        Logs status messages from the WorkflowQueue.
        :param message: Status message to log
        """
        QgsMessageLog.logMessage(message, tag="Geest", level=Qgis.Info)
