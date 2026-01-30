# -*- coding: utf-8 -*-
"""📦 Workflow Queue module.

This module contains functionality for workflow queue.
"""

from functools import partial
from typing import List

from PyQt5.QtCore import QObject, pyqtSignal
from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QMutex, QMutexLocker

from geest.core import setting
from geest.utilities import log_message

from .workflow_job import WorkflowJob


class WorkflowQueue(QObject):
    """
    A queue of workflow jobs. Handles submission of the jobs as background tasks
    using a pool of available threads.
    """

    # Signals
    status_changed = pyqtSignal()
    processing_completed = pyqtSignal(bool)
    status_message = pyqtSignal(str)
    processing_error = pyqtSignal(str)  # propogate error messages

    def __init__(self, pool_size: int, parent=None):
        """🏗️ Initialize the instance.

        Args:
            pool_size: Pool size.
            parent: Parent.
        """
        super().__init__(parent=parent)
        # The maximum number of concurrent threads to allow
        self.thread_pool_size = pool_size
        # A list of tasks that need to be executed but
        # cannot be because the job queue is full.
        self.job_queue: List[WorkflowJob] = []
        self.active_tasks = {}
        # Mutex to protect active_tasks dictionary from concurrent access
        self._active_tasks_mutex = QMutex()

        # Overall queue statistics
        self.total_queue_size = 0
        self.total_completed = 0

    def get_effective_pool_size(self) -> int:
        """
        Get the effective pool size, reading from settings if not set.

        This allows the pool size to be changed dynamically without restarting QGIS.
        If thread_pool_size was set during initialization, that value is used.
        Otherwise, reads from the 'concurrent_tasks' setting.

        Returns:
            The pool size to use for concurrent tasks.
        """
        if self.thread_pool_size is None:
            return int(setting(key="concurrent_tasks", default=1))
        return self.thread_pool_size

    def active_queue_size(self) -> int:
        """
        Returns the number of currently active tasks (thread-safe).

        This is a PUBLIC method that acquires the lock.
        """
        locker = QMutexLocker(self._active_tasks_mutex)
        return len(self.active_tasks)

    def _active_queue_size_unsafe(self) -> int:
        """
        Returns the number of currently active tasks WITHOUT locking.

        INTERNAL USE ONLY - caller must hold _active_tasks_mutex lock.
        """
        return len(self.active_tasks)

    def reset(self):
        """
        Resets the queue
        """
        self.job_queue.clear()
        locker = QMutexLocker(self._active_tasks_mutex)
        self.active_tasks.clear()
        locker = None  # Release lock
        self.total_queue_size = 0
        self.total_completed = 0
        self.update_status()

    def cancel_processing(self):
        """
        Cancels any in-progress operation.

        Best practice: Copy task list while locked, cancel outside lock.
        """
        self.job_queue.clear()
        self.total_queue_size = 0
        self.total_completed = 0

        # Step 1: Acquire lock, copy task list, release lock
        locker = QMutexLocker(self._active_tasks_mutex)
        tasks_to_cancel = list(self.active_tasks.values())
        locker = None  # Release lock

        # Step 2: Cancel tasks outside of lock (task.cancel() might trigger callbacks)
        for task in tasks_to_cancel:
            task.cancel()

        # Step 3: Emit signals (no locks held)
        self.status_message.emit("Cancelling...")
        self.update_status()

    def update_status(self):
        """
        Called whenever the status of the queue has changed and listeners should be notified accordingly
        """
        self.status_changed.emit()

    def start_processing(self):
        """
        Starts processing the queue
        """
        self.process_queue()

    def process_queue(self):
        """
        Feed the QgsTaskManager with the next task in the queue.

        Best practice: Read all locked values first, release lock, then compute.
        """
        # Step 1: Acquire lock once, read all necessary values, then release
        locker = QMutexLocker(self._active_tasks_mutex)
        active_count = self._active_queue_size_unsafe()
        locker = None  # Release lock immediately

        # Step 2: Check completion condition (no locks held)
        if not self.job_queue and active_count == 0:
            # All tasks are done
            self.update_status()
            self.processing_completed.emit(True)
            return

        if not self.job_queue:
            # No more jobs to add, but some jobs are still running
            self.update_status()
            return

        # Step 3: Calculate free threads (no locks held)
        pool_size = self.get_effective_pool_size()
        free_threads = pool_size - active_count

        # Step 4: Process jobs (acquire lock only when modifying active_tasks)
        for _ in range(free_threads):
            if not self.job_queue:
                break
            job = self.job_queue.pop(0)

            # Emit signal before acquiring lock
            self.status_message.emit(f"Starting workflow task: {job.description()}")

            # Acquire lock only for dictionary modification
            locker = QMutexLocker(self._active_tasks_mutex)
            self.active_tasks[job.description()] = job
            locker = None  # Release lock immediately

            # Connect signals and add task (no locks held)
            job.taskCompleted.connect(partial(self.task_completed, job_name=job.description()))
            job.taskTerminated.connect(partial(self.finalize_task, job_name=job.description()))
            # Connect to error signal - this assumes your WorkflowJob has an error_occurred signal
            if hasattr(job, "error_occurred"):
                job.error_occurred.connect(self.handle_job_error)
            else:
                log_message("######################################################")
                log_message(f"Job {job.description()} does not have an error_occurred signal.")
                log_message("######################################################")
            QgsApplication.taskManager().addTask(job)

        # Emit status update (no locks held)
        self.update_status()

    def task_completed(self, job_name: str):
        """
        Called whenever an active task is successfully completed
        """
        self.finalize_task(job_name)

    def finalize_task(self, job_name: str):
        """
        Finalizes a task -- called for both successful and non-successful tasks
        """
        locker = QMutexLocker(self._active_tasks_mutex)
        if job_name in self.active_tasks:
            del self.active_tasks[job_name]
        locker = None  # Release lock

        self.total_completed += 1

        self.status_changed.emit()
        self.process_queue()

    def add_job(self, job):
        """
        Adds a job to the queue
        """
        if job not in self.job_queue:
            # Check if the job is already in the queue
            self.status_message.emit(f"Adding workflow task: {job.description()}")
            self.job_queue.append(job)
            self.total_queue_size += 1
        else:
            # Job is already in the queue
            self.status_message.emit(f"Job {job.description()} is already in the queue. Skipping.")
            return

    def handle_job_error(self, error_message: str):
        """
        Handle errors from workflow jobs
        :param error_message: The error message from the job
        """
        self.status_message.emit(f"Error in workflow: {error_message}")
        # Propagate the error up to listeners
        self.processing_error.emit(error_message)
