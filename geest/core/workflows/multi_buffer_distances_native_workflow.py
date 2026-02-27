# -*- coding: utf-8 -*-
"""Multi-buffer distances workflow using native QGIS network analysis."""
import os
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
    QgsVectorLayer,
    edit,
)
from qgis.PyQt.QtCore import QVariant

from geest.core import JsonTreeItem
from geest.core.algorithms import NativeNetworkAnalysisProcessingTask
from geest.core.workflows.mappings import MAPPING_REGISTRY
from geest.utilities import log_message

from .workflow_base import WorkflowBase


class MultiBufferDistancesNativeWorkflow(WorkflowBase):
    """Multi-buffer workflow using native QGIS network analysis.

    Creates concentric isochrones around points using road network distances.
    Results are rasterized and combined into a VRT.
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
                tag="Geest",
                level=Qgis.Warning,
            )
            self.distances = self.attributes.get("default_multi_buffer_distances", None)
            if not self.distances:
                log_message(
                    "Invalid default travel distances and no default specified.",
                    tag="Geest",
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
                tag="Geest",
                level=Qgis.Warning,
            )
            raise Exception("Invalid travel distances provided.")

        layer_path = self.attributes.get("multi_buffer_point_shapefile", None)
        if layer_path:
            layer_path = unquote(layer_path)
        if not layer_path:
            log_message(
                "Invalid points layer found in multi_buffer_point_shapefile, trying Multi Buffer Point_layer_name.",
                tag="Geest",
                level=Qgis.Warning,
            )
            layer_path = self.attributes.get("multi_buffer_point_layer_source", None)
            if not layer_path:
                log_message(
                    f"No points layer found  at multi_buffer_point_layer_source {layer_path}.",
                    tag="Geest",
                    level=Qgis.Warning,
                )
                raise Exception("Invalid points layer found.")
        log_message(f"Using points layer at {layer_path}")
        self.features_layer = QgsVectorLayer(layer_path, "points", "ogr")
        if not self.features_layer.isValid():
            log_message(
                f"Invalid points layer found in {layer_path}.",
                tag="Geest",
                level=Qgis.Warning,
            )
            raise Exception("Invalid points layer found.")

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
                    f"Invalid network layer found in {self.road_network_layer_path}.",
                    tag="Geest",
                    level=Qgis.Warning,
                )
                raise Exception("Invalid network layer found.")
        log_message("Multi Buffer Distances Native Workflow initialized")

    def _process_features_for_area(
        self,
        current_area: "QgsGeometry",
        clip_area: "QgsGeometry",
        current_bbox: "QgsGeometry",
        area_features: "QgsVectorLayer",
        index: int,
    ) -> str:
        """Process a single area.

        Args:
            current_area: Polygon from study area.
            clip_area: Polygon to clip features to.
            current_bbox: Bounding box.
            area_features: Features to analyze.
            index: Area number being processed.

        Returns:
            Raster file path, or False if failed.
        """
        # Check if we should use simple buffer (Regional scale) instead of network analysis
        if self.use_simple_buffer and self.buffer_distance:
            log_message(
                f"Using simple buffer for Regional scale: {self.buffer_distance}m",
                level=Qgis.Info,
            )
            return self._process_features_with_simple_buffer(
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
            clip_geometry=current_area,
            area_index=index,
        )
        if not isochrones_gpkg:
            log_message(
                f"No isochrones created for area {index}.",
                tag="Geest",
                level=Qgis.Warning,
            )
            return False

        bands = self._create_bands(isochrones_gpkg_path=isochrones_gpkg, index=index)
        scored_buffers = self._assign_scores(bands)

        if scored_buffers is False:
            log_message("No scored buffers were created.", level=Qgis.Warning)
            return False

        raster_output = self._rasterize(
            input_layer=scored_buffers,
            bbox=current_bbox,
            index=index,
            value_field="value",
        )

        return raster_output

    def _clip_network_to_area(
        self,
        clip_geometry: QgsGeometry,
        area_index: int,
    ) -> str:
        """Clip road network to area with buffer for spatial isolation.

        Args:
            clip_geometry: Area geometry to clip to.
            area_index: Area index for file naming.

        Returns:
            Path to clipped network GeoPackage, or None if failed.
        """
        buffer_distance = max(self.distances) if self.distances else 5000
        buffered_geometry = clip_geometry.buffer(buffer_distance, 5)
        bbox = buffered_geometry.boundingBox()

        clipped_network_path = os.path.join(self.workflow_directory, f"clipped_network_area_{area_index}.gpkg")

        if os.path.exists(clipped_network_path):
            os.remove(clipped_network_path)

        try:
            road_network_layer = QgsVectorLayer(self.road_network_layer_path, "network", "ogr")
            if not road_network_layer.isValid():
                log_message(
                    f"ERROR: Cannot load road network from {self.road_network_layer_path}",
                    level=Qgis.Critical,
                )
                return None

            road_crs = road_network_layer.crs()
            log_message(
                f"Area {area_index}: Road network CRS: {road_crs.authid()}, Target CRS: {self.target_crs.authid()}",
                level=Qgis.Info,
            )

            # Auto-reproject road network if CRS mismatch detected
            if road_crs != self.target_crs:
                log_message(
                    f"Road network CRS mismatch detected. Auto-reprojecting from "
                    f"{road_crs.authid()} to {self.target_crs.authid()}",
                    level=Qgis.Info,
                )

                # Reproject to target CRS in memory (consistent with check_and_reproject_layer behavior)
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
        clip_geometry: QgsGeometry,
        area_index: int = 0,
    ):
        """Create isochrones using batch network analysis.

        Args:
            point_layer: Starting point features.
            clip_geometry: Geometry to clip network to.
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
            clip_geometry=clip_geometry,
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

    def _process_features_with_simple_buffer(
        self,
        current_area: "QgsGeometry",
        clip_area: "QgsGeometry",
        current_bbox: "QgsGeometry",
        area_features: "QgsVectorLayer",
        index: int,
    ) -> str:
        """Process a single area using simple buffer (no network analysis).

        Used for Regional scale - creates a single buffer around POIs
        and scores grid cells based on percentage intersection.

        Args:
            current_area: Polygon from study area.
            clip_area: Polygon to clip features to.
            current_bbox: Bounding box.
            area_features: Features to analyze.
            index: Area number being processed.

        Returns:
            Raster file path, or False if failed.
        """
        from qgis import processing
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
        grid_layer: "QgsVectorLayer",
        buffered_layer: "QgsVectorLayer",
    ) -> "QgsVectorLayer":
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

        grid_layer.startEditing()
        for grid_feature in grid_layer.getFeatures():
            grid_geom = grid_feature.geometry()
            if grid_geom.isNull():
                continue

            grid_area = grid_geom.area()
            if grid_area == 0:
                continue

            max_score = 0
            max_overlap_percent = 0

            for buffered_feature in buffered_layer.getFeatures():
                buffered_geom = buffered_feature.geometry()
                if buffered_geom.isNull():
                    continue

                intersection = grid_geom.intersection(buffered_geom)
                if intersection.isNull() or intersection.area() == 0:
                    continue

                # Calculate % of buffer within hexagon (not % of hexagon covered)
                buffer_area = buffered_geom.area()
                if buffer_area > 0:
                    overlap_percent = (intersection.area() / buffer_area) * 100
                else:
                    overlap_percent = 0

                if overlap_percent > max_overlap_percent:
                    max_overlap_percent = overlap_percent

            # Calculate score based on final max_overlap_percent after all buffers checked
            # Table ranges: Score 0: 0%, Score 1: 0.01-6%, Score 2: 6.01-12%, etc.
            sorted_items = sorted(self.percentage_scores.items())
            log_message(
                f"DEBUG: Feature {grid_feature.id()} - max_overlap: {max_overlap_percent:.4f}%, thresholds: {sorted_items}",
                level=Qgis.Info,
            )
            max_score = 0
            for i, (min_pct, score) in enumerate(sorted_items):
                if score == 0:
                    if max_overlap_percent == 0:
                        max_score = 0
                        log_message(
                            f"DEBUG: Feature {grid_feature.id()} - Score 0 (overlap=0%)",
                            level=Qgis.Info,
                        )
                elif i == len(sorted_items) - 1:
                    # Last score: prev_pct < overlap (e.g., 24 < x <= 100, but use >= for float precision)
                    prev_pct = sorted_items[i - 1][0]
                    in_range = prev_pct < max_overlap_percent
                    log_message(
                        f"DEBUG: Feature {grid_feature.id()} - Checking Score {score}: {prev_pct} < {max_overlap_percent:.4f} = {in_range}",
                        level=Qgis.Info,
                    )
                    if in_range:
                        max_score = score
                else:
                    # Middle scores: prev_pct < overlap <= min_pct
                    prev_pct = sorted_items[i - 1][0]
                    in_range = prev_pct < max_overlap_percent <= min_pct
                    log_message(
                        f"DEBUG: Feature {grid_feature.id()} - Checking Score {score}: {prev_pct} < {max_overlap_percent:.4f} <= {min_pct} = {in_range}",
                        level=Qgis.Info,
                    )
                    if in_range:
                        max_score = score

            log_message(
                f"DEBUG: Feature {grid_feature.id()} - FINAL: max_overlap={max_overlap_percent:.4f}%, assigned_score={max_score}",
                level=Qgis.Info,
            )

            grid_feature.setAttribute("value", max_score)
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

    def _assign_percentage_scores(self, layer: "QgsVectorLayer") -> "QgsVectorLayer":
        """Assign scores based on percentage intersection with buffer.

        For Regional scale: calculates what percentage of each grid cell
        is covered by the accessibility buffer and assigns score accordingly.

        Args:
            layer: The buffered features layer.

        Returns:
            The same layer with a "value" field containing the assigned scores.
        """
        log_message("Using percentage-based scoring for Regional scale")

        buffer_distance = 0
        if hasattr(self, "buffer_distances") and self.buffer_distances:
            buffer_distance = (
                max(self.buffer_distances) if isinstance(self.buffer_distances, list) else self.buffer_distances
            )
        elif self.distances:
            buffer_distance = max(self.distances) if isinstance(self.distances, list) else self.distances

        log_message(f"Buffer distance for percentage scoring: {buffer_distance}m")

        layer.startEditing()
        for feature in layer.getFeatures():
            grid_geom = feature.geometry()
            if grid_geom.isNull():
                continue

            grid_area = grid_geom.area()

            buffer_geom = feature.geometry()
            if buffer_geom.isNull():
                continue

            intersection = grid_geom.intersection(buffer_geom)
            if intersection.isNull() or intersection.area() == 0:
                feature.setAttribute("value", 0)
            else:
                overlap_percent = (intersection.area() / grid_area) * 100

                score = 0
                for min_pct, score_value in sorted(self.percentage_scores.items(), reverse=True):
                    if overlap_percent >= min_pct:
                        score = score_value
                        break

                feature.setAttribute("value", score)
                log_message(
                    f"Grid cell overlap: {overlap_percent:.2f}%, score: {score}",
                    tag="Geest",
                    level=Qgis.Info,
                )

            layer.updateFeature(feature)

        layer.commitChanges()
        return layer

    def _assign_distance_scores(self, layer: "QgsVectorLayer") -> "QgsVectorLayer":
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
                    tag="Geest",
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
    ):
        """Execute the workflow, reporting progress and checking for cancellation.

        Args:
            current_area: Current polygon from our study area.
            clip_area: Polygon to clip to.
            current_bbox: Bounding box of the above area.
            index: Index of the current area.
        """
        pass
