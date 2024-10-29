from qgis.core import (
    QgsFeature,
    QgsFeatureRequest,
    QgsField,
    QgsGeometry,
    QgsProcessingFeedback,
    QgsProcessingException,
    QgsVectorLayer,
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
        cell_size_m: float,
        input_layer: QgsVectorLayer,
        buffer_distance: float,
        workflow_directory: str,
        gpkg_path: str,
    ):
        """
        Initializes the SinglePointBufferProcessor.

        Args:
            output_prefix (str): Prefix for naming output files.
            cell_size_m (float): The cell size in meters for the analysis.
            input_layer (QgsVectorLayer): The input layer containing the points to buffer.
            buffer_distance (float): The distance in meters to buffer the points.
            workflow_directory (str): Directory where temporary and output files will be stored.
            gpkg_path (str): Path to the GeoPackage containing study areas and bounding boxes.
        """
        self.output_prefix = output_prefix
        self.cell_size_m = cell_size_m
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
        QgsMessageLog.logMessage(
            f"Target CRS: {self.target_crs.authid()}", tag="Geest", level=Qgis.Info
        )
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

            # Step 3: Buffer the selected features
            buffered_layer = self._buffer_features(
                area_features, f"{self.output_prefix}_buffered_{index}"
            )

            # Step 3: Assign values to the buffered polygons
            scored_layer = self._assign_scores(buffered_layer)

            # Step 4: Rasterize the scored buffer layer
            raster_output = self._rasterize(scored_layer, current_bbox, index)

            # Step 5: Multiply the area by it matching mask layer in study_area folder
            masked_layer = self._mask_raster(
                raster_path=raster_output,
                area_geometry=current_area,
                bbox=current_bbox,
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
            "Single Point Buffer Select Features Started", tag="Geest", level=Qgis.Info
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
            f"Single Point Buffer writing {len(selected_features)} features",
            tag="Geest",
            level=Qgis.Info,
        )

        # Save the memory layer to a file for persistence
        QgsVectorFileWriter.writeAsVectorFormat(
            temp_layer, output_path, "UTF-8", temp_layer.crs(), "ESRI Shapefile"
        )

        QgsMessageLog.logMessage(
            "Single Point Buffer Select Features Ending", tag="Geest", level=Qgis.Info
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
                "SEGMENTS": 15,
                "DISSOLVE": True,
                "OUTPUT": output_path,
            },
        )["OUTPUT"]

        buffered_layer = QgsVectorLayer(output_path, output_name, "ogr")
        return buffered_layer

    def _assign_scores(self, layer: QgsVectorLayer) -> QgsVectorLayer:
        """
        Assign values to buffered polygons based 5 for presence of a polygon.

        Args:
            layer QgsVectorLayer: The buffered features layer.

        Returns:
            QgsVectorLayer: A new layer with a "value" field containing the assigned scores.
        """

        QgsMessageLog.logMessage(
            f"Assigning scores to {layer.name()}", tag="Geest", level=Qgis.Info
        )
        # Create a new field in the layer for the scores
        layer.startEditing()
        layer.dataProvider().addAttributes([QgsField("value", QVariant.Int)])
        layer.updateFields()

        # Assign scores to the buffered polygons
        score = 5
        for feature in layer.getFeatures():
            feature.setAttribute("value", score)
            layer.updateFeature(feature)

        layer.commitChanges()

        return layer

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
            f"{self.output_prefix}_buffered_{index}.tif",
        )
        if not input_layer.isValid():
            QgsMessageLog.logMessage(
                f"Layer failed to load! {input_layer}", "Geest", Qgis.Info
            )
            return
        else:
            QgsMessageLog.logMessage(f"Rasterizing {input_layer}", "Geest", Qgis.Info)

        # Ensure resolution parameters are properly formatted as float values
        x_res = self.cell_size_m  # pixel size in X direction
        y_res = self.cell_size_m  # pixel size in Y direction
        bbox = bbox.boundingBox()
        # Define rasterization parameters for the temporary layer
        params = {
            "INPUT": input_layer,
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
            "INIT": 1,
            "INVERT": False,
            "EXTRA": f"-a_srs {self.target_crs.authid()}",
            "OUTPUT": output_path,
        }

        #'OUTPUT':'TEMPORARY_OUTPUT'})

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
        self,
        raster_path: str,
        area_geometry: QgsGeometry,
        bbox: QgsGeometry,
        index: int,
        output_name: str,
    ) -> QgsVectorLayer:
        """
        Mask the raster with the study area mask layer.

        Args:
            raster_path (str): The path to the raster to mask.
            area_geometry (QgsGeometry): The geometry of the study area.
            bbox (QgsGeometry): The bounding box for the raster extents.
            index (int): The current index used for naming the output raster.
            output_name (str): A name for the output masked layer.

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
        # Save the area layer to a file for persistence
        QgsMessageLog.logMessage(
            f"Saving area layer to {output_name} with crs {self.target_crs.authid()}",
            tag="Geest",
        )
        QgsVectorFileWriter.writeAsVectorFormat(
            area_layer,
            os.path.join(
                self.workflow_directory, f"{self.output_prefix}_area_{index}.shp"
            ),
            "UTF-8",
            self.target_crs,
            "ESRI Shapefile",
        )

        bbox = bbox.boundingBox()
        params = {
            "INPUT": f"{raster_path}",
            "MASK": area_layer,
            "SOURCE_CRS": self.target_crs,
            "TARGET_CRS": self.target_crs,
            # This fails!
            # "EXTENT": f"{bbox.xMinimum()},{bbox.xMaximum()},{bbox.yMinimum()},{bbox.yMaximum()} [{self.target_crs.authid()}]",
            "NODATA": 255,
            "ALPHA_BAND": False,
            "CROP_TO_CUTLINE": True,
            "KEEP_RESOLUTION": False,
            "SET_RESOLUTION": True,
            "X_RESOLUTION": self.cell_size_m,
            "Y_RESOLUTION": self.cell_size_m,
            "MULTITHREADING": True,
            "DATA_TYPE": 0,  # byte
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
            f"{self.output_prefix}_buffered_combined.vrt",
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
