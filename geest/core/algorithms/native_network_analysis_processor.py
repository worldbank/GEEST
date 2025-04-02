import os
import traceback
from typing import Optional, List

from qgis.core import (
    QgsTask,
    QgsFeature,
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
)
from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY
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
        crs: The coordinate reference system to use for the analysis.
        mode: Travel time or travel distance ("time" or "distance").
        value: The time (in seconds) or distance (in meters) value to use for the analysis.
        working_directory: The directory to save the output files.
        force_clear: Flag to clear the output directory before running the analysis.
    """

    def __init__(
        self,
        network_layer_path: str,
        feature: QgsFeature,
        crs: QgsCoordinateReferenceSystem,
        mode: str,
        value: float,
        working_directory: str,
    ):
        super().__init__("Native Network Analysis Processor", QgsTask.CanCancel)
        self.working_directory = working_directory
        os.makedirs(self.working_directory, exist_ok=True)

        self.network_layer_path = network_layer_path
        self.feature = feature
        self.crs = crs

        self.mode = mode
        if self.mode not in ["time", "distance"]:
            raise ValueError("Invalid mode. Must be 'time' or 'distance'.")
        self.value = value
        if self.value <= 0:
            raise ValueError("Value must be greater than 0.")
        self.service_area = None  # Will hold the calculated service area feature
        log_message("Initialized Native Network Analysis Processing Task")

    def run(self) -> bool:
        """
        Executes the Native Network Analysis Processing Task calculation task.
        """
        try:
            self.calculate_network()
            # self.service_area should be set after the calculation
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
        # Create a memory layer with a single point feature
        point_layer = QgsVectorLayer(
            f"Point?crs=EPSG:{self.crs.authid}&field=id:integer",
            "start_point",
            "memory",
        )
        provider = point_layer.dataProvider()
        provider.addFeature(self.feature)
        point_layer.updateExtents()

        result1 = processing.run(
            "native:serviceareafromlayer",
            {
                "INPUT": self.network_layer_path,  # Use parameterized road layer input
                "STRATEGY": 0,
                "DIRECTION_FIELD": "",
                "VALUE_FORWARD": "",
                "VALUE_BACKWARD": "",
                "VALUE_BOTH": "",
                "DEFAULT_DIRECTION": 2,
                "SPEED_FIELD": "",
                "DEFAULT_SPEED": 50,
                "TOLERANCE": 0,
                "START_POINTS": point_layer,  # Use the created memory layer as input
                "TRAVEL_COST2": self.value,
                "INCLUDE_BOUNDS": False,
                "POINT_TOLERANCE": None,
                "OUTPUT_LINES": None,
                "OUTPUT": "TEMPORARY_OUTPUT",
            },
        )

        result2 = processing.run(
            "native:multiparttosingleparts",
            {
                "INPUT": result1["OUTPUT"],  # Pass output from service area step
                "OUTPUT": "TEMPORARY_OUTPUT",
            },
        )

        result3 = processing.run(
            "native:concavehull",
            {
                "INPUT": result2["OUTPUT"],  # Pass output from multipart step
                "ALPHA": 0.3,
                "HOLES": False,
                "NO_MULTIGEOMETRY": False,
                "OUTPUT": "TEMPORARY_OUTPUT",
            },
        )

        # There should only be one feature in the concave hull layer
        concave_hull_layer = result3["OUTPUT"]
        if concave_hull_layer.featureCount() != 1:
            raise ValueError("Concave hull layer should have only one feature.")
        # return the feature
        self.service_area = concave_hull_layer.getFeature(0)
        log_message(f"Service area calculated for feature {self.feature.id()}.")
        return

    def finished(self, result: bool) -> None:
        """
        Called when the task completes.
        """
        if result:
            log_message(
                "Native Network Analysis Processing Task calculation completed successfully."
                "Access the service area feature using the 'service_area' attribute."
            )
        else:
            log_message("Native Network Analysis Processing Task calculation failed.")
