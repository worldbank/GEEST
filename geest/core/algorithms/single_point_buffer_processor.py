from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCoordinateTransformContext,
    QgsFeature,
    QgsFeatureRequest,
    QgsField,
    QgsGeometry,
    QgsProcessingFeedback,
    QgsProcessingException,
    QgsVectorLayer,
    QgsPointXY,
    QgsFields,
    QgsProject,
    QgsMessageLog,
    QgsVectorFileWriter,
    QgsWkbTypes,
    QgsRasterLayer,
    Qgis,
)
from qgis.PyQt.QtCore import QVariant
import os
import csv
import processing
from .area_iterator import AreaIterator


class SinglePointBufferProcessor:
    def __init__(
        self,
        output_prefix: str,
        input_layer: QgsVectorLayer,
        buffer_distance: float,
        workflow_directory: str,
        gpkg_path: str,
    ):
        """
        Initializes the SinglePointBufferProcessor.

        Args:
            output_prefix (str): Prefix for naming output files.
            input_layer (QgsVectorLayer): The input layer containing the points to buffer.
            buffer_distance (float): The distance in meters to buffer the points.
            workflow_directory (str): Directory where temporary and output files will be stored.
            gpkg_path (str): Path to the GeoPackage containing study areas and bounding boxes.
        """
        self.output_prefix = output_prefix
        self.features_layer = input_layer
        self.buffer_distance = buffer_distance
        self.workflow_directory = workflow_directory
        self.gpkg_path = gpkg_path
        # Retrieve CRS from a layer in the GeoPackage to match the points with that CRS
        gpkg_layer = QgsVectorLayer(
            f"{self.gpkg_path}|layername=study_area_polygons", "areas", "ogr"
        )
        if not gpkg_layer.isValid():
            raise QgsProcessingException(
                f"Failed to load GeoPackage layer for CRS retrieval."
            )
        self.target_crs = gpkg_layer.crs()  # Get the CRS of the GeoPackage layer

        # Load the CSV and create a point layer
        self.features_layer = self._load_csv_as_point_layer()

        if not self.features_layer.isValid():
            raise QgsProcessingException(
                f"Failed to load features layer from {self.features_layer.source()}"
            )

        QgsMessageLog.logMessage(
            "Single Point Buffer Processor Initialized", tag="Geest", level=Qgis.Info
        )

    def process_areas(self) -> str:
        """
        Main function to iterate over areas from the GeoPackage and perform the analysis for each area.

        This function processes areas (defined by polygons and bounding boxes) from the GeoPackage using
        the provided input layers (features, grid). It applies the steps of selecting intersecting
        features, buffering them by 5 km, assigning values, and rasterizing the grid.

        Raises:
            QgsProcessingException: If any processing step fails during the execution.

        Returns:
            str: The file path to the VRT file containing the combined rasters
        """
        QgsMessageLog.logMessage(
            "Single Point Buffer Processing Started", tag="Geest", level=Qgis.Info
        )

        feedback = QgsProcessingFeedback()
        area_iterator = AreaIterator(self.gpkg_path)

        for index, (current_area, current_bbox, progress) in enumerate(area_iterator):
            feedback.pushInfo(f"Processing area {index} with progress {progress:.2f}%")

            # Step 1: Select features that intersect with the current area
            area_features = self._select_features(
                self.features_layer,
                current_area,
                f"{self.output_prefix}_area_features_{index}",
            )

            if area_features.featureCount() == 0:
                continue

            # Step 2: Buffer the selected features by 5 km
            buffered_layer = self._buffer_features(
                area_features,
                f"{self.output_prefix}_buffers_{index}",
            )

            # Step 3: Assign values based on event_type
            scored_layer = self._assign_scores(buffered_layer)

            # Step 4: Dissolve and remove overlapping areas, keeping areas withe the lowest value
            dissolved_layer = self._overlay_analysis(
                scored_layer, f"{self.output_prefix}_dissolved_{index}.shp"
            )

            # Step 5: Rasterize the scored buffer layer
            raster_output = self._rasterize(dissolved_layer, current_bbox, index)

            # Step 6: Multiply the area by it matching mask layer in study_area folder
            masked_layer = self._mask_raster(
                raster_path=raster_output,
                area_geometry=current_area,
                output_name=f"{self.output_prefix}_masked_{index}.shp",
                index=index,
            )
        # Combine all area rasters into a VRT
        vrt_filepath = self._combine_rasters_to_vrt(index + 1)

        QgsMessageLog.logMessage(
            f"Single Point Buffer Processing Completed. Output VRT: {vrt_filepath}",
            tag="Geest",
            level=Qgis.Info,
        )
        return ""  # vrt_filepath

    def _select_features(
        self, layer: QgsVectorLayer, area_geom: QgsGeometry, output_name: str
    ) -> QgsVectorLayer:
        """
        Select features from the input layer that intersect with the given area geometry
        using the QGIS API. The selected features are stored in a temporary layer.

        Args:
            layer (QgsVectorLayer): The input layer to select features from (e.g., points, lines, polygons).
            area_geom (QgsGeometry): The current area geometry for which intersections are evaluated.
            output_name (str): A name for the output temporary layer to store selected features.

        Returns:
            QgsVectorLayer: A new temporary layer containing features that intersect with the given area geometry.
        """
        QgsMessageLog.logMessage(
            "ACLED Select Features Started", tag="Geest", level=Qgis.Info
        )
        output_path = os.path.join(self.workflow_directory, f"{output_name}.shp")

        # Get the WKB type (geometry type) of the input layer (e.g., Point, LineString, Polygon)
        geometry_type = layer.wkbType()

        # Determine geometry type name based on input layer's geometry
        if QgsWkbTypes.geometryType(geometry_type) == QgsWkbTypes.PointGeometry:
            geometry_name = "Point"
        elif QgsWkbTypes.geometryType(geometry_type) == QgsWkbTypes.LineGeometry:
            geometry_name = "LineString"
        else:
            raise QgsProcessingException(f"Unsupported geometry type: {geometry_type}")

        # Create a memory layer to store the selected features with the correct geometry type
        crs = layer.crs().authid()
        temp_layer = QgsVectorLayer(f"{geometry_name}?crs={crs}", output_name, "memory")
        temp_layer_data = temp_layer.dataProvider()

        # Add fields to the temporary layer
        temp_layer_data.addAttributes(layer.fields())
        temp_layer.updateFields()

        # Iterate through features and select those that intersect with the area
        request = QgsFeatureRequest(area_geom.boundingBox()).setFilterRect(
            area_geom.boundingBox()
        )
        selected_features = [
            feat
            for feat in layer.getFeatures(request)
            if feat.geometry().intersects(area_geom)
        ]
        temp_layer_data.addFeatures(selected_features)

        QgsMessageLog.logMessage(
            f"Acled writing {len(selected_features)} features",
            tag="Geest",
            level=Qgis.Info,
        )

        # Save the memory layer to a file for persistence
        QgsVectorFileWriter.writeAsVectorFormat(
            temp_layer, output_path, "UTF-8", temp_layer.crs(), "ESRI Shapefile"
        )

        QgsMessageLog.logMessage(
            "ACLED Select Features Ending", tag="Geest", level=Qgis.Info
        )

        return QgsVectorLayer(output_path, output_name, "ogr")

    def _buffer_features(
        self, layer: QgsVectorLayer, output_name: str
    ) -> QgsVectorLayer:
        """
        Buffer the input features by the buffer_distance km.

        Args:
            layer (QgsVectorLayer): The input feature layer.
            output_name (str): A name for the output buffered layer.

        Returns:
            QgsVectorLayer: The buffered features layer.
        """
        output_path = os.path.join(self.workflow_directory, f"{output_name}.shp")
        buffered_layer = processing.run(
            "native:buffer",
            {
                "INPUT": layer,
                "DISTANCE": self.buffer_distance,  # 5 km buffer
                "SEGMENTS": 5,
                "DISSOLVE": False,
                "OUTPUT": output_path,
            },
        )["OUTPUT"]

        return buffered_layer

    def _assign_scores(self, layer_path: str) -> QgsVectorLayer:
        """
        Assign values to buffered polygons based on their event_type.

        Args:
            layer_path (str): The buffered features layer.

        Returns:
            QgsVectorLayer: A new layer with a "value" field containing the assigned scores.
        """
        layer = QgsVectorLayer(
            layer_path, "buffered_features", "ogr"
        )  # Load the buffered layer
        QgsMessageLog.logMessage(
            f"Assigning scores to {layer.name()}", tag="Geest", level=Qgis.Info
        )
        # Create a new field in the layer for the scores
        layer.startEditing()
        layer.dataProvider().addAttributes([QgsField("value", QVariant.Int)])
        layer.updateFields()

        # Assign scores based on event_type
        score = 5
        for feature in layer.getFeatures():
            feature.setAttribute("value", score)
            layer.updateFeature(feature)

        layer.commitChanges()

        return layer

    def _overlay_analysis(self, input_layer, output_filepath):
        """
        Perform an overlay analysis on a set of circular polygons, prioritizing areas with the lowest value in overlapping regions,
        and save the result as a shapefile.

        This function processes an input shapefile containing circular polygons, each with a value between 1 and 4, representing
        different priority levels. The function performs an overlay analysis where the polygons overlap and ensures that for any
        overlapping areas, the polygon with the lowest value (i.e., highest priority) is retained, while polygons with higher values
        are removed from those regions.

        The analysis is performed as follows:
        1. The input layer is loaded from the provided shapefile path.
        2. A dissolve operation is performed on the input layer to combine any adjacent polygons with the same value.
        3. A union operation is performed on the input layer to break the polygons into distinct, non-overlapping areas.
        4. For each distinct area, the value from the overlapping polygons is compared, and the minimum value (representing the highest priority) is assigned to that area.
        5. The resulting dataset, which consists of non-overlapping polygons with the highest priority (smallest value), is saved to a new shapefile at the specified output path.

        Parameters:
        -----------
        input_layer : QgsVectorLayer
            The input shapefile containing the circular polygons with values between 1 and 4.

        output_filepath : str
            The file path where the output shapefile with the results of the overlay analysis will be saved. The
            output will be saved in self.workflow_directory.

        Returns:
        --------
        None
            The function does not return a value but writes the result to the specified output shapefile.

        Logging:
        --------
        Messages related to the status of the operation (success or failure) are logged using QgsMessageLog with the tag 'Geest'
        and the log level set to Qgis.Info.

        Raises:
        -------
        IOError:
            If the input layer cannot be loaded or if an error occurs during the file writing process.

        Example:
        --------
        To perform an overlay analysis on a shapefile located at "path/to/input.shp" and save the result to "path/to/output.shp",
        use the following:

        overlay_analysis(qgis_vector_layer, "path/to/output.shp")
        """
        QgsMessageLog.logMessage("Overlay analysis started", "Geest", Qgis.Info)
        # Step 1: Load the input layer from the provided shapefile path
        # layer = QgsVectorLayer(input_filepath, "circles_layer", "ogr")

        if not input_layer.isValid():
            QgsMessageLog.logMessage("Layer failed to load!", "Geest", Qgis.Info)
            return

        # Step 2: Create a memory layer to store the result
        result_layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "result_layer", "memory")
        provider = result_layer.dataProvider()

        # Step 3: Add a field to store the minimum value (lower number = higher rank)
        provider.addAttributes([QgsField("min_value", QVariant.Int)])
        result_layer.updateFields()
        # Step 4: Perform the dissolve operation to separate disjoint polygons
        dissolve = processing.run(
            "native:dissolve",
            {
                "INPUT": input_layer,
                "FIELD": ["value"],
                "SEPARATE_DISJOINT": True,
                "OUTPUT": "TEMPORARY_OUTPUT",
            },
        )["OUTPUT"]
        QgsMessageLog.logMessage(
            f"Dissolved areas have {len(dissolve)} features",
            tag="Geest",
            level=Qgis.Info,
        )
        # Step 5: Perform the union to get all overlapping areas
        union = processing.run(
            "qgis:union",
            {
                "INPUT": dissolve,
                #'OVERLAY': '', #input_layer, # Do we need this?
                "OUTPUT": "memory:",
            },
        )["OUTPUT"]
        QgsMessageLog.logMessage(
            f"Unioned areas have {len(dissolve)} features", tag="Geest", level=Qgis.Info
        )
        # Step 6: Iterate through the unioned features to assign the minimum value in overlapping areas
        for feature in union.getFeatures():
            geom = feature.geometry()
            attrs = feature.attributes()
            value_1 = attrs[input_layer.fields().indexFromName("value")]
            value_2 = attrs[
                input_layer.fields().indexFromName("value_2")
            ]  # This comes from the unioned layer

            # Assign the minimum value to the overlapping area (lower number = higher rank)
            min_value = min(value_1, value_2)

            # Create a new feature with this geometry and the min value
            new_feature = QgsFeature()
            new_feature.setGeometry(geom)
            new_feature.setAttributes([min_value])

            # Add the new feature to the result layer
            provider.addFeature(new_feature)
        full_output_filepath = os.path.join(self.workflow_directory, output_filepath)
        # Step 7: Save the result layer to the specified output shapefile
        error = QgsVectorFileWriter.writeAsVectorFormat(
            result_layer,
            full_output_filepath,
            "UTF-8",
            result_layer.crs(),
            "ESRI Shapefile",
        )

        if error[0] == 0:
            QgsMessageLog.logMessage(
                f"Overlay analysis complete, output saved to {full_output_filepath}",
                "Geest",
                Qgis.Info,
            )
        else:
            raise QgsProcessingException(
                f"Error saving dissolved layer to disk: {error[1]}"
            )
        return full_output_filepath

    def _rasterize(
        self, input_layer: QgsVectorLayer, bbox: QgsGeometry, index: int
    ) -> str:
        """

        ⭐️🚩⭐️ Warning this is not DRY - almost same function exists in study_area.py

        Rasterize the grid layer based on the 'value' attribute.

        Args:
            input_layer (QgsVectorLayer): The layer to rasterize.
            bbox (QgsGeometry): The bounding box for the raster extents.
            index (int): The current index used for naming the output raster.

        Returns:
            str: The file path to the rasterized output.
        """
        QgsMessageLog.logMessage("--- Rasterizingrid", tag="Geest", level=Qgis.Info)
        QgsMessageLog.logMessage(f"--- bbox {bbox}", tag="Geest", level=Qgis.Info)
        QgsMessageLog.logMessage(f"--- index {index}", tag="Geest", level=Qgis.Info)

        output_path = os.path.join(
            self.workflow_directory,
            f"{self.output_prefix}_dissolved_{index}.tif",
        )
        layer = QgsVectorLayer(input_layer, "acled_areas", "ogr")
        if not layer.isValid():
            QgsMessageLog.logMessage(
                f"Layer failed to load! {input_layer}", "Geest", Qgis.Info
            )
            return
        else:
            QgsMessageLog.logMessage(f"Rasterizing {input_layer}", "Geest", Qgis.Info)

        # Ensure resolution parameters are properly formatted as float values
        x_res = 100.0  # 100m pixel size in X direction
        y_res = 100.0  # 100m pixel size in Y direction
        bbox = bbox.boundingBox()
        # Define rasterization parameters for the temporary layer
        params = {
            "INPUT": f"{input_layer}",
            "FIELD": "min_value",
            "BURN": 0,
            "INIT": 5,  # use 5 as the initial value where there is no data. Sea will be masked out later.
            "USE_Z": False,
            "UNITS": 1,
            "WIDTH": x_res,
            "HEIGHT": y_res,
            "EXTENT": f"{bbox.xMinimum()},{bbox.xMaximum()},"
            f"{bbox.yMinimum()},{bbox.yMaximum()}",  # Extent of the aligned bbox
            "NODATA": -9999,
            "OPTIONS": "",
            #'OPTIONS':'COMPRESS=DEFLATE|PREDICTOR=2|ZLEVEL=9',
            "DATA_TYPE": 0,  # byte
            "INVERT": False,
            "EXTRA": "",
            "OUTPUT": output_path,
            # TODO this doesnt work, layer is written in correct CRS but advertises 4326
            "TARGET_CRS": self.target_crs.toWkt(),
        }

        processing.run("gdal:rasterize", params)
        QgsMessageLog.logMessage(
            f"Rasterize Parameter: {params}", tag="Geest", level=Qgis.Info
        )

        QgsMessageLog.logMessage(
            f"Rasterize complete for: {output_path}",
            tag="Geest",
            level=Qgis.Info,
        )

        QgsMessageLog.logMessage(
            f"Created raster: {output_path}", tag="Geest", level=Qgis.Info
        )
        return output_path

    def _mask_raster(
        self, raster_path: str, area_geometry: QgsGeometry, index: int, output_name: str
    ) -> QgsVectorLayer:
        """
        Mask the raster with the study area mask layer.

        Args:
            raster_path (str): The path to the raster to mask.
            output_name (str): A name for the output masked layer.

        """
        # Clip the raster to the study area boundary
        masked_raster_filepath = os.path.join(
            self.workflow_directory,
            f"{self.output_prefix}_final_{index}.tif",
        )
        # Convert the area geometry to a temporary layer
        epsg_code = self.target_crs.authid()
        area_layer = QgsVectorLayer(f"Polygon?crs=EPSG:{epsg_code}", "area", "memory")
        area_provider = area_layer.dataProvider()
        area_feature = QgsFeature()
        area_feature.setGeometry(area_geometry)
        area_provider.addFeatures([area_feature])
        params = {
            "INPUT": f"{raster_path}",
            "MASK": area_layer,
            "NODATA": 255,
            "CROP_TO_CUTLINE": False,
            "OUTPUT": masked_raster_filepath,
            # TODO this doesnt work, layer is written in correct CRS but advertises 4326
            "TARGET_CRS": self.target_crs.toWkt(),
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
            "ASSIGN_CRS": self.target_crs.toWkt(),
            "RESAMPLING": 0,
            "SRC_NODATA": "255",
            "EXTRA": "",
        }

        # Run the gdal:buildvrt processing algorithm to create the VRT
        processing.run("gdal:buildvirtualraster", params)
        QgsMessageLog.logMessage(
            f"Created VRT: {vrt_filepath}", tag="Geest", level=Qgis.Info
        )

        # Add the VRT to the QGIS map
        vrt_layer = QgsRasterLayer(vrt_filepath, f"{self.output_prefix}_combined VRT")

        if vrt_layer.isValid():
            QgsProject.instance().addMapLayer(vrt_layer)
            QgsMessageLog.logMessage(
                "Added VRT layer to the map.", tag="Geest", level=Qgis.Info
            )
        else:
            QgsMessageLog.logMessage(
                "Failed to add VRT layer to the map.", tag="Geest", level=Qgis.Critical
            )
        return vrt_filepath
