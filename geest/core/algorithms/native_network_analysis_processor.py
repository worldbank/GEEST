import os
import traceback
from math import atan2, degrees
from typing import List, Optional

import numpy as np
from osgeo import ogr, osr
from qgis import processing
from qgis.core import (QgsCoordinateReferenceSystem, QgsFeature, QgsFeedback,
                       QgsGeometry, QgsRectangle, QgsTask, QgsVectorLayer,
                       QgsWkbTypes)
from qgis.PyQt.QtCore import QVariant

from geest.utilities import log_message


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

        output_path = self._prepare_output_path()
        self.feedback.setProgress(2)

        rect = self._construct_rectangle()
        self.feedback.setProgress(3)

        clipped_layer = self._clip_network_layer(rect, output_path)
        self.feedback.setProgress(4)

        self._process_values(clipped_layer)

        del clipped_layer
        self.feedback.setProgress(100)
        self.isochrone_ds = None
        self.isochrone_layer = None
        log_message(f"Service areas calculated for feature {self.feature.id()}.")

    def _prepare_output_path(self) -> str:
        """Prepare the output path for the clipped network layer."""
        return os.path.join(self.working_directory, f"network_{self.feature.id()}.gpkg")

    def _construct_rectangle(self) -> QgsRectangle:
        """Construct a rectangle around the feature's geometry."""
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
        return rect

    def _clip_network_layer(
        self, rect: QgsRectangle, output_path: str
    ) -> QgsVectorLayer:
        """Clip the network layer to the specified rectangle."""
        clipped_layer = processing.run(
            "native:extractbyextent",
            {
                "INPUT": self.network_layer_path,
                "EXTENT": f"{rect.xMinimum()},{rect.xMaximum()},{rect.yMinimum()},{rect.yMaximum()} [{self.crs.authid()}]",
                "CLIP": False,
                "OUTPUT": output_path,
            },
        )["OUTPUT"]
        return clipped_layer

    def _process_values(self, clipped_layer: QgsVectorLayer) -> None:
        """Process each value to calculate service areas and concave hulls."""
        interval = 80.0 / len(self.values)
        for index, value in enumerate(self.values):
            self.feedback.setProgress(int((index + 1) * interval))
            log_message(f"Processing value: {value}")

            service_area_layer = self._calculate_service_area(clipped_layer, value)
            self.feedback.setProgress(int(((index + 1) * interval) + (interval / 2)))

            self._process_service_area(service_area_layer, value)

    def _calculate_service_area(
        self, clipped_layer: QgsVectorLayer, value: int
    ) -> QgsVectorLayer:
        """Calculate the service area for a given value."""
        service_area_layer = processing.run(
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
                "START_POINT": f"{self.feature.geometry().asPoint().x()},{self.feature.geometry().asPoint().y()} [{self.crs.authid()}]",
                "TRAVEL_COST2": value,
                "POINT_TOLERANCE": 50,
                "INCLUDE_BOUNDS": False,
                "OUTPUT": "TEMPORARY_OUTPUT",
            },
        )["OUTPUT"]
        log_message("Service area layer created successfully.")
        return service_area_layer

    def _process_service_area(
        self, service_area_layer: QgsVectorLayer, value: int
    ) -> None:
        """Process the service area layer and add features to the isochrone layer."""
        if not service_area_layer.isValid():
            log_message(f"Service area layer is invalid: {service_area_layer.source()}")
            return

        service_area_features = list(service_area_layer.getFeatures())
        if service_area_features:
            service_area_feature = service_area_features[0]
            service_area_geometry = service_area_feature.geometry()

            try:
                self._add_concave_hull(service_area_geometry, value)
            except Exception as e:
                log_message(f"Failed to compute concave hull: {e}")
                log_message("Falling back to standard processing...")

    def _add_concave_hull(self, geometry: QgsGeometry, value: int) -> None:
        """Add a concave hull of the geometry to the isochrone layer."""
        ogr_geometry = ogr.CreateGeometryFromWkt(geometry.asWkt())
        concave_hull_geometry = ogr_geometry.ConcaveHull(0.3, False)

        if concave_hull_geometry:
            log_message("Concave hull computed successfully.")
            new_feature = ogr.Feature(self.isochrone_layer.GetLayerDefn())
            new_feature.SetGeometry(concave_hull_geometry)
            new_feature.SetField("value", value)
            self.isochrone_layer.CreateFeature(new_feature)
            log_message(
                f"Added concave hull feature with value {value} to the GeoPackage."
            )
