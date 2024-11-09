from typing import Optional
import json

from qgis.core import (
    QgsTask,
    QgsMessageLog,
    Qgis,
    QgsNetworkAccessManager,
    QgsNetworkReplyContent,
)
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest, QNetworkReply
from qgis.PyQt.QtCore import pyqtSignal
from geest.core import setting


class OrsCheckerTask(QgsTask):
    # Custom signal to emit when the job is finished
    job_finished = pyqtSignal(bool)

    def __init__(self, url: str):
        super().__init__("ORS API Key Validation Task", QgsTask.CanCancel)
        self.url = url
        self.exception: Optional[Exception] = None
        self.is_key_valid = False  # Store whether the key is valid or not

    def run(self):
        """Do the work to validate the ORS API key."""
        try:
            # Retrieve the ORS API key from settings
            ors_key = setting("ors_key", "")
            if not ors_key:
                raise ValueError("ORS API key is missing from settings.")

            # Prepare the network request with the API key in headers
            nam = QgsNetworkAccessManager()
            url = QUrl(f"{self.url}/v2/health")  # Example endpoint for health check
            request = QNetworkRequest(url)
            request.setRawHeader(b"Authorization", ors_key.encode("utf-8"))

            # Send the request and block until a response is received
            reply: QgsNetworkReplyContent = nam.blockingGet(request)

            # Check the HTTP status code
            if reply.error() != QNetworkReply.NoError:
                raise ValueError("Network error occurred while validating ORS API key.")

            # Parse the response content to determine if the key is valid
            response_content = reply.content().data().decode("utf-8")
            response_json = json.loads(response_content)

            # Assuming the response JSON contains a 'status' field
            if response_json.get("status") == "ready":
                self.is_key_valid = True
                QgsMessageLog.logMessage(
                    "ORS API Key is valid.", tag="Geest", level=Qgis.Info
                )
            else:
                self.is_key_valid = False
                QgsMessageLog.logMessage(
                    "ORS API Key is invalid.", tag="Geest", level=Qgis.Warning
                )

            self.setProgress(100)
            return True
        except Exception as e:
            self.exception = e
            QgsMessageLog.logMessage(
                f"Exception in ORS API Key Validation Task: {str(e)}",
                tag="Geest",
                level=Qgis.Critical,
            )
            return False

    def finished(self, result):
        """Postprocessing after the run() method."""
        if self.isCanceled():
            QgsMessageLog.logMessage(
                "ORS API Key Validation Task was canceled by the user.",
                tag="Geest",
                level=Qgis.Warning,
            )
            self.job_finished.emit(False)
            return

        if not result:
            QgsMessageLog.logMessage(
                "ORS API Key Validation Task failed.", tag="Geest", level=Qgis.Critical
            )
            if self.exception:
                QgsMessageLog.logMessage(
                    f"Error: {self.exception}", tag="Geest", level=Qgis.Critical
                )
            self.job_finished.emit(False)
            return

        # Check the result of the API key validation
        if self.is_key_valid:
            QgsMessageLog.logMessage(
                "ORS API Key is valid.", tag="Geest", level=Qgis.Info
            )
            self.job_finished.emit(True)
        else:
            QgsMessageLog.logMessage(
                "ORS API Key is invalid.", tag="Geest", level=Qgis.Warning
            )
            self.job_finished.emit(False)
