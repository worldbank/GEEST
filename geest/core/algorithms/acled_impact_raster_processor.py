from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCoordinateTransformContext,
    QgsFeature,
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
    Qgis,
)
from qgis.PyQt.QtCore import QVariant
import os
import csv
import processing
from .area_iterator import AreaIterator


class AcledImpactRasterProcessor:
    def __init__(
        self,
        output_prefix: str,
        csv_path: str,
        workflow_directory: str,
        gpkg_path: str,
    ):
        """
        Initializes the AcledImpactRasterProcessor.

        Args:
            output_prefix (str): Prefix for naming output files.
            csv_path (str): The input ACLED event CSV file path.
            workflow_directory (str): Directory where temporary and output files will be stored.
            gpkg_path (str): Path to the GeoPackage containing study areas and bounding boxes.
        """
        self.output_prefix = output_prefix
        self.csv_path = csv_path
        self.workflow_directory = workflow_directory
        self.gpkg_path = gpkg_path

        # Load the CSV and create a point layer
        self.features_layer = self._load_csv_as_point_layer()

        if not self.features_layer.isValid():
            raise QgsProcessingException(
                f"Failed to load features layer from CSV at {self.csv_path}"
            )

        QgsMessageLog.logMessage(
            "ACLED Impact Raster Processor Initialized", tag="Geest", level=Qgis.Info
        )

    def _load_csv_as_point_layer(self) -> QgsVectorLayer:
        """
        Load the CSV file, extract relevant columns (latitude, longitude, event_type),
        create a point layer from the retained columns, reproject the points to match the
        CRS of the layers from the GeoPackage, and save the result as a shapefile.

        Returns:
            QgsVectorLayer: The reprojected point layer created from the CSV.
        """
        # Retrieve CRS from a layer in the GeoPackage to match the points with that CRS
        gpkg_layer = QgsVectorLayer(
            f"{self.gpkg_path}|layername=study_area_polygons", "areas", "ogr"
        )
        if not gpkg_layer.isValid():
            raise QgsProcessingException(
                f"Failed to load GeoPackage layer for CRS retrieval."
            )

        target_crs = gpkg_layer.crs()  # Get the CRS of the GeoPackage layer
        source_crs = QgsCoordinateReferenceSystem(
            "EPSG:4326"
        )  # Assuming the CSV uses WGS84

        # Set up a coordinate transform from WGS84 to the target CRS
        transform_context = QgsProject.instance().transformContext()
        coordinate_transform = QgsCoordinateTransform(
            source_crs, target_crs, transform_context
        )

        # Define fields for the point layer
        fields = QgsFields()
        fields.append(QgsField("event_type", QVariant.String))

        # Create an in-memory point layer in the target CRS
        point_layer = QgsVectorLayer(
            f"Point?crs={target_crs.authid()}", "acled_points", "memory"
        )
        point_provider = point_layer.dataProvider()
        point_provider.addAttributes(fields)
        point_layer.updateFields()

        # Read the CSV and add reprojected points to the layer
        with open(self.csv_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            features = []
            for row in reader:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
                event_type = row["event_type"]

                # Transform point to the target CRS
                point_wgs84 = QgsPointXY(lon, lat)
                point_transformed = coordinate_transform.transform(point_wgs84)

                feature = QgsFeature()
                feature.setGeometry(QgsGeometry.fromPointXY(point_transformed))
                feature.setAttributes([event_type])
                features.append(feature)

            point_provider.addFeatures(features)
            QgsMessageLog.logMessage(
                f"Loaded {len(features)} points from CSV", tag="Geest", level=Qgis.Info
            )
        # Save the layer to disk as a shapefile
        # Ensure the workflow directory exists
        if not os.path.exists(self.workflow_directory):
            os.makedirs(self.workflow_directory)
        shapefile_path = os.path.join(
            self.workflow_directory, f"{self.output_prefix}_acled_points.shp"
        )
        QgsMessageLog.logMessage(
            f"Writing points to {shapefile_path}", tag="Geest", level=Qgis.Info
        )
        error = QgsVectorFileWriter.writeAsVectorFormat(
            point_layer, shapefile_path, "utf-8", target_crs, "ESRI Shapefile"
        )

        if error != QgsVectorFileWriter.NoError:
            raise QgsProcessingException(f"Error saving point layer to disk: {error}")

        QgsMessageLog.logMessage(
            f"Point layer created from CSV saved to {shapefile_path}",
            tag="Geest",
            level=Qgis.Info,
        )

        # Reload the saved shapefile as the final point layer to ensure consistency
        saved_layer = QgsVectorLayer(shapefile_path, "acled_points", "ogr")
        if not saved_layer.isValid():
            raise QgsProcessingException(
                f"Failed to reload saved point layer from {shapefile_path}"
            )

        return saved_layer

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
            "ACLED Impact Raster Processing Started", tag="Geest", level=Qgis.Info
        )

        feedback = QgsProcessingFeedback()
        area_iterator = AreaIterator(self.gpkg_path)

        for index, (current_area, current_bbox, progress) in enumerate(area_iterator):
            feedback.pushInfo(
                f"Processing area {index + 1} with progress {progress:.2f}%"
            )

            # Step 1: Select features that intersect with the current area
            area_features = self._select_features(self.features_layer, current_area)

            if area_features.featureCount() == 0:
                continue

            # Step 2: Buffer the selected features by 5 km
            buffered_layer = self._buffer_features(area_features)

            # Step 3: Assign values based on event_type
            scored_layer = self._assign_scores(buffered_layer)

            # Step 4: Rasterize the scored buffer layer
            raster_output = self._rasterize_layer(scored_layer, current_bbox, index)

        # Combine all area rasters into a VRT
        vrt_filepath = self._combine_rasters_to_vrt(index + 1)

        QgsMessageLog.logMessage(
            f"ACLED Impact Raster Processing Completed. Output VRT: {vrt_filepath}",
            tag="Geest",
            level=Qgis.Info,
        )
        return vrt_filepath

    def _select_features(
        self, layer: QgsVectorLayer, area_geom: QgsGeometry
    ) -> QgsVectorLayer:
        """
        Select features from the input layer that intersect with the provided area geometry.

        Args:
            layer (QgsVectorLayer): The input feature layer.
            area_geom (QgsGeometry): The area geometry to intersect with.

        Returns:
            QgsVectorLayer: A new layer containing the intersecting features.
        """
        # Clip features based on the area geometry
        clipped_layer = processing.run(
            "native:extractbylocation",
            {
                "INPUT": layer,
                "PREDICATE": [0],  # Intersects
                "INTERSECT": area_geom,
                "OUTPUT": "memory:",
            },
        )["OUTPUT"]

        return clipped_layer

    def _buffer_features(self, layer: QgsVectorLayer) -> QgsVectorLayer:
        """
        Buffer the input features by 5 km.

        Args:
            layer (QgsVectorLayer): The input feature layer.

        Returns:
            QgsVectorLayer: The buffered features layer.
        """
        buffered_layer = processing.run(
            "native:buffer",
            {
                "INPUT": layer,
                "DISTANCE": 5000,  # 5 km buffer
                "SEGMENTS": 5,
                "DISSOLVE": False,
                "OUTPUT": "memory:",
            },
        )["OUTPUT"]

        return buffered_layer

    def _assign_scores(self, layer: QgsVectorLayer) -> QgsVectorLayer:
        """
        Assign values to buffered polygons based on their event_type.

        Args:
            layer (QgsVectorLayer): The buffered features layer.

        Returns:
            QgsVectorLayer: A new layer with a "value" field containing the assigned scores.
        """
        # Define scoring categories based on event_type
        event_scores = {
            "Battles": 0,
            "Explosions/Remote violence": 1,
            "Violence against civilians": 2,
            "Protests": 4,
            "Riots": 4,
        }

        # Create a new field in the layer for the scores
        layer.startEditing()
        layer.dataProvider().addAttributes([QgsField("value", QVariant.Int)])
        layer.updateFields()

        # Assign scores based on event_type
        for feature in layer.getFeatures():
            event_type = feature["event_type"]
            score = event_scores.get(event_type, 5)
            feature.setAttribute("value", score)
            layer.updateFeature(feature)

        layer.commitChanges()

        return layer

    def _rasterize_grid(
        self, grid_layer: QgsVectorLayer, bbox: QgsGeometry, index: int
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
            "INPUT": grid_layer,
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
            f"Created grid for Features Per Cell: {output_path}",
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
