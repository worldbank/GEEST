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
    QgsCoordinateTransform,
    QgsProcessingContext,
    QgsProject,
    QgsVectorLayer,
    QgsFeature,
)

from qgis.PyQt.QtCore import QVariant
import processing
from geest.core.ors_client import ORSClient
from geest.core import setting


class ORSMultiBufferProcessor:
    """
    A processor that creates multiple buffers (isochrones) around point features using the OpenRouteService (ORS) API.

    This class allows you to process point features in batches, query the ORS API for buffers (isochrones)
    based on distance or time, and merge the resulting polygons into a final output layer. It supports
    travel modes such as walking or driving, and the final buffer results are always projected in EPSG:4326.

    The buffer results (polygons) are retrieved as isochrones from ORS and merged into a final polygon layer
    stored in the specified output path.

    Note: The final polygon results are always in EPSG:4326.

    Attributes:
        distance_list (list): A list of buffer distances (in meters or seconds if using time-based buffers).
        subset_size (int): The number of features to process in each subset.
        context (QgsProcessingContext): The processing context, needed for thread safety.
        ors_client (ORSClient): The OpenRouteService client to interact with the ORS API.
        api_key (str): The API key for OpenRouteService.
        masked_api_key (str): A masked version of the API key (for logging purposes).
        temp_layers (list): Stores intermediate layers created during processing.
    """

    def __init__(
        self, distance_list, subset_size=5, context: QgsProcessingContext = None
    ):
        """
        Initialize the ORSMultiBufferProcessor.

        :param distance_list: List of buffer distances (in meters or seconds if using time-based buffers)
        :param subset_size: Number of features to process in each subset
        :param context: QgsProcessingContext object for processing - needed for thread safety
        """
        self.distance_list = distance_list
        self.subset_size = subset_size
        self.context = context
        self.ors_client = ORSClient("https://api.openrouteservice.org/v2/isochrones")
        self.api_key = self.ors_client.check_api_key()
        # Create the masked API key for logging
        self.masked_api_key = (
            self.api_key[:4] + "*" * (len(self.api_key) - 8) + self.api_key[-4:]
        )
        self.temp_layers = []  # Store intermediate layers

    def create_multibuffers(
        self,
        point_layer,
        output_path,
        mode="foot-walking",
        measurement="distance",
    ):
        """
        Create multiple buffers (isochrones) for each point in the input point layer using ORSClient.

        This method processes the point features in subsets (to handle large datasets), makes API calls
        to the OpenRouteService to fetch the isochrones (buffers) for each subset, and merges the results
        into a final output layer.

        :param point_layer: QgsVectorLayer containing point features to process.
        :param output_path: Path to save the merged output layer.
        :param mode: Mode of travel for ORS API (e.g., 'walking', 'driving-car').
        :param measurement: Either 'distance' or 'time' for the ORS isochrones.
        :return: QgsVectorLayer containing the buffers as polygons.
        """
        QgsMessageLog.logMessage(
            f"Using ORS API key: {self.masked_api_key}",
            "Geest",
            Qgis.Info,
        )
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

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
                json = self._fetch_isochrones(subset_layer, mode, measurement)
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
            crs = point_layer.crs()
            merged_layer = self._merge_layers(self.temp_layers, crs, output_dir)
            self._create_bands(merged_layer, output_path, crs)
            return True
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

    def _fetch_isochrones(self, subset_layer, mode, measurement):
        """
        Fetch isochrones for the given subset of features using ORSClient.

        :param subset_layer: A QgsVectorLayer containing the subset of features.
        :param mode: Travel mode for ORS API (e.g., 'driving-car').
        :param measurement: Either 'distance' or 'time' for ORS isochrones.
        :return: A dict representing the JSON response from the ORS API.
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
        json = self.ors_client.make_request(mode, params)
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

    def _merge_layers(self, temp_layers, crs, output_dir):
        """
        Merge all temporary isochrone layers into a single layer.

        :param temp_layers: List of temporary QgsVectorLayers to merge.
        :param crs: The CRS to use for the merged layer.
        :param output_dir: Directory to save the merged output layer.
        :return: A QgsVectorLayer representing the merged isochrone layers.
        """
        merge_output = os.path.join(output_dir, "merged_isochrones.shp")
        merge_params = {
            "LAYERS": temp_layers,
            "CRS": crs,
            "OUTPUT": merge_output,
        }
        merged_result = processing.run("native:mergevectorlayers", merge_params)
        merge = QgsVectorLayer(merged_result["OUTPUT"], "merge", "ogr")
        return merge

    def _create_bands(self, merged_layer, output_path, crs):
        """
        Create bands by computing differences between isochrone ranges.

        :param merged_layer: The merged isochrone layer.
        :param output_path: Path to save the final output layer.
        :param crs: Coordinate reference system for the output.
        """
        ranges_field = "value"
        field_index = merged_layer.fields().indexFromName(ranges_field)
        if field_index == -1:
            raise KeyError(
                f"Field '{ranges_field}' does not exist in the merged layer."
            )

        unique_ranges = sorted(
            {feat[ranges_field] for feat in merged_layer.getFeatures()}
        )

        range_layers = {}
        for r in unique_ranges:
            expr = f'"{ranges_field}" = {r}'
            request = QgsFeatureRequest().setFilterExpression(expr)
            features = [feat for feat in merged_layer.getFeatures(request)]
            if features:
                range_layer = QgsVectorLayer(
                    f"Polygon?crs={crs.authid()}", f"range_{r}", "memory"
                )
                dp = range_layer.dataProvider()
                dp.addAttributes(merged_layer.fields())
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
                [QgsField("rasField", QVariant.Int)]
            )
            diff_layer.updateFields()
            with edit(diff_layer):
                for feat in diff_layer.getFeatures():
                    feat["rasField"] = current_range
                    diff_layer.updateFeature(feat)

            band_layers.append(diff_layer)

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

        merge_bands_params = {
            "LAYERS": band_layers,
            "CRS": crs,
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
        QgsMessageLog.logMessage(f"Layer written to {output_path}", "Geest", Qgis.Info)

    def rasterize(
        input_path: str = None,
        output_path: str = None,
        burn_values: list = None,
        burn_field: str = "rasField",
        cell_size=100,
    ):
        """
        Rasterize the input vector layer based on the burn field and values.

        Args:
            input_path (str, optional): _description_. Defaults to None.
            output_path (str, optional): _description_. Defaults to None.
            burn_field (str, optional): _description_. Defaults to "rasField".
            burn_values (list, optional): _description_. Defaults to None.
            cell_size (int, optional): _description_. Defaults to 100.
        """
        QgsMessageLog.logMessage(
            f"Rasterizing {input_path} to {output_path}",
            "Geest",
            Qgis.Info,
        )
        if not input_path:
            raise ValueError("Input path is required")
        if not output_path:
            raise ValueError("Output path is required")
        if not burn_values:
            raise ValueError("Burn values are required")
        # Add a column to the input layer to store the burn values
        # The burn field should be calculated based on the item number in the distance list

        # Load the input vector layer
        input_layer = QgsVectorLayer(input_path, "input_layer", "ogr")
        if not input_layer.isValid():
            raise ValueError(f"Failed to load input layer from {input_path}")

        # Add the burn field to the input layer
        input_layer.dataProvider().addAttributes([QgsField(burn_field, QVariant.Int)])
        input_layer.updateFields()

        # Calculate the burn field value based on the item number in the distance list

        input_layer.addAttribute(QgsField("value", QVariant.Int))
        input_layer.commitChanges()
        input_layer.startEditing()
        for i, feature in enumerate(input_layer.getFeatures()):
            # Get the value of the burn field from the feature
            burn_field_value = feature.attribute(burn_field)
            # get the index of the burn field value from the distances list
            burn_values_index = burn_values.index(burn_field_value)
            # The list should have max 5 values in it. If the index is greater than 5, set it to 5
            burn_values_index = min(burn_values_index, 5)
            # Invert the value so that closer distances have higher values
            burn_values_index = 5 - burn_values_index
            feature.setAttribute("value", burn_values_index)
            input_layer.updateFeature(feature)
        input_layer.commitChanges()

        # use the processing algorithm to rasterize the vector layer

        rasterize_params = {
            "INPUT": input_path,
            "FIELD": "value",
            "BURN": 0,
            "UNITS": 1,
            "WIDTH": cell_size,
            "HEIGHT": cell_size,
            "EXTENT": None,
            "NODATA": 0,
            "OPTIONS": "",
            "DATA_TYPE": 5,
            "OUTPUT": output_path,
        }
        result = processing.run("gdal:rasterize", rasterize_params)
        return result["OUTPUT"]
