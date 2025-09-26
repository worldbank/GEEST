# -*- coding: utf-8 -*-
from PyQt5.QtCore import QObject, pyqtSignal
from qgis.core import Qgis, QgsProcessingContext, QgsProject, QgsTask

from geest.utilities import log_message

from .json_tree_item import JsonTreeItem
from .workflow_job import WorkflowJob
from .workflow_queue import WorkflowQueue


class WorkflowQueueManager(QObject):
    """
    Manages the overall workflow queue system. Delegates task management
    to the WorkflowQueue, which handles concurrent task execution.
    """

    # Qt signal for when the queue is completed
    processing_completed = pyqtSignal()
    processing_error = pyqtSignal(str)  # error message as payload

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

        # Connect to error signal from workflow queue
        self.workflow_queue.processing_error.connect(self.on_processing_error)

    def add_task(self, task: QgsTask) -> None:
        """
        Add a QgsTask to the queue.

        Use this when you just want to run any QgsTask subclass in tbe queue.

        See Also add_workflow method below
        .
        :param task: A QgsTask object representing the task
        """
        # ⭐️ Now we are passing the item ritemeference to the WorkflowJob
        #    any changes made to the item will be reflected in the tree directly

        self.workflow_queue.add_job(task)
        log_message("Task added")
        return task

    def add_workflow(self, item: JsonTreeItem, cell_size_m: float, analysis_scale: str) -> None:
        """
        Add a task to the WorkflowQueue for QgsProcessingContext using the item provided.

        Internally uses the WorkflowFactory to create the appropriate workflow.

        :param item: A reference to a JsonTreeItem object representing the task
        :param cell_size_m: Cell size in meters for raster operations
        :param analysis_scale: Analysis scale string to determine the workflow e.g. local, national
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
            analysis_scale=analysis_scale,
            context=context,
        )
        self.workflow_queue.add_job(task)
        log_message(f"Task added: {task.description()}")
        return task

    def start_processing(self) -> None:
        """Start processing the tasks in the WorkflowQueue."""
        log_message("Starting workflow queue processing...")
        self.workflow_queue.start_processing()

    def start_processing_in_foreground(self) -> None:
        """Start processing the tasks in the WorkflowQueue in the main thread.

        Used for debugging and testing purposes.
        """
        log_message(
            "Starting FOREGROUND workflow queue processing...",
            tag="Geest",
            level=Qgis.Info,
        )
        for job in self.workflow_queue.job_queue:
            job._workflow.execute()

    def cancel_processing(self) -> None:
        """Cancels all tasks in the WorkflowQueue."""
        log_message("Cancelling workflow queue...")
        self.workflow_queue.cancel_processing()

    def update_status(self) -> None:
        """Update the status of the workflow queue (for UI updates, etc.)."""
        log_message("Workflow queue status updated.")

    def on_processing_completed(self, success: bool) -> None:
        """
        Handle when all tasks in the queue have completed.
        :param success: Indicates whether all tasks completed successfully
        """
        if success:
            log_message(
                "All workflow tasks completed successfully.",
                tag="Geest",
                level=Qgis.Info,
            )
        else:
            log_message("Workflow processing was canceled.")
        self.processing_completed.emit()

    def log_status_message(self, message: str) -> None:
        """
        Logs status messages from the WorkflowQueue.
        :param message: Status message to log
        """
        log_message(message)

    def on_processing_error(self, error_message: str) -> None:
        """
        Handle when a task in the queue encounters an error.
        :param error_message: The error message from the failed task
        """
        log_message(f"Workflow error: {error_message}", tag="Geest", level=Qgis.Critical)
        # Forward the error through the manager's signal
        self.processing_error.emit(error_message)
