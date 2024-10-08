import os
from qgis.core import (
    QgsVectorLayer,
    QgsField,
    QgsFeatureRequest,
    QgsCoordinateReferenceSystem,
    edit,
    Qgis,
    QgsMessageLog,
    QgsGeometry,
    QgsFeature,
    QgsPointXY,
)
from qgis.PyQt.QtCore import QVariant, QEventLoop, QTimer
import processing
from geest.core.ors_client import ORSClient


class MultiBufferCreator:
    """Creates multiple buffers around point features using the OpenRouteService API."""

    def __init__(self, distance_list, subset_size=5):
        """
        Initialize the MultiBufferCreator class.

        :param distance_list: List of buffer distances (in meters or seconds if using time-based buffers)
        :param subset_size: Number of features to process in each subset
        """
        self.distance_list = distance_list
        self.subset_size = subset_size
        self.ors_client = ORSClient("https://api.openrouteservice.org/v2/isochrones")
        self.api_key = os.getenv("ORS_API_KEY")
        # Create the masked API key before using it in the f-string
        self.masked_api_key = (
            self.api_key[:4] + "*" * (len(self.api_key) - 8) + self.api_key[-4:]
        )
        self.temp_layers = []  # Store intermediate layers

        # Create an event loop to handle asynchronous responses
        self.loop = QEventLoop()

    def create_multibuffers(
        self,
        point_layer,
        output_path,
        mode="foot-walking",
        measurement="distance",
        crs="EPSG:4326",
    ):
        """
        Creates multibuffers for each point in the input point layer using ORSClient.

        :param point_layer: QgsVectorLayer containing point features
        :param output_path: Path to save the merged output layer
        :param mode: Mode of travel for ORS API (e.g., 'walking', 'driving-car')
        :param measurement: 'distance' or 'time'
        :param crs: Coordinate reference system (default is WGS84)
        :return: QgsVectorLayer containing the buffers as polygons
        """
        QgsMessageLog.logMessage(
            f"Using ORS API key: {self.masked_api_key}",
            "Geest",
            Qgis.Info,
        )
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Prepare to collect intermediate layers
        features = list(point_layer.getFeatures())
        QgsMessageLog.logMessage(
            f"Creating buffers for {len(features)} points", "Geest", Qgis.Info
        )
        total_features = len(features)

        self.ors_client.request_finished.connect(self._handle_ors_response)

        # Process features in subsets to handle large datasets
        for i in range(0, total_features, self.subset_size):
            subset_features = features[i : i + self.subset_size]
            subset_layer = self._create_subset_layer(subset_features, point_layer, crs)

            # Connect to the ORSClient's request_finished signal to handle responses

            # Make API calls using ORSClient for the subset
            try:
                self._fetch_isochrones(subset_layer, mode, measurement)
                QgsMessageLog.logMessage(
                    f"Waiting for response for subset {i + 1} to {min(i + self.subset_size, total_features)}",
                    "Geest",
                    Qgis.Info,
                )

                # Start the event loop to wait for the asynchronous response
                if not self.loop.isRunning():
                    self.loop.exec_()
                QgsMessageLog.logMessage(
                    f"Response received for subset {i + 1} to {min(i + self.subset_size, total_features)}",
                    "Geest",
                    Qgis.Info,
                )
                # Log progress using QgsMessageLog
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

        # Merge all isochrone layers into one
        if self.temp_layers:
            merged_layer = self._merge_layers(self.temp_layers, crs, output_dir)
            self._create_bands(merged_layer, output_path, crs)
        else:
            QgsMessageLog.logMessage(
                "No isochrones were created.", "Geest", Qgis.Warning
            )

    def _create_subset_layer(self, subset_features, point_layer, crs):
        """Create a subset layer for processing."""
        subset_layer = QgsVectorLayer(f"Point?crs={crs}", "subset", "memory")
        subset_layer_data = subset_layer.dataProvider()
        subset_layer_data.addAttributes(point_layer.fields())
        subset_layer.updateFields()
        subset_layer_data.addFeatures(subset_features)
        return subset_layer

    def _fetch_isochrones(self, subset_layer, mode, measurement):
        """
        Fetches isochrones for the given subset of features using ORSClient.

        :param subset_layer: QgsVectorLayer containing the subset of features
        :param mode: Travel mode for ORS API (e.g., 'driving-car')
        :param measurement: 'distance' or 'time'
        :return: None (Response will be handled asynchronously)
        """
        # Prepare the coordinates for the API request
        coordinates = []
        for feature in subset_layer.getFeatures():
            geom = feature.geometry()
            if geom and not geom.isMultipart():  # Single point geometry
                coords = geom.asPoint()
                coordinates.append([coords.x(), coords.y()])

        if not coordinates:
            raise ValueError("No valid coordinates found in the layer")

        # Prepare parameters for ORS API
        params = {
            "locations": coordinates,
            "range": self.distance_list,  # Distances or times in the list
            "range_type": measurement,
        }

        # Make the request to ORS API using ORSClient
        self.ors_client.make_request(mode, params)
        QTimer.singleShot(10000, self.loop.quit)

    def _handle_ors_response(self, response):
        """
        Handles the response from ORS API and creates a QgsVectorLayer.

        :param response: JSON response from the ORS API
        :return: None
        """
        QgsMessageLog.logMessage(
            f"Received response from ORS API: {response}", "Geest", Qgis.Info
        )
        if response:
            try:
                # Create isochrone layer from the ORS response
                isochrone_layer = self._create_isochrone_layer(response)
                QgsMessageLog.logMessage(
                    f"Isochrone layer created: {isochrone_layer}", "Geest", Qgis.Info
                )
                self.temp_layers.append(isochrone_layer)
            except Exception as e:
                QgsMessageLog.logMessage(
                    f"Error creating isochrone layer: {e}",
                    "Geest",
                    Qgis.Critical,
                )
        else:
            QgsMessageLog.logMessage(
                "No response or invalid response from ORS API.",
                "Geest",
                Qgis.Critical,
            )

        # Stop the event loop after the response is handled
        self.loop.quit()

    def _create_isochrone_layer(self, isochrone_data):
        """
        Creates a QgsVectorLayer from ORS isochrone data.

        :param isochrone_data: JSON data returned from ORS
        :return: QgsVectorLayer containing the isochrones
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

    def _merge_layers(self, temp_layers, crs, output_dir):
        """Merges all temporary isochrone layers."""
        merge_output = os.path.join(output_dir, "merged_isochrones.shp")
        merge_params = {
            "LAYERS": temp_layers,
            "CRS": QgsCoordinateReferenceSystem(crs),
            "OUTPUT": merge_output,
        }
        merged_result = processing.run("native:mergevectorlayers", merge_params)
        # return merged_result["OUTPUT"]
        merge = QgsVectorLayer(merged_result["OUTPUT"], "merge", "ogr")
        return merge

    def _create_bands(self, merged_layer, output_path, crs):
        """
        Creates bands by differencing isochrone ranges.

        :param merged_layer: The merged isochrone layer
        :param output_path: Path to save the final output layer
        :param crs: Coordinate reference system
        """
        # Extract unique ranges from the 'value' field added by ORS
        ranges_field = "value"
        # Verify that the field exists in the merged_layer
        field_index = merged_layer.fields().indexFromName(ranges_field)
        if field_index == -1:
            raise KeyError(
                f"Field '{ranges_field}' does not exist in the merged layer."
            )

        unique_ranges = sorted(
            {feat[ranges_field] for feat in merged_layer.getFeatures()}
        )

        # Create dissolved layers for each range
        range_layers = {}
        for r in unique_ranges:
            # Select features matching the current range
            expr = f'"{ranges_field}" = {r}'
            request = QgsFeatureRequest().setFilterExpression(expr)
            features = [feat for feat in merged_layer.getFeatures(request)]
            if features:
                # Create a memory layer for this range
                range_layer = QgsVectorLayer(
                    f"Polygon?crs={crs}", f"range_{r}", "memory"
                )
                dp = range_layer.dataProvider()
                dp.addAttributes(merged_layer.fields())
                range_layer.updateFields()
                dp.addFeatures(features)

                # Dissolve the range layer to create a single feature
                dissolve_params = {
                    "INPUT": range_layer,
                    "FIELD": [],
                    "OUTPUT": "memory:",
                }
                dissolve_result = processing.run("native:dissolve", dissolve_params)
                dissolved_layer = dissolve_result["OUTPUT"]
                range_layers[r] = dissolved_layer

        # Create bands by computing differences between the ranges
        band_layers = []
        sorted_ranges = sorted(range_layers.keys(), reverse=True)
        for i in range(len(sorted_ranges) - 1):
            current_range = sorted_ranges[i]
            next_range = sorted_ranges[i + 1]
            current_layer = range_layers[current_range]
            next_layer = range_layers[next_range]

            # Difference between current and next range
            difference_params = {
                "INPUT": current_layer,
                "OVERLAY": next_layer,
                "OUTPUT": "memory:",
            }
            diff_result = processing.run("native:difference", difference_params)
            diff_layer = diff_result["OUTPUT"]

            # Add 'rasField' attribute to store the range value
            diff_layer.dataProvider().addAttributes(
                [QgsField("rasField", QVariant.Int)]
            )
            diff_layer.updateFields()
            with edit(diff_layer):
                for feat in diff_layer.getFeatures():
                    feat["rasField"] = current_range
                    diff_layer.updateFeature(feat)

            band_layers.append(diff_layer)

        # Handle the smallest range separately
        smallest_range = sorted_ranges[-1]
        smallest_layer = range_layers[smallest_range]
        smallest_layer.dataProvider().addAttributes(
            [QgsField("rasField", QVariant.Int)]
        )
        smallest_layer.updateFields()
        with edit(smallest_layer):
            for feat in smallest_layer.getFeatures():
                feat["rasField"] = smallest_range
                smallest_layer.updateFeature(feat)
        band_layers.append(smallest_layer)

        # Merge all band layers into the final output
        merge_bands_params = {
            "LAYERS": band_layers,
            "CRS": QgsCoordinateReferenceSystem(crs),
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
