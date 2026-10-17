# -*- coding: utf-8 -*-
"""📦 Workflow Queue Manager module.

This module contains functionality for workflow queue manager.
"""

import traceback
from typing import Optional

from qgis.core import Qgis, QgsProcessingContext, QgsProject, QgsTask
from qgis.PyQt.QtCore import QObject, pyqtSignal

from geest.utilities import (
    apply_sqlite_write_safety_options,
    log_message,
    restore_sqlite_write_safety_options,
)

from .json_tree_item import JsonTreeItem
from .workflow_job import WorkflowJob
from .workflow_queue import WorkflowQueue
from .workflows.workflow_base import WorkflowNotConfiguredError


class WorkflowQueueManager(QObject):
    """
    Manages the overall workflow queue system. Delegates task management
    to the WorkflowQueue, which handles concurrent task execution.
    """

    # Qt signal for when the queue is completed
    processing_completed = pyqtSignal()
    processing_error = pyqtSignal(str)  # error message as payload

    def __init__(self, pool_size: Optional[int] = None, parent=None):
        """
        Initialize the WorkflowQueueManager with a thread pool size and a workflow factory.

        Args:
            pool_size: Maximum number of concurrent tasks. If None, will read from
                      'concurrent_tasks' setting dynamically for each batch of workflows.
                      This allows settings changes without restarting QGIS.
            parent: Optional parent QObject.
        """
        super().__init__(parent=parent)
        self.workflow_queue = WorkflowQueue(pool_size)
        # Snapshot of GDAL SQLite options from before analysis started, so
        # they can be restored once the whole run completes. None means no
        # hardening is currently applied.
        self._sqlite_safety_snapshot = None

        # Connect signals to manage queue updates
        self.workflow_queue.status_changed.connect(self.update_status)
        self.workflow_queue.processing_completed.connect(self.on_processing_completed)
        self.workflow_queue.status_message.connect(self.log_status_message)

        # Connect to error signal from workflow queue
        self.workflow_queue.processing_error.connect(self.on_processing_error)

    def add_task(self, task: QgsTask) -> None:
        """
        Add a QgsTask to the queue.

        Use this when you just want to run any QgsTask subclass in the queue.

        See Also:
            add_workflow method below.

        Args:
            task: A QgsTask object representing the task.

        Returns:
            QgsTask: The task that was added to the queue.
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

        Args:
            item: A reference to a JsonTreeItem object representing the task.
            cell_size_m: Cell size in meters for raster operations.
            analysis_scale: Analysis scale string to determine the workflow e.g. local, national.

        Returns:
            WorkflowJob: The workflow job that was added to the queue.
        """
        # Create a new QgsProcessingContext so we can pass the QgsProject instance
        # to the threads in a thread safe manner
        context = QgsProcessingContext()
        context.setProject(QgsProject.instance())

        # ⭐️ Note we are passing the item reference to the WorkflowJob
        #    any changes made to the item will be reflected in the tree directly
        # Use unique description to avoid collision in active_tasks dictionary
        # when running multiple concurrent tasks (fixes issue #231)
        try:
            task = WorkflowJob(
                description=f"GeoE3: {item.attribute('id', item.guid)}",
                item=item,
                cell_size_m=cell_size_m,
                analysis_scale=analysis_scale,
                context=context,
            )
        except WorkflowNotConfiguredError as error:
            # The workflow declined the job (e.g. no data source configured
            # for the indicator) — skip it rather than crash the run.
            log_message(
                f"Skipping {item.attribute('id', item.guid)}: {error}",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            self._mark_item_errored(item, str(error))
            self.processing_error.emit(str(error))
            return None
        except Exception as error:  # one broken indicator must never abort the run
            log_message(
                f"Could not create workflow for {item.attribute('id', item.guid)}: {error}\n"
                f"{traceback.format_exc()}",
                tag="GeoE3",
                level=Qgis.Critical,
            )
            message = (
                f"This indicator could not be started ({error}). "
                "Check its data source configuration and run it again."
            )
            self._mark_item_errored(item, message)
            self.processing_error.emit(message)
            return None
        self.workflow_queue.add_job(task)
        log_message(f"Task added: {task.description()}")
        return task

    @staticmethod
    def _mark_item_errored(item: JsonTreeItem, message: str) -> None:
        """Record a start failure on the tree item.

        Setting ``result`` to an error marker flips the item's status to
        "Workflow failed" (red icon) and ``error`` becomes its tooltip, so
        the user can see which indicator needs attention and why while the
        rest of the run continues.
        """
        try:
            item.setAttribute("result", "Workflow Error")
            item.setAttribute("error", message)
        except Exception:  # nosec B110 — display bookkeeping must never raise
            pass

    def _ensure_sqlite_safety_options_applied(self) -> None:
        """Harden GDAL SQLite options for the duration of an analysis run.

        Every indicator's workflow opens its own AreaIterator (3 fresh
        QgsVectorLayer reads) against the same study_area.gpkg that
        grid_column_utils is concurrently writing to; running many
        indicators back-to-back (a whole dimension/factor/analysis) without
        this hardening has been seen to corrupt the GeoPackage or hand back
        a stale GDAL dataset handle (Windows access violation inside
        getFeatures() - worldbank/GeoE3#447, #448). Idempotent: a second
        call before the matching restore is a no-op.
        """
        if self._sqlite_safety_snapshot is None:
            self._sqlite_safety_snapshot = apply_sqlite_write_safety_options()

    def _restore_sqlite_safety_options_if_applied(self) -> None:
        """Undo _ensure_sqlite_safety_options_applied, if it was applied."""
        if self._sqlite_safety_snapshot is not None:
            restore_sqlite_write_safety_options(self._sqlite_safety_snapshot)
            self._sqlite_safety_snapshot = None

    def start_processing(self) -> None:
        """Start processing the tasks in the WorkflowQueue."""
        log_message("Starting workflow queue processing...")
        self._ensure_sqlite_safety_options_applied()
        self.workflow_queue.start_processing()

    def start_processing_in_foreground(self) -> None:
        """Start processing the tasks in the WorkflowQueue in the main thread.

        Used for debugging and testing purposes.
        """
        log_message(
            "Starting FOREGROUND workflow queue processing...",
            tag="GeoE3",
            level=Qgis.Info,
        )
        self._ensure_sqlite_safety_options_applied()
        try:
            for job in self.workflow_queue.job_queue:
                job._workflow.execute()
        finally:
            self._restore_sqlite_safety_options_if_applied()

    def cancel_processing(self) -> None:
        """Cancels all tasks in the WorkflowQueue."""
        log_message("Cancelling workflow queue...")
        self.workflow_queue.cancel_processing()
        # cancel_processing() never emits processing_completed, so the
        # restore there would otherwise never run.
        self._restore_sqlite_safety_options_if_applied()

    def update_status(self) -> None:
        """Update the status of the workflow queue (for UI updates, etc.)."""
        log_message("Workflow queue status updated.")

    def on_processing_completed(self, success: bool) -> None:
        """
        Handle when all tasks in the queue have completed.

        Args:
            success: Indicates whether all tasks completed successfully.
        """
        self._restore_sqlite_safety_options_if_applied()
        if success:
            log_message(
                "All workflow tasks completed successfully.",
                tag="GeoE3",
                level=Qgis.Info,
            )
        else:
            log_message("Workflow processing was canceled.")
        self.processing_completed.emit()

    def log_status_message(self, message: str) -> None:
        """
        Logs status messages from the WorkflowQueue.

        Args:
            message: Status message to log.
        """
        log_message(message)

    def on_processing_error(self, error_message: str) -> None:
        """
        Handle when a task in the queue encounters an error.

        Args:
            error_message: The error message from the failed task.
        """
        log_message(f"Workflow error: {error_message}", tag="GeoE3", level=Qgis.Critical)
        # Forward the error through the manager's signal
        self.processing_error.emit(error_message)
