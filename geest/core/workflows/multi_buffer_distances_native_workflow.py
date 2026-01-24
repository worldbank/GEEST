# -*- coding: utf-8 -*-
"""📦 Multi Buffer Distances Native Workflow module.

This module contains functionality for multi buffer distances native workflow.

Performance optimizations:
- Parallel processing of point features using QgsTaskManager
- Each point writes to its own temporary GeoPackage to avoid lock contention
- Results are merged after all parallel tasks complete
"""

import os
from typing import List
from urllib.parse import unquote

from osgeo import ogr
from qgis import processing
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsFeatureRequest,
    QgsFeedback,
    QgsField,
    QgsGeometry,
    QgsProcessingContext,
    QgsVectorLayer,
    edit,
)
from qgis.PyQt.QtCore import QVariant

from geest.core import JsonTreeItem
from geest.core.algorithms import NativeNetworkAnalysisProcessor
from geest.core.workflows.mappings import MAPPING_REGISTRY
from geest.utilities import log_message, setting

from .workflow_base import WorkflowBase


class MultiBufferDistancesNativeWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'multi_buffer_distances' workflow.

    This uses native QGIS network analysis on a roads layer to calculate the distances
    around the selected points of interest.

    It will create concentric buffers (isochrones) around the points and calculate
    the distances to the points of interest.

    The isochrones will be calcuated either using travel time or travel distance.

    The results will be stored as a collection of tif files scaled to the likert scale.

    These results will be be combined into a VRT file and added to the QGIS map.

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
        """
        Initialize the workflow with attributes and feedback.
        :param item: JsonTreeItem representing the analysis, dimension, or factor to process.
        :param cell_size_m: Cell size in meters for rasterization.
        :param analysis_scale: Scale of the analysis, e.g., 'local', 'national',
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :param context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        :param working_directory: Folder containing study_area.gpkg and where the outputs will be placed. If not set will be taken from QSettings.
        """
        super().__init__(
            item, cell_size_m, analysis_scale, feedback, context, working_directory
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.workflow_name = "use_multi_buffer_point"
        self.distances = self.attributes.get("multi_buffer_travel_distances", None)
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
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
    ) -> str:
        """
        Executes the actual workflow logic for a single area.
        Must be implemented by subclasses.

        :current_area: Current polygon from our study area.
        :current_bbox: Bounding box of the above area.
        :area_features: A vector layer of features to analyse that includes only features in the study area.
        :index: Iteration / number of area being processed.

        :return: A raster layer file path if processing completes successfully, False if canceled or failed.
        """

        # Step 1: Process these areas in batches and create buffers
        isochrones_gpkg = self.create_isochrones(
            point_layer=area_features,
            area_index=index,
        )
        # A return of false does not neccessarily indicate an error -
        # there may be no coincident points in a given area in which case
        # we just skip it
        if not isochrones_gpkg:
            log_message(
                f"No isochrones created for area {index}.",
                tag="Geest",
                level=Qgis.Warning,
            )
            return False
        # Step 2: Merge all isochrone layers into one final output, removing any overlaps
        bands = self._create_bands(isochrones_gpkg_path=isochrones_gpkg, index=index)

        # Step 3: Assign scores to the buffers based on the distances
        scored_buffers = self._assign_scores(bands)

        if scored_buffers is False:
            log_message("No scored buffers were created.", level=Qgis.Warning)
            return False
        # Step 4: Rasterize the scored buffers
        raster_output = self._rasterize(
            input_layer=scored_buffers,
            bbox=current_bbox,
            index=index,
            value_field="value",
        )

        return raster_output

    def create_isochrones(
        self,
        point_layer: QgsVectorLayer,
        area_index: int = 0,
    ):
        """
        Create multiple buffers (isochrones) for each point in the input point layer using network analysis.

        This method processes the point features using parallel QgsTask execution,
        then merges the results into a final output layer.

        Performance optimization: Uses QgsTaskManager for parallel point processing.
        Each point writes to its own temporary GeoPackage to avoid lock contention,
        then results are merged at the end.

        :param point_layer: QgsVectorLayer containing point features to process.
        :param area_index: Index of the current area being processed.
        :return: Path to the GeoPackage.
        """
        total_features = point_layer.featureCount()
        if total_features == 0:
            log_message(f"No features to process for area {area_index}.")
            return False

        isochrone_layer_path = os.path.join(self.workflow_directory, f"isochrones_area_{area_index}.gpkg")
        log_message(f"Creating isochrones for {total_features} points")
        log_message(f"Writing isochrones to {isochrone_layer_path}")

        if os.path.exists(isochrone_layer_path):
            os.remove(isochrone_layer_path)

        # Determine parallelization strategy
        parallel_mode = int(setting(key="parallel_network_analysis", default=1))
        max_parallel_tasks = int(setting(key="max_parallel_tasks", default=4))

        if parallel_mode and total_features > 1:
            return self._create_isochrones_parallel(
                point_layer, area_index, isochrone_layer_path, total_features, max_parallel_tasks
            )
        else:
            return self._create_isochrones_sequential(point_layer, area_index, isochrone_layer_path, total_features)

    def _create_isochrones_sequential(
        self, point_layer: QgsVectorLayer, area_index: int, isochrone_layer_path: str, total_features: int
    ):
        """
        Sequential processing of points (original implementation).

        Used when parallel processing is disabled or for small feature counts.
        """
        log_message("Using sequential processing for network analysis")

        for i, point_feature in enumerate(point_layer.getFeatures()):
            log_message(f"Processing point {i + 1} of {total_features}")
            processor = NativeNetworkAnalysisProcessor(
                network_layer_path=self.road_network_layer_path,
                isochrone_layer_path=isochrone_layer_path,
                point_feature=point_feature,
                area_index=area_index,
                crs=self.target_crs,
                mode=self.mode,
                values=self.distances,
                working_directory=self.workflow_directory,
            )
            try:
                processor.run()
            except Exception as e:
                log_message(f"Task failed for point {i}: {e}", level=Qgis.Warning)
                self.item.setAttribute(self.result_key, f"Task failed: {e}")

            progress = ((i + 1) / total_features) * 100.0
            self.feedback.setProgress(progress)

            if self.feedback.isCanceled():
                log_message("Processing canceled by user.")
                return False

        return isochrone_layer_path

    def _create_isochrones_parallel(
        self,
        point_layer: QgsVectorLayer,
        area_index: int,
        final_output_path: str,
        total_features: int,
        max_parallel: int,
    ):
        """
        Parallel processing of points using QgsTaskManager.

        Each point writes to its own temporary GeoPackage, then all results
        are merged into the final output to avoid concurrent write issues.
        """
        log_message(f"Using parallel processing for network analysis (max {max_parallel} concurrent tasks)")

        # Create temporary output paths for each point
        temp_outputs: List[str] = []
        tasks: List[NativeNetworkAnalysisProcessor] = []
        completed_count = [0]  # Use list to allow modification in nested function

        # Collect all features first (needed for parallel processing)
        features = list(point_layer.getFeatures())

        def on_task_completed(task_index: int):
            """Callback when a task completes."""
            completed_count[0] += 1
            progress = (completed_count[0] / total_features) * 100.0
            self.feedback.setProgress(progress)
            log_message(f"Completed {completed_count[0]}/{total_features} network analysis tasks")

        # Create tasks for all features (but don't start them all at once)
        for i, point_feature in enumerate(features):
            # Each point gets its own temp output to avoid lock contention
            temp_output = os.path.join(self.workflow_directory, f"isochrones_temp_{area_index}_{i}.gpkg")
            temp_outputs.append(temp_output)

            if os.path.exists(temp_output):
                os.remove(temp_output)

            processor = NativeNetworkAnalysisProcessor(
                network_layer_path=self.road_network_layer_path,
                isochrone_layer_path=temp_output,
                point_feature=point_feature,
                area_index=area_index,
                crs=self.target_crs,
                mode=self.mode,
                values=self.distances,
                working_directory=self.workflow_directory,
            )
            tasks.append(processor)

        # Process in batches to control parallelism
        task_manager = QgsApplication.taskManager()

        for batch_start in range(0, len(tasks), max_parallel):
            batch_end = min(batch_start + max_parallel, len(tasks))
            batch_tasks = tasks[batch_start:batch_end]

            log_message(f"Starting batch {batch_start // max_parallel + 1}: tasks {batch_start + 1}-{batch_end}")

            # Add batch tasks to task manager
            for task in batch_tasks:
                task_manager.addTask(task)

            # Wait for batch to complete
            for task in batch_tasks:
                task.waitForFinished()
                on_task_completed(0)

            if self.feedback.isCanceled():
                log_message("Processing canceled by user.")
                return False

        # Merge all temporary outputs into final output
        log_message("Merging parallel results into final output...")
        self._merge_isochrone_outputs(temp_outputs, final_output_path)

        # Cleanup temporary files
        for temp_path in temp_outputs:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except OSError:
                pass  # Ignore cleanup errors

        return final_output_path

    def _merge_isochrone_outputs(self, temp_outputs: List[str], final_output_path: str):
        """
        Merge multiple temporary isochrone GeoPackages into a single output.

        Uses OGR for efficient direct file operations.
        """
        driver = ogr.GetDriverByName("GPKG")

        # Create the final output
        if os.path.exists(final_output_path):
            os.remove(final_output_path)

        final_ds = driver.CreateDataSource(final_output_path)
        final_layer = None
        feature_count = 0

        for temp_path in temp_outputs:
            if not os.path.exists(temp_path):
                continue

            temp_ds = ogr.Open(temp_path, 0)
            if temp_ds is None:
                continue

            temp_layer = temp_ds.GetLayerByName("isochrones")
            if temp_layer is None:
                temp_ds = None
                continue

            # Create final layer on first valid temp layer
            if final_layer is None:
                srs = temp_layer.GetSpatialRef()
                final_layer = final_ds.CreateLayer("isochrones", srs, ogr.wkbPolygon)
                # Copy field definitions
                layer_defn = temp_layer.GetLayerDefn()
                for i in range(layer_defn.GetFieldCount()):
                    field_defn = layer_defn.GetFieldDefn(i)
                    final_layer.CreateField(field_defn)

            # Copy features
            for feature in temp_layer:
                new_feature = ogr.Feature(final_layer.GetLayerDefn())
                new_feature.SetGeometry(feature.GetGeometryRef().Clone())
                for i in range(feature.GetFieldCount()):
                    new_feature.SetField(i, feature.GetField(i))
                final_layer.CreateFeature(new_feature)
                feature_count += 1

            temp_ds = None

        final_ds = None
        log_message(f"Merged {feature_count} isochrone features into {final_output_path}")

    def _create_bands(self, isochrones_gpkg_path, index):
        """
        Create bands by computing differences between isochrone ranges.

        This method computes the differences between isochrone ranges to create bands
        of non overlapping polygons. The bands are then merged into a final output layer.

        :param isochrones_gpkg_path: Path to the GeoPackage containing the isochrones.

        Returns:
            QgsVectoryLayer: The final output QgsVectorLayer layer path containing the bands.
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
        """
        Assign values to buffered polygons based 5 for presence of a polygon.

        Args:
            layer QgsVectorLayer: The buffered features layer.

        Returns:
            QgsVectorLayer: The same layer with a "value" field containing the assigned scores.
        """
        if not layer or not layer.isValid():
            return False

        # Check if the "value" field already exists
        field_names = [field.name() for field in layer.fields()]
        log_message(f"Field names: {field_names}")
        if "value" not in field_names:
            log_message("Adding 'value' field to input layer")
            # Add the burn field to the input layer if it doesn't exist
            layer.dataProvider().addAttributes([QgsField("value", QVariant.Int)])
            layer.updateFields()

            # Log message when the field is added
            log_message('Added "value" field to input layer')

        # Calculate the burn field value based on the item number in the distance list
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
        """
        Executes the actual workflow logic for a single area using a raster.

        :current_area: Current polygon from our study area.
        :clip_area: Polygon to clip the raster to which is aligned to cell edges.
        :current_bbox: Bounding box of the above area.
        :area_raster: A raster layer of features to analyse that includes only bbox pixels in the study area.
        :index: Index of the current area.

        :return: Path to the reclassified raster.
        """
        pass

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
    ):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        pass
