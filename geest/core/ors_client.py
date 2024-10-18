import os
from qgis.PyQt.QtCore import QUrl, QByteArray, QObject, pyqtSignal
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.core import (
    QgsNetworkAccessManager,
    Qgis,
    QgsNetworkReplyContent,
    QgsMessageLog,
)
import json
from geest.core import setting


class ORSClient(QObject):
    # Signal to emit when the request is finished
    request_finished = pyqtSignal(object)

    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.network_manager = QgsNetworkAccessManager.instance()
        self.check_api_key()

    def check_api_key(self):
        self.api_key = setting(key="ors_key", default="")
        if not self.api_key:
            self.api_key = os.getenv("ORS_API_KEY")
        if not self.api_key:
            raise EnvironmentError(
                "ORS API key is missing. Set it in settings panel or the environment variable 'ORS_API_KEY"
            )
        return self.api_key

    def make_request(self, endpoint, params):
        """Make a request to the ORS API.

        This will make a blocking post request to the ORS API and return the response as a JSON object.
        It is intended to be used in a thread so that the UI does not freeze.


        Args:
            endpoint (str): The endpoint to send the request to.
            params (dict): The parameters to send with the request.

        Returns:
            dict: The response from the ORS API as a JSON object.

        """
        url = QUrl(f"{self.base_url}/{endpoint}")
        request = QNetworkRequest(QUrl(url))

        # Set necessary headers for the ORS API
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
        request.setRawHeader(b"Authorization", self.api_key.encode())

        # Convert parameters (Python dict) to JSON
        # data = QByteArray(json.dumps(params).encode("utf-8"))
        data = json.dumps(params).encode("utf-8")
        QgsMessageLog.logMessage(str(params), tag="Geest", level=Qgis.Info)
        # Send the request and connect the finished signal
        reply: QgsNetworkReplyContent = self.network_manager.blockingPost(request, data)
        response_data = reply.content()
        QgsMessageLog.logMessage(str(response_data), tag="Geest", level=Qgis.Info)
        response_string = str(response_data)
        # remove b' at the beginning and ' at the end
        response_string = response_string[2:-1]
        response_json = json.loads(response_string)
        QgsMessageLog.logMessage(str(response_json), tag="Geest", level=Qgis.Info)
        return response_json
