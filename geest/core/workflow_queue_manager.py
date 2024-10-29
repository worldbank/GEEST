from PyQt5.QtCore import QObject, pyqtSignal
from qgis.core import QgsMessageLog, Qgis, QgsTask, QgsProcessingContext, QgsProject
from .workflow_queue import WorkflowQueue
from .workflow_job import WorkflowJob
from .json_tree_item import JsonTreeItem


class WorkflowQueueManager(QObject):
    """
    Manages the overall workflow queue system. Delegates task management
    to the WorkflowQueue, which handles concurrent task execution.
    """

    # Qt signal for when the queue is completed
    processing_completed = pyqtSignal()

    def __init__(self, pool_size: int, parent=None):
        """
        Initialize the WorkflowQueueManager with a thread pool size and a workflow factory.
        :param pool_size: Maximum number of concurrent tasks
        :param parent: Optional parent QObject
        """
        super().__init__(parent=parent)
        self.workflow_queue = WorkflowQueue(pool_size)

        # Connect signals to manage queue updates
        self.workflow_queue.status_changed.connect(self.update_status)
        self.workflow_queue.processing_completed.connect(self.on_processing_completed)
        self.workflow_queue.status_message.connect(self.log_status_message)

    def add_task(self, task: QgsTask) -> None:
        """
        Add a QgsTask to the queue.

        Use this when you just want to run any QgsTask subclass in tbe queue.

        See Also add_workflow method below
        .
        :param task: A QgsTask object representing the task
        """
        # ⭐️ Now we are passing the item reference to the WorkflowJob
        #    any changes made to the item will be reflected in the tree directly

        self.workflow_queue.add_job(task)
        QgsMessageLog.logMessage(f"Task added", tag="Geest", level=Qgis.Info)
        return task

    def add_workflow(self, item: JsonTreeItem, cell_size_m: float) -> None:
        """
        Add a task to the WorkflowQueue for QgsProcessingContext using the item provided.

        Internally uses the WorkflowFactory to create the appropriate workflow.

        :param item: A reference to a JsonTreeItem object representing the task
        """
        # Create a new QgsProcessingContext so we can pass the QgsProject instance
        # to the threads in a thread safe manner
        context = QgsProcessingContext()
        context.setProject(QgsProject.instance())

        # ⭐️ Note we are passing the item reference to the WorkflowJob
        #    any changes made to the item will be reflected in the tree directly
        task = WorkflowJob(
            description="Geest Task",
            item=item,
            cell_size_m=cell_size_m,
            context=context,
        )
        self.workflow_queue.add_job(task)
        QgsMessageLog.logMessage(
            f"Task added: {task.description()}", tag="Geest", level=Qgis.Info
        )
        return task

    def start_processing(self) -> None:
        """Start processing the tasks in the WorkflowQueue."""
        QgsMessageLog.logMessage(
            "Starting workflow queue processing...", tag="Geest", level=Qgis.Info
        )
        self.workflow_queue.start_processing()

    def start_processing_in_foreground(self) -> None:
        """Start processing the tasks in the WorkflowQueue in the main thread.

        Used for debugging and testing purposes.
        """
        QgsMessageLog.logMessage(
            "Starting FOREGROUND workflow queue processing...",
            tag="Geest",
            level=Qgis.Info,
        )
        for job in self.workflow_queue.job_queue:
            job._workflow.execute()

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
                "All workflow tasks completed successfully.",
                tag="Geest",
                level=Qgis.Info,
            )
        else:
            QgsMessageLog.logMessage(
                "Workflow processing was canceled.", tag="Geest", level=Qgis.Info
            )
        self.processing_completed.emit()

    def log_status_message(self, message: str) -> None:
        """
        Logs status messages from the WorkflowQueue.
        :param message: Status message to log
        """
        QgsMessageLog.logMessage(message, tag="Geest", level=Qgis.Info)
