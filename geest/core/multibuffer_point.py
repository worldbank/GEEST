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
    QgsProcessingException,
)
from qgis.PyQt.QtCore import QVariant
import processing
import json
from geest.core.ors_client import ORSClient


class MultiBufferCreator:
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

    # TODO: refactor function
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
        # Prepare to collect intermediate layers
        temp_layers = []
        features = list(point_layer.getFeatures())
        total_features = len(features)

        # Process features in subsets to handle large datasets
        for i in range(0, total_features, self.subset_size):
            subset_features = features[i: i + self.subset_size]
            subset_layer = self._create_subset_layer(subset_features, point_layer, crs)

            # Make API calls using ORSClient for the subset
            try:
                isochrone_layer = self._fetch_isochrones(subset_layer, mode, measurement)
                if isochrone_layer:
                    temp_layers.append(isochrone_layer)

                # Log progress using QgsMessageLog
                QgsMessageLog.logMessage(
                    f"Processed subset {i + 1} to {min(i + self.subset_size, total_features)} of {total_features}",
                    "MultiBufferCreator",
                    Qgis.Info
                )

            except Exception as e:
                QgsMessageLog.logMessage(
                    f"Error processing subset {i + 1} to {min(i + self.subset_size, total_features)}: {e}",
                    "MultiBufferCreator",
                    Qgis.Critical
                )
                continue

        # Merge all isochrone layers into one
        if temp_layers:
            merged_layer = self._merge_layers(temp_layers, crs)
            self._create_bands(merged_layer, output_path, crs)
        else:
            QgsMessageLog.logMessage(
                "No isochrones were created.",
                "MultiBufferCreator",
                Qgis.Warning
            )
            
    def _create_subset_layer(self, subset_features, point_layer, crs):
        """
        Create a subset layer for processing.

        :param subset_features: List of QgsFeature objects to be processed
        :param point_layer: Original point layer
        :param crs: CRS of the subset layer
        :return: QgsVectorLayer representing the subset
        """
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
        :param crs: CRS of the layer
        :return: QgsVectorLayer containing the isochrones
        """
        # Prepare the coordinates for the API request
        coordinates = []
        for feature in subset_layer.getFeatures():
            geom = feature.geometry()
            if geom and geom.isMultipart() is False:  # Single point geometry
                coords = geom.asPoint()
                coordinates.append([coords.x(), coords.y()])

        if not coordinates:
            raise ValueError("No valid coordinates found in the layer")

        # Prepare parameters for ORS API
        params = {
            "locations": coordinates,
            "range": self.distance_list,  # Distances or times in the list
            "range_type": measurement
        }
        
        # Make the request to ORS API using ORSClient
        reply = self.ors_client.make_request(mode, params)
        reply.finished.connect(lambda: self._handle_ors_response(reply))

    def _handle_ors_response(self, reply):
        """
        Handles the response from ORS and creates a QgsVectorLayer.

        :param reply: The network reply from ORSClient
        :return: QgsVectorLayer containing the isochrones, or raises an exception on failure.
        """
        if reply.error() == reply.NoError:
            response_data = reply.readAll().data().decode()
            response_json = json.loads(response_data)
            isochrone_layer = self._create_isochrone_layer(response_json)
            return isochrone_layer
        else:
            raise QgsProcessingException(f"Error fetching isochrones: {reply.errorString()}")


    def _create_isochrone_layer(self, isochrone_data):
        """
        Creates a QgsVectorLayer from ORS isochrone data.

        :param isochrone_data: JSON data returned from ORS
        :return: QgsVectorLayer containing the isochrones
        """
        isochrone_layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "isochrones", "memory")
        provider = isochrone_layer.dataProvider()

        # Parse the features from ORS response
        features = []
        for feature_data in isochrone_data["features"]:
            geom = QgsGeometry.fromWkt(feature_data["geometry"]["coordinates"])
            feat = QgsFeature()
            feat.setGeometry(geom)
            feat.setAttributes([feature_data["properties"].get("value", 0)])  # Add attributes as needed
            features.append(feat)

        provider.addFeatures(features)
        return isochrone_layer

    def _merge_layers(self, temp_layers, crs):
        """
        Merges all temporary isochrone layers.

        :param temp_layers: List of QgsVectorLayer containing the isochrones
        :param crs: CRS of the merged layer
        :return: Merged QgsVectorLayer
        """
        merge_params = {
            "LAYERS": temp_layers,
            "CRS": QgsCoordinateReferenceSystem(crs),
            "OUTPUT": "memory:",
        }
        merged_result = processing.run("native:mergevectorlayers", merge_params)
        return merged_result["OUTPUT"]

    def _create_bands(self, merged_layer, output_path, crs):
        """
        Creates bands by differencing isochrone ranges.

        :param merged_layer: The merged isochrone layer
        :param output_path: Path to save the final output layer
        :param crs: Coordinate reference system
        """
        # Extract unique ranges from the 'value' field added by ORS
        ranges_field = "value"
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
            Qgis.Info,
        )
