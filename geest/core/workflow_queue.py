from functools import partial
from qgis.core import QgsApplication
from PyQt5.QtCore import QObject, pyqtSignal
from typing import List, Optional
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

    def __init__(self, pool_size: int, parent=None):
        super().__init__(parent=parent)
        # The maximum number of concurrent threads to allow
        self.thread_pool_size = pool_size
        # A list of tasks that need to be executed but
        # cannot be because the job queue is full.
        self.job_queue: List[WorkflowJob] = []
        self.active_tasks = {}

        # Overall queue statistics
        self.total_queue_size = 0
        self.total_completed = 0

    def active_queue_size(self) -> int:
        """
        Returns the number of currently active tasks
        """
        return len(self.active_tasks)

    def reset(self):
        """
        Resets the queue
        """
        self.job_queue.clear()
        self.active_tasks.clear()
        self.total_queue_size = 0
        self.total_completed = 0
        self.update_status()

    def cancel_processing(self):
        """
        Cancels any in-progress operation
        """
        self.job_queue.clear()
        self.total_queue_size = 0
        self.total_completed = 0

        for _, task in self.active_tasks.items():
            task.cancel()

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
        Feed the QgsTaskManager with the next task in the queue
        """
        if not self.job_queue and not self.active_tasks:
            # All tasks are done
            self.update_status()
            self.processing_completed.emit(True)
            return

        if not self.job_queue:
            # No more jobs to add, but some jobs are still running
            self.update_status()
            return

        # Determine how many threads are free to take new jobs
        free_threads = self.thread_pool_size - self.active_queue_size()
        for _ in range(free_threads):
            if not self.job_queue:
                break
            job = self.job_queue.pop(0)

            self.status_message.emit(f"Starting workflow task: {job.description()}")

            self.active_tasks[job.description()] = job

            job.taskCompleted.connect(
                partial(self.task_completed, job_name=job.description())
            )
            job.taskTerminated.connect(
                partial(self.finalize_task, job_name=job.description())
            )

            QgsApplication.taskManager().addTask(job)

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
        if job_name in self.active_tasks:
            del self.active_tasks[job_name]
        self.total_completed += 1

        self.status_changed.emit()
        self.process_queue()

    def add_job(self, job):
        """
        Adds a job to the queue
        """
        self.job_queue.append(job)
        self.total_queue_size += 1
