import os
from qgis.PyQt.QtCore import QUrl, QByteArray, QObject, pyqtSignal
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.core import (
    QgsNetworkAccessManager,
    Qgis,
    QgsNetworkReplyContent,
)
import json
from geest.core import setting
from geest.utilities import log_message


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

    def make_request(self, endpoint: str, params: dict) -> dict:
        """Make a request to the ORS API.

        This will make a blocking post request to the ORS API and return the response as a JSON object.
        It is intended to be used in a thread so that the UI does not freeze.

        Args:
            endpoint (str): The endpoint to send the request to.
            params (dict): The parameters to send with the request.

        Returns:
            dict: The response from the ORS API as a JSON object.

        Raises:
            ValueError: If the API token is invalid.
            RuntimeError: If the request fails with a 404 or other errors.
        """
        url = QUrl(f"{self.base_url}/{endpoint}")
        request = QNetworkRequest(QUrl(url))

        # Set necessary headers for the ORS API
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
        request.setRawHeader(b"Authorization", self.api_key.encode())

        # Convert parameters (Python dict) to JSON
        data = json.dumps(params).encode("utf-8")
        verbose_mode = int(setting(key="verbose_mode", default=0))
        if verbose_mode:
            log_message(f"Request parameters: {params}")

        # Send the request and connect the finished signal
        reply = self.network_manager.blockingPost(request, data)

        # Check HTTP status code
        status_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if status_code is None:
            raise RuntimeError("No status code received. Network issue?")

        if status_code == 404:
            raise RuntimeError(f"Error 404: Endpoint {endpoint} not found.")
        elif status_code == 401:
            raise ValueError("Invalid API token. Please check your credentials.")
        elif status_code == 429:
            raise RuntimeError("API quota exceeded. Please try again later.")
        elif status_code >= 400:
            # Generic error handling for other client/server errors
            raise RuntimeError(f"HTTP Error {status_code}: {reply.content()}")

        # Parse JSON response
        try:
            # Get response data
            response_data = reply.content()
            # response_string = response_data.decode("utf-8")
            response_string = str(response_data)
            # remove b' at the beginning and ' at the end
            response_string = response_string[2:-1]
            response_json = json.loads(response_string)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse JSON response: {e}")

        if verbose_mode:
            log_message(f"Response JSON: {response_json}")

        return response_json
