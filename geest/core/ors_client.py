import os
from qgis.PyQt.QtCore import QUrl, QByteArray
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.core import QgsMessageLog, QgsNetworkAccessManager, Qgis
import json


class ORSClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.network_manager = QgsNetworkAccessManager.instance()
        self.api_key = os.getenv("ORS_API_KEY")

        # Ensure the API key is available
        if not self.api_key:
            raise EnvironmentError(
                "ORS API key is missing. Set it in the environment variable 'ORS_API_KEY'."
            )

    def make_request(self, endpoint, params):
        url = f"{self.base_url}/{endpoint}"
        request = QNetworkRequest(QUrl(url))

        # Set necessary headers for the ORS API
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
        if self.api_key:
            request.setRawHeader(b"Authorization", self.api_key.encode())

        # Convert parameters (Python dict) to JSON
        data = QByteArray(json.dumps(params).encode("utf-8"))

        # Send the request and return the reply object
        reply = self.network_manager.post(request, data)
        return reply

    def handle_response(self, reply):
        if reply.error() == reply.NoError:
            response_data = reply.readAll().data().decode()
            try:
                # Parse the JSON response
                response_json = json.loads(response_data)
                QgsMessageLog.logMessage(f"ORS Response: {response_json}", "ORS")
                return (
                    response_json  # Return the parsed response for further processing
                )
            except json.JSONDecodeError as e:
                QgsMessageLog.logMessage(
                    f"Failed to decode JSON: {e}", "ORS", Qgis.CRITICAL
                )
                return None  # Return None in case of failure
        else:
            # Handle error
            QgsMessageLog.logMessage(
                f"Error: {reply.errorString()}", "ORS", Qgis.CRITICAL
            )
            return None  # Return None in case of error
        reply.deleteLater()
