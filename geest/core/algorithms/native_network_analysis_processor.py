import os
import traceback
from typing import Optional, List

from qgis.core import (
    QgsTask,
    QgsFeature,
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
    QgsRectangle,
    QgsWkbTypes,
    QgsVectorFileWriter,
    QgsFields,
    QgsField,
    QgsProject,
    edit,
)
from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY
from qgis.PyQt.QtCore import QVariant
from qgis import processing
from geest.utilities import log_message, resources_path


class NativeNetworkAnalysisProcessor(QgsTask):
    """
    A QgsTask subclass for calculating a network analysis using native QGIS algorithms.

    It generates a polygon using the minimum convex hull of the points on
    the road network that can be travelled to within a specified time limit
    or distance.

    The output polygon is written to the isochrones geopackage in the
    working directory. If they geopackage already exists, it will be appended to.
    If the geopackage does not exist, it will be created.
    The output is a GeoPackage with the name "isochrones.gpkg" in the working directory.
    The output polygon is a single part polygon, and the travel time or distance

    Args:
        network_layer_path (str): Path to the GeoPackage containing the network_layer_path.
        feature: The feature to use as the origin for the network analysis.
        crs: The coordinate reference system to use for the analysis.
        mode: Travel time or travel distance ("time" or "distance").
        values (List[int]): A list of time (in seconds) or distance (in meters) values to use for the analysis.
        working_directory: The directory to save the output files.

    """

    def __init__(
        self,
        network_layer_path: str,
        feature: QgsFeature,
        crs: QgsCoordinateReferenceSystem,
        mode: str,
        values: List[int],
        working_directory: str,
    ):
        super().__init__("Native Network Analysis Processor", QgsTask.CanCancel)
        self.working_directory = working_directory
        os.makedirs(self.working_directory, exist_ok=True)
        self.crs = crs

        self.network_layer_path = network_layer_path
        # Verify the network layer is a valid line layer and in the
        # same crs as the self.crs
        network_layer = QgsVectorLayer(self.network_layer_path, "network_layer", "ogr")
        if not network_layer.isValid():
            raise ValueError(f"Network layer is invalid: {self.network_layer_path}")
        if network_layer.geometryType() != QgsWkbTypes.LineGeometry:
            raise ValueError("Network layer must be a line layer.")
        if network_layer.crs() != self.crs:
            raise ValueError(
                f"Network layer CRS {network_layer.crs().authid()} does not match the specified CRS {self.crs.authid()}."
            )

        self.feature = feature

        self.mode = mode
        if self.mode not in ["time", "distance"]:
            raise ValueError("Invalid mode. Must be 'time' or 'distance'.")
        self.values = values
        if not all(isinstance(value, int) and value > 0 for value in self.values):
            raise ValueError(f"All values must be positive integers. {self.values}")
        self.service_areas = []  # Will hold the calculated service area features

        self.isochrone_layer_path = os.path.join(
            self.working_directory, "isochrones.gpkg"
        )
        layer_name: str = "isochrones"
        # try to open the GeoPackage to check if it exists
        self.isochrone_layer = QgsVectorLayer(
            self.isochrone_layer_path, layer_name, "ogr"
        )
        if self.isochrone_layer.isValid():
            # If the layer exists, append to it
            log_message(
                f"Appending to existing GeoPackage: {self.isochrone_layer_path}"
            )
        else:
            # Define the fields (attributes)
            fields: QgsFields = QgsFields()
            fields.append(QgsField("value", QVariant.Double))

            # Create the GeoPackage layer

            # SaveVectorOptions contains many settings for the writer process
            save_options = QgsVectorFileWriter.SaveVectorOptions()
            # save_options.driverName = "ESRI Shapefile"
            # save_options.fileEncoding = "UTF-8"
            # if driverName is not set, Write to a GeoPackage (default)
            transform_context = QgsProject.instance().transformContext()
            writer = QgsVectorFileWriter.create(
                self.isochrone_layer_path,
                fields,
                QgsWkbTypes.Polygon,
                self.crs,
                transform_context,
                save_options,
            )
            if writer.hasError() != QgsVectorFileWriter.NoError:
                log_message(
                    "Error when creating isochrone gpkg: ", writer.errorMessage()
                )

            else:
                log_message("Isochrone layer created with success!")
                self.isochrone_layer = QgsVectorLayer(
                    self.isochrone_layer_path, layer_name, "ogr"
                )

        log_message("Initialized Native Network Analysis Processing Task")

    def __del__(self):
        """
        Destructor to clean up resources.
        """
        if hasattr(self, "isochrone_layer") and self.isochrone_layer:
            try:
                self.isochrone_layer.stopeEditing(saveChanges=True)
            except Exception as e:
                log_message(f"Error stopping editing: {e}")
            del self.isochrone_layer
        log_message("Native Network Analysis Processor resources cleaned up.")

    def run(self) -> bool:
        """
        Executes the Native Network Analysis Processing Task calculation task.
        """
        try:
            self.calculate_network()
            return True
        except Exception as e:
            log_message(f"Task failed: {e}")
            log_message(traceback.format_exc())
            return False

    def calculate_network(self) -> None:
        """
        Calculates all the points on the network that are reachable from the origin feature
        within the specified time or distance.

        This function calculates the reachable areas on a network from a given origin point
        within specified time or distance limits. It performs the following steps:

        1. Creates a memory layer with the origin point.
        2. Determines the largest travel value to construct a bounding rectangle.
        3. Clips the network layer to the bounding rectangle for efficiency.
        4. Iterates over each travel value (distance in meters or time in seconds):
           - Runs a service area analysis to find reachable network points.
           - Converts multipart geometries that the points are returned as to single parts.
           - Generates a concave hull polygon around the reachable points.
           - Adds the travel value as an attribute to the resulting polygon.
        5. Stores the resulting polygons in `self.service_areas`.
        """

        log_message(
            f"Calculating Network for feature {self.feature.id()} using {self.mode} with these values: {self.values}..."
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

        # Determine the largest value
        largest_value = max(self.values)

        # Get the geometry of the feature
        geometry = self.feature.geometry()
        if not geometry.isEmpty():
            center_point = geometry.asPoint()
        else:
            raise ValueError("Feature geometry is invalid or not a single point.")

        # Construct a QgsRectangle with the point at its center
        rect = QgsRectangle(
            center_point.x() - largest_value,
            center_point.y() - largest_value,
            center_point.x() + largest_value,
            center_point.y() + largest_value,
        )
        log_message(f"Constructed rectangle: {rect.toString()}")

        # Clip the network layer to the bounding rectangle
        clipped_layer = processing.run(
            "native:extractbyextent",
            {
                "INPUT": self.network_layer_path,
                "EXTENT": f"{rect.xMinimum()},{rect.xMaximum()},{rect.yMinimum()},{rect.yMaximum()} [EPSG:{self.crs.authid()}]",
                "CLIP": False,
                "OUTPUT": "TEMPORARY_OUTPUT",
            },
        )["OUTPUT"]

        # Iterate over each value in self.values
        for value in self.values:
            service_area_result = processing.run(
                "native:serviceareafromlayer",
                {
                    "INPUT": clipped_layer,  # Use the clipped network layer
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
                    "TRAVEL_COST2": value,
                    "INCLUDE_BOUNDS": False,
                    "POINT_TOLERANCE": None,
                    "OUTPUT_LINES": None,
                    "OUTPUT": "TEMPORARY_OUTPUT",
                },
            )

            service_area_layer = service_area_result["OUTPUT"]

            single_part_edge_points_result = processing.run(
                "native:multiparttosingleparts",
                {
                    "INPUT": service_area_layer,  # Pass output from service area step
                    "OUTPUT": "TEMPORARY_OUTPUT",
                },
            )
            del service_area_layer

            singlepart_layer = single_part_edge_points_result["OUTPUT"]
            concave_hull_result = processing.run(
                "native:concavehull",
                {
                    "INPUT": singlepart_layer,  # Pass output from multipart step
                    "ALPHA": 0.3,
                    "HOLES": False,
                    "NO_MULTIGEOMETRY": False,
                    "OUTPUT": "TEMPORARY_OUTPUT",
                },
            )
            del singlepart_layer
            # Extract features from the concave hull layer
            # Typically there will only be one feature
            concave_hull_layer = concave_hull_result["OUTPUT"]
            for feature in concave_hull_layer.getFeatures():
                # Add the travel cost value as an attribute to the feature
                # if the feature does not have a value attribute, add it
                # Get the geometry from the feature
                geometry = feature.geometry()
                # Create a new feature with the same geometry
                new_feature = QgsFeature(self.isochrone_layer.fields())
                new_feature.setGeometry(geometry)
                # Set the value attribute to the travel cost value
                # and add the feature to the writer
                new_feature.setAttribute("value", value)
                # Add the feature to the layer inside an edit session
                if not self.isochrone_layer.isEditable():
                    self.isochrone_layer.startEditing()
                self.isochrone_layer.addFeature(new_feature)
                self.isochrone_layer.commitChanges()  # leaves the layer in edit mode
                self.isochrone_layer.updateExtents()
                log_message(f"Added feature with value {value} to the GeoPackage.")
            del concave_hull_layer
        del clipped_layer
        log_message(f"Service areas calculated for feature {self.feature.id()}.")
        return

    def finished(self, result: bool) -> None:
        """
        Called when the task completes.
        """
        if result:
            log_message(
                "Native Network Analysis Processing Task calculation completed successfully. "
                "Access the service area feature using the 'service_area' attribute. "
                f"Service areas created: {len(self.service_areas)}"
            )
        else:
            log_message("Native Network Analysis Processing Task calculation failed.")
