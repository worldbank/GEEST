from qgis.core import QgsTask, QgsFeedback, Qgis, QgsProcessingContext
from qgis.PyQt.QtCore import pyqtSignal
from .json_tree_item import JsonTreeItem
from .workflow_factory import WorkflowFactory
from geest.utilities import log_message


class WorkflowJob(QgsTask):
    """
    Represents an individual workflow task. Uses QgsFeedback for progress reporting
    and cancellation, and the WorkflowFactory to create the appropriate workflow.
    """

    # Signals for task lifecycle
    job_queued = pyqtSignal()
    job_started = pyqtSignal()
    job_canceled = pyqtSignal()
    # Custom signal to emit when the job is finished
    job_finished = pyqtSignal(bool)

    def __init__(
        self,
        description: str,
        context: QgsProcessingContext,
        item: JsonTreeItem,
        cell_size_m: float = 100.0,
    ):
        """
        Initialize the workflow job.
        :param description: Task description
        :param context: QgsProcessingContext object - we will use this to pass any QObjects in to the thread
                to keep things thread safe
        :param item: JsonTreeItem object representing the task - this is a reference
              so it will update the tree directly when modified
        :param cell_size_m: Cell size in meters for raster operations
        """
        super().__init__(description)
        self.context = (
            context  # QgsProcessingContext object used to pass objects to the thread
        )
        self._item = item  # ⭐️ This is a reference - whatever you change in this item will directly update the tree
        self._cell_size_m = cell_size_m  # Cell size in meters for raster operations
        self._feedback = QgsFeedback()  # Feedback object for progress and cancellation
        workflow_factory = WorkflowFactory()
        self._workflow = workflow_factory.create_workflow(
            item=self._item,
            cell_size_m=self._cell_size_m,
            feedback=self._feedback,
            context=self.context,
        )  # Create the workflow
        self.setProgress(0)
        self._workflow.progressChanged.connect(self.updateProgress)
        # TODO this raises an error... need to figure out how to connect this signal
        # self._workflow.progressChanged.connect(self.setProgress)
        # Emit the 'queued' signal upon initialization
        self.job_queued.emit()

    # Dont call this setProgress to avoid recursion
    def updateProgress(self, progress: int):
        """
        Used by the workflow to set the progress of the task.
        :param progress: The progress value
        """
        self.setProgress(progress)

    def run(self) -> bool:
        """
        Executes the workflow created by the WorkflowFactory. Uses the QgsFeedback
        object for progress reporting and cancellation.
        :return: True if the task was successful, False otherwise
        """

        if not self._workflow:
            log_message(
                f"Error: No workflow assigned to {self.description()}",
                tag="Geest",
                level=Qgis.Critical,
            )
            return False

        try:
            log_message(f"Running workflow: {self.description()}")

            # Emit the 'started' signal before running the workflow
            self.job_started.emit()
            result = self._workflow.execute()
            log_message(
                f"WorkflowJob {self.description()} attributes.",
                tag="Geest",
                level=Qgis.Info,
            )
            attributes = self._item.attributes()
            log_message(f"{self._item.attributesAsMarkdown()}")
            if result:
                log_message(
                    f"Workflow {self.description()} completed.",
                    tag="Geest",
                    level=Qgis.Info,
                )
                return True
            else:
                log_message(
                    f"Workflow {self.description()} did not complete successfully.",
                    tag="Geest",
                    level=Qgis.Info,
                )
                return False

        except Exception as e:
            log_message(f"Error during task execution: {e}", level=Qgis.Critical)
            import traceback

            log_message(
                f"{traceback.format_exc()}",
                tag="Geest",
                level=Qgis.Critical,
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
        log_message(
            "0000000000000 🏁 Job Finished 000000000000000000",
            tag="Geest",
            level=Qgis.Info,
        )
        # Emit the custom signal job_finished with the success state
        self.job_finished.emit(success)
