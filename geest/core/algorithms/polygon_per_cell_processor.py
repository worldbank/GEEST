from qgis.core import (
    edit,
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCoordinateTransformContext,
    QgsFeature,
    QgsFeatureRequest,
    QgsFields,
    QgsField,
    QgsGeometry,
    QgsMessageLog,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProject,
    QgsRasterLayer,
    QgsSpatialIndex,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsWkbTypes,
)
import processing
from qgis.PyQt.QtCore import QVariant
from .area_iterator import AreaIterator
from typing import List
import os


class PolygonPerCellProcessor:
    """
    A class to process spatial areas and perform spatial analysis using QGIS API.

    This class iterates over areas (polygons) and corresponding bounding boxes within a GeoPackage.
    For each area, it performs spatial operations on the input layer representing pedestrian or other feature-based data,
    and a grid layer from the same GeoPackage. The results are processed and rasterized.

    The following steps are performed for each area:

    1. Reproject the features layer to match the CRS of the grid layer.
    2. Select features (from a reprojected features layer) that intersect with the current area.
    3. Select grid cells (from the `study_area_grid` layer in the GeoPackage) that intersect with the features, ensuring no duplicates.
    4. Assign values to the grid cells based on the number of intersecting features:
        - A value of 3 if the grid cell intersects only one feature.
        - A value of 5 if the grid cell intersects more than one feature.
    5. Rasterize the grid cells, using their assigned values to create a raster for each area.
    6. Convert the resulting raster to byte format to minimize space usage.
    7. After processing all areas, combine the resulting byte rasters into a single VRT file.

    Attributes:
        output_prefix (str): Prefix to be used for naming output files. Based on the layer ID.
        gpkg_path (str): Path to the GeoPackage containing the study areas, bounding boxes, and grid.
        features_layer (QgsVectorLayer): A layer representing pedestrian crossings or other feature-based data.
        workflow_directory (str): Directory where temporary and output files will be stored.
        grid_layer (QgsVectorLayer): A grid layer (study_area_grid) loaded from the GeoPackage.

    Example:
        ```python
        processor = PolygonsPerCellProcessor(features_layer, '/path/to/workflow_directory', '/path/to/your/geopackage.gpkg')
        processor.process_areas()
        ```
    """

    def __init__(
        self,
        output_prefix: str,
        features_layer: QgsVectorLayer,
        workflow_directory: str,
        gpkg_path: str,
    ) -> None:
        """
        Initialize the PolygonsPerCellProcessor with the features layer, working directory, and the GeoPackage path.

        Args:
            features_layer (QgsVectorLayer): The input feature layer representing features like pedestrian crossings.
            workflow_directory (str): Directory where temporary and final output files will be stored.
            gpkg_path (str): Path to the GeoPackage file containing the study areas, bounding boxes, and grid layer.
        """
        QgsMessageLog.logMessage(
            "Polygons per Cell Processor Initialising", tag="Geest", level=Qgis.Info
        )
        self.output_prefix = output_prefix
        self.features_layer = features_layer
        self.workflow_directory = workflow_directory
        self.gpkg_path = gpkg_path  # top-level folder where the GeoPackage is stored

        # Load the grid layer from the GeoPackage
        self.grid_layer = QgsVectorLayer(
            f"{self.gpkg_path}|layername=study_area_grid", "study_area_grid", "ogr"
        )
        if not self.grid_layer.isValid():
            raise QgsProcessingException(
                f"Failed to load 'study_area_grid' layer from the GeoPackage at {self.gpkg_path}"
            )
        if not self.features_layer.isValid():
            raise QgsProcessingException(
                f"Failed to load features layer for Polygons per Cell Processor at {self.features_layer.source()}"
            )
        QgsMessageLog.logMessage(
            "Polygons per Cell Processor Initialised", tag="Geest", level=Qgis.Info
        )

    def process_areas(self) -> None:
        """
        Main function to iterate over areas from the GeoPackage and perform the analysis for each area.

        This function processes areas (defined by polygons and bounding boxes) from the GeoPackage using
        the provided input layers (features, grid). It applies the steps of selecting intersecting
        features, assigning values to grid cells, rasterizing the grid, in byte format, and finally
        combining the rasters into a VRT.

        Raises:
            QgsProcessingException: If any processing step fails during the execution.

        Returns:
            str: The file path to the VRT file containing the combined rasters

        """
        QgsMessageLog.logMessage(
            "Polygons per Cell Process Areas Started", tag="Geest", level=Qgis.Info
        )
        total_features = self.features_layer.featureCount()
        QgsMessageLog.logMessage(
            f"Polygons layer loaded with {total_features} features.",
            tag="Geest",
            level=Qgis.Info,
        )
        # Step 1: Reproject the features layer to match the CRS of the grid layer
        reprojected_features_layer = self._reproject_layer(
            self.features_layer, self.grid_layer.crs()
        )
        total_features = reprojected_features_layer.featureCount()
        QgsMessageLog.logMessage(
            f"Reprojected features layer loaded with {total_features} features.",
            tag="Geest",
            level=Qgis.Info,
        )

        feedback = QgsProcessingFeedback()
        area_iterator = AreaIterator(
            self.gpkg_path
        )  # Use the class-level GeoPackage path

        # Iterate over areas and perform the analysis for each
        for index, (current_area, current_bbox, progress) in enumerate(area_iterator):
            feedback.pushInfo(
                f"Processing area {index + 1} with progress {progress:.2f}%"
            )

            # Step 2: Select features that intersect with the current area and store in a temporary layer
            area_features = self._select_features(
                reprojected_features_layer,
                current_area,
                f"{self.output_prefix}_area_features_{index+1}",
            )
            area_features_count = area_features.featureCount()
            QgsMessageLog.logMessage(
                f"Polygons layer for area {index+1} loaded with {area_features_count} features.",
                tag="Geest",
                level=Qgis.Info,
            )
            # Step 2: Assign reclassification values to polygons based on their perimeter
            reclassified_layer = self._assign_reclassification_to_polygons(
                reprojected_features_layer
            )

            # Step 3: Rasterize the polygons using the reclassification values
            raster_output = self._rasterize_polygons(
                reclassified_layer, current_bbox, index
            )

        # Step 4: Combine the resulting byte rasters into a single VRT
        vrt_filepath = self._combine_rasters_to_vrt(index + 1)
        return vrt_filepath

    def _reproject_layer(
        self, layer: QgsVectorLayer, target_crs: QgsCoordinateReferenceSystem
    ) -> QgsVectorLayer:
        """
        Reproject the given layer to the target CRS and save the reprojected layer to a new GeoPackage, writing features
        to disk as they are processed to avoid memory overflow.

        Args:
            layer (QgsVectorLayer): The input layer to be reprojected.
            target_crs (QgsCoordinateReferenceSystem): The target CRS for the reprojection.

        Returns:
            QgsVectorLayer: A new layer that has been reprojected and saved to the working directory GeoPackage.
        """
        QgsMessageLog.logMessage(
            f"Reprojecting {layer.name()} to {target_crs.authid()}",
            tag="Geest",
            level=Qgis.Info,
        )

        # Define the output GPKG path
        output_layer_name = f"{self.output_prefix}_{layer.name()}_reprojected"
        output_gpkg_path = os.path.join(
            self.workflow_directory, f"{self.output_prefix}_reprojected_layers.gpkg"
        )

        # Remove the GeoPackage if it already exists
        if os.path.exists(output_gpkg_path):
            os.remove(output_gpkg_path)

        # Get the WKB type of the input layer
        geometry_type = layer.wkbType()

        # Create the output layer with the correct CRS
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.fileEncoding = "UTF-8"
        options.layerName = output_layer_name

        writer = QgsVectorFileWriter.create(
            fileName=output_gpkg_path,
            fields=layer.fields(),
            geometryType=geometry_type,
            srs=target_crs,
            transformContext=QgsCoordinateTransformContext(),
            options=options,
        )
        if writer.hasError() != QgsVectorFileWriter.NoError:
            QgsMessageLog.logMessage(
                f"Error when creating layer: {writer.errorMessage()}",
                tag="Geest",
                level=Qgis.Critical,
            )
            raise QgsProcessingException(
                f"Failed to create output layer: {writer.errorMessage()}"
            )

        # Set up the transformation object
        transform = QgsCoordinateTransform(
            layer.crs(), target_crs, QgsProject.instance()
        )
        QgsMessageLog.logMessage(
            f"Transforming from {layer.crs().authid()} to {target_crs.authid()}",
            tag="Geest",
            level=Qgis.Info,
        )

        # Iterate through features, reproject their geometries, and write them directly to disk
        for feature in layer.getFeatures():
            geom = QgsGeometry(feature.geometry())  # Make a copy of the geometry
            geom.transform(transform)  # Transform the copied geometry

            new_feature = QgsFeature(feature)  # Make a copy of the feature
            new_feature.setGeometry(
                geom
            )  # Set the reprojected geometry to the new feature

            # Write the feature directly to disk
            writer.addFeature(new_feature)

        del writer  # Finalize the writer and close the file

        QgsMessageLog.logMessage(
            f"Reprojection of {layer.name()} completed. Saved to {output_gpkg_path}",
            tag="Geest",
            level=Qgis.Info,
        )

        # Return the reprojected layer loaded from the GPKG
        reprojected_layer = QgsVectorLayer(
            f"{output_gpkg_path}|layername={output_layer_name}",
            output_layer_name,
            "ogr",
        )
        if not reprojected_layer.isValid():
            QgsMessageLog.logMessage(
                f"Failed to load reprojected layer from {output_gpkg_path}.",
                tag="Geest",
                level=Qgis.Critical,
            )
            raise QgsProcessingException(
                "Reprojected layer is invalid or the CRS is not recognized."
            )

        return reprojected_layer

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
            "Polygons per Cell Select Polygons Started", tag="Geest", level=Qgis.Info
        )
        output_path = os.path.join(self.workflow_directory, f"{output_name}.shp")

        # Get the WKB type (geometry type) of the input layer (e.g., Point, LineString, Polygon)
        geometry_type = layer.wkbType()

        # Determine geometry type name based on input layer's geometry
        if QgsWkbTypes.geometryType(geometry_type) == QgsWkbTypes.PolygonGeometry:
            geometry_name = "Polygon"
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
            f"Polygons per Cell writing {len(selected_features)} features",
            tag="Geest",
            level=Qgis.Info,
        )

        # Save the memory layer to a file for persistence
        QgsVectorFileWriter.writeAsVectorFormat(
            temp_layer, output_path, "UTF-8", temp_layer.crs(), "ESRI Shapefile"
        )

        QgsMessageLog.logMessage(
            "Polygons per Cell Select Polygons Ending", tag="Geest", level=Qgis.Info
        )

        return QgsVectorLayer(output_path, output_name, "ogr")

    def _assign_reclassification_to_polygons(
        self, layer: QgsVectorLayer
    ) -> QgsVectorLayer:
        """
        Assign reclassification values to polygons based on their perimeter length.

        A value is assigned according to the perimeter thresholds:
        - Very large blocks: value = 1 (perimeter > 1000)
        - Large blocks: value = 2 (751 <= perimeter <= 1000)
        - Moderate blocks: value = 3 (501 <= perimeter <= 750)
        - Small blocks: value = 4 (251 <= perimeter <= 500)
        - Very small blocks: value = 5 (0 < perimeter <= 250)
        - No intersection or invalid: value = 0

        Args:
            layer (QgsVectorLayer): The input polygon layer.

        Returns:
            QgsVectorLayer: The updated polygon layer with reclassification values assigned.
        """

        with edit(layer):  # Allow editing of the layer
            # Check if the 'value' field exists, if not, create it
            if layer.fields().indexFromName("value") == -1:
                layer.dataProvider().addAttributes([QgsField("value", QVariant.Int)])
                layer.updateFields()
            for feature in layer.getFeatures():
                perimeter = (
                    feature.geometry().length()
                )  # Calculate the perimeter of the polygon

                QgsMessageLog.logMessage(
                    f"Perimeter of polygon {feature.id()}: {perimeter}",
                    tag="Geest",
                    level=Qgis.Info,
                )

                # Assign reclassification value based on the perimeter
                if perimeter > 1000:  # Very large blocks
                    reclass_val = 1
                elif 751 <= perimeter <= 1000:  # Large blocks
                    reclass_val = 2
                elif 501 <= perimeter <= 750:  # Moderate blocks
                    reclass_val = 3
                elif 251 <= perimeter <= 500:  # Small blocks
                    reclass_val = 4
                elif 0 < perimeter <= 250:  # Very small blocks
                    reclass_val = 5
                else:
                    reclass_val = 0  # No valid perimeter or no intersection

                feature.setAttribute("value", reclass_val)  # Set the 'value' field
                layer.updateFeature(
                    feature
                )  # Update the feature with the new attribute

        return layer

    def _rasterize_polygons(
        self, polygon_layer: QgsVectorLayer, bbox: QgsGeometry, index: int
    ) -> str:
        """

        ⭐️🚩⭐️ Warning this is not DRY - almost same function exists in study_area.py

        Rasterize the grid layer based on the 'value' attribute.

        Args:
            grid_layer (QgsVectorLayer): The grid layer to rasterize.
            bbox (QgsGeometry): The bounding box for the raster extents.
            index (int): The current index used for naming the output raster.

        Returns:
            str: The file path to the rasterized output.
        """
        QgsMessageLog.logMessage("--- Rasterizing grid", tag="Geest", level=Qgis.Info)
        QgsMessageLog.logMessage(f"--- bbox {bbox}", tag="Geest", level=Qgis.Info)
        QgsMessageLog.logMessage(f"--- index {index}", tag="Geest", level=Qgis.Info)

        output_path = os.path.join(
            self.workflow_directory,
            f"{self.output_prefix}_features_per_cell_output_{index}.tif",
        )

        # Ensure resolution parameters are properly formatted as float values
        x_res = 100.0  # 100m pixel size in X direction
        y_res = 100.0  # 100m pixel size in Y direction
        bbox = bbox.boundingBox()
        # Define rasterization parameters for the temporary layer
        params = {
            "INPUT": polygon_layer,
            "FIELD": "value",
            "BURN": -9999,
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
            "INIT": None,
            "INVERT": False,
            "EXTRA": "",
            "OUTPUT": output_path,
        }

        processing.run("gdal:rasterize", params)
        QgsMessageLog.logMessage(
            f"Created grid for Polygons Per Cell: {output_path}",
            tag="Geest",
            level=Qgis.Info,
        )
        return output_path

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
                f"{self.output_prefix}_features_per_cell_output_{i}.tif",
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
                "No valid raster masks found to combine into VRT.",
                tag="Geest",
                level=Qgis.Warning,
            )
            return
        vrt_filepath = os.path.join(
            self.workflow_directory,
            f"{self.output_prefix}_features_per_cell_output_combined.vrt",
        )

        QgsMessageLog.logMessage(
            f"Creating VRT of masks '{vrt_filepath}' layer to the map.",
            tag="Geest",
            level=Qgis.Info,
        )

        if not raster_files:
            QgsMessageLog.logMessage(
                "No raster masks found to combine into VRT.",
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
            "ASSIGN_CRS": None,
            "RESAMPLING": 0,
            "SRC_NODATA": "0",
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
