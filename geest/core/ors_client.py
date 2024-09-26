import os
from qgis.PyQt.QtCore import QUrl, QByteArray, QObject, pyqtSignal
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.core import QgsNetworkAccessManager, Qgis
import json


class ORSClient(QObject):
    # Signal to emit when the request is finished
    request_finished = pyqtSignal(object)

    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.network_manager = QgsNetworkAccessManager.instance()
        self.api_key = os.getenv("ORS_API_KEY")

        # Ensure the API key is available
        if not self.api_key:
            raise EnvironmentError(
                "ORS API key is missing. Set it in the environment variable 'ORS_API_KEY'."
            )

    def make_request(self, endpoint, params):
        """Make a request to the ORS API."""
        url = f"{self.base_url}/{endpoint}"
        request = QNetworkRequest(QUrl(url))

        # Set necessary headers for the ORS API
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
        request.setRawHeader(b"Authorization", self.api_key.encode())

        # Convert parameters (Python dict) to JSON
        data = QByteArray(json.dumps(params).encode("utf-8"))

        # Send the request and connect the finished signal
        reply = self.network_manager.post(request, data)
        reply.finished.connect(lambda: self.handle_response(reply))

    def handle_response(self, reply):
        """Handle the response from ORS API."""
        if reply.error() == reply.NoError:
            response_data = reply.readAll().data().decode()
            try:
                # Parse the JSON response
                response_json = json.loads(response_data)
                self.request_finished.emit(response_json)
            except json.JSONDecodeError:
                # Log or print the raw content if it is not valid JSON
                self.request_finished.emit(None)  # Emit None in case of failure
        else:
            # Emit None in case of error
            self.request_finished.emit(None)

        reply.deleteLater()
