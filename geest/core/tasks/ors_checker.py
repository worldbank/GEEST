from typing import Optional

from qgis.core import (
    QgsTask,
    Qgis,
)
from qgis.PyQt.QtCore import pyqtSignal
from geest.core import setting
from geest.core.ors_client import ORSClient
from geest.utilities import log_message


class OrsCheckerTask(QgsTask):
    # Custom signal to emit when the job is finished
    job_finished = pyqtSignal(bool)

    def __init__(self, url: str):
        super().__init__("ORS API Key Validation Task", QgsTask.CanCancel)
        self.url = url
        self.exception: Optional[Exception] = None
        self.is_key_valid = False  # Store whether the key is valid or not
        self.ors_client = ORSClient("https://api.openrouteservice.org/v2/isochrones")

    def run(self):
        """Do the work to validate the ORS API key."""
        try:
            # Retrieve the ORS API key from settings
            ors_key = setting("ors_key", "")
            if not ors_key:
                raise ValueError("ORS API key is missing from settings.")
            params = {
                "locations": [[8.681495, 49.41461]],
                "range": [100, 500],  # Distances or times in the list
                "range_type": "distance",
            }
            mode = "foot-walking"
            # Make the request to ORS API using ORSClient
            response = self.ors_client.make_request(mode, params)
            log_message(
                f"ORS API Key Validation Task response: {response}",
                tag="Geest",
                level=Qgis.Info,
            )
            # Assuming the response JSON contains a 'status' field
            if response.get("type") == "FeatureCollection":
                self.is_key_valid = True
                log_message("ORS API Key is valid.")
            else:
                self.is_key_valid = False
                log_message("ORS API Key is invalid.", level=Qgis.Warning)

            self.setProgress(100)
            return True
        except Exception as e:
            self.exception = e
            log_message(
                f"Exception in ORS API Key Validation Task: {str(e)}",
                tag="Geest",
                level=Qgis.Critical,
            )
            return False

    def finished(self, result):
        """Postprocessing after the run() method."""
        if self.isCanceled():
            log_message(
                "ORS API Key Validation Task was canceled by the user.",
                tag="Geest",
                level=Qgis.Warning,
            )
            self.job_finished.emit(False)
            return

        if not result:
            log_message("ORS API Key Validation Task failed.", level=Qgis.Critical)
            if self.exception:
                log_message(f"Error: {self.exception}", level=Qgis.Critical)
            self.job_finished.emit(False)
            return

        # Check the result of the API key validation
        if self.is_key_valid:
            log_message("ORS API Key is valid.")
            self.job_finished.emit(True)
        else:
            log_message("ORS API Key is invalid.", level=Qgis.Warning)
            self.job_finished.emit(False)
