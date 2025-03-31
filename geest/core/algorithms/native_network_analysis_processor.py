import os
import traceback
from typing import Optional, List
import shutil

from qgis.core import (
    QgsTask,
    QgsFeature,
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
)
from qgis import processing
from geest.utilities import log_message, resources_path


class NativeNetworkAnalysisProcessor(QgsTask):
    """
    A QgsTask subclass for calculating a network analysis using native QGIS algorithms.

    It generates a polygon using the minimum convex hull of the points on
    the road network that can be travelled to within a specified time limit
    or distance.

    Args:
        network_layer_path (str): Path to the GeoPackage containing the network_layer_path.
        feature: The feature to use as the origin for the network analysis.
        mode: Travel time or travel distance ("time" or "distance").
        value: The time (in seconds) or distance (in meters) value to use for the analysis.
        working_directory: The directory to save the output files.
        force_clear: Flag to clear the output directory before running the analysis.
    """

    def __init__(
        self,
        network_layer_path: str,
        feature: QgsFeature,
        mode: str,
        value: float,
        working_directory: str,
    ):
        super().__init__("Native Network Analysis Processor", QgsTask.CanCancel)
        self.working_directory = working_directory
        os.makedirs(self.working_directory, exist_ok=True)

        self.network_layer_path = network_layer_path
        self.feature = feature

        self.mode = mode
        if self.mode not in ["time", "distance"]:
            raise ValueError("Invalid mode. Must be 'time' or 'distance'.")
        self.value = value
        if self.value <= 0:
            raise ValueError("Value must be greater than 0.")

        log_message("Initialized Native Network Analysis Processing Task")

    def run(self) -> bool:
        """
        Executes the Native Network Analysis Processing Task calculation task.
        """
        try:
            self.calculate_network()
            vrt_path = self.generate_vrt()

            return True
        except Exception as e:
            log_message(f"Task failed: {e}")
            log_message(traceback.format_exc())
            self.item.setAttribute(self.result_key, f"Task failed: {e}")
            return False

    def calculate_network(self) -> None:
        """
        Calculates all the points on the network that are reachable from the origin feature
        within the specified time or distance.
        """

        log_message(
            f"Calculating Network for feature {self.feature.id()} using {self.mode} {self.value}..."
        )
        output_path = os.path.join(
            self.working_directory, f"network_{self.feature.id()}.gpkg"
        )

        params = {
            "INPUT_A": mask_layer,
            "BAND_A": 1,
            "INPUT_B": wee_score_by_population_layer,
            "BAND_B": 1,
            "FORMULA": "A * B",
            "NO_DATA": None,
            "EXTENT_OPT": 3,
            "PROJWIN": None,
            "RTYPE": 0,
            "OPTIONS": "",
            "EXTRA": "",
            "OUTPUT": output_path,
        }

        processing.run("gdal:rastercalculator", params)
        self.output_rasters.append(output_path)

        log_message(f"Masked WEE SCORE raster saved to {output_path}")

    def finished(self, result: bool) -> None:
        """
        Called when the task completes.
        """
        if result:
            log_message(
                "Native Network Analysis Processing Task calculation completed successfully."
            )
        else:
            log_message("Native Network Analysis Processing Task calculation failed.")
