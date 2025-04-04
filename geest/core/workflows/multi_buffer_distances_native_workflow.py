import os
import traceback
from qgis.core import (
    edit,
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureRequest,
    QgsFeedback,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsProcessingContext,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QVariant
from qgis import processing
from geest.core.ors_client import ORSClient
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem, setting
from geest.utilities import log_message
from geest.core.algorithms import NativeNetworkAnalysisProcessor


class MultiBufferDistancesNativeWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'multi_buffer_distances' workflow.

    This uses native QGIS network analysis on a roads layer to calculate the distances
    around the selected points of interest.

    It will create concentric buffers (isochrones) around the points and calculate
    the distances to the points of interest.

    The buffers will be calcuated either using travel time or travel distance.

    The results will be stored as a collection of tif files scaled to the likert scale.

    These results will be be combined into a VRT file and added to the QGIS map.

    """

    def __init__(
        self,
        item: JsonTreeItem,
        cell_size_m: float,
        feedback: QgsFeedback,
        context: QgsProcessingContext,
        working_directory: str = None,
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param attributes: Item containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        :working_directory: Folder containing study_area.gpkg and where the outputs will be placed. If not set will be taken from QSettings.
        """
        super().__init__(
            item, cell_size_m, feedback, context, working_directory
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
            log_message(
                "Invalid travel distances provided. Distances should be a comma-separated list of up to 5 numbers.",
                tag="Geest",
                level=Qgis.Warning,
            )
            raise Exception("Invalid travel distances provided.")

        layer_path = self.attributes.get("multi_buffer_shapefile", None)
        if not layer_path:
            log_message(
                "Invalid points layer found in multi_buffer_shapefile, trying Multi Buffer Point_layer_name.",
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

        self.temp_layers = []  # Store intermediate layers
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

        # Step 2: Process these areas in batches and create buffers
        buffers = self.create_multibuffers(
            point_layer=area_features,
            index=index,
        )

        scored_buffers = self._assign_scores(buffers)

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

    def create_multibuffers(
        self,
        point_layer: QgsVectorLayer,
        index: int = 0,
    ):
        """
        Create multiple buffers (isochrones) for each point in the input point layer using ORSClient.

        This method processes the point features in subsets (to handle large datasets), makes API calls
        to the OpenRouteService to fetch the isochrones (buffers) for each subset, and merges the results
        into a final output layer.

        :param point_layer: QgsVectorLayer containing point features to process.
        :param index: Index of the current area being processed.
        :return: QgsVectorLayer containing the buffers as polygons.
        """

        # Collect intermediate layers from ORS API
        features = list(point_layer.getFeatures())
        log_message(f"Creating buffers for {len(features)} points")
        total_features = len(features)

        # Process features one at a time
        for i in range(0, total_features):
            feature = features[i]
            # Process this point using QGIS native network analysis
            layer = self._create_isochrone_layer(feature)
            if layer:
                self.temp_layers.append(layer)
            log_message(f"Processed subset {i} of {total_features}")

        # Merge all isochrone layers into one final output
        if self.temp_layers:
            log_message(
                f"Merging {len(self.temp_layers)} isochrone layers",
                tag="Geest",
                level=Qgis.Info,
            )
            merged_layer = self._merge_layers(self.temp_layers, index)
            log_message(
                f"Merged isochrone layer created at {merged_layer.source()}",
                tag="Geest",
                level=Qgis.Info,
            )
            log_message(
                f"Removing overlaps between isochrones for {merged_layer.source()}",
                tag="Geest",
                level=Qgis.Info,
            )
            result = self._create_bands(merged_layer, index)
            return result
        else:
            log_message("No isochrones were created.", level=Qgis.Warning)
            return False

    def _create_isochrone_layer(self, feature):
        """
        Run the native isochrone algorithm for the given feature.

        :param isochrone_data: JSON data returned from ORS.
        :return: A QgsVectorLayer containing the isochrones as polygons.
        """
        isochrone_layer = QgsVectorLayer(
            f"Polygon?crs=EPSG:{self.target_crs.authid}", "isochrones", "memory"
        )
        provider = isochrone_layer.dataProvider()

        # Add the 'value' field to the layer's attribute table
        isochrone_layer.startEditing()
        isochrone_layer.addAttribute(QgsField("value", QVariant.Int))
        isochrone_layer.commitChanges()

        # Parse the features from the networking analysis response
        verbose_mode = int(setting(key="verbose_mode", default=0))
        # network_layer_path (str): Path to the GeoPackage containing the network_layer_path.
        # feature: The feature to use as the origin for the network analysis.
        # crs: The coordinate reference system to use for the analysis.
        # mode: Travel time or travel distance ("time" or "distance").
        # values (List[int]): A list of time (in seconds) or distance (in meters) values to use for the analysis.
        # working_directory: The directory to save the output files.
        # force_clear: Flag to clear the output directory before running the analysis.
        processor = NativeNetworkAnalysisProcessor(
            network_layer_path=None,
            feature=feature,
            crs=self.target_crs,
            mode=self.mode,
            values=self.distances,
            working_directory=self.workflow_directory,
        )
        try:
            result = processor.run()
        except Exception as e:
            self.item.setAttribute(self.result_key, f"Task failed: {e}")

        isochrones = processor.service_areas
        if not isochrones:
            log_message(
                "No isochrones were created.",
                tag="Geest",
                level=Qgis.Warning,
            )
            return None

        provider.addFeatures(isochrones)
        return isochrone_layer

    def _merge_layers(self, layers=None, index=None):
        """
        Merge all temporary isochrone layers into a single layer.

        :param layers: List of temporary QgsVectorLayers to merge.
        :param crs: The CRS to use for the merged layer.
        :param index: The index of the current area being processed.

        :return: A QgsVectorLayer representing the merged isochrone layers.
        """
        merge_output = os.path.join(
            self.workflow_directory, f"{self.layer_id}_merged_isochrones_{index}.shp"
        )
        merge_params = {
            "LAYERS": layers,
            "CRS": self.target_crs,
            "OUTPUT": merge_output,
        }
        merged_result = processing.run("native:mergevectorlayers", merge_params)
        merge = QgsVectorLayer(merged_result["OUTPUT"], "merge", "ogr")
        return merge

    def _create_bands(self, layer, index):
        """
        Create bands by computing differences between isochrone ranges.

        This method computes the differences between isochrone ranges to create bands
        of non overlapping polygons. The bands are then merged into a final output layer.

        :param layer: The merged isochrone layer.
        :param crs: Coordinate reference system for the output.
        :param index: The index of the current area being processed.

        Returns:
            QgsVectoryLayer: The final output QgsVectorLayer layer path containing the bands.
        """
        output_path = os.path.join(
            self.workflow_directory, f"final_isochrones_{index}.shp"
        )

        ranges_field = "value"
        field_index = layer.fields().indexFromName(ranges_field)
        if field_index == -1:
            raise KeyError(
                f"Field '{ranges_field}' does not exist in the merged layer."
            )

        unique_ranges = sorted({feat[ranges_field] for feat in layer.getFeatures()})

        range_layers = {}
        for r in unique_ranges:
            expr = f'"{ranges_field}" = {r}'
            request = QgsFeatureRequest().setFilterExpression(expr)
            features = [feat for feat in layer.getFeatures(request)]
            if features:
                range_layer = QgsVectorLayer(f"Polygon", f"range_{r}", "memory")
                range_layer.setCrs(self.target_crs)
                dp = range_layer.dataProvider()
                dp.addAttributes(layer.fields())
                range_layer.updateFields()
                dp.addFeatures(features)

                dissolve_params = {
                    "INPUT": range_layer,
                    "FIELD": [],
                    "OUTPUT": "memory:",
                }
                dissolve_result = processing.run("native:dissolve", dissolve_params)
                dissolved_layer = dissolve_result["OUTPUT"]
                range_layers[r] = dissolved_layer

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

        smallest_range = sorted_ranges[-1]
        smallest_layer = range_layers[smallest_range]
        smallest_layer.dataProvider().addAttributes(
            [QgsField("distance", QVariant.Int)]
        )
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
        final_merge_result = processing.run(
            "native:mergevectorlayers", merge_bands_params
        )
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

    def reproject_isochrones(self, layer: QgsVectorLayer):
        """
        Reproject the isochrone layer to target crs.

        The resulting layer will be saved in the working directory too.

        Parameters:
            layer (QgsVectorLayer): The input isochrone layer to reproject.

        Returns:
            QgsVectorLayer: The reprojected isochrone layer.
        """

        # reproject the later to self.target_crs
        input_path = layer.source()
        reprojected_layer_path = input_path.replace(
            ".shp", f"_epsg{self.target_crs.postgisSrid()}.shp"
        )
        transform_params = {
            "INPUT": layer,
            "TARGET_CRS": self.target_crs,
            "OUTPUT": reprojected_layer_path,
        }
        log_message(
            f"Reprojecting input layer to {self.target_crs.authid()}",
            tag="Geest",
            level=Qgis.Info,
        )
        reprojected_layer_result = processing.run(
            "native:reprojectlayer", transform_params
        )
        reprojected_layer = QgsVectorLayer(
            reprojected_layer_result["OUTPUT"], "reprojected_layer", "ogr"
        )

        if not reprojected_layer.isValid():
            raise ValueError(
                f"Failed to reproject input layer to {self.target_crs.authid()}"
            )
        return reprojected_layer

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
