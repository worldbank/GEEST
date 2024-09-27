import os
import re
import glob
from typing import List, Optional
from qgis.core import (
    QgsRectangle,
    QgsFeature,
    QgsGeometry,
    QgsField,
    QgsProject,
    QgsCoordinateTransform,
    QgsCoordinateReferenceSystem,
    QgsRasterLayer,
    QgsWkbTypes,
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsFields,
    QgsCoordinateTransformContext,
    QgsMessageLog,
    Qgis,
)
from qgis.PyQt.QtCore import QVariant
import processing  # QGIS processing toolbox


class StudyAreaProcessor:
    def __init__(
        self,
        layer: QgsVectorLayer,
        field_name: str,
        working_dir: str,
        mode: str = "raster",
        epsg_code: Optional[int] = None,
    ):
        """
        Initializes the StudyAreaProcessor class.

        :param layer: The vector layer containing study area features.
        :param field_name: The name of the field containing area names.
        :param working_dir: Directory path where outputs will be saved.
        :param mode: Processing mode, either 'vector' or 'raster'. Default is raster.
        :param epsg_code: Optional EPSG code for the output CRS. If None, a UTM zone
                          is calculated based on layer extent or extent of selected features.
        """
        self.layer: QgsVectorLayer = layer
        self.field_name: str = field_name
        self.working_dir: str = working_dir
        self.mode: str = mode
        self.gpkg_path: str = os.path.join(self.working_dir, "study_area", "study_area.gpkg")

        # Remove the GeoPackage if it already exists to start with a clean state
        if os.path.exists(self.gpkg_path):
            try:
                os.remove(self.gpkg_path)
                QgsMessageLog.logMessage(
                    f"Existing GeoPackage removed: {self.gpkg_path}", tag="Geest", level=Qgis.Info
                )
            except Exception as e:
                QgsMessageLog.logMessage(
                    f"Error removing existing GeoPackage: {e}", tag="Geest", level=Qgis.Critical
                )

        self.create_study_area_directory(self.working_dir)

        # Determine the correct CRS and layer bounding box based on selected features
        selected_features = self.layer.selectedFeatures()

        if selected_features:
            # Calculate bounding box based on selected features only
            self.layer_bbox: QgsRectangle = QgsRectangle()
            for feature in selected_features:
                self.layer_bbox.combineExtentWith(feature.geometry().boundingBox())
        else:
            # No features selected, use full layer extent
            self.layer_bbox: QgsRectangle = self.layer.extent()

        # Determine EPSG code based on provided input or calculated UTM zone
        if epsg_code is None:
            self.epsg_code: int = self.calculate_utm_zone(self.layer_bbox)
        else:
            self.epsg_code: int = epsg_code

        self.output_crs: QgsCoordinateReferenceSystem = QgsCoordinateReferenceSystem(
            f"EPSG:{self.epsg_code}"
        )
        QgsMessageLog.logMessage(
            f"Project CRS Set to: EPSG:{self.epsg_code}", tag="Geest", level=Qgis.Info
        )

        # Reproject and align the transformed layer_bbox to a 100m grid and output crs
        self.layer_bbox = self.grid_aligned_bbox(self.layer_bbox)

    def process_study_area(self) -> None:
        """
        Processes each feature in the input layer, creating bounding boxes and grids.
        It handles the CRS transformation and calls appropriate processing functions based on geometry type.
        """
        # First, write the layer_bbox to the GeoPackage
        study_area_bbox_feature = QgsFeature()
        study_area_bbox_feature.setGeometry(QgsGeometry.fromRect(self.layer_bbox))
        study_area_bbox_feature.setAttributes(["Layer Bounding Box"])

        self.save_to_geopackage(
            [study_area_bbox_feature],
            "study_area_bbox",
            [QgsField("area_name", QVariant.String)],
            QgsWkbTypes.Polygon,
        )

        # Add the study_area_bbox layer to the map
        self.add_layer_to_map("study_area_bbox")

        # Initialize counters for tracking valid and invalid features
        invalid_feature_count = 0
        valid_feature_count = 0
        fixed_feature_count = 0

        # Process individual features
        selected_features = self.layer.selectedFeatures()
        features = selected_features if selected_features else self.layer.getFeatures()

        for feature in features:
            geom: QgsGeometry = feature.geometry()
            area_name: str = feature[self.field_name]
            normalized_name: str = re.sub(r"\s+", "_", area_name.lower())

            # Check for geometry validity
            if geom.isEmpty() or not geom.isGeosValid():
                QgsMessageLog.logMessage(
                    f"Feature ID {feature.id()} has an invalid geometry. Attempting to fix.",
                    tag="Geest",
                    level=Qgis.Warning,
                )

                # Try to fix the geometry
                fixed_geom = geom.makeValid()

                # Check if the fixed geometry is valid
                if fixed_geom.isEmpty() or not fixed_geom.isGeosValid():
                    invalid_feature_count += 1
                    QgsMessageLog.logMessage(
                        f"Feature ID {feature.id()} could not be fixed. Skipping.",
                        tag="Geest",
                        level=Qgis.Critical,
                    )
                    continue

                # Use the fixed geometry if it is valid
                geom = fixed_geom
                fixed_feature_count += 1
                QgsMessageLog.logMessage(
                    f"Feature ID {feature.id()} geometry fixed successfully.",
                    tag="Geest",
                    level=Qgis.Info,
                )

            # Process valid geometry
            try:
                valid_feature_count += 1
                if geom.isMultipart():
                    self.process_multipart_geometry(geom, normalized_name, area_name)
                else:
                    self.process_singlepart_geometry(geom, normalized_name, area_name)

            except Exception as e:
                # Log any unexpected errors during processing
                invalid_feature_count += 1
                QgsMessageLog.logMessage(
                    f"Error processing geometry for feature {feature.id()}: {e}",
                    tag="Geest",
                    level=Qgis.Critical,
                )

        # Log the count of valid, fixed, and invalid features processed
        QgsMessageLog.logMessage(
            f"Processing completed. Valid features: {valid_feature_count}, Fixed features: {fixed_feature_count}, Invalid features: {invalid_feature_count}",
            tag="Geest",
            level=Qgis.Info,
        )

        # Add the 'study_area_bboxes' layer to the QGIS map after processing is complete
        self.add_layer_to_map("study_area_bboxes")
        self.add_layer_to_map("study_area_polygons")

        # Create and add the VRT of all generated raster masks if in raster mode
        if self.mode == "raster":
            self.create_raster_vrt()


    def add_layer_to_map(self, layer_name: str) -> None:
        """
        Adds the specified layer from the GeoPackage to the QGIS map.

        :param layer_name: Name of the layer to add from the GeoPackage.
        """
        gpkg_layer_path = f"{self.gpkg_path}|layername={layer_name}"
        layer = QgsVectorLayer(gpkg_layer_path, layer_name, "ogr")

        if layer.isValid():
            QgsProject.instance().addMapLayer(layer)
            QgsMessageLog.logMessage(
                f"Added '{layer_name}' layer to the map.",
                tag="Geest",
                level=Qgis.Info,
            )
        else:
            QgsMessageLog.logMessage(
                f"Failed to add '{layer_name}' layer to the map.",
                tag="Geest",
                level=Qgis.Critical,
            )

    def process_singlepart_geometry(
        self, geom: QgsGeometry, normalized_name: str, area_name: str
    ) -> None:
        """
        Processes a singlepart geometry feature. Creates vector grids or raster masks based on mode.

        :param geom: Geometry of the feature.
        :param normalized_name: Name normalized for file storage.
        :param area_name: Name of the study area.
        """
       
        # Compute the aligned bounding box based on the transformed geometry
        # This will do the CRS transform too
        bbox: QgsRectangle = self.grid_aligned_bbox(geom.boundingBox())

        # Create a feature for the aligned bounding box
        study_area_feature: QgsFeature = QgsFeature()
        study_area_feature.setGeometry(QgsGeometry.fromRect(bbox))
        study_area_feature.setAttributes([area_name])        
        # Always save the study area bounding boxes regardless of mode
        self.save_to_geopackage(
            [study_area_feature],
            "study_area_bboxes",
            [QgsField("area_name", QVariant.String)],
            QgsWkbTypes.Polygon,
        )
               
        # Transform the geometry to the output CRS
        crs_src: QgsCoordinateReferenceSystem = self.layer.crs()
        transform: QgsCoordinateTransform = QgsCoordinateTransform(
            crs_src, self.output_crs, QgsProject.instance()
        )
        geom.transform(transform)

        # Create a feature for the original part
        study_area_polygon: QgsFeature = QgsFeature()
        study_area_polygon.setGeometry(geom)
        study_area_polygon.setAttributes([area_name])        
        # Always save the study area bounding boxes regardless of mode
        self.save_to_geopackage(
            [study_area_polygon],
            "study_area_polygons",
            [QgsField("area_name", QVariant.String)],
            QgsWkbTypes.Polygon,
        )


        # Process the geometry based on the selected mode
        if self.mode == "vector":
            QgsMessageLog.logMessage(
                f"Creating vector grid for {normalized_name}.",
                tag="Geest",
                level=Qgis.Info,
            )            
            self.create_and_save_grid(geom, bbox)
        elif self.mode == "raster":
            QgsMessageLog.logMessage(
                f"Creating raster mask for {normalized_name}.",
                tag="Geest",
                level=Qgis.Info,
            )
            self.create_raster_mask(geom, bbox, normalized_name)

    def process_multipart_geometry(
        self, geom: QgsGeometry, normalized_name: str, area_name: str
    ) -> None:
        """
        Processes each part of a multipart geometry by exploding the parts and delegating 
        to process_singlepart_geometry, ensuring the part index is included in the output name.

        :param geom: Geometry of the multipart feature.
        :param normalized_name: Name normalized for file storage.
        :param area_name: Name of the study area.
        """
        parts: List[QgsGeometry] = geom.asGeometryCollection()

        # Iterate over each part and delegate to process_singlepart_geometry
        for part_index, part in enumerate(parts):
            # Create a unique name for the part by appending the part index
            part_normalized_name = f"{normalized_name}_part{part_index}"

            # Delegate to process_singlepart_geometry
            self.process_singlepart_geometry(part, part_normalized_name, area_name)

    def grid_aligned_bbox(self, bbox: QgsRectangle) -> QgsRectangle:
        """
        Transforms and aligns the bounding box to a 100m grid in the output CRS.
        The alignment ensures that the bbox aligns with the study area grid, offset by an exact multiple of 100m.

        :param bbox: The bounding box to be aligned, in the CRS of the input layer.
        :return: A new bounding box aligned to the grid, in the output CRS.
        """
        # Transform the bounding box to the output CRS
        crs_src: QgsCoordinateReferenceSystem = self.layer.crs()
        transform: QgsCoordinateTransform = QgsCoordinateTransform(
            crs_src, self.output_crs, QgsProject.instance()
        )
        bbox_transformed = transform.transformBoundingBox(bbox)

        # Align the bounding box to a grid aligned at 100m intervals, offset by the study area origin
        study_area_origin_x = int(self.layer_bbox.xMinimum() // 100) * 100
        study_area_origin_y = int(self.layer_bbox.yMinimum() // 100) * 100

        # Align bbox to the grid based on the study area origin
        x_min = study_area_origin_x + int((bbox_transformed.xMinimum() - study_area_origin_x) // 100) * 100
        y_min = study_area_origin_y + int((bbox_transformed.yMinimum() - study_area_origin_y) // 100) * 100
        x_max = study_area_origin_x + (int((bbox_transformed.xMaximum() - study_area_origin_x) // 100) + 1) * 100
        y_max = study_area_origin_y + (int((bbox_transformed.yMaximum() - study_area_origin_y) // 100) + 1) * 100

        # Return the aligned bbox in the output CRS
        return QgsRectangle(x_min, y_min, x_max, y_max)


    def save_to_geopackage(self, features: List[QgsFeature], layer_name: str, fields: List[QgsField], geometry_type: QgsWkbTypes) -> None:
        """
        Save features to GeoPackage. Create or append the layer as necessary.

        :param features: List of features to save.
        :param layer_name: Name of the layer in the GeoPackage.
        :param fields: Fields for the layer.
        :param geometry_type: Geometry type for the layer.
        """
        self.create_layer_if_not_exists(layer_name, fields, geometry_type)
        self.append_to_layer(layer_name, features)

    def append_to_layer(self, layer_name: str, features: List[QgsFeature]) -> None:
        """
        Append features to an existing layer in the GeoPackage.

        :param layer_name: Name of the layer in the GeoPackage.
        :param features: List of features to append.
        """
        gpkg_layer_path = f"{self.gpkg_path}|layername={layer_name}"
        gpkg_layer = QgsVectorLayer(gpkg_layer_path, layer_name, "ogr")

        if gpkg_layer.isValid():
            QgsMessageLog.logMessage(f"Appending to existing layer: {layer_name}", tag="Geest", level=Qgis.Info)
            provider = gpkg_layer.dataProvider()
            provider.addFeatures(features)
            gpkg_layer.updateExtents()
        else:
            QgsMessageLog.logMessage(f"Layer '{layer_name}' is not valid for appending.", tag="Geest", level=Qgis.Critical)

    def create_layer_if_not_exists(self, layer_name: str, fields: List[QgsField], geometry_type: QgsWkbTypes) -> None:
        """
        Create a new layer in the GeoPackage if it doesn't already exist.

        :param layer_name: Name of the layer to create.
        :param fields: Fields for the layer.
        :param geometry_type: Geometry type for the layer.
        """
        gpkg_layer_path = f"{self.gpkg_path}|layername={layer_name}"
        layer = QgsVectorLayer(gpkg_layer_path, layer_name, "ogr")
        append = True
        # Check if the GeoPackage file exists
        if not os.path.exists(self.gpkg_path):
            append = False
            QgsMessageLog.logMessage(f"GeoPackage does not exist. Creating: {self.gpkg_path}", tag="Geest", level=Qgis.Info)

        # If the layer doesn't exist, create it
        if not layer.isValid():
            QgsMessageLog.logMessage(f"Layer '{layer_name}' does not exist. Creating it.", tag="Geest", level=Qgis.Info)
            crs = QgsCoordinateReferenceSystem(f"EPSG:{self.epsg_code}")
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = "GPKG"
            options.fileEncoding = "UTF-8"
            options.layerName = layer_name
            if append:
                options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

            # Convert list of QgsField objects to QgsFields object
            qgs_fields = QgsFields()
            for field in fields:
                qgs_fields.append(field)

            # Create a new GeoPackage layer
            QgsVectorFileWriter.create(
                fileName=self.gpkg_path,
                fields=qgs_fields,
                geometryType=geometry_type,
                srs=crs,
                transformContext=QgsCoordinateTransformContext(),
                options=options,
            )

    def create_and_save_grid(self, geom: QgsGeometry, bbox: QgsRectangle) -> None:
        """
        Creates a vector grid over the bounding box of a geometry and streams it directly to the GeoPackage.

        :param geom: Geometry to create grid over.
        :param bbox: Bounding box for the grid.
        """
        grid_layer_name = "study_area_grid"
        grid_fields = [QgsField("id", QVariant.Int)]

        self.create_layer_if_not_exists(grid_layer_name, grid_fields, QgsWkbTypes.Polygon)

        step = 100  # 100m grid cells
        feature_id = 0
        feature_batch = []

        x_min, x_max = bbox.xMinimum(), bbox.xMaximum()
        y_min, y_max = bbox.yMinimum(), bbox.yMaximum()

        # Access the GeoPackage layer to append features
        gpkg_layer_path = f"{self.gpkg_path}|layername={grid_layer_name}"
        gpkg_layer = QgsVectorLayer(gpkg_layer_path, grid_layer_name, "ogr")
        if not gpkg_layer.isValid():
            QgsMessageLog.logMessage(f"Failed to access layer '{grid_layer_name}' in the GeoPackage.", tag="Geest", level=Qgis.Critical)
            return
        
        provider = gpkg_layer.dataProvider()

        # Loop through the grid cells
        for x in range(int(x_min), int(x_max), step):
            for y in range(int(y_min), int(y_max), step):
                rect = QgsRectangle(x, y, x + step, y + step)
                grid_geom = QgsGeometry.fromRect(rect)

                # Check if grid_geom intersects with the geometry
                if grid_geom.intersects(geom):
                    # Create the grid feature
                    feature = QgsFeature()
                    feature.setGeometry(grid_geom)
                    feature.setAttributes([feature_id])
                    feature_batch.append(feature)
                    feature_id += 1

        # Commit the features to the layer
        provider.addFeatures(feature_batch)
        gpkg_layer.updateExtents()

    def create_raster_mask(self, geom: QgsGeometry, aligned_box: QgsRectangle, mask_name: str) -> None:
        """
        Creates a 1-bit raster mask for a single geometry.

        :param geom: Geometry to be rasterized.
        :param aligned_box: Aligned bounding box for the geometry.
        :param mask_name: Name for the output raster file.
        """    
        mask_filepath = os.path.join(self.working_dir, "study_area", f"{mask_name}.tif")

        # Create a memory layer to hold the geometry
        temp_layer = QgsVectorLayer(
            f"Polygon?crs={self.output_crs.authid()}", "temp_mask_layer", "memory"
        )
        temp_layer_data_provider = temp_layer.dataProvider()

        # Define a field to store the mask value
        temp_layer_data_provider.addAttributes([QgsField(self.field_name, QVariant.String)])
        temp_layer.updateFields()

        # Add the geometry to the memory layer
        temp_feature = QgsFeature()
        temp_feature.setGeometry(geom)
        temp_feature.setAttributes(["1"])  # Setting an arbitrary value for the mask
        temp_layer_data_provider.addFeature(temp_feature)

        # Ensure resolution parameters are properly formatted as float values
        x_res = 100.0  # 100m pixel size in X direction
        y_res = 100.0  # 100m pixel size in Y direction

        # Define rasterization parameters for the temporary layer
        params = {
            "INPUT": temp_layer,
            "FIELD": None,
            "BURN": 1,
            "USE_Z": False,
            "UNITS": 1,
            "WIDTH": x_res,
            "HEIGHT": y_res,
            "EXTENT": f"{aligned_box.xMinimum()},{aligned_box.xMaximum()},"
                    f"{aligned_box.yMinimum()},{aligned_box.yMaximum()}",  # Extent of the aligned bbox
            "NODATA": 0,
            "OPTIONS": "",
            "DATA_TYPE": 0, # byte
            "INIT": None,
            "INVERT": False,
            "EXTRA": "-co NBITS=1",
            "OUTPUT": mask_filepath,
        }
        # Run the rasterize algorithm
        processing.run("gdal:rasterize", params)
        QgsMessageLog.logMessage(f"Created raster mask: {mask_filepath}", tag="Geest", level=Qgis.Info)


    def calculate_utm_zone(self, bbox: QgsRectangle) -> int:
        """
        Calculates the UTM zone based on the centroid of the bounding box.
        The calculation is based on transforming the centroid to WGS84 (EPSG:4326).

        :param bbox: The bounding box of the layer.
        :return: The EPSG code for the UTM zone.
        """
        # Get the source CRS (from the input layer)
        crs_src: QgsCoordinateReferenceSystem = self.layer.crs()
        crs_wgs84: QgsCoordinateReferenceSystem = QgsCoordinateReferenceSystem("EPSG:4326")

        # Create the transform object
        transform: QgsCoordinateTransform = QgsCoordinateTransform(
            crs_src, crs_wgs84, QgsProject.instance()
        )

        # Transform the centroid to WGS84
        centroid: QgsPointXY = bbox.center()
        centroid_wgs84 = transform.transform(centroid)

        lon = centroid_wgs84.x()
        lat = centroid_wgs84.y()

        # Calculate the UTM zone based on the longitude
        utm_zone = int((lon + 180) / 6) + 1

        # EPSG code for the UTM zone
        if lat >= 0:
            epsg_code = 32600 + utm_zone  # Northern Hemisphere
        else:
            epsg_code = 32700 + utm_zone  # Southern Hemisphere

        return epsg_code


    def create_study_area_directory(self, working_dir: str) -> None:
        """
        Creates the 'study_area' directory if it doesn't already exist.

        :param working_dir: Path to the working directory.
        """
        study_area_dir = os.path.join(working_dir, "study_area")
        if not os.path.exists(study_area_dir):
            try:
                os.makedirs(study_area_dir)
                QgsMessageLog.logMessage(f"Created study area directory: {study_area_dir}", tag="Geest", level=Qgis.Info)
            except Exception as e:
                QgsMessageLog.logMessage(f"Error creating directory: {e}", tag="Geest", level=Qgis.Critical)


    def create_raster_vrt(self, output_vrt_name: str = "combined_mask.vrt") -> None:
            """
            Creates a VRT file from all generated raster masks and adds it to the QGIS map.

            :param output_vrt_name: The name of the VRT file to create.
            """
            QgsMessageLog.logMessage(
                f"Creating VRT of masks '{output_vrt_name}' layer to the map.",
                tag="Geest",
                level=Qgis.Info,
            )              
            # Directory containing raster masks
            raster_dir = os.path.join(self.working_dir, "study_area")
            raster_files = glob.glob(os.path.join(raster_dir, "*.tif"))

            if not raster_files:
                QgsMessageLog.logMessage("No raster masks found to combine into VRT.", tag="Geest", level=Qgis.Warning)
                return

            vrt_filepath = os.path.join(raster_dir, output_vrt_name)

            # Define the VRT parameters
            params = {
                "INPUT": raster_files,
                "RESOLUTION": 0,  # Use highest resolution among input files
                "SEPARATE": False,  # Combine all input rasters as a single band
                "OUTPUT": vrt_filepath,
                'PROJ_DIFFERENCE':False,
                'ADD_ALPHA':False,
                'ASSIGN_CRS':None,
                'RESAMPLING':0,
                'SRC_NODATA':'0',
                'EXTRA':''
            }

            # Run the gdal:buildvrt processing algorithm to create the VRT
            processing.run("gdal:buildvirtualraster", params)
            QgsMessageLog.logMessage(f"Created VRT: {vrt_filepath}", tag="Geest", level=Qgis.Info)

            # Add the VRT to the QGIS map
            vrt_layer = QgsRasterLayer(vrt_filepath, "Combined Mask VRT")

            if vrt_layer.isValid():
                QgsProject.instance().addMapLayer(vrt_layer)
                QgsMessageLog.logMessage("Added VRT layer to the map.", tag="Geest", level=Qgis.Info)
            else:
                QgsMessageLog.logMessage("Failed to add VRT layer to the map.", tag="Geest", level=Qgis.Critical)
