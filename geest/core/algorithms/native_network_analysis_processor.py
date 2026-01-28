# -*- coding: utf-8 -*-
"""Batch network analysis using QGIS native algorithms."""

import os
from typing import List, Optional

from osgeo import ogr, osr
from qgis import processing
from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsTask,
    QgsVectorLayer,
)

from geest.utilities import log_message


class NativeNetworkAnalysisProcessingTask(QgsTask):
    """Batch network analysis task for generating isochrones.

    Processes all points simultaneously per distance value for performance.
    Outputs concave hull polygons to GeoPackage with spatial indexing.

    Attributes:
        point_layer: Starting point features.
        distances: Distance values in meters.
        road_network_path: Path to road network.
        output_gpkg_path: Output GeoPackage path.
        target_crs: Coordinate reference system.
        result_path: Created GeoPackage path (set after run).
    """

    # Network analysis configuration (hardcoded for consistency)
    POINT_TOLERANCE = 50  # Maximum distance from point to network (meters)
    NETWORK_TOLERANCE = 50  # Network topology tolerance (meters)
    STRATEGY = 0  # 0=Shortest path, 1=Fastest path
    DEFAULT_DIRECTION = 2  # 0=Forward, 1=Backward, 2=Both
    DEFAULT_SPEED = 50  # Default road speed (km/h)
    INCLUDE_BOUNDS = False  # Whether to include unreachable boundary
    CONCAVE_HULL_ALPHA = 0.3  # Alpha value for concave hull computation

    def __init__(
        self,
        point_layer: QgsVectorLayer,
        distances: List[int],
        road_network_path: str,
        output_gpkg_path: str,
        target_crs: QgsCoordinateReferenceSystem,
    ):
        """Initialize the task.

        Args:
            point_layer: Starting point features.
            distances: Distance values in meters.
            road_network_path: Path to road network.
            output_gpkg_path: Output path.
            target_crs: Coordinate reference system.
        """
        super().__init__("Native Network Analysis (Batch Isochrones)", QgsTask.CanCancel)

        if not road_network_path:
            raise ValueError("road_network_path cannot be empty")
        if not output_gpkg_path:
            raise ValueError("output_gpkg_path cannot be empty")
        if not distances:
            raise ValueError("distances list cannot be empty")

        self.point_layer = point_layer
        self.distances = distances
        self.road_network_path = road_network_path
        self.output_gpkg_path = output_gpkg_path
        self.target_crs = target_crs
        self.result_path: Optional[str] = None
        self.error_message: Optional[str] = None

        # Verify CRS compatibility
        point_crs = point_layer.crs()
        log_message(
            f"NativeNetworkAnalysisProcessingTask - Point layer CRS: {point_crs.authid()}, "
            f"Target CRS: {target_crs.authid()}",
            level=Qgis.Info,
        )

        if point_crs != target_crs:
            error_msg = (
                f"CRS mismatch in NativeNetworkAnalysisProcessingTask! "
                f"Point layer CRS ({point_crs.authid()}) does not match target CRS ({target_crs.authid()}). "
                f"This will cause incorrect distance calculations and 'point too far' errors."
            )
            log_message(error_msg, level=Qgis.Critical)
            raise ValueError(error_msg)

        log_message(
            f"Initialized NativeNetworkAnalysisProcessingTask with network: {road_network_path}",
            level=Qgis.Info,
        )

    def run(self) -> bool:
        """Execute batch isochrone generation.

        Returns:
            True if successful, False if failed/cancelled.
        """
        try:
            total_features = self.point_layer.featureCount()
            if total_features == 0:
                log_message("No point features to process.", level=Qgis.Warning)
                self.error_message = "No point features to process"
                return False

            log_message(
                f"Creating isochrones for {total_features} points using batch network analysis",
                level=Qgis.Info,
            )
            log_message(f"Writing isochrones to {self.output_gpkg_path}", level=Qgis.Info)

            # Remove existing output if present
            if os.path.exists(self.output_gpkg_path):
                os.remove(self.output_gpkg_path)

            # Initialize GeoPackage structure
            self._initialize_gpkg()

            # Process each distance value with ALL points simultaneously
            total_distances = len(self.distances)
            for distance_idx, distance_value in enumerate(self.distances):
                if self.isCanceled():
                    log_message("Task cancelled by user.", level=Qgis.Warning)
                    return False

                # Calculate base progress for this distance
                base_progress = (distance_idx / total_distances) * 100.0
                self.setProgress(base_progress)

                log_message(
                    f"\nProcessing distance {distance_idx + 1}/{total_distances}: "
                    f"{distance_value}m for {total_features} points (batch mode)",
                    level=Qgis.Info,
                )

                try:
                    service_area_result = processing.run(
                        "native:serviceareafromlayer",
                        {
                            "INPUT": self.road_network_path,
                            "START_POINTS": self.point_layer,
                            "STRATEGY": self.STRATEGY,
                            "DIRECTION_FIELD": "",
                            "VALUE_FORWARD": "",
                            "VALUE_BACKWARD": "",
                            "VALUE_BOTH": "",
                            "DEFAULT_DIRECTION": self.DEFAULT_DIRECTION,
                            "SPEED_FIELD": "",
                            "DEFAULT_SPEED": self.DEFAULT_SPEED,
                            "TOLERANCE": self.NETWORK_TOLERANCE,
                            "TRAVEL_COST2": distance_value,
                            "POINT_TOLERANCE": self.POINT_TOLERANCE,
                            "INCLUDE_BOUNDS": self.INCLUDE_BOUNDS,
                            "OUTPUT_LINES": "TEMPORARY_OUTPUT",
                        },
                    )

                    service_area_layer = service_area_result["OUTPUT_LINES"]

                    if service_area_layer.featureCount() == 0:
                        log_message(
                            f"Warning: No service areas generated for distance {distance_value}m. "
                            f"Points may be unreachable from road network (>{self.POINT_TOLERANCE}m away).",
                            level=Qgis.Warning,
                        )
                        continue

                    self._process_service_areas(service_area_layer, distance_value)

                    log_message(
                        f"Completed distance {distance_value}m: "
                        f"{service_area_layer.featureCount()} service areas processed",
                        level=Qgis.Info,
                    )

                except Exception as e:
                    log_message(
                        f"Error processing distance {distance_value}m: {e}",
                        level=Qgis.Warning,
                    )
                    continue

                progress = ((distance_idx + 1) / total_distances) * 100.0
                self.setProgress(progress)

            log_message(
                f"Batch isochrone generation complete: {self.output_gpkg_path}",
                level=Qgis.Info,
            )
            self.result_path = self.output_gpkg_path
            return True

        except Exception as e:
            log_message(
                f"Fatal error in network analysis task: {e}",
                level=Qgis.Critical,
            )
            self.error_message = str(e)
            return False

    def finished(self, result: bool) -> None:
        """Called when task completes.

        Args:
            result: True if successful, False otherwise.
        """
        if result:
            log_message(
                f"Network analysis task completed successfully: {self.result_path}",
                level=Qgis.Info,
            )
        else:
            error_msg = self.error_message or "Unknown error"
            log_message(
                f"Network analysis task failed: {error_msg}",
                level=Qgis.Critical,
            )

    def cancel(self) -> None:
        """Called when task is cancelled."""
        log_message(
            "Network analysis task cancelled",
            level=Qgis.Warning,
        )
        super().cancel()

    def _initialize_gpkg(self) -> None:
        """
        📦 Initialize GeoPackage for isochrone storage.

        Creates an empty GeoPackage with the proper schema for storing isochrone polygons.
        The layer includes a 'value' field for storing the distance value.

        Raises:
            RuntimeError: If GeoPackage creation fails.
        """
        driver = ogr.GetDriverByName("GPKG")
        ds = driver.CreateDataSource(self.output_gpkg_path)

        if ds is None:
            raise RuntimeError(f"Failed to create GeoPackage at {self.output_gpkg_path}")

        # Set up spatial reference
        srs = osr.SpatialReference()
        srs.ImportFromProj4(self.target_crs.toProj4())

        # Create polygon layer
        layer = ds.CreateLayer("isochrones", srs, ogr.wkbPolygon)

        if layer is None:
            ds = None
            raise RuntimeError(f"Failed to create layer in GeoPackage at {self.output_gpkg_path}")

        # Add value field for distance
        field_defn = ogr.FieldDefn("value", ogr.OFTReal)
        layer.CreateField(field_defn)

        # Close and flush to disk
        ds = None
        log_message(
            f"📦 Isochrone GeoPackage initialized successfully: {self.output_gpkg_path}",
            level=Qgis.Info,
        )

    def _process_service_areas(
        self,
        service_area_layer: QgsVectorLayer,
        distance_value: int,
    ) -> None:
        """
        🔄 Process service area line results and compute concave hull polygons.

        Takes the service area line geometries (roads within travel distance) and
        computes concave hull polygons around them to create isochrone boundaries.
        Results are written to the GeoPackage.

        Args:
            service_area_layer: Result layer from native:serviceareafromlayer containing
                               line geometries representing reachable road segments.
            distance_value: The distance value (meters) for this batch of service areas.

        Raises:
            RuntimeError: If GeoPackage cannot be opened for writing.
        """
        # Open GeoPackage for appending
        driver = ogr.GetDriverByName("GPKG")
        ds = driver.Open(self.output_gpkg_path, 1)  # 1 = write mode

        if ds is None:
            raise RuntimeError(f"Failed to open GeoPackage for writing: {self.output_gpkg_path}")

        isochrone_layer = ds.GetLayerByName("isochrones")

        if isochrone_layer is None:
            ds = None
            raise RuntimeError(f"Failed to access isochrones layer in {self.output_gpkg_path}")

        # Process each service area feature
        processed_count = 0
        failed_count = 0

        for feature in service_area_layer.getFeatures():
            if self.isCanceled():
                ds = None
                return

            geometry = feature.geometry()

            if geometry.isEmpty():
                continue

            try:
                # Compute concave hull using GDAL/OGR
                ogr_geometry = ogr.CreateGeometryFromWkt(geometry.asWkt())
                concave_hull_geometry = ogr_geometry.ConcaveHull(self.CONCAVE_HULL_ALPHA, False)

                if concave_hull_geometry:
                    # Create new feature in GeoPackage
                    new_feature = ogr.Feature(isochrone_layer.GetLayerDefn())
                    new_feature.SetGeometry(concave_hull_geometry)
                    new_feature.SetField("value", distance_value)
                    isochrone_layer.CreateFeature(new_feature)
                    processed_count += 1
                else:
                    failed_count += 1
                    log_message(
                        "⚠️ Warning: Failed to compute concave hull for feature",
                        level=Qgis.Warning,
                    )
            except Exception as e:
                failed_count += 1
                log_message(
                    f"⚠️ Error processing service area feature: {e}",
                    level=Qgis.Warning,
                )
                continue

        # Close and flush to disk
        ds = None

        log_message(
            f"✅ Wrote {processed_count} concave hulls for distance {distance_value}m to GeoPackage "
            f"({failed_count} failed)",
            level=Qgis.Info,
        )
