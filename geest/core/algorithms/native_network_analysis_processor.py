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
from functools import lru_cache

# Import the Timer module
from geest.core.timer import Timer, timed


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

        with Timer("🔍 initialize_network_layer"):
            self.network_layer_path = network_layer_path
            network_layer = QgsVectorLayer(
                self.network_layer_path, "network_layer", "ogr"
            )
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

        with Timer("🧩 initialize_isochrone_layer"):
            self._initialize_isochrone_layer()

        log_message(
            f"✅ Initialized Native Network Analysis Processing Task Instance: {self.instance_id}."
        )

    def _initialize_isochrone_layer(self):
        """Initialize or open the isochrone output layer."""
        driver = ogr.GetDriverByName("GPKG")
        if os.path.exists(self.isochrone_layer_path):
            with Timer("📂 open_existing_gpkg"):
                log_message(
                    f"Appending to existing GeoPackage: {self.isochrone_layer_path}"
                )
                self.isochrone_ds = driver.Open(self.isochrone_layer_path, 1)
                self.isochrone_layer = self.isochrone_ds.GetLayerByName("isochrones")
        else:
            with Timer("🆕 create_new_gpkg"):
                self.isochrone_ds = driver.CreateDataSource(self.isochrone_layer_path)
                srs = osr.SpatialReference()
                srs.ImportFromProj4(self.crs.toProj4())
                self.isochrone_layer = self.isochrone_ds.CreateLayer(
                    "isochrones", srs, ogr.wkbPolygon
                )
                field_defn = ogr.FieldDefn("value", ogr.OFTReal)
                self.isochrone_layer.CreateField(field_defn)
                log_message("🆕 Isochrone layer created successfully!")

    @lru_cache(maxsize=128)
    def isochrone_feature_count(self) -> int:
        """Return the number of features in the isochrone layer."""
        if self.isochrone_layer is None:
            raise ValueError("Isochrone layer is not initialized.")
        if not self.isochrone_layer:
            raise ValueError("Isochrone layer is invalid.")
        # Check if the layer is valid
        return self.isochrone_layer.GetFeatureCount()

    def __del__(self):
        """Cleanup resources when object is destroyed."""
        if hasattr(self, "isochrone_ds") and self.isochrone_ds:
            self.isochrone_ds = None
        log_message(
            f"🧹 Native Network Analysis Processor resources cleaned up instance {self.instance_id}."
        )

    @timed
    def run(self) -> str:
        """Main task runner method."""
        try:
            with Timer("🚀 network_calculation"):
                self.calculate_network()
            return True
        except Exception as e:
            log_message(f"❌ Task failed: {e}")
            log_message(traceback.format_exc())
            return False

    @timed
    def calculate_network(self) -> None:
        """Main method to calculate network analysis."""
        self.feedback.setProgress(1)
        log_message(
            f"🧮 Calculating Network for feature {self.feature.id()} using {self.mode} with these values: {self.values}..."
        )

        # Prepare geometry and extent
        with Timer("📐 geometry_preparation"):
            center_point, rect = self._prepare_geometry()

        # Clip network by extent
        with Timer("✂️ network_clipping"):
            clipped_layer = self._clip_network(rect)

        # Process each value to create isochrones
        with Timer("🚗 isochrone_processing"):
            self._process_isochrones(center_point, clipped_layer)

        # Cleanup
        with Timer("🧹 resource_cleanup"):
            self._cleanup_resources(clipped_layer)

        # Print performance summary at the end
        Timer.print_summary()
        return

    @timed
    def _prepare_geometry(self):
        """Prepare geometry and calculate clipping extent."""
        largest_value = max(self.values)

        with Timer("📍 extract_point"):
            geometry = self.feature.geometry()
            if not geometry.isEmpty():
                center_point = geometry.asPoint()
            else:
                raise ValueError("Feature geometry is invalid or not a single point.")

        with Timer("🔲 create_extent"):
            rect = QgsRectangle(
                center_point.x() - largest_value,
                center_point.y() - largest_value,
                center_point.x() + largest_value,
                center_point.y() + largest_value,
            )
            log_message(f"📏 Constructed rectangle: {rect.toString()}")
            self.feedback.setProgress(3)

        return center_point, rect

    @timed
    def _clip_network(self, rect):
        """Clip network by extent."""
        output_path = os.path.join(
            self.working_directory, f"network_{self.feature.id()}.gpkg"
        )

        with Timer("🔪 extract_by_extent"):
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

        return clipped_layer

    @timed
    def _process_isochrones(self, center_point, clipped_layer):
        """Process isochrones for all values."""
        interval = 80.0 / len(self.values)
        first_run = True

        for index, value in enumerate(self.values):
            with Timer(f"🔄 process_value_{value}"):
                self.feedback.setProgress(int((index + 1) * interval))
                log_message(f"⏱️ Processing value: {value}")

                # Calculate service area
                service_area_layer = self._calculate_service_area(
                    center_point, clipped_layer, value
                )

                # Create concave hull and add to output
                self._create_concave_hull(service_area_layer, value)

                self.feedback.setProgress(
                    int(((index + 1) * interval) + (interval / 2))
                )

    @timed
    def _calculate_service_area(self, center_point, clipped_layer, value):
        """Calculate service area for a specific value."""
        with Timer(f"🚗 service_area_{value}"):
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
                    "TOLERANCE": 0,
                    "START_POINT": f"{center_point.x()},{center_point.y()} [{self.crs.authid()}]",
                    "TRAVEL_COST2": value,
                    "POINT_TOLERANCE": 50,
                    "INCLUDE_BOUNDS": False,
                    "OUTPUT": "TEMPORARY_OUTPUT",
                },
            )["OUTPUT"]

        log_message("✅ Service area layer created successfully.")

        # Check if layer is valid
        with Timer("🔍 validate_service_area"):
            if not service_area_vector_layer.isValid():
                log_message(
                    f"⚠️ Service area layer is invalid: {service_area_vector_layer.source()}"
                )
            else:
                log_message(
                    f"ℹ️ Service area feature count (1 is expected): {service_area_vector_layer.featureCount()}"
                )

        return service_area_vector_layer

    @timed
    def _create_concave_hull(self, service_area_layer, value):
        """Create concave hull from service area and add to output."""
        with Timer(f"🔷 concave_hull_{value}"):
            service_area_features = list(service_area_layer.getFeatures())

            if not service_area_features:
                log_message("⚠️ No service area features found.")
                return

            with Timer("🔍 extract_geometry"):
                service_area_feature = service_area_features[0]
                service_area_geometry = service_area_feature.geometry()

                # Get number of parts in the geometry
                parts_count = 1  # Default for single geometries
                if service_area_geometry.isMultipart():
                    parts_count = service_area_geometry.constGet().numGeometries()

                log_message(
                    f"ℹ️ Service area geometry type: {service_area_geometry.wkbType()}"
                )
                log_message(f"ℹ️ Service area geometry has {parts_count} parts")

                # Convert QGIS geometry to OGR geometry
                ogr_geometry = ogr.CreateGeometryFromWkt(service_area_geometry.asWkt())

            try:
                # Calculate the concave hull
                with Timer(f"🔶 direct_concave_hull_{value}"):
                    concave_hull_geometry = ogr_geometry.ConcaveHull(0.3, False)

                if concave_hull_geometry:
                    log_message("✅ Concave hull computed successfully using GEOS API.")

                    # Add to output
                    with Timer(f"💾 save_direct_hull_{value}"):
                        new_feature = ogr.Feature(self.isochrone_layer.GetLayerDefn())
                        new_feature.SetGeometry(concave_hull_geometry)
                        new_feature.SetField("value", value)
                        self.isochrone_layer.CreateFeature(new_feature)
                        new_feature = None

                    log_message(
                        f"✅ Added concave hull feature with value {value} to the GeoPackage."
                    )
                    log_message(
                        f"ℹ️ Isochrone layer has {self.isochrone_layer.GetFeatureCount()} features."
                    )
                    return
            except Exception as e:
                log_message(f"⚠️ Failed to compute concave hull using GEOS API: {e}")
                log_message("⚠️ Falling back to standard processing...")

            # Fallback processing
            with Timer(f"🔄 fallback_processing_{value}"):
                # Run the concave hull algorithm from QGIS processing
                hull_params = {
                    "INPUT": service_area_layer,
                    "ALPHA": 0.3,
                    "HOLES": False,
                    "NO_MULTIGEOMETRY": True,
                    "OUTPUT": "TEMPORARY_OUTPUT",
                }

                try:
                    with Timer("🔄 run_concave_hull"):
                        hull_result = processing.run("native:concavehull", hull_params)
                        hull_result_layer = hull_result["OUTPUT"]

                    # Show how many features in the concave hull layer
                    log_message(
                        f"ℹ️ Concave hull layer has {hull_result_layer.featureCount()} features."
                    )

                    with Timer("💾 save_fallback_hull"):
                        for feature in hull_result_layer.getFeatures():
                            geometry = feature.geometry()
                            ogr_geometry = ogr.CreateGeometryFromWkt(geometry.asWkt())
                            new_feature = ogr.Feature(
                                self.isochrone_layer.GetLayerDefn()
                            )
                            new_feature.SetGeometry(ogr_geometry)
                            new_feature.SetField("value", value)
                            self.isochrone_layer.CreateFeature(new_feature)
                            new_feature = None
                            log_message(
                                f"✅ Added feature with value {value} to the GeoPackage."
                            )

                    # Show how many features in the isochrone layer
                    log_message(
                        f"ℹ️ Isochrone layer has {self.isochrone_layer.GetFeatureCount()} features."
                    )

                    with Timer("🗑️ cleanup_temp_layer"):
                        del hull_result_layer

                except Exception as e:
                    log_message(f"❌ Fallback concave hull processing failed: {e}")

    @timed
    def _cleanup_resources(self, clipped_layer):
        """Clean up resources."""
        with Timer("🧹 delete_clipped_layer"):
            del clipped_layer
            self.feedback.setProgress(100)

        # Only close these resources if we're explicitly cleaning up
        # The __del__ method will handle final cleanup
        log_message(f"✅ Service areas calculated for feature {self.feature.id()}.")
