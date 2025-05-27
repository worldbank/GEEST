from osgeo import ogr, osr
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
    QgsFeedback,
)
from qgis.PyQt.QtCore import QVariant
from qgis import processing
from geest.utilities import log_message
import numpy as np
from math import atan2, degrees


class NativeNetworkAnalysisProcessor(QgsTask):
    _instance_counter = 0  # Class variable to keep track of instances

    def __init__(
        self,
        network_layer_path: str,
        isochrone_layer_path: str,
        area_index: int,
        point_feature: QgsFeature,
        crs: QgsCoordinateReferenceSystem,
        mode: str,
        values: List[int],
        working_directory: str,
    ):
        super().__init__("Native Network Analysis Processor", QgsTask.CanCancel)
        self.feedback = QgsFeedback()
        NativeNetworkAnalysisProcessor._instance_counter += 1  # Increment counter
        self.instance_id = (
            NativeNetworkAnalysisProcessor._instance_counter
        )  # Assign unique ID to instance
        self.area_index = area_index
        self.working_directory = working_directory
        os.makedirs(self.working_directory, exist_ok=True)
        self.crs = crs

        self.network_layer_path = network_layer_path
        network_layer = QgsVectorLayer(self.network_layer_path, "network_layer", "ogr")
        if not network_layer.isValid():
            raise ValueError(f"Network layer is invalid: {self.network_layer_path}")
        if network_layer.geometryType() != QgsWkbTypes.LineGeometry:
            raise ValueError("Network layer must be a line layer.")
        if network_layer.crs() != self.crs:
            raise ValueError(
                f"Network layer CRS {network_layer.crs().authid()} does not match the specified CRS {self.crs.authid()}."
            )

        self.feature = point_feature
        self.mode = mode
        if self.mode not in ["time", "distance"]:
            raise ValueError("Invalid mode. Must be 'time' or 'distance'.")
        self.values = values
        if not all(isinstance(value, int) and value > 0 for value in self.values):
            raise ValueError(f"All values must be positive integers. {self.values}")
        self.isochrone_layer = None
        self.isochrone_layer_path = isochrone_layer_path
        self._initialize_isochrone_layer()

        log_message(
            f"Initialized Native Network Analysis Processing Task Instance: {self.instance_id}."
        )

    def _initialize_isochrone_layer(self):
        driver = ogr.GetDriverByName("GPKG")
        if os.path.exists(self.isochrone_layer_path):
            log_message(
                f"Appending to existing GeoPackage: {self.isochrone_layer_path}"
            )
            self.isochrone_ds = driver.Open(self.isochrone_layer_path, 1)
            self.isochrone_layer = self.isochrone_ds.GetLayerByName("isochrones")
        else:
            self.isochrone_ds = driver.CreateDataSource(self.isochrone_layer_path)
            srs = osr.SpatialReference()
            srs.ImportFromProj4(self.crs.toProj4())
            self.isochrone_layer = self.isochrone_ds.CreateLayer(
                "isochrones", srs, ogr.wkbPolygon
            )
            field_defn = ogr.FieldDefn("value", ogr.OFTReal)
            self.isochrone_layer.CreateField(field_defn)
            log_message("Isochrone layer created successfully!")

    def isochrone_feature_count(self) -> int:
        if self.isochrone_layer is None:
            raise ValueError("Isochrone layer is not initialized.")
        if not self.isochrone_layer:
            raise ValueError("Isochrone layer is invalid.")
        # Check if the layer is valid
        return self.isochrone_layer.GetFeatureCount()

    def __del__(self):
        if hasattr(self, "isochrone_ds") and self.isochrone_ds:
            self.isochrone_ds = None
        log_message(
            f"Native Network Analysis Processor resources cleaned up instance {self.instance_id}."
        )

    def run(self) -> str:
        try:
            self.calculate_network()
            return True
        except Exception as e:
            log_message(f"Task failed: {e}")
            log_message(traceback.format_exc())
            return False

    def calculate_network(self) -> None:
        self.feedback.setProgress(1)
        log_message(
            f"Calculating Network for feature {self.feature.id()} using {self.mode} with these values: {self.values}..."
        )
        output_path = os.path.join(
            self.working_directory, f"network_{self.feature.id()}.gpkg"
        )
        self.feedback.setProgress(2)
        # point_layer = QgsVectorLayer(
        #     f"Point?crs=EPSG:{self.crs.authid()}&field=id:integer",
        #     "start_point",
        #     "memory",
        # )
        # provider = point_layer.dataProvider()
        # provider.addFeature(self.feature)
        # point_layer.updateExtents()

        largest_value = max(self.values)
        geometry = self.feature.geometry()
        if not geometry.isEmpty():
            center_point = geometry.asPoint()
        else:
            raise ValueError("Feature geometry is invalid or not a single point.")

        rect = QgsRectangle(
            center_point.x() - largest_value,
            center_point.y() - largest_value,
            center_point.x() + largest_value,
            center_point.y() + largest_value,
        )
        log_message(f"Constructed rectangle: {rect.toString()}")
        self.feedback.setProgress(3)
        clipped_layer = processing.run(
            "native:extractbyextent",
            {
                "INPUT": self.network_layer_path,
                "EXTENT": f"{rect.xMinimum()},{rect.xMaximum()},{rect.yMinimum()},{rect.yMaximum()} [{self.crs.authid()}]",
                "CLIP": False,
                "OUTPUT": output_path,
            },
        )["OUTPUT"]
        self.feedback.setProgress(4)
        interval = 80.0 / len(self.values)
        # hack for https://github.com/worldbank/GEEST/issues/54
        # See below for logic
        first_run = True
        for index, value in enumerate(self.values):
            self.feedback.setProgress(int((index + 1) * interval))
            log_message(f"Processing value: {value}")
            # Hack end
            service_area_vector_layer = processing.run(
                "native:serviceareafrompoint",
                {
                    "INPUT": clipped_layer,
                    "STRATEGY": 0,
                    "DIRECTION_FIELD": "",
                    "VALUE_FORWARD": "",
                    "VALUE_BACKWARD": "",
                    "VALUE_BOTH": "",
                    "DEFAULT_DIRECTION": 2,
                    "SPEED_FIELD": "",
                    "DEFAULT_SPEED": 50,
                    "TOLERANCE": 50,
                    "START_POINT": f"{center_point.x()},{center_point.y()} [{self.crs.authid()}]",
                    "TRAVEL_COST2": value,
                    "POINT_TOLERANCE": 50,  # Maximum distance a point can be from the network
                    "INCLUDE_BOUNDS": False,
                    "OUTPUT": "TEMPORARY_OUTPUT",
                },
            )["OUTPUT"]

            self.feedback.setProgress(int(((index + 1) * interval) + (interval / 2)))
            log_message("Service area layer created successfully.")
            # Try to compute the concave hull directly using the GEOS API
            if not service_area_vector_layer.isValid():
                log_message(
                    f"Service area layer is invalid: {service_area_vector_layer.source()}"
                )
            else:
                log_message(
                    f"Service area feature count (1 is expected): f{service_area_vector_layer.featureCount()}"
                )
                service_area_features = list(service_area_vector_layer.getFeatures())
                if service_area_features:
                    service_area_feature = service_area_features[0]
                    service_area_geometry = service_area_feature.geometry()
                    # Get number of parts in the geometry
                    parts_count = 1  # Default for single geometries
                    if service_area_geometry.isMultipart():
                        parts_count = service_area_geometry.constGet().numGeometries()

                    log_message(
                        f"Service area geometry type: {service_area_geometry.wkbType()}"
                    )
                    log_message(f"Service area geometry has {parts_count} parts")

                    # Convert QGIS geometry to OGR geometry
                    ogr_geometry = ogr.CreateGeometryFromWkt(
                        service_area_geometry.asWkt()
                    )

                    try:
                        # Calculate the concave hull with a ratio of 0.3 and no holes
                        concave_hull_geometry = ogr_geometry.ConcaveHull(0.3, False)

                        if concave_hull_geometry:
                            log_message(
                                "Concave hull computed successfully using GEOS API."
                            )

                            # Add the concave hull directly to the isochrone layer
                            new_feature = ogr.Feature(
                                self.isochrone_layer.GetLayerDefn()
                            )
                            new_feature.SetGeometry(concave_hull_geometry)
                            new_feature.SetField("value", value)
                            self.isochrone_layer.CreateFeature(new_feature)
                            new_feature = None

                            log_message(
                                f"Added concave hull feature with value {value} to the GeoPackage."
                            )
                            log_message(
                                f"Isochrone layer has {self.isochrone_layer.GetFeatureCount()} features."
                            )
                            continue  # Skip the rest of the processing for this value
                    except Exception as e:
                        log_message(
                            f"Failed to compute concave hull using GEOS API: {e}"
                        )
                        log_message("Falling back to standard processing...")
            # Show how many features in the concave hull layer
            log_message(
                f"Concave hull layer has {hull_result_layer.featureCount()} features."
            )
            self.progress.setProgress(90)
            for feature in hull_result_layer.getFeatures():
                geometry = feature.geometry()
                ogr_geometry = ogr.CreateGeometryFromWkt(geometry.asWkt())
                new_feature = ogr.Feature(self.isochrone_layer.GetLayerDefn())
                new_feature.SetGeometry(ogr_geometry)
                new_feature.SetField("value", value)
                self.isochrone_layer.CreateFeature(new_feature)
                new_feature = None
                log_message(
                    f"Added feature with value **{value}** to the GeoPackage.\n\n"
                )
                # show how many features in the isochrone layer
                # This might be slow!
                log_message(
                    f"Isochrone layer has {self.isochrone_layer.GetFeatureCount()} features."
                )

            del hull_result_layer

        del clipped_layer
        # del point_layer
        self.feedback.setProgress(100)
        self.isochrone_ds = None
        self.isochrone_layer = None
        log_message(f"Service areas calculated for feature {self.feature.id()}.")
        return
