import os
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
    QgsMessageLog,
    QgsPointXY,
    QgsProcessingContext,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QVariant
import processing
from geest.core.ors_client import ORSClient
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem, setting


class MultiBufferDistancesWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'multi_buffer_distances' workflow.

    This uses ORS (OpenRouteService) to calculate the distances between the study area
    and the selected points of interest.

    It will create concentric buffers (isochrones) around the study area and calculate
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
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param: item: Item containing workflow parameters.
        :cell_size_m: Cell size in meters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        """
        super().__init__(
            item, cell_size_m, feedback, context
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.workflow_name = "use_multi_buffer_point"
        self.distances = self.attributes.get("multi_buffer_travel_distances", None)
        if not self.distances:
            QgsMessageLog.logMessage(
                "Invalid travel distances, using default.",
                tag="Geest",
                level=Qgis.Warning,
            )
            distances = self.attributes.get("default_multi_buffer_distances", None)
            if not distances:
                QgsMessageLog.logMessage(
                    "Invalid default travel distances and no default specified.",
                    tag="Geest",
                    level=Qgis.Warning,
                )
                raise Exception("Invalid travel distances.")
        try:
            self.distances = [float(x) for x in self.distances.split(",")]
        except Exception as e:
            QgsMessageLog.logMessage(
                "Invalid travel distances provided. Distances should be a comma separated list of up to 5 numbers.",
                tag="Geest",
                level=Qgis.Warning,
            )
            raise Exception("Invalid travel distances provided.")

        layer_path = self.attributes.get("multi_buffer_shapefile", None)
        if not layer_path:
            QgsMessageLog.logMessage(
                "Invalid points layer found in multi_buffer_shapefile, trying Multi Buffer Point_layer_name.",
                tag="Geest",
                level=Qgis.Warning,
            )
            layer_path = self.attributes.get("multi_buffer_point_layer_source", None)
            if not layer_path:
                QgsMessageLog.logMessage(
                    f"No points layer found  at multi_buffer_point_layer_source {layer_path}.",
                    tag="Geest",
                    level=Qgis.Warning,
                )
                raise Exception("Invalid points layer found.")
        QgsMessageLog.logMessage(
            f"Using points layer at {layer_path}", tag="Geest", level=Qgis.Info
        )
        self.features_layer = QgsVectorLayer(layer_path, "points", "ogr")
        if not self.features_layer.isValid():
            QgsMessageLog.logMessage(
                f"Invalid points layer found in {layer_path}.",
                tag="Geest",
                level=Qgis.Warning,
            )
            raise Exception("Invalid points layer found.")

        mode = self.attributes.get("multi_buffer_travel_mode", "Walking")
        self.mode = None
        if mode == "Walking":
            self.mode = "foot-walking"
        else:
            self.mode = "driving-car"
        self.measurement = None
        measurement = self.attributes.get("multi_buffer_travel_units", "Distance")
        if measurement == "Distance":
            self.measurement = "distance"
        else:
            self.measurement = "time"

        self.subset_size = 5  # Process 5 features at a time - hardcoded for now
        self.ors_client = ORSClient("https://api.openrouteservice.org/v2/isochrones")
        self.api_key = self.ors_client.check_api_key()
        # Create the masked API key for logging
        self.masked_api_key = (
            self.api_key[:4] + "*" * (len(self.api_key) - 8) + self.api_key[-4:]
        )
        self.temp_layers = []  # Store intermediate layers
        # We can remove this next line once all workflows are refactored
        self.workflow_is_legacy = False
        QgsMessageLog.logMessage(
            f"Using ORS API key: {self.masked_api_key}", "Geest", Qgis.Info
        )
        QgsMessageLog.logMessage(
            "Multi Buffer Distances Workflow initialized", "Geest", Qgis.Info
        )

    def _process_features_for_area(
        self,
        current_area: QgsGeometry,
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
        QgsMessageLog.logMessage(
            f"Using ORS API key: {self.masked_api_key}",
            "Geest",
            Qgis.Info,
        )

        # Collect intermediate layers from ORS API
        features = list(point_layer.getFeatures())
        QgsMessageLog.logMessage(
            f"Creating buffers for {len(features)} points", "Geest", Qgis.Info
        )
        total_features = len(features)

        # Process features in subsets to handle large datasets
        for i in range(0, total_features, self.subset_size):
            subset_features = features[i : i + self.subset_size]
            subset_layer = self._create_subset_layer(subset_features, point_layer)

            # Make API calls using ORSClient for the subset
            try:
                json = self._fetch_isochrones(subset_layer)
                layer = self._create_isochrone_layer(json)
                self.temp_layers.append(layer)
                QgsMessageLog.logMessage(
                    f"Processed subset {i + 1} to {min(i + self.subset_size, total_features)} of {total_features}",
                    "Geest",
                    Qgis.Info,
                )

            except Exception as e:
                QgsMessageLog.logMessage(
                    f"Error processing subset {i + 1} to {min(i + self.subset_size, total_features)}: {e}",
                    "Geest",
                    Qgis.Critical,
                )
                continue

        # Merge all isochrone layers into one final output
        if self.temp_layers:
            QgsMessageLog.logMessage(
                f"Merging {len(self.temp_layers)} isochrone layers",
                "Geest",
                Qgis.Info,
            )
            merged_layer = self._merge_layers(self.temp_layers, index)
            QgsMessageLog.logMessage(
                f"Merged isochrone layer created at {merged_layer.source()}",
                "Geest",
                Qgis.Info,
            )
            QgsMessageLog.logMessage(
                f"Removing overlaps between isochrones for {merged_layer.source()}",
                "Geest",
                Qgis.Info,
            )
            result = self._create_bands(merged_layer, index)
            return result
        else:
            QgsMessageLog.logMessage(
                "No isochrones were created.", "Geest", Qgis.Warning
            )
            return False

    def _create_subset_layer(self, subset_features, point_layer):
        """
        Create a subset layer for processing, with reprojection of points
        from the point_layer CRS to EPSG:4326 (WGS 84).

        :param subset_features: List of QgsFeature objects to add to the subset layer.
        :param point_layer: The original point layer (QgsVectorLayer) to reproject from.
        :return: A QgsVectorLayer (subset layer) with reprojected features.
        """
        target_crs = QgsCoordinateReferenceSystem("EPSG:4326")

        # Create a new memory layer with the target CRS (EPSG:4326)
        subset_layer = QgsVectorLayer(
            f"Point?crs={target_crs.authid()}", "subset", "memory"
        )
        subset_layer_data = subset_layer.dataProvider()

        # Add attributes (fields) from the point_layer
        subset_layer_data.addAttributes(point_layer.fields())
        subset_layer.updateFields()

        # Create coordinate transformation from point_layer CRS to the target CRS (EPSG:4326)
        source_crs = point_layer.crs()
        transform_context = self.context.project().transformContext()
        transform = QgsCoordinateTransform(source_crs, target_crs, transform_context)

        # Reproject and add features to the subset layer
        reprojected_features = []
        for feature in subset_features:
            reprojected_feature = QgsFeature(feature)
            geom = reprojected_feature.geometry()

            # Transform the geometry to the target CRS
            geom.transform(transform)
            reprojected_feature.setGeometry(geom)

            reprojected_features.append(reprojected_feature)

        # Add reprojected features to the new subset layer
        subset_layer_data.addFeatures(reprojected_features)

        return subset_layer

    def _fetch_isochrones(self, layer):
        """
        Fetch isochrones for the given subset of features using ORSClient.

        :param layer: A QgsVectorLayer containing the subset of features.
        :return: A dict representing the JSON response from the ORS API.
        """
        # Prepare the coordinates for the API request
        coordinates = []
        for feature in layer.getFeatures():
            geom = feature.geometry()
            if geom and not geom.isMultipart():  # Single point geometry
                coords = geom.asPoint()
                coordinates.append([coords.x(), coords.y()])

        if not coordinates:
            raise ValueError("No valid coordinates found in the layer")

        # Prepare parameters for ORS API
        params = {
            "locations": coordinates,
            "range": self.distances,  # Distances or times in the list
            "range_type": self.measurement,
        }

        # Make the request to ORS API using ORSClient
        json = self.ors_client.make_request(self.mode, params)
        return json

    def _create_isochrone_layer(self, isochrone_data):
        """
        Create a QgsVectorLayer from the ORS isochrone data.

        :param isochrone_data: JSON data returned from ORS.
        :return: A QgsVectorLayer containing the isochrones as polygons.
        """
        isochrone_layer = QgsVectorLayer(
            "Polygon?crs=EPSG:4326", "isochrones", "memory"
        )
        provider = isochrone_layer.dataProvider()

        # Add the 'value' field to the layer's attribute table
        isochrone_layer.startEditing()
        isochrone_layer.addAttribute(QgsField("value", QVariant.Int))
        isochrone_layer.commitChanges()

        # Parse the features from ORS response
        verbose_mode = int(setting(key="verbose_mode", default=0))
        if verbose_mode:
            QgsMessageLog.logMessage(
                f"Creating isochrone layer with {len(isochrone_data['features'])} features",
                "Geest",
                Qgis.Info,
            )
        features = []
        for feature_data in isochrone_data["features"]:
            geometry = feature_data["geometry"]
            # Check if the geometry type is Polygon or MultiPolygon
            if geometry["type"] == "Polygon":
                coordinates = geometry["coordinates"]
                # Create QgsPolygon from the coordinate array
                qgs_geometry = QgsGeometry.fromPolygonXY(
                    [[QgsPointXY(pt[0], pt[1]) for pt in ring] for ring in coordinates]
                )
            elif geometry["type"] == "MultiPolygon":
                coordinates = geometry["coordinates"]
                # Create QgsMultiPolygon from the coordinate array
                qgs_geometry = QgsGeometry.fromMultiPolygonXY(
                    [
                        [[QgsPointXY(pt[0], pt[1]) for pt in ring] for ring in polygon]
                        for polygon in coordinates
                    ]
                )
            else:
                raise ValueError(f"Unsupported geometry type: {geometry['type']}")
            feat = QgsFeature()
            feat.setGeometry(qgs_geometry)
            feat.setAttributes(
                [feature_data["properties"].get("value", 0)]
            )  # Add attributes as needed
            features.append(feat)

        provider.addFeatures(features)
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
        QgsMessageLog.logMessage(
            f"Multi-buffer layer created at {output_path}",
            "Geest",
            Qgis.Info,
        )
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
        QgsMessageLog.logMessage(f"Field names: {field_names}", "Geest", Qgis.Info)
        if "value" not in field_names:
            QgsMessageLog.logMessage(
                "Adding 'value' field to input layer", "Geest", Qgis.Info
            )
            # Add the burn field to the input layer if it doesn't exist
            layer.dataProvider().addAttributes([QgsField("value", QVariant.Int)])
            layer.updateFields()

            # Log message when the field is added
            QgsMessageLog.logMessage(
                'Added "value" field to input layer',
                "Geest",
                Qgis.Info,
            )

        # Calculate the burn field value based on the item number in the distance list
        layer.startEditing()
        for i, feature in enumerate(layer.getFeatures()):
            # Get the value of the burn field from the feature
            distance_field_value = feature.attribute("distance")
            # Get the index of the burn field value from the distances list
            if distance_field_value in self.distances:
                distance_field_index = self.distances.index(distance_field_value)
                QgsMessageLog.logMessage(
                    f"Found {distance_field_value} at index {distance_field_index}",
                    "Geest",
                    Qgis.Info,
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
        QgsMessageLog.logMessage(
            f"Reprojecting input layer to {self.target_crs.authid()}",
            "Geest",
            Qgis.Info,
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

    # Remove when refactoring is done
    def do_execute(self):
        return super().do_execute()

    # Default implementation of the abstract method - not used in this workflow
    def _process_raster_for_area(
        self,
        current_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_raster: str,
        index: int,
    ):
        """
        Executes the actual workflow logic for a single area using a raster.

        :current_area: Current polygon from our study area.
        :current_bbox: Bounding box of the above area.
        :area_raster: A raster layer of features to analyse that includes only bbox pixels in the study area.
        :index: Index of the current area.

        :return: Path to the reclassified raster.
        """
        pass

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
    ):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        pass
