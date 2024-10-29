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
    QgsVectorLayer,
    QgsFeature,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsVectorFileWriter,
    QgsWkbTypes,
    QgsVectorLayer,
    QgsRasterLayer,
)

from qgis.PyQt.QtCore import QVariant
import processing
from geest.core.ors_client import ORSClient
from geest.core import setting
from geest.core.algorithms import AreaIterator


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
        points_layer (QgsVectorLayer): A point layer containing features to generate isochrones for.
        output_prefix (str): Prefix for naming output files.
        workflow_directory (str): Directory where temporary and output files will be stored.
        gpkg_path (str): Path to the GeoPackage containing study areas and bounding boxes.
        context (QgsProcessingContext): QgsProcessingContext object for processing - needed for thread safety.
        subset_size (int): Number of features to process in each subset (default: 5).
        ors_client (ORSClient): An instance of the ORSClient for making API requests.
        api_key (str): The API key used for ORS API requests.
        masked_api_key (str): The masked API key for logging purposes.
        temp_layers (list): List of intermediate layers created during processing.
        target_crs (QgsCoordinateReferenceSystem): The target CRS for the final output layer (EPSG:4326).
    """

    def __init__(
        self,
        distance_list: list,
        points_layer: QgsVectorLayer,
        output_prefix: str,
        workflow_directory: str,
        gpkg_path: str,
        context: QgsProcessingContext,
    ):
        """
        Initialize the ORSMultiBufferProcessor.

        :param distance_list (list): List of buffer distances (in meters or seconds if using time-based buffers)
        :param output_prefix (str): Prefix for naming output files.
        :param points_layer (QgsVectorLayer): A point layer containing features to generate isochrones for.
        :param csv_path (str): The input ORS event CSV file path.
        :param workflow_directory (str): Directory where temporary and output files will be stored.
        :param gpkg_path (str): Path to the GeoPackage containing study areas and bounding boxes.
        :param context: QgsProcessingContext object for processing - needed for thread safety
        """

        self.distance_list = distance_list
        self.subset_size = 5  # Process 5 features at a time - hardcoded for now
        self.output_prefix = output_prefix
        self.points_layer = points_layer
        self.workflow_directory = workflow_directory
        self.gpkg_path = gpkg_path
        self.context = (
            context  # Used to pass objects to the thread. e.g. the QgsProject Instance
        )

        self.ors_client = ORSClient("https://api.openrouteservice.org/v2/isochrones")
        self.api_key = self.ors_client.check_api_key()
        # Create the masked API key for logging
        self.masked_api_key = (
            self.api_key[:4] + "*" * (len(self.api_key) - 8) + self.api_key[-4:]
        )
        self.temp_layers = []  # Store intermediate layers

        # Retrieve CRS from a layer in the GeoPackage to match the outputs with that CRS
        gpkg_layer = QgsVectorLayer(
            f"{self.gpkg_path}|layername=study_area_polygons", "areas", "ogr"
        )
        if not gpkg_layer.isValid():
            raise QgsProcessingException(
                f"Failed to load GeoPackage layer for CRS retrieval."
            )
        self.target_crs = gpkg_layer.crs()  # Get the CRS of the GeoPackage layer

        if not self.points_layer.isValid():
            raise QgsProcessingException(f"Failed to load points layer")

        QgsMessageLog.logMessage(
            "ORS Multibuffer Processor Initialized", tag="Geest", level=Qgis.Info
        )

    def process_areas(self, mode="foot-walking", measurement="distance") -> str:
        """
        Main function to iterate over areas from the GeoPackage and perform the analysis for each area.

        This function processes areas (defined by polygons and bounding boxes) from the GeoPackage using
        the provided input layers (features, grid). It applies the steps of selecting intersecting
        features, buffering them by 5 km, assigning values, and rasterizing the grid.

        Param:
            mode (str): The mode of travel for the ORS API (e.g., 'walking', 'driving-car')
            measurement (str): The measurement type for the ORS isochrones ('distance' or 'time')

        Raises:
            QgsProcessingException: If any processing step fails during the execution.

        Returns:
            str: The file path to the VRT file containing the combined rasters
        """
        QgsMessageLog.logMessage(
            "ORS  Mulitbuffer Processing Started", tag="Geest", level=Qgis.Info
        )

        feedback = QgsProcessingFeedback()
        area_iterator = AreaIterator(self.gpkg_path)

        for index, (current_area, current_bbox, progress) in enumerate(area_iterator):
            feedback.pushInfo(f"Processing area {index} with progress {progress:.2f}%")

            # Step 1: Select features that intersect with the current area
            area_features = self._select_features(
                self.points_layer,
                current_area,
                f"{self.output_prefix}_area_features_{index}",
            )

            if area_features.featureCount() == 0:
                continue

            # Step 2: Process these areas in batches and create buffers
            vector_output_path = f"{self.output_prefix}_area_features_{index}"
            result = self.create_multibuffers(
                point_layer=area_features,
                output_path=vector_output_path,
                mode=mode,
                measurement=measurement,
                index=index,
            )
            if not result:
                QgsMessageLog.logMessage(
                    f"Error creating buffers for {vector_output_path}",
                    tag="Geest",
                    level=Qgis.Warning,
                )
                return False
            QgsMessageLog.logMessage(
                f"Buffers created for {vector_output_path}",
                tag="Geest",
                level=Qgis.Info,
            )

            # Step 3: Assign values based on distance

            # Step 4: Dissolve and remove overlapping areas, keeping areas withe the lowest value

            # Step 5: Rasterize the scored buffer layer
            raster_output_path = os.path.join(
                self.workflow_directory, f"{self.output_prefix}_multibuffer_{index}.tif"
            )
            # Call the rasterize function from MultiBufferCreator
            QgsMessageLog.logMessage(
                f"Rasterizing buffers for area {index} with input_path {vector_output_path}",
                tag="Geest",
                level=Qgis.Info,
            )
            raster_output = self.rasterize(
                input_path=result,
                output_path=raster_output_path,
                distance_field="distance",
                bbox=current_bbox,
            )
            # raster_output = self._rasterize(dissolved_layer, current_bbox, index)

            # Step 6: Multiply the area by it matching area in the study_area
            masked_layer = self._mask_raster(
                raster_path=raster_output,
                area_geometry=current_area,
                bbox=current_bbox,
                index=index,
            )
        # Combine all area rasters into a VRT
        vrt_filepath = self._combine_rasters_to_vrt(index + 1)

        QgsMessageLog.logMessage(
            f"ORS Impact Raster Processing Completed. Output VRT: {vrt_filepath}",
            tag="Geest",
            level=Qgis.Info,
        )
        return vrt_filepath

    def _select_features(
        self, layer: QgsVectorLayer, area_geom: QgsGeometry, output_name: str
    ) -> QgsVectorLayer:
        """
        Select features from the input layer that intersect with the given area geometry
        using the QGIS API. The selected features are stored in a temporary layer.

        Args:
            layer (QgsVectorLayer): The input layer to select features from (should be a point layer)
            area_geom (QgsGeometry): The current area geometry for which intersections are evaluated.
            output_name (str): A name for the output temporary layer to store selected features.

        Returns:
            QgsVectorLayer: A new temporary layer containing features that intersect with the given area geometry.
        """
        QgsMessageLog.logMessage(
            "ORS Select Features Started", tag="Geest", level=Qgis.Info
        )
        output_path = os.path.join(self.workflow_directory, f"{output_name}.shp")

        # Get the WKB type (geometry type) of the input layer (e.g., Point, LineString, Polygon)
        geometry_type = layer.wkbType()

        # Determine geometry type name based on input layer's geometry
        if QgsWkbTypes.geometryType(geometry_type) == QgsWkbTypes.PointGeometry:
            geometry_name = "Point"
        else:
            raise QgsProcessingException(f"Unsupported geometry type: {geometry_type}")

        # Create a memory layer to store the selected features with the correct geometry type
        crs = layer.crs().authid()
        temp_layer = QgsVectorLayer(f"{geometry_name}?crs={crs}", output_name, "memory")
        temp_layer_data = temp_layer.dataProvider()

        # Add fields to the temporary layer
        temp_layer_data.addAttributes(layer.fields())
        temp_layer.updateFields()

        # Transform the area geometry to match the point layer CRS
        transform = QgsCoordinateTransform(
            self.target_crs, layer.crs(), self.context.project()
        )
        reprojected_area_geom = QgsGeometry(area_geom)
        reprojected_area_geom.transform(transform)
        # Iterate through features and select those that intersect with the area
        request = QgsFeatureRequest(area_geom.boundingBox()).setFilterRect(
            reprojected_area_geom.boundingBox()
        )

        selected_features = [
            feat
            for feat in layer.getFeatures(request)
            if feat.geometry().intersects(reprojected_area_geom)
        ]
        temp_layer_data.addFeatures(selected_features)

        QgsMessageLog.logMessage(
            f"ORS writing {len(selected_features)} features",
            tag="Geest",
            level=Qgis.Info,
        )

        # Save the memory layer to a file for persistence
        QgsVectorFileWriter.writeAsVectorFormat(
            temp_layer, output_path, "UTF-8", temp_layer.crs(), "ESRI Shapefile"
        )

        QgsMessageLog.logMessage(
            "ORS Select Features Ending", tag="Geest", level=Qgis.Info
        )

        return QgsVectorLayer(output_path, output_name, "ogr")

    def create_multibuffers(
        self,
        point_layer: str,
        output_path: str,
        mode: str = "foot-walking",
        measurement: str = "distance",
        index: int = 0,
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
        :param index: Index of the current area being processed.
        :return: QgsVectorLayer containing the buffers as polygons.
        """
        QgsMessageLog.logMessage(
            f"Using ORS API key: {self.masked_api_key}",
            "Geest",
            Qgis.Info,
        )
        QgsMessageLog.logMessage(
            f"Creating buffers for {point_layer.name()} in {output_path}",
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
            QgsMessageLog.logMessage(
                f"Merging {len(self.temp_layers)} isochrone layers",
                "Geest",
                Qgis.Info,
            )
            crs = point_layer.crs()
            merged_layer = self._merge_layers(self.temp_layers, crs, index)
            QgsMessageLog.logMessage(
                f"Merged isochrone layer created at {output_path}",
                "Geest",
                Qgis.Info,
            )
            QgsMessageLog.logMessage(
                f"Removing overlaps between isochrones for {merged_layer}",
                "Geest",
                Qgis.Info,
            )
            result = self._create_bands(merged_layer, crs, index)
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

    def _fetch_isochrones(
        self, subset_layer, mode="foot-walking", measurement="distance"
    ):
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

    def _merge_layers(self, temp_layers=None, crs=None, index=None):
        """
        Merge all temporary isochrone layers into a single layer.

        :param temp_layers: List of temporary QgsVectorLayers to merge.
        :param crs: The CRS to use for the merged layer.
        :param index: The index of the current area being processed.
        :return: A QgsVectorLayer representing the merged isochrone layers.
        """
        merge_output = os.path.join(
            self.workflow_directory, f"merged_isochrones_{index}.shp"
        )
        merge_params = {
            "LAYERS": temp_layers,
            "CRS": crs,
            "OUTPUT": merge_output,
        }
        merged_result = processing.run("native:mergevectorlayers", merge_params)
        merge = QgsVectorLayer(merged_result["OUTPUT"], "merge", "ogr")
        return merge

    def _create_bands(self, merged_layer, crs, index):
        """
        Create bands by computing differences between isochrone ranges.

        This method computes the differences between isochrone ranges to create bands
        of non overlapping polygons. The bands are then merged into a final output layer.

        :param merged_layer: The merged isochrone layer.
        :param crs: Coordinate reference system for the output.
        :param index: The index of the current area being processed.

        Returns:
            str: The final output layer path containing the bands.
        """
        output_path = os.path.join(
            self.workflow_directory, f"final_isochrones_{index}.shp"
        )

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
        return output_path

    def rasterize(
        self,
        input_path: str = None,
        output_path: str = None,
        distance_field: str = "distance",
        bbox: QgsGeometry = None,
    ):
        """
        Rasterize the input vector layer based on the burn field and values.

        Args:
            input_path (str, optional): Path to the input vector layer. Defaults to None.
            output_path (str, optional): Path to save the rasterized output. Defaults to None.
            distance_field (str, optional): Field to be used for the burn values. Defaults to "distance".
            cell_size (int, optional): Cell size for rasterization. Defaults to 100.

        Returns:
            str: The path to the rasterized output.
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
        if not self.distance_list:
            raise ValueError("Burn values are required")

        # Load the input vector layer
        input_layer = QgsVectorLayer(input_path, "input_layer", "ogr")
        if not input_layer.isValid():
            raise ValueError(f"Failed to load input layer from {input_path}")

        # Check if the "value" field already exists
        field_names = [field.name() for field in input_layer.fields()]
        QgsMessageLog.logMessage(f"Field names: {field_names}", "Geest", Qgis.Info)
        if "value" not in field_names:
            QgsMessageLog.logMessage(
                "Adding 'value' field to input layer", "Geest", Qgis.Info
            )
            # Add the burn field to the input layer if it doesn't exist
            input_layer.dataProvider().addAttributes([QgsField("value", QVariant.Int)])
            input_layer.updateFields()

            # Log message when the field is added
            QgsMessageLog.logMessage(
                'Added "value" field to input layer',
                "Geest",
                Qgis.Info,
            )

        # Calculate the burn field value based on the item number in the distance list
        input_layer.startEditing()
        for i, feature in enumerate(input_layer.getFeatures()):
            # Get the value of the burn field from the feature
            distance_field_value = feature.attribute(distance_field)
            # Get the index of the burn field value from the distances list
            if distance_field_value in self.distance_list:
                distance_field_index = self.distance_list.index(distance_field_value)
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
                input_layer.updateFeature(feature)
        input_layer.commitChanges()

        # reproject the later to self.target_crs
        reprojected_layer_path = input_path.replace(
            ".shp", f"_epsg{self.target_crs.postgisSrid()}.shp"
        )
        transform_params = {
            "INPUT": input_layer,
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

        # Ensure resolution parameters are properly formatted as float values
        x_res = self.cell_size_m  # pixel size in X direction
        y_res = self.cell_size_m  # pixel size in Y direction
        bbox = bbox.boundingBox()
        # Define rasterization parameters for the temporary layer
        params = {
            "INPUT": reprojected_layer,
            "FIELD": "value",
            "BURN": 0,
            "USE_Z": False,
            "UNITS": 1,
            "WIDTH": x_res,
            "HEIGHT": y_res,
            "EXTENT": f"{bbox.xMinimum()},{bbox.xMaximum()},{bbox.yMinimum()},{bbox.yMaximum()} [{self.target_crs.authid()}]",
            "NODATA": 0,
            "OPTIONS": "",
            "DATA_TYPE": 0,
            "INIT": 5,
            "INVERT": False,
            "EXTRA": "",
            "OUTPUT": output_path,
        }
        verbose_mode = int(setting(key="verbose_mode", default=0))
        if not verbose_mode:
            QgsMessageLog.logMessage(str(params), tag="Geest", level=Qgis.Info)
        result = processing.run("gdal:rasterize", params)
        QgsMessageLog.logMessage(
            f"Rasterized output saved to {output_path}", "Geest", Qgis.Info
        )
        return output_path

    def _mask_raster(
        self,
        raster_path: str,
        area_geometry: QgsGeometry,
        bbox: QgsGeometry,
        index: int,
    ) -> QgsVectorLayer:
        """
        Mask the raster with the study area mask layer.

        Args:
            raster_path (str): The path to the raster to mask.
            area_geometry (QgsGeometry): The geometry of the study area.
            bbox (QgsGeometry): The bounding box of the study area.
            index (int): The index of the current area being processed.
        Returns:
            masked_raster_filepath (str): The file path to the masked raster.
        """
        # Clip the raster to the study area boundary
        masked_raster_filepath = os.path.join(
            self.workflow_directory,
            f"{self.output_prefix}_final_{index}.tif",
        )
        # Convert the area geometry to a temporary layer
        epsg_code = self.target_crs.authid()
        area_layer = QgsVectorLayer(f"Polygon?crs={epsg_code}", "area", "memory")
        area_provider = area_layer.dataProvider()
        area_feature = QgsFeature()
        area_feature.setGeometry(area_geometry)
        area_provider.addFeatures([area_feature])
        verbose_mode = int(setting(key="verbose_mode", default=0))
        if verbose_mode:
            # save the area layer to a file
            area_layer_path = os.path.join(self.workflow_directory, f"area_{index}.shp")
            QgsVectorFileWriter.writeAsVectorFormat(
                area_layer, area_layer_path, "UTF-8", self.target_crs, "ESRI Shapefile"
            )
        bbox = bbox.boundingBox()
        params = {
            "INPUT": f"{raster_path}",
            "MASK": area_layer,
            "SOURCE_CRS": None,
            "TARGET_CRS": None,
            "EXTENT": f"{bbox.xMinimum()},{bbox.xMaximum()},{bbox.yMinimum()},{bbox.yMaximum()} [{self.target_crs.authid()}]",
            "NODATA": 255,
            "ALPHA_BAND": False,
            "CROP_TO_CUTLINE": True,
            "KEEP_RESOLUTION": True,
            "SET_RESOLUTION": False,
            "X_RESOLUTION": None,
            "Y_RESOLUTION": None,
            "MULTITHREADING": False,
            "OPTIONS": "",
            "DATA_TYPE": 0,
            "EXTRA": "",
            "OUTPUT": masked_raster_filepath,
        }

        processing.run("gdal:cliprasterbymasklayer", params)
        QgsMessageLog.logMessage(
            f"Mask Parameter: {params}", tag="Geest", level=Qgis.Info
        )
        QgsMessageLog.logMessage(
            f"Masked raster saved to {masked_raster_filepath}",
            tag="Geest",
            level=Qgis.Info,
        )
        return masked_raster_filepath

    def _combine_rasters_to_vrt(self, num_rasters: int) -> None:
        """
        Combine all the rasters into a single VRT file.

        Args:
            num_rasters (int): The number of rasters to combine into a VRT.

        Returns:
            vrtpath (str): The file path to the VRT file.
        """
        raster_files = []
        for i in range(num_rasters):
            raster_path = os.path.join(
                self.workflow_directory,
                f"{self.output_prefix}_final_{i}.tif",
            )
            if os.path.exists(raster_path) and QgsRasterLayer(raster_path).isValid():
                raster_files.append(raster_path)
            else:
                QgsMessageLog.logMessage(
                    f"Skipping invalid or non-existent raster: {raster_path}",
                    tag="Geest",
                    level=Qgis.Warning,
                )

        if not raster_files:
            QgsMessageLog.logMessage(
                "No valid raster layers found to combine into VRT.",
                tag="Geest",
                level=Qgis.Warning,
            )
            return
        vrt_filepath = os.path.join(
            self.workflow_directory,
            f"{self.output_prefix}_dissolved_combined.vrt",
        )

        QgsMessageLog.logMessage(
            f"Creating VRT of layers '{vrt_filepath}' layer to the map.",
            tag="Geest",
            level=Qgis.Info,
        )

        if not raster_files:
            QgsMessageLog.logMessage(
                "No raster layers found to combine into VRT.",
                tag="Geest",
                level=Qgis.Warning,
            )
            return

        # Define the VRT parameters
        params = {
            "INPUT": raster_files,
            "RESOLUTION": 0,  # Use highest resolution among input files
            "SEPARATE": False,  # Combine all input rasters as a single band
            "OUTPUT": vrt_filepath,
            "PROJ_DIFFERENCE": False,
            "ADD_ALPHA": False,
            "ASSIGN_CRS": self.target_crs,
            "RESAMPLING": 0,
            "SRC_NODATA": "255",
            "EXTRA": "",
        }

        # Run the gdal:buildvrt processing algorithm to create the VRT
        results = processing.run("gdal:buildvirtualraster", params)
        QgsMessageLog.logMessage(
            f"Created VRT: {vrt_filepath}", tag="Geest", level=Qgis.Info
        )
        # Add the VRT to the QGIS map
        vrt_layer = QgsRasterLayer(vrt_filepath, f"{self.output_prefix}_combined VRT")

        if vrt_layer.isValid():

            # output_layer = context.getMapLayer(results['OUTPUT'])

            # because getMapLayer doesn't transfer ownership, the layer will
            # be deleted when context goes out of scope and you'll get a
            # crash.
            # takeMapLayer transfers ownership so it's then safe to add it
            # to the project and give the project ownership.
            # See https://docs.qgis.org/3.34/en/docs/pyqgis_developer_cookbook/tasks.html

            # QgsProject.instance().addMapLayer(
            #    self.context.takeResultLayer(vrt_layer.id()))

            # self.context.project().addMapLayer(vrt_layer)
            QgsMessageLog.logMessage(
                "Added VRT layer to the map.", tag="Geest", level=Qgis.Info
            )
        else:
            QgsMessageLog.logMessage(
                "Failed to add VRT layer to the map.", tag="Geest", level=Qgis.Critical
            )
        return vrt_filepath
