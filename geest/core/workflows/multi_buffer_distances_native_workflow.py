# -*- coding: utf-8 -*-
"""Multi-buffer distances workflow using native QGIS network analysis.

Supports grid-first mode where buffer scores are written directly to
the study_area_grid column, then rasterized.
"""

import os
from typing import Optional
from urllib.parse import unquote

from qgis import processing
from qgis.core import (
    Qgis,
    QgsFeature,
    QgsFeatureRequest,
    QgsFeedback,
    QgsField,
    QgsGeometry,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProject,
    QgsVectorLayer,
    edit,
)
from qgis.PyQt.QtCore import QVariant

from geest.core import JsonTreeItem
from geest.core.algorithms import NativeNetworkAnalysisProcessingTask
from geest.core.grid_column_utils import (
    clear_grid_column,
    rasterize_grid_column,
    write_buffer_values_to_grid,
    write_percentage_scores_to_grid,
)
from geest.core.workflows.mappings import MAPPING_REGISTRY
from geest.utilities import log_message

from .workflow_base import WorkflowBase, WorkflowNotConfiguredError


class MultiBufferDistancesNativeWorkflow(WorkflowBase):
    """Multi-buffer workflow using native QGIS network analysis.

    Creates concentric isochrones around points using road network distances.
    Results are written to grid columns and rasterized.
    """

    def __init__(
        self,
        item: JsonTreeItem,
        cell_size_m: float,
        analysis_scale: str,
        feedback: QgsFeedback,
        context: QgsProcessingContext,
        working_directory: str = None,
    ):
        """Initialize the workflow.

        Args:
            item: JsonTreeItem representing the analysis/dimension/factor.
            cell_size_m: Cell size in meters for rasterization.
            analysis_scale: Analysis scale ('local' or 'national').
            feedback: QgsFeedback for progress reporting.
            context: QgsProcessingContext for processing.
            working_directory: Folder containing study_area.gpkg.
        """
        super().__init__(item, cell_size_m, analysis_scale, feedback, context, working_directory)
        self.workflow_name = "use_multi_buffer_point"
        self.distances = self.attributes.get("multi_buffer_travel_distances", None)
        # Default scoring method (distance-based for national/local)
        self.scoring_method = ""
        self.percentage_scores = {}
        self.use_simple_buffer = False  # Use network isochrones by default
        self.buffer_distance = 0  # Single buffer distance for Regional scale
        if not self.distances:
            factor_id = None
            if item.isIndicator() and item.parentItem:
                factor_id = item.parentItem.attribute("id", None)
            mapping_id = self.attributes.get("mapping_id")
            indicator_id = self.attributes.get("id")
            mapping = MAPPING_REGISTRY.get(factor_id or mapping_id or indicator_id)
            if mapping:
                config = mapping.get(analysis_scale, mapping.get("national"))
                if config:
                    thresholds = config.get("thresholds")
                    if thresholds:
                        self.distances = thresholds
                    # Get buffer distance for regional scale (single buffer approach)
                    buffer_distance = config.get("buffer_distance")
                    if buffer_distance:
                        self.buffer_distance = buffer_distance
                    # Get scoring method and percentage scores for regional scale
                    self.scoring_method = config.get("scoring_method", "")
                    self.percentage_scores = config.get("percentage_scores", {})
                    # Flag to use simple buffer instead of network analysis
                    self.use_simple_buffer = self.scoring_method == "percentage_intersection"
        if not self.distances:
            log_message(
                "Invalid travel distances, using default.",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            self.distances = self.attributes.get("default_multi_buffer_distances", None)
            if not self.distances:
                log_message(
                    "Invalid default travel distances and no default specified.",
                    tag="GeoE3",
                    level=Qgis.Warning,
                )
                raise Exception("Invalid travel distances.")
        try:
            if isinstance(self.distances, list):
                self.distances = [int(x) for x in self.distances]
            else:
                self.distances = [int(x.strip()) for x in self.distances.split(",")]
        except Exception:
            log_message(
                "Invalid travel distances provided. Distances should be a comma-separated list of up to 5 numbers.",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            raise Exception("Invalid travel distances provided.")
        layer_path = self.attributes.get("multi_buffer_point_shapefile", None)
        if layer_path:
            layer_path = unquote(layer_path)
        if not layer_path:
            log_message(
                "Invalid points layer found in multi_buffer_point_shapefile, trying Multi Buffer Point_layer_name.",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            layer_path = self.attributes.get("multi_buffer_point_layer_source", None)
            if not layer_path:
                log_message(
                    f"No points layer found  at multi_buffer_point_layer_source {layer_path}.",
                    tag="GeoE3",
                    level=Qgis.Warning,
                )
                raise WorkflowNotConfiguredError(
                    "No point layer is set for this indicator. Open its data source settings and choose a point layer."
                )
        log_message(f"Using points layer at {layer_path}")
        self.features_layer = QgsVectorLayer(layer_path, "points", "ogr")
        if not self.features_layer.isValid():
            # OGR cannot open memory/temporary layers (e.g. from QuickOSM).
            # Fall back to finding the layer in the current QGIS project by
            # layer ID first, then by layer name.
            log_message(
                f"Could not open '{layer_path}' via OGR — trying QGIS project lookup.",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            self.features_layer = None

            # 1) Try by layer ID (most reliable within the same session)
            layer_id = self.attributes.get("multi_buffer_point_layer_id", None)
            if layer_id:
                candidate = QgsProject.instance().mapLayer(layer_id)
                if candidate and candidate.isValid():
                    self.features_layer = candidate
                    log_message(
                        f"Resolved points layer from QGIS project by ID: {layer_id}",
                        tag="GeoE3",
                        level=Qgis.Info,
                    )

            # 2) Fall back to layer name
            if self.features_layer is None:
                layer_name = self.attributes.get("multi_buffer_point_layer_name", None)
                if layer_name:
                    matches = QgsProject.instance().mapLayersByName(layer_name)
                    if matches:
                        self.features_layer = matches[0]
                        log_message(
                            f"Resolved points layer from QGIS project by name: {layer_name}",
                            tag="GeoE3",
                            level=Qgis.Info,
                        )

            if self.features_layer is None or not self.features_layer.isValid():
                log_message(
                    f"Points layer '{layer_path}' could not be loaded via OGR or found in the QGIS project. "
                    "If you used a temporary QuickOSM layer, ensure it is still loaded in QGIS.",
                    tag="GeoE3",
                    level=Qgis.Critical,
                )
                raise WorkflowNotConfiguredError(
                    "The point layer for this indicator could not be opened. If it was a temporary "
                    "layer (e.g. from QuickOSM), load it in QGIS again or re-select a saved layer in "
                    "the indicator's data source settings."
                )
        mode = self.attributes.get("multi_buffer_travel_mode", "Walking")
        self.mode = None
        if mode == "Walking":
            self.mode = "distance"
        else:  # Driving
            self.mode = "time"
        self.road_network_layer_path = self.attributes.get("road_network_layer_path", None)
        # Only require network layer for National/Local scale (Regional uses simple buffer)
        if not self.use_simple_buffer:
            log_message(f"Using network layer at {self.road_network_layer_path}")
            if not self.road_network_layer_path:
                log_message(
                    "Road network not configured. Please set the road network in the "
                    "Road Network panel before running accessibility indicators.",
                    tag="GeoE3",
                    level=Qgis.Warning,
                )
                raise Exception(
                    "Road network not configured. Please set the road network in the "
                    "Road Network panel before running accessibility indicators."
                )
        log_message("Multi Buffer Distances Native Workflow initialized")
        self.workflow_name = "multi_buffer_point"
        self.supports_empty_features_fallback = True
        # Grid-first mode: write results to grid columns first, then rasterize
        self.use_grid_first = True
        # Track if we've cleared the column (only do once, not per area)
        self._column_cleared = False
        # Road network load + CRS reprojection is expensive and area-independent
        # - cache it once instead of reopening/reprojecting the whole network
        # from scratch for every area (up to 27x for a country, times every
        # indicator in the WTP dimension).
        self._cached_road_network_layer = None
        self._road_network_load_failed = False

    def _process_features_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
        area_name: Optional[str] = None,
    ) -> str:
        """Process a single area.

        Args:
            current_area: Polygon from study area.
            clip_area: Polygon to clip features to.
            current_bbox: Bounding box.
            area_features: Features to analyze.
            index: Area number being processed.
            area_name: Name of the area being processed.

        Returns:
            Raster file path, or False if failed.
        """
        if self.use_grid_first:
            return self._process_grid_first(
                current_bbox=current_bbox,
                area_features=area_features,
                index=index,
                area_name=area_name,
            )
        else:
            return self._process_raster_first(
                current_area=current_area,
                clip_area=clip_area,
                current_bbox=current_bbox,
                area_features=area_features,
                index=index,
            )

    def _process_raster_first(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
    ) -> str:
        """Legacy raster-first processing."""
        # Check if we should use simple buffer (Regional scale) instead of network analysis
        if self.use_simple_buffer and self.buffer_distance:
            log_message(
                f"Using simple buffer for Regional scale: {self.buffer_distance}m",
                level=Qgis.Info,
            )
            return self._process_features_with_simple_buffer_legacy(
                current_area=current_area,
                clip_area=clip_area,
                current_bbox=current_bbox,
                area_features=area_features,
                index=index,
            )
        # Original network analysis approach for National/Local scale
        log_message(
            f"Starting network analysis for area {index + 1}",
            level=Qgis.Info,
        )
        isochrones_gpkg = self.create_isochrones(
            point_layer=area_features,
            area_index=index,
        )
        if not isochrones_gpkg:
            log_message(
                f"No isochrones created for area {index}.",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            return False
        bands = self._create_bands(isochrones_gpkg_path=isochrones_gpkg, index=index)
        scored_buffers = self._assign_scores(bands)
        if scored_buffers is False:
            log_message("No scored buffers were created.", level=Qgis.Warning)
            # Not an error — the area legitimately scores 0 — but the user
            # needs to know WHY (tooltip on the indicator): typically every
            # point sits further than the snapping tolerance from the road
            # network, so no service areas could be computed.
            self.attributes["warning"] = (
                "No service areas could be computed for this indicator: none of the point "
                "features are close enough to the road network (within 50 m). The area was "
                "scored 0. Check that the road network layer covers the area around the "
                "points, or use a denser network."
            )
            return False
        raster_output = self._rasterize(
            input_layer=scored_buffers,
            bbox=current_bbox,
            index=index,
            value_field="value",
        )
        return raster_output

    def _process_grid_first(
        self,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
        area_name: str,
    ) -> str:
        """Grid-first processing - writes buffer scores directly to study_area_grid."""
        # Clear column once at the start (not per area)
        if not self._column_cleared:
            log_message(f"Clearing column {self.layer_id} before processing")
            clear_grid_column(self.gpkg_path, self.layer_id)
            self._column_cleared = True
            # Keep the base class's own "has this column been cleared" flag
            # in sync: _apply_grid_column_zero_fallback() (triggered later
            # for any area with no input features, which is common and
            # unrelated to this flag) checks self._grid_column_cleared, not
            # self._column_cleared - leaving them out of sync meant that
            # fallback still issued its own clear-the-whole-column UPDATE,
            # wiping out every area already written above.
            self._grid_column_cleared = True

        self.progressChanged.emit(5.0)

        # Check if we should use simple buffer (Regional scale) instead of network analysis
        if self.use_simple_buffer and self.buffer_distance:
            log_message(
                f"Using simple buffer for Regional scale: {self.buffer_distance}m",
                level=Qgis.Info,
            )
            scored_buffers = self._create_simple_buffer_scored(area_features, index)
        else:
            # Original network analysis approach for National/Local scale
            log_message(
                f"Starting network analysis for area {index + 1}",
                level=Qgis.Info,
            )
            isochrones_gpkg = self.create_isochrones(
                point_layer=area_features,
                area_index=index,
            )
            if not isochrones_gpkg:
                log_message(
                    f"No isochrones created for area {index}.",
                    tag="GeoE3",
                    level=Qgis.Warning,
                )
                return False

            self.progressChanged.emit(40.0)

            bands = self._create_bands(isochrones_gpkg_path=isochrones_gpkg, index=index)
            scored_buffers = self._assign_scores(bands)

        if scored_buffers is False:
            log_message("No scored buffers were created.", level=Qgis.Warning)
            # Not an error — the area legitimately scores 0 — but the user
            # needs to know WHY (tooltip on the indicator): typically every
            # point sits further than the snapping tolerance from the road
            # network, so no service areas could be computed.
            self.attributes["warning"] = (
                "No service areas could be computed for this indicator: none of the point "
                "features are close enough to the road network (within 50 m). The area was "
                "scored 0. Check that the road network layer covers the area around the "
                "points, or use a denser network."
            )
            return False

        self.progressChanged.emit(50.0)

        # Write buffer scores to grid cells
        log_message(f"Writing buffer scores to grid column {self.layer_id}")
        if self.use_simple_buffer and self.buffer_distance:
            write_percentage_scores_to_grid(
                gpkg_path=self.gpkg_path,
                column_name=self.layer_id,
                buffer_layer=scored_buffers,
                percentage_scores=self.percentage_scores,
                feedback=self.feedback,
            )
        else:
            write_buffer_values_to_grid(
                gpkg_path=self.gpkg_path,
                column_name=self.layer_id,
                buffer_layer=scored_buffers,
                value_field="value",
                aggregation_method="MAX",
                feedback=self.feedback,
            )

        self.progressChanged.emit(80.0)

        # Rasterize from grid column
        output_path = os.path.join(
            self.workflow_directory,
            f"{self.layer_id}_{index}.tif",
        )

        rect = current_bbox.boundingBox()
        extent = (rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum())

        rasterize_grid_column(
            gpkg_path=self.gpkg_path,
            column_name=self.layer_id,
            output_raster_path=output_path,
            cell_size=self.cell_size_m,
            extent=extent,
            nodata=-9999.0,
            area_name=area_name,
        )

        self.progressChanged.emit(100.0)
        log_message(f"Rasterized grid column to {output_path}")
        return output_path

    def _create_simple_buffer_scored(
        self,
        area_features: QgsVectorLayer,
        index: int,
    ) -> QgsVectorLayer:
        """Create simple buffer and assign scores for Regional scale.

        Args:
            area_features: Features to buffer.
            index: Area index.

        Returns:
            Scored buffer layer with "value" field.
        """
        buffer_output = os.path.join(self.workflow_directory, f"simple_buffer_{index}.gpkg")
        if os.path.exists(buffer_output):
            os.remove(buffer_output)

        buffer_params = {
            "INPUT": area_features,
            "DISTANCE": self.buffer_distance,
            "OUTPUT": buffer_output,
        }
        result = processing.run("native:buffer", buffer_params, feedback=QgsProcessingFeedback())
        buffered_layer_path = result["OUTPUT"]

        if not buffered_layer_path or not os.path.exists(buffered_layer_path):
            log_message(
                f"Failed to create buffer for area {index}",
                level=Qgis.Warning,
            )
            return False

        buffered_layer = QgsVectorLayer(buffered_layer_path, "buffered", "ogr")
        if not buffered_layer.isValid():
            log_message(
                f"Failed to load buffered layer for area {index}",
                level=Qgis.Warning,
            )
            return False

        # Add value field (placeholder — actual scoring happens in
        # write_percentage_scores_to_grid via percentage intersection)
        field_names = [field.name() for field in buffered_layer.fields()]
        if "value" not in field_names:
            buffered_layer.dataProvider().addAttributes([QgsField("value", QVariant.Int)])
            buffered_layer.updateFields()

        return buffered_layer

    def _get_cached_road_network_layer(self, area_index: int) -> Optional[QgsVectorLayer]:
        """Load and (if needed) reproject the road network once, then reuse it.

        The network itself and its CRS don't change between areas, so
        loading the file and running a full-layer reprojection fresh for
        every area (up to 27x per indicator, times every indicator in the
        dimension) was pure waste. This loads/reprojects once on first use
        and caches the result; a failed load is also cached so later areas
        don't keep retrying a network that's already known to be broken.

        Args:
            area_index: Current area index, used only for log messages.

        Returns:
            The (possibly reprojected) road network layer, or None on failure.
        """
        if self._cached_road_network_layer is not None:
            return self._cached_road_network_layer
        if self._road_network_load_failed:
            return None

        road_network_layer = QgsVectorLayer(self.road_network_layer_path, "network", "ogr")
        if not road_network_layer.isValid():
            log_message(
                f"Road network layer could not be loaded from '{self.road_network_layer_path}'. "
                "If this was a temporary layer (e.g. from QuickOSM), it no longer exists in this session. "
                "Please reload it in QGIS or replace it with a file-based layer (GeoPackage or shapefile) "
                "in the Road Network panel.",
                tag="GeoE3",
                level=Qgis.Critical,
            )
            self._road_network_load_failed = True
            raise Exception(
                "Road network layer could not be loaded. "
                "If you used a temporary or QuickOSM layer in a previous session, it no longer exists. "
                "Please reload it in QGIS or replace it with a saved file in the Road Network panel."
            )

        road_crs = road_network_layer.crs()
        log_message(
            f"Area {area_index}: Road network CRS: {road_crs.authid()}, Target CRS: {self.target_crs.authid()}",
            level=Qgis.Info,
        )
        if road_crs != self.target_crs:
            log_message(
                f"Road network CRS mismatch detected. Auto-reprojecting from "
                f"{road_crs.authid()} to {self.target_crs.authid()} (once, cached for all areas)",
                level=Qgis.Info,
            )
            try:
                reproject_result = processing.run(
                    "native:reprojectlayer",
                    {
                        "INPUT": road_network_layer,
                        "TARGET_CRS": self.target_crs,
                        "OUTPUT": "memory:",
                    },
                    context=self.context,
                )
                road_network_layer = reproject_result["OUTPUT"]
                if not road_network_layer.isValid():
                    log_message(
                        f"ERROR: Failed to reproject road network for area {area_index}",
                        level=Qgis.Critical,
                    )
                    self._road_network_load_failed = True
                    return None
                log_message(
                    f"Successfully reprojected road network to {self.target_crs.authid()}",
                    level=Qgis.Info,
                )
            except Exception as e:
                log_message(
                    f"ERROR: Exception during road network reprojection for area {area_index}: {e}",
                    level=Qgis.Critical,
                )
                self._road_network_load_failed = True
                return None

        self._cached_road_network_layer = road_network_layer
        return road_network_layer

    def _clip_network_to_area(
        self,
        point_layer: QgsVectorLayer,
        area_index: int,
    ) -> str:
        """Clip road network to a dissolved buffer around the points being
        analysed, not the (often much larger) surrounding study-area
        polygon.

        The isochrone/service-area computation only ever needs road network
        within max(self.distances) of an actual point. Buffering the whole
        area polygon instead clips (and then routes through) network that's
        nowhere near any point whenever the points don't fill the area -
        the common case, since most areas have only a handful of points
        clustered in part of a much larger polygon.

        Args:
            point_layer: The point features being analysed for this area.
            area_index: Area index for file naming.

        Returns:
            Path to clipped network GeoPackage, or None if failed.
        """
        buffer_distance = max(self.distances) if self.distances else 5000
        point_buffers = [feature.geometry().buffer(buffer_distance, 5) for feature in point_layer.getFeatures()]
        if not point_buffers:
            log_message(
                f"No point geometries to buffer for area {area_index}.",
                level=Qgis.Warning,
            )
            return None
        buffered_geometry = QgsGeometry.unaryUnion(point_buffers)
        if buffered_geometry.isEmpty() or not buffered_geometry.isGeosValid():
            buffered_geometry = buffered_geometry.makeValid()
            if buffered_geometry.isEmpty() or not buffered_geometry.isGeosValid():
                log_message(
                    f"Dissolved point buffer for area {area_index} is invalid - cannot clip network.",
                    level=Qgis.Warning,
                )
                return None
        clipped_network_path = os.path.join(self.workflow_directory, f"clipped_network_area_{area_index}.gpkg")
        if os.path.exists(clipped_network_path):
            os.remove(clipped_network_path)
        try:
            road_network_layer = self._get_cached_road_network_layer(area_index)
            if road_network_layer is None:
                return None
            log_message(
                f"Clipping road network to area {area_index} with {buffer_distance}m buffer",
                level=Qgis.Info,
            )
            temp_layer = QgsVectorLayer(f"Polygon?crs={self.target_crs.authid()}", "clip_geometry", "memory")
            temp_provider = temp_layer.dataProvider()
            temp_feature = QgsFeature()
            temp_feature.setGeometry(buffered_geometry)
            temp_provider.addFeatures([temp_feature])
            temp_layer.updateExtents()
            # Use road_network_layer (potentially reprojected) instead of path
            result = processing.run(
                "native:clip",
                {
                    "INPUT": road_network_layer,  # Use layer object (handles reprojection)
                    "OVERLAY": temp_layer,
                    "OUTPUT": clipped_network_path,
                },
                context=self.context,
            )
            clipped_layer = result["OUTPUT"]
            if isinstance(clipped_layer, str):
                check_layer = QgsVectorLayer(clipped_layer, "check", "ogr")
                feature_count = check_layer.featureCount()
            else:
                feature_count = clipped_layer.featureCount()
            if feature_count == 0:
                log_message(
                    f"Warning: Clipped network for area {area_index} has no features. "
                    f"This area may have no roads within {buffer_distance}m.",
                    level=Qgis.Warning,
                )
                return None
            log_message(
                f"Successfully clipped network to area {area_index}: {feature_count} road segments",
                level=Qgis.Info,
            )
            return clipped_network_path
        except Exception as e:
            log_message(
                f"Error clipping network for area {area_index}: {e}",
                level=Qgis.Warning,
            )
            return None

    def create_isochrones(
        self,
        point_layer: QgsVectorLayer,
        area_index: int = 0,
    ):
        """Create isochrones using batch network analysis.

        Args:
            point_layer: Starting point features.
            area_index: Current area index.

        Returns:
            Path to GeoPackage, or False if no features.
        """
        total_features = point_layer.featureCount()
        if total_features == 0:
            log_message(f"No features to process for area {area_index}.")
            return False
        point_crs = point_layer.crs()
        log_message(
            f"Area {area_index}: Point layer CRS: {point_crs.authid()}, Target CRS: {self.target_crs.authid()}",
            level=Qgis.Info,
        )
        if point_crs != self.target_crs:
            log_message(
                f"ERROR: CRS mismatch for area {area_index}! "
                f"Point layer is in {point_crs.authid()} but expected {self.target_crs.authid()}. "
                f"This will cause incorrect distance calculations.",
                level=Qgis.Critical,
            )
            return False
        isochrone_layer_path = os.path.join(self.workflow_directory, f"isochrones_area_{area_index}.gpkg")
        clipped_network_path = self._clip_network_to_area(
            point_layer=point_layer,
            area_index=area_index,
        )
        if not clipped_network_path:
            log_message(
                f"No road network available for area {area_index}. Skipping network analysis.",
                level=Qgis.Warning,
            )
            return False
        task = NativeNetworkAnalysisProcessingTask(
            point_layer=point_layer,
            distances=self.distances,
            road_network_path=clipped_network_path,
            output_gpkg_path=isochrone_layer_path,
            target_crs=self.target_crs,
        )
        task.progressChanged.connect(lambda progress: self.feedback.setProgress(progress))
        success = task.run()
        if os.path.exists(clipped_network_path):
            try:
                os.remove(clipped_network_path)
                log_message(
                    f"Cleaned up temporary clipped network for area {area_index}",
                    level=Qgis.Info,
                )
            except Exception as e:
                log_message(
                    f"Warning: Failed to clean up clipped network {clipped_network_path}: {e}",
                    level=Qgis.Warning,
                )
        if not success:
            error_msg = task.error_message or "Unknown error"
            log_message(
                f"Network analysis task failed: {error_msg}",
                level=Qgis.Warning,
            )
            return False
        # Return the path to the created GeoPackage
        return task.result_path

    def _process_features_with_simple_buffer_legacy(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
        area_name: str = None,
    ) -> str:
        """Process a single area using simple buffer (no network analysis).

        Used for Regional scale - creates a single buffer around POIs
        and scores grid cells based on percentage intersection.

        This is the legacy raster-first version.

        Args:
            current_area: Polygon from study area.
            clip_area: Polygon to clip features to.
            current_bbox: Bounding box.
            area_features: Features to analyze.
            index: Area number being processed.

        Returns:
            Raster file path, or False if failed.
        """
        from geest.core.algorithms.utilities import subset_vector_layer

        log_message(
            f"Creating simple buffer for area {index + 1} (buffer: {self.buffer_distance}m)",
            level=Qgis.Info,
        )
        buffer_output = os.path.join(self.workflow_directory, f"simple_buffer_{index}.gpkg")
        if os.path.exists(buffer_output):
            os.remove(buffer_output)
        buffer_params = {
            "INPUT": area_features,
            "DISTANCE": self.buffer_distance,
            "OUTPUT": buffer_output,
        }
        result = processing.run("native:buffer", buffer_params, feedback=QgsProcessingFeedback())
        buffered_layer_path = result["OUTPUT"]
        if not buffered_layer_path or not os.path.exists(buffered_layer_path):
            log_message(
                f"Failed to create buffer for area {index}",
                level=Qgis.Warning,
            )
            return False
        buffered_layer = QgsVectorLayer(buffered_layer_path, "buffered", "ogr")
        if not buffered_layer.isValid():
            log_message(
                f"Failed to load buffered layer for area {index}",
                level=Qgis.Warning,
            )
            return False
        grid_output = os.path.join(self.workflow_directory, f"grid_area_{index}.gpkg")
        if os.path.exists(grid_output):
            os.remove(grid_output)
        area_grid = subset_vector_layer(
            self.workflow_directory,
            self.grid_layer,
            current_area,
            f"grid_area_{index}",
        )
        if not area_grid or not area_grid.isValid():
            log_message(
                f"Failed to get grid cells for area {index}",
                level=Qgis.Warning,
            )
            return False
        scored_grid = self._score_grid_for_percentage(
            grid_layer=area_grid,
            buffered_layer=buffered_layer,
        )
        if scored_grid is False:
            log_message(
                "No scored grid cells were created.",
                level=Qgis.Warning,
            )
            return False
        raster_output = self._rasterize(
            input_layer=scored_grid,
            bbox=current_bbox,
            index=index,
            value_field="value",
        )
        return raster_output

    def _score_grid_for_percentage(
        self,
        grid_layer: QgsVectorLayer,
        buffered_layer: QgsVectorLayer,
    ) -> QgsVectorLayer:
        """Score grid cells based on percentage intersection with buffered features.

        For Regional scale: calculates what percentage of each grid cell
        is covered by the accessibility buffer and assigns score accordingly.

        Args:
            grid_layer: The grid layer (H3 hexagons).
            buffered_layer: The buffered POI features.

        Returns:
            The grid layer with "value" field containing assigned scores.
        """
        log_message("Scoring grid cells based on percentage intersection")
        field_names = [field.name() for field in grid_layer.fields()]
        if "value" not in field_names:
            grid_layer.dataProvider().addAttributes([QgsField("value", QVariant.Int)])
            grid_layer.updateFields()

        buffer_geoms = []
        for buffered_feature in buffered_layer.getFeatures():
            geom = buffered_feature.geometry()
            if geom.isNull() or geom.isEmpty():
                continue
            if not geom.isGeosValid():
                geom = geom.makeValid()
                if geom.isEmpty():
                    continue
            buffer_geoms.append(geom)

        dissolved = QgsGeometry.unaryUnion(buffer_geoms) if buffer_geoms else QgsGeometry()
        if dissolved.isNull() or dissolved.isEmpty():
            log_message("No valid buffer geometries to dissolve", level=Qgis.Warning)
            return grid_layer
        if not dissolved.isGeosValid():
            dissolved = dissolved.makeValid()

        log_message(f"Dissolved {len(buffer_geoms)} buffers for percentage scoring")

        sorted_thresholds = sorted(self.percentage_scores.items())

        grid_layer.startEditing()
        for grid_feature in grid_layer.getFeatures():
            grid_geom = grid_feature.geometry()
            if grid_geom.isNull():
                continue
            grid_area = grid_geom.area()
            if grid_area == 0:
                continue

            intersection = grid_geom.intersection(dissolved)
            if intersection.isNull() or intersection.area() == 0:
                grid_feature.setAttribute("value", 0)
                grid_layer.updateFeature(grid_feature)
                continue

            overlap_percent = (intersection.area() / grid_area) * 100
            score = 0
            for max_pct, s in sorted_thresholds:
                if overlap_percent <= max_pct:
                    score = s
                    break
            else:
                score = sorted_thresholds[-1][1]
            grid_feature.setAttribute("value", score)
            grid_layer.updateFeature(grid_feature)
        grid_layer.commitChanges()
        return grid_layer

    def _create_bands(self, isochrones_gpkg_path, index):
        """Create bands by computing differences between isochrone ranges.

        This method computes the differences between isochrone ranges to create bands
        of non overlapping polygons. The bands are then merged into a final output layer.

        Args:
            isochrones_gpkg_path: Path to the GeoPackage containing the isochrones.
            index: Index of the current area being processed.

        Returns:
            The final output QgsVectorLayer containing the bands.

        Raises:
            ValueError: If the isochrone layer cannot be loaded.
            KeyError: If the value field does not exist in the isochrone layer.
        """
        isochrone_layer_path = f"{isochrones_gpkg_path}|layername=isochrones"
        layer = QgsVectorLayer(isochrone_layer_path, "isochrones", "ogr")
        if not layer.isValid():
            raise ValueError(f"Failed to load isochrone layer from {isochrone_layer_path}")
        output_path = os.path.join(self.workflow_directory, f"final_isochrones_{index}.shp")
        ranges_field = "value"
        field_index = layer.fields().indexFromName(ranges_field)
        if field_index == -1:
            raise KeyError(
                f"Field '{ranges_field}' does not exist in isochrones layer: {isochrone_layer_path}"  # noqa E713
            )
        unique_ranges = sorted(self.distances, reverse=False)
        range_layers = {}
        for value in unique_ranges:
            expression = f'"value" = {value}'
            request = QgsFeatureRequest().setFilterExpression(expression)
            features = [feat for feat in layer.getFeatures(request)]
            if features:
                range_layer = QgsVectorLayer("Polygon", f"range_{value}", "memory")
                range_layer.setCrs(self.target_crs)
                data_provider = range_layer.dataProvider()
                data_provider.addAttributes(layer.fields())
                range_layer.updateFields()
                data_provider.addFeatures(features)
                dissolve_params = {
                    "INPUT": range_layer,
                    "FIELD": [],
                    "OUTPUT": "memory:",
                }
                dissolve_result = processing.run("native:dissolve", dissolve_params)
                dissolved_layer = dissolve_result["OUTPUT"]
                range_layers[value] = dissolved_layer
        band_layers = []
        sorted_ranges = sorted(range_layers.keys(), reverse=True)
        for i in range(len(sorted_ranges) - 1):
            current_range = sorted_ranges[i]
            next_range = sorted_ranges[i + 1]
            current_layer = range_layers[current_range]
            next_layer = range_layers[next_range]
            difference_params = {
                "INPUT": current_layer,
                "OVERLAY": next_layer,
                "OUTPUT": "memory:",
            }
            diff_result = processing.run("native:difference", difference_params)
            diff_layer = diff_result["OUTPUT"]
            diff_layer.dataProvider().addAttributes(
                [
                    QgsField("distance", QVariant.Int),
                ]
            )
            diff_layer.updateFields()
            with edit(diff_layer):
                for feat in diff_layer.getFeatures():
                    feat["distance"] = current_range
                    diff_layer.updateFeature(feat)
            band_layers.append(diff_layer)
        try:
            smallest_range = sorted_ranges[-1]
        except IndexError:
            return None
        smallest_layer = range_layers[smallest_range]
        smallest_layer.dataProvider().addAttributes([QgsField("distance", QVariant.Int)])
        smallest_layer.updateFields()
        with edit(smallest_layer):
            for feat in smallest_layer.getFeatures():
                feat["distance"] = smallest_range
                smallest_layer.updateFeature(feat)
        band_layers.append(smallest_layer)
        merge_bands_params = {
            "LAYERS": band_layers,
            "CRS": self.target_crs,
            "OUTPUT": output_path,
        }
        final_merge_result = processing.run("native:mergevectorlayers", merge_bands_params)  # noqa F841
        final_layer = QgsVectorLayer(output_path, "MultiBuffer", "ogr")
        log_message(f"Multi-buffer layer created at {output_path}")
        return final_layer

    def _assign_scores(self, layer: QgsVectorLayer) -> QgsVectorLayer:
        """Assign values to buffered polygons based on presence of a polygon.

        Args:
            layer: The buffered features layer.

        Returns:
            The same layer with a "value" field containing the assigned scores.
        """
        if not layer or not layer.isValid():
            return False
        # Check if the "value" field already exists
        field_names = [field.name() for field in layer.fields()]
        log_message(f"Field names: {field_names}")
        if "value" not in field_names:
            log_message("Adding 'value' field to input layer")
            layer.dataProvider().addAttributes([QgsField("value", QVariant.Int)])
            layer.updateFields()
            log_message('Added "value" field to input layer')
        # Check if we should use percentage-based scoring (Regional scale)
        if self.scoring_method == "percentage_intersection" and self.percentage_scores:
            layer = self._assign_percentage_scores(layer)
        else:
            # Original distance-based scoring
            layer = self._assign_distance_scores(layer)
        return layer

    def _assign_percentage_scores(self, layer: QgsVectorLayer) -> QgsVectorLayer:
        """Assign scores based on percentage intersection with buffer.

        Note: This method is only reachable from the legacy raster-first path
        via _assign_scores(). The grid-first path uses
        write_percentage_scores_to_grid() directly. The legacy Regional path
        uses _score_grid_for_percentage() instead.

        This method operates on a single buffer layer and cannot compute
        percentage intersection without a separate grid layer. It assigns
        score 0 as a safe fallback; percentage scoring requires the
        grid-first path or _score_grid_for_percentage().

        Args:
            layer: The buffered features layer.

        Returns:
            The same layer with a "value" field set to 0.
        """
        log_message(
            "_assign_percentage_scores called on buffer layer without grid context — "
            "assigning score 0. Use grid-first path for percentage-based scoring.",
            level=Qgis.Warning,
        )
        layer.startEditing()
        for feature in layer.getFeatures():
            feature.setAttribute("value", 0)
            layer.updateFeature(feature)
        layer.commitChanges()
        return layer

    def _assign_distance_scores(self, layer: QgsVectorLayer) -> QgsVectorLayer:
        """Assign scores based on distance band (original method).

        Args:
            layer: The buffered features layer.

        Returns:
            The same layer with a "value" field containing the assigned scores.
        """
        layer.startEditing()
        for i, feature in enumerate(layer.getFeatures()):
            # Get the value of the burn field from the feature
            distance_field_value = feature.attribute("distance")
            # Get the index of the burn field value from the distances list
            if distance_field_value in self.distances:
                distance_field_index = self.distances.index(distance_field_value)
                log_message(
                    f"Found {distance_field_value} at index {distance_field_index}",
                    tag="GeoE3",
                    level=Qgis.Info,
                )
                # The list should have max 5 values in it. If the index is greater than 5, set it to 5
                distance_field_index = min(distance_field_index, 5)
                # Invert the value so that closer distances have higher values
                distance_field_index = 5 - distance_field_index
                feature.setAttribute("value", distance_field_index)
                layer.updateFeature(feature)
        layer.commitChanges()
        return layer

    # Default implementation of the abstract method - not used in this workflow
    def _process_raster_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_raster: str,
        index: int,
        area_name: str = None,
    ):
        """Execute the actual workflow logic for a single area using a raster.

        Not used in this workflow - default implementation.

        Args:
            current_area: Current polygon from our study area.
            clip_area: Polygon to clip the raster to which is aligned to cell edges.
            current_bbox: Bounding box of the above area.
            area_raster: A raster layer of features to analyse.
            index: Index of the current area.
        """
        pass

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
        area_name: str = None,
    ):
        """Execute the workflow, reporting progress and checking for cancellation.

        Args:
            current_area: Current polygon from our study area.
            clip_area: Polygon to clip to.
            current_bbox: Bounding box of the above area.
            index: Index of the current area.
        """
        pass
