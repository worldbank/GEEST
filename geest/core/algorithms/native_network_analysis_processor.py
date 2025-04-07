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
)
from qgis.PyQt.QtCore import QVariant
from qgis import processing
from geest.utilities import log_message


class NativeNetworkAnalysisProcessor(QgsTask):
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
        self.service_areas = []

        self.isochrone_layer_path = os.path.join(
            self.working_directory, "isochrones.gpkg"
        )
        self._initialize_isochrone_layer()

        log_message("Initialized Native Network Analysis Processing Task")

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

    def __del__(self):
        if hasattr(self, "isochrone_ds") and self.isochrone_ds:
            self.isochrone_ds = None
        log_message("Native Network Analysis Processor resources cleaned up.")

    def run(self) -> bool:
        try:
            self.calculate_network()
            return True
        except Exception as e:
            log_message(f"Task failed: {e}")
            log_message(traceback.format_exc())
            return False

    def calculate_network(self) -> None:
        log_message(
            f"Calculating Network for feature {self.feature.id()} using {self.mode} with these values: {self.values}..."
        )
        output_path = os.path.join(
            self.working_directory, f"network_{self.feature.id()}.gpkg"
        )
        point_layer = QgsVectorLayer(
            f"Point?crs=EPSG:{self.crs.authid()}&field=id:integer",
            "start_point",
            "memory",
        )
        provider = point_layer.dataProvider()
        provider.addFeature(self.feature)
        point_layer.updateExtents()

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

        clipped_layer = processing.run(
            "native:extractbyextent",
            {
                "INPUT": self.network_layer_path,
                "EXTENT": f"{rect.xMinimum()},{rect.xMaximum()},{rect.yMinimum()},{rect.yMaximum()} [{self.crs.authid()}]",
                "CLIP": False,
                "OUTPUT": "TEMPORARY_OUTPUT",
            },
        )["OUTPUT"]

        for value in self.values:
            service_area_result = processing.run(
                "native:serviceareafromlayer",
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
                    "TOLERANCE": 0,
                    "START_POINTS": point_layer,
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
                    "INPUT": service_area_layer,
                    "OUTPUT": "TEMPORARY_OUTPUT",
                },
            )
            del service_area_layer

            singlepart_layer = single_part_edge_points_result["OUTPUT"]
            concave_hull_result = processing.run(
                "native:concavehull",
                {
                    "INPUT": singlepart_layer,
                    "ALPHA": 0.3,
                    "HOLES": False,
                    "NO_MULTIGEOMETRY": False,
                    "OUTPUT": "TEMPORARY_OUTPUT",
                },
            )
            del singlepart_layer

            concave_hull_layer = concave_hull_result["OUTPUT"]
            for feature in concave_hull_layer.getFeatures():
                geometry = feature.geometry()
                ogr_geometry = ogr.CreateGeometryFromWkt(geometry.asWkt())
                new_feature = ogr.Feature(self.isochrone_layer.GetLayerDefn())
                new_feature.SetGeometry(ogr_geometry)
                new_feature.SetField("value", value)
                self.isochrone_layer.CreateFeature(new_feature)
                new_feature = None
                log_message(f"Added feature with value {value} to the GeoPackage.")
            del concave_hull_layer
        del clipped_layer
        log_message(f"Service areas calculated for feature {self.feature.id()}.")
        return

    def finished(self, result: bool) -> None:
        if result:
            log_message(
                "Native Network Analysis Processing Task calculation completed successfully."
            )
        else:
            log_message("Native Network Analysis Processing Task calculation failed.")
