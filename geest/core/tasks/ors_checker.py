from qgis.core import (
    QgsTask,
    QgsMessageLog,
    Qgis,
    QgsNetworkAccessManager,
    QgsApplication,
)
from qgis.PyQt.QtCore import QEventLoop, QUrl, QMetaObject, Qt, pyqtSignal
from qgis.PyQt.QtNetwork import QNetworkRequest


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
        self.response_content = None  # To store the response

    def run(self):
        """This code will be executed in the background thread."""
        try:
            # Move the network request to the main thread
            QMetaObject.invokeMethod(
                self, "make_synchronous_request", Qt.QueuedConnection
            )
            self.wait_for_reply()  # Wait for the reply synchronously
            if self.response_content:
                QgsMessageLog.logMessage(
                    f"Response: {self.response_content}", "Geest", Qgis.Info
                )
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
        """Perform synchronous network request using QgsNetworkAccessManager."""
        # Create a network access manager instance
        network_manager = QgsNetworkAccessManager.instance()

        # Create a network request
        request = QNetworkRequest(QUrl(self.url))

        # Create a local event loop to wait for the response
        event_loop = QEventLoop()

        # Make the request (GET request in this case)
        reply = network_manager.get(request)

        # Connect the finished signal of the reply to quit the event loop
        reply.finished.connect(event_loop.quit)

        # Start the event loop and wait for the request to finish
        event_loop.exec_()

        # Check if the request was successful
        if reply.error() == reply.NoError:
            return reply.readAll().data().decode("utf-8")
        else:
            raise Exception(f"Network error: {reply.errorString()}")

    def wait_for_reply(self):
        """Wait until the network request is completed."""
        while self.response_content is None:
            QgsApplication.processEvents()  # Keep processing events


# Example usage within QGIS
# def run_task():
#    url = "https://httpbin.org/get"
#    task = NetworkTask("Fetch Network Data", url)
