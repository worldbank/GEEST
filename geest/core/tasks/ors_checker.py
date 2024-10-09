from typing import Optional

from qgis.core import (
    QgsTask,
    QgsMessageLog,
    Qgis,
    QgsNetworkAccessManager,
    QgsNetworkReplyContent,
)
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest


class OrsCheckerTask(QgsTask):
    # Crashes QGIS
    # job_finished = pyqtSignal(bool)
    # job_failed = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__("ORS download task", QgsTask.CanCancel)
        self.output_dir = "/tmp/"
        self.content = None
        self.url = url
        self.exception: Optional[Exception] = None

    def run(self):
        """Do the work."""
        try:
            nam = QgsNetworkAccessManager()

            # get the new tile if it didn't exist
            url = QUrl(f"{self.url}")
            request = QNetworkRequest(url)
            reply: QgsNetworkReplyContent = nam.blockingGet(request)
            self.content = reply.content()
            # write the content to "/tmp/ors_response.json"
            with open("/tmp/ors_response.json", "wb") as f:
                f.write(self.content)
            self.setProgress(100)

            return True
        except Exception as e:
            # Dont raise the exception in a thread, you will crash QGIS
            self.exception = e
            return False

    def finished(self, result):
        """Postprocessing after the run() method."""
        if self.isCanceled():
            # if it was canceled by the user
            QgsMessageLog.logMessage(
                message=f"Canceled download task.",
                level=Qgis.Warning,
            )
            return
        elif not result:
            # if there was an error
            QgsMessageLog.logMessage(
                message=f"Canceled download task.",
                level=Qgis.Warning,
            )
            return
        QgsMessageLog.logMessage(
            message=f"ORS Check Succeeded.",
            level=Qgis.Warning,
        )
