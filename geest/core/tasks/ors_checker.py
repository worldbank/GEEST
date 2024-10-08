from functools import partial
import typing
from qgis.core import (
    QgsTask,
    QgsMessageLog,
    Qgis,
    QgsNetworkContentFetcherTask,
    QgsApplication,
)
from qgis.PyQt.QtCore import pyqtSignal, QEventLoop, QUrl


class OrsCheckerTask(QgsTask):
    """
    Utility to demonstrate that we have a valid ORS key set up and we can call ORS
    from a thread.
    """

    # Signals for task lifecycle
    job_queued = pyqtSignal()
    job_started = pyqtSignal()
    job_canceled = pyqtSignal()
    # Custom signal to emit when the job is finished
    job_finished = pyqtSignal(bool)
    job_failed = pyqtSignal(str)  # Signal for task failure

    def __init__(self, description, url):
        super().__init__(description)
        self.url = url
        self.result_path = "/tmp/test.txt"
        self.response_content = None  # To store the response
        self.response_handler: typing.Callable
        self.error_handler: typing.Callable
        self.event_loop = (
            QEventLoop()
        )  # Local event loop to simulate synchronous behavior

    def run(self):
        """This code will be executed in the background thread."""
        try:
            # Move the network request to the main thread
            self.make_synchronous_request()
            return True
        except Exception as e:
            QgsMessageLog.logMessage(f"Error: {str(e)}", "Geest", Qgis.Critical)
            return False

    def finished(self, result):
        """Called when the task is complete."""
        if result:
            QgsMessageLog.logMessage(
                "Task completed successfully", "Geest", Qgis.Success
            )
            self.job_finished.emit(True)
        else:
            QgsMessageLog.logMessage("Task failed", "Geest", Qgis.Critical)
            self.job_failed.emit("ORS Check Task failed")

    def make_synchronous_request(self):
        """Perform synchronous network request using QgsNetworkContentFetcherTask."""
        # Create the QgsNetworkContentFetcherTask
        task = QgsNetworkContentFetcherTask(QUrl(self.url))

        # Connect response handler
        task.fetched.connect(partial(self.response_handler, task))

        # Connect error handler
        task.errorOccurred.connect(self.error_handler)

        # Run the task (this runs in the background thread)
        QgsApplication.taskManager().addTask(task)

        # Start the event loop and wait for the request to complete
        # enable this to CRASH QGIS!
        # self.event_loop.exec_()

    def response_handler(self, task, content=None):
        """Handle the fetched response content."""
        if task.errorOccurred():
            QgsMessageLog.logMessage(
                f"Error: {task.errorMessage()}", "Geest", Qgis.Critical
            )
            self.event_loop.quit()  # Exit the event loop on error
            return

        # Process the response
        self.response_content = content.decode("utf-8") if content else None

        if self.response_content:
            QgsMessageLog.logMessage(
                f"Response received: {self.response_content}", "Geest", Qgis.Info
            )
        else:
            QgsMessageLog.logMessage("No content received", "Geest", Qgis.Warning)

        # Quit the event loop after processing the response
        self.event_loop.quit()

    def error_handler(self, error_msg):
        """Handle any errors that occur during the network request."""
        QgsMessageLog.logMessage(f"Network error: {error_msg}", "Geest", Qgis.Critical)
        # Exit the event loop in case of error
        self.event_loop.quit()
