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
import numpy as np
from math import atan2, degrees


class NativeNetworkAnalysisProcessor(QgsTask):
    _instance_counter = 0  # Class variable to keep track of instances

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

        NativeNetworkAnalysisProcessor._instance_counter += 1  # Increment counter
        self.instance_id = (
            NativeNetworkAnalysisProcessor._instance_counter
        )  # Assign unique ID to instance

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

    def __del__(self):
        if hasattr(self, "isochrone_ds") and self.isochrone_ds:
            self.isochrone_ds = None
        log_message(
            f"Native Network Analysis Processor resources cleaned up instance {self.instance_id}."
        )

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
            log_message("Service area layer created successfully.")
            single_part_edge_points_result = processing.run(
                "native:multiparttosingleparts",
                {
                    "INPUT": service_area_layer,
                    "OUTPUT": "TEMPORARY_OUTPUT",
                },
            )
            del service_area_layer
            log_message("Converted multipart to singlepart successfully.")

            singlepart_layer = single_part_edge_points_result["OUTPUT"]
            # Show how many features in the singlepart layer
            log_message(
                f"Singlepart layer has {singlepart_layer.featureCount()} features."
            )

            # Compute the concave hull using grass
            # for some reason, grass output (lower case) is a path not a qgsvectorlayer obnect
            concave_hull_result_path = processing.run(
                "grass:v.hull",
                {
                    "input": singlepart_layer,
                    "where": "",
                    "-f": False,
                    "output": "TEMPORARY_OUTPUT",
                    "GRASS_REGION_PARAMETER": None,
                    "GRASS_SNAP_TOLERANCE_PARAMETER": -1,
                    "GRASS_MIN_AREA_PARAMETER": 0.0001,
                    "GRASS_OUTPUT_TYPE_PARAMETER": 0,
                    "GRASS_VECTOR_DSCO": "",
                    "GRASS_VECTOR_LCO": "",
                    "GRASS_VECTOR_EXPORT_NOCAT": False,
                },
            )["output"]
            # Load the output as a QgsVetorLayer
            concave_hull_result_layer = QgsVectorLayer(
                concave_hull_result_path, "concave_hull", "ogr"
            )
            if not concave_hull_result_layer.isValid():
                raise ValueError(
                    f"Concave hull result layer is invalid: {concave_hull_result_path}"
                )
            log_message("Concave hull created successfully.")

            # Crashes QGIS randomly

            # concave_hull_result = processing.run(
            #     "qgis:minimumboundinggeometry",
            #     {
            #         "INPUT": singlepart_layer,
            #         "FIELD": "",
            #         "TYPE": 3, # concave hull polygon
            #         "OUTPUT": "TEMPORARY_OUTPUT",
            #     },
            # )

            # Also crashes QGIS randomly

            # concave_hull_result = processing.run(
            #     "native:concavehull",
            #     {
            #         "INPUT": singlepart_layer,
            #         "ALPHA": 0.3,
            #         "HOLES": False,
            #         "NO_MULTIGEOMETRY": False,
            #         "OUTPUT": "TEMPORARY_OUTPUT",
            #     },
            # )

            del singlepart_layer
            # Show how many features in the concave hull layer
            log_message(
                f"Concave hull layer has {concave_hull_result_layer.featureCount()} features."
            )
            for feature in concave_hull_result_layer.getFeatures():
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
                log_message(
                    f"Isochrone layer has {self.isochrone_layer.GetFeatureCount()} features."
                )
            del concave_hull_result_layer

        del clipped_layer
        del point_layer
        log_message(f"Service areas calculated for feature {self.feature.id()}.")
        return

    def _calculate_angle(self, p1, p2):
        """Calculate the angle between two points."""
        return degrees(atan2(p2[1] - p1[1], p2[0] - p1[0]))

    def _distance(self, p1, p2):
        """Calculate the Euclidean distance between two points."""
        return np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    def _find_concave_hull(self, points, k):
        """Compute the concave hull of a set of points in a single iteration."""
        if len(points) < 3:
            raise ValueError("At least 3 points are required to compute a hull.")
        if k < 3:
            raise ValueError("k must be at least 3.")

        points = np.array(points)
        hull = []

        # Find the starting point (lowest y, then lowest x)
        start = points[np.lexsort((points[:, 0], points[:, 1]))][0]
        hull.append(start.tolist())
        current_point = start
        points = points.tolist()
        points.remove(start.tolist())

        prev_angle = 0
        while True:
            # Sort points by angle and distance
            sorted_points = sorted(
                points,
                key=lambda p: (
                    (self._calculate_angle(current_point, p) - prev_angle) % 360,
                    self._distance(current_point, p),
                ),
            )

            # Iterate through sorted points to find the next valid point
            for next_point in sorted_points:
                if len(hull) > 2:
                    # Check for intersections with the existing hull
                    if self._creates_intersection(hull, current_point, next_point):
                        continue

                hull.append(next_point)
                points.remove(next_point)
                current_point = next_point
                prev_angle = self._calculate_angle(hull[-2], hull[-1])

                # Close the hull if we return to the starting point
                if len(hull) > 3 and hull[-1] == hull[0]:
                    return hull[:-1]
                break
            else:
                # If no valid next point is found, terminate
                break

        return hull

    def _creates_intersection(self, hull, current_point, next_point):
        """Check if adding the next point creates an intersection in the hull."""
        new_segment = (current_point, next_point)
        for i in range(len(hull) - 1):
            existing_segment = (hull[i], hull[i + 1])
            if self._segments_intersect(new_segment, existing_segment):
                return True
        return False

    def _segments_intersect(self, seg1, seg2):
        """Check if two line segments intersect."""

        def ccw(a, b, c):
            return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])

        a, b = seg1
        c, d = seg2
        return ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d)

    def finished(self, result: bool) -> None:
        if result:
            log_message(
                "Native Network Analysis Processing Task calculation completed successfully."
            )
        else:
            log_message("Native Network Analysis Processing Task calculation failed.")
