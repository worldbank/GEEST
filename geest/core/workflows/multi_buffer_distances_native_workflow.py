# -*- coding: utf-8 -*-
"""📦 Multi Buffer Distances Native Workflow module.

This module contains functionality for multi buffer distances native workflow.
"""
import os
from urllib.parse import unquote

from qgis import processing
from qgis.core import (
    Qgis,
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
from geest.utilities import log_message

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
            self.distances = [int(x.strip()) for x in self.distances.split(",")]
        except Exception as e:
            del e
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

        This method processes the point features using a QgsVectorLayer iterator, uses
        QGIS native routing analysis, and merges the results
        into a final output layer.

        :param point_layer: QgsVectorLayer containing point features to process.
        :param index: Index of the current area being processed.
        :return: Path to the GeoPackage.
        """
        # verbose_mode = int(setting(key="verbose_mode", default=0))

        total_features = point_layer.featureCount()
        if total_features == 0:
            log_message(f"No features to process for area {area_index}.")
            return False
        isochrone_layer_path = os.path.join(self.workflow_directory, f"isochrones_area_{area_index}.gpkg")
        log_message(f"Creating isochrones for {total_features} points")
        log_message(f"Writing isochrones to {isochrone_layer_path}")

        if os.path.exists(isochrone_layer_path):
            os.remove(isochrone_layer_path)

        # Process features using an iterator
        for i, point_feature in enumerate(point_layer.getFeatures()):
            # Process this point using QGIS native network analysis
            log_message("\n\n*************************************")
            log_message(f"Processing point {i + 1} of {total_features}")
            # Parse the features from the networking analysis response
            processor = NativeNetworkAnalysisProcessor(
                network_layer_path=self.road_network_layer_path,  # network_layer_path (str): Path to the GeoPackage containing the network_layer_path.
                isochrone_layer_path=isochrone_layer_path,  # isochrone_layer_path: Path to the output GeoPackage for the isochrones.
                point_feature=point_feature,  # feature: The feature to use as the origin for the network analysis.
                area_index=area_index,  # area_id: The ID of the area being processed.
                crs=self.target_crs,  # crs: The coordinate reference system to use for the analysis.
                mode=self.mode,  # mode: Travel time or travel distance ("time" or "distance").
                values=self.distances,  # values (List[int]): A list of time (in seconds) or distance (in meters) values to use for the analysis.
                working_directory=self.workflow_directory,  # working_directory: The directory to save the output files.
            )
            try:
                result = processor.run()
                del result
            except Exception as e:
                self.item.setAttribute(self.result_key, f"Task failed: {e}")

            log_message(f"Processed point {i + 1} of {total_features}")
            progress = ((i + 1) / total_features) * 100.0
            # Todo: feedback should show text messages rather
            # since QgsTask.setProgress already provides needded functionality
            # for progress reporting
            self.feedback.setProgress(progress)
            log_message(f"Task progress: {progress}")
            if self.feedback.isCanceled():
                log_message("Processing canceled by user.")
                return False
        return isochrone_layer_path

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
