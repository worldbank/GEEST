import os
import re
from typing import List, Optional
from qgis.core import (
    QgsRectangle,
    QgsFeature,
    QgsGeometry,
    QgsField,
    QgsProject,
    QgsCoordinateTransform,
    QgsCoordinateReferenceSystem,
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
        :param mode: Processing mode, either 'vector' or 'raster'.
        :param epsg_code: Optional EPSG code for the output CRS. If None, a UTM zone is calculated based on layer extent.
        """
        self.layer: QgsVectorLayer = layer
        self.field_name: str = field_name
        self.working_dir: str = working_dir
        self.mode: str = mode
        self.gpkg_path: str = os.path.join(self.working_dir, "study_area.gpkg")
        self.create_study_area_directory(self.working_dir)

        # Determine the correct CRS for output based on optional EPSG code or UTM zone calculation
        if epsg_code is None:
            layer_bbox: QgsRectangle = self.layer.extent()
            self.epsg_code: int = self.calculate_utm_zone(layer_bbox)
        else:
            self.epsg_code: int = epsg_code

        self.output_crs: QgsCoordinateReferenceSystem = QgsCoordinateReferenceSystem(
            f"EPSG:{self.epsg_code}"
        )

    def create_study_area_directory(self, working_dir: str) -> str:
        """
        Creates the 'study_area' directory if it does not exist.

        :param working_dir: The working directory path.
        :return: The path to the created or existing study_area directory.
        """
        study_area_dir: str = os.path.join(working_dir, "study_area")
        if not os.path.exists(study_area_dir):
            try:
                os.makedirs(study_area_dir)
            except Exception as e:
                raise (f"Error creating directory: {e}")
        return study_area_dir

    def process_study_area(self) -> None:
        """
        Processes each feature in the input layer, creating bounding boxes and grids.
        It handles the CRS transformation and calls appropriate processing functions based on geometry type.
        """
        selected_features = self.layer.selectedFeatures()
        features = selected_features if selected_features else self.layer.getFeatures()

        crs_src: QgsCoordinateReferenceSystem = self.layer.crs()
        transform: QgsCoordinateTransform = QgsCoordinateTransform(
            crs_src, self.output_crs, QgsProject.instance()
        )

        for feature in features:
            geom: QgsGeometry = feature.geometry()
            area_name: str = feature[self.field_name]
            normalized_name: str = re.sub(r"\s+", "_", area_name.lower())

            try:
                # Transform geometry to the correct CRS once at the start
                geom.transform(transform)

                if not geom.isEmpty() and geom.isGeosValid():
                    if geom.isMultipart():
                        self.process_multipart_geometry(
                            geom, normalized_name, area_name
                        )
                    else:
                        self.process_singlepart_geometry(
                            geom, normalized_name, area_name
                        )
                else:
                    QgsMessageLog.logMessage(
                        f"Invalid geometry for feature {feature.id()}. Skipping.",
                        tag="Geest",
                        level=Qgis.Critical,
                    )
            except Exception as e:
                QgsMessageLog.logMessage(
                    f"Error transforming geometry for feature {feature.id()}: {e}",
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
        bbox: QgsRectangle = self.grid_aligned_bbox(geom.boundingBox())
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

        if self.mode == "vector":
            self.create_and_save_grid(geom, bbox)
        elif self.mode == "raster":
            self.create_raster_mask(geom, normalized_name)

    def process_multipart_geometry(
        self, geom: QgsGeometry, normalized_name: str, area_name: str
    ) -> None:
        """
        Processes each part of a multipart geometry, creating vector grids or raster masks based on mode.

        :param geom: Geometry of the multipart feature.
        :param normalized_name: Name normalized for file storage.
        :param area_name: Name of the study area.
        """
        parts: List[QgsGeometry] = geom.asGeometryCollection()

        for part_index, part in enumerate(parts):
            bbox: QgsRectangle = self.grid_aligned_bbox(part.boundingBox())
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

            if self.mode == "vector":
                self.create_and_save_grid(part, bbox)
            elif self.mode == "raster":
                self.create_raster_mask(part, f"{normalized_name}_part{part_index}")

    def create_raster_mask(self, geom: QgsGeometry, mask_name: str) -> None:
        """
        Creates a 1-bit raster mask for a single geometry.

        :param geom: Geometry to be rasterized.
        :param mask_name: Name for the output raster file.
        """
        bbox: QgsRectangle = geom.boundingBox()
        aligned_bbox: QgsRectangle = self.grid_aligned_bbox(bbox)

        mask_filepath: str = os.path.join(
            self.working_dir, "study_area", f"{mask_name}.tif"
        )

        params = {
            "INPUT": self.layer,
            "FIELD": self.field_name,
            "BURN": 1,
            "UNITS": 0,
            "WIDTH": 100,
            "HEIGHT": 100,
            "EXTENT": aligned_bbox,
            "NODATA": 0,
            "OUTPUT": mask_filepath,
        }

        processing.run("gdal:rasterize", params)
        QgsMessageLog.logMessage(
            f"Created raster mask: {mask_filepath}", tag="Geest", level=Qgis.Info
        )

    def create_and_save_grid(self, geom: QgsGeometry, bbox: QgsRectangle) -> None:
        """
        Creates a 100m grid over a geometry and saves it to a GeoPackage.

        :param geom: Geometry over which the grid will be generated.
        :param bbox: Bounding box aligned to the grid.
        """
        grid_layer_name: str = "study_area_grid"
        grid_fields: List[QgsField] = [QgsField("id", QVariant.Int)]

        # Create layer if not exists
        self.create_layer_if_not_exists(
            grid_layer_name, grid_fields, QgsWkbTypes.Polygon
        )

        x_min, y_min, x_max, y_max = (
            bbox.xMinimum(),
            bbox.yMinimum(),
            bbox.xMaximum(),
            bbox.yMaximum(),
        )
        step: int = 100  # Grid size in meters
        feature_id: int = 0
        feature_batch: List[QgsFeature] = []

        gpkg_layer_path: str = f"{self.gpkg_path}|layername={grid_layer_name}"
        gpkg_layer: QgsVectorLayer = QgsVectorLayer(
            gpkg_layer_path, grid_layer_name, "ogr"
        )

        if not gpkg_layer.isValid():
            QgsMessageLog.logMessage(
                f"Failed to access layer '{grid_layer_name}' in the GeoPackage.",
                tag="Geest",
                level=Qgis.Critical,
            )
            return

        provider = gpkg_layer.dataProvider()

        for x in range(int(x_min), int(x_max), step):
            for y in range(int(y_min), int(y_max), step):
                rect: QgsRectangle = QgsRectangle(x, y, x + step, y + step)
                grid_geom: QgsGeometry = QgsGeometry.fromRect(rect)

                if grid_geom.intersects(geom):
                    feature: QgsFeature = QgsFeature()
                    feature.setGeometry(grid_geom)
                    feature.setAttributes([feature_id])
                    feature_batch.append(feature)
                    feature_id += 1

        provider.addFeatures(feature_batch)
        gpkg_layer.updateExtents()

    def grid_aligned_bbox(self, bbox: QgsRectangle) -> QgsRectangle:
        """
        Adjusts bounding box dimensions to align with a 100m grid.

        :param bbox: The bounding box to be aligned.
        :return: A new bounding box aligned to the grid.
        """
        x_min = self.align_to_grid(bbox.xMinimum(), 100)
        y_min = self.align_to_grid(bbox.yMinimum(), 100)
        x_max = self.align_to_grid(bbox.xMaximum(), 100, snap_up=True)
        y_max = self.align_to_grid(bbox.yMaximum(), 100, snap_up=True)
        return QgsRectangle(x_min, y_min, x_max, y_max)

    def align_to_grid(
        self, coord: float, grid_size: int, snap_up: bool = False
    ) -> float:
        """
        Aligns a coordinate to the nearest multiple of grid_size.

        :param coord: Coordinate value to align.
        :param grid_size: Grid size to align to.
        :param snap_up: If True, rounds up; otherwise, rounds down.
        :return: Aligned coordinate.
        """
        if snap_up:
            return (
                coord + (grid_size - (coord % grid_size))
                if coord % grid_size != 0
                else coord
            )
        return coord - (coord % grid_size)

    def save_to_geopackage(
        self,
        features: List[QgsFeature],
        layer_name: str,
        fields: List[QgsField],
        geometry_type: QgsWkbTypes.Type,
    ) -> None:
        """
        Saves features to a GeoPackage, creating the layer if necessary.

        :param features: List of features to save.
        :param layer_name: Name of the layer in the GeoPackage.
        :param fields: Fields to define in the layer.
        :param geometry_type: The type of geometry in the layer.
        """
        self.create_layer_if_not_exists(layer_name, fields, geometry_type)
        self.append_to_layer(layer_name, features)

    def append_to_layer(self, layer_name: str, features: List[QgsFeature]) -> None:
        """
        Appends features to an existing layer in the GeoPackage.

        :param layer_name: Name of the layer to append features to.
        :param features: List of features to append.
        """
        gpkg_layer_path: str = f"{self.gpkg_path}|layername={layer_name}"
        gpkg_layer: QgsVectorLayer = QgsVectorLayer(gpkg_layer_path, layer_name, "ogr")

        if gpkg_layer.isValid():
            QgsMessageLog.logMessage(
                f"Appending to existing layer: {layer_name}",
                tag="Geest",
                level=Qgis.Info,
            )
            provider = gpkg_layer.dataProvider()
            provider.addFeatures(features)
            gpkg_layer.updateExtents()

    def create_layer_if_not_exists(
        self, layer_name: str, fields: List[QgsField], geometry_type: QgsWkbTypes.Type
    ) -> None:
        """
        Creates a new layer in the GeoPackage if it doesn't already exist.

        :param layer_name: Name of the layer to create.
        :param fields: Fields to define in the layer.
        :param geometry_type: The type of geometry in the layer.
        """
        gpkg_layer_path: str = f"{self.gpkg_path}|layername={layer_name}"
        layer: QgsVectorLayer = QgsVectorLayer(gpkg_layer_path, layer_name, "ogr")

        if not layer.isValid():
            crs: QgsCoordinateReferenceSystem = self.output_crs
            options: QgsVectorFileWriter.SaveVectorOptions = (
                QgsVectorFileWriter.SaveVectorOptions()
            )
            options.driverName = "GPKG"
            options.fileEncoding = "UTF-8"
            options.layerName = layer_name
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

            qgs_fields: QgsFields = QgsFields()
            for field in fields:
                qgs_fields.append(field)

            QgsVectorFileWriter.create(
                fileName=self.gpkg_path,
                fields=qgs_fields,
                geometryType=geometry_type,
                srs=crs,
                transformContext=QgsCoordinateTransformContext(),
                options=options,
            )

    def calculate_utm_zone(self, bbox: QgsRectangle) -> int:
        """
        Calculates the UTM zone based on the centroid of the bounding box.

        :param bbox: Bounding box to calculate the UTM zone for.
        :return: The EPSG code for the UTM zone.
        """
        centroid: QgsPointXY = bbox.center()
        lon: float = centroid.x()
        lat: float = centroid.y()

        utm_zone: int = int((lon + 180) / 6) + 1
        if lat >= 0:
            return 32600 + utm_zone  # Northern Hemisphere
        else:
            return 32700 + utm_zone  # Southern Hemisphere

    def add_layers_to_qgis(self) -> None:
        """
        Adds the generated layers from the GeoPackage to QGIS.
        """
        group = QgsProject.instance().layerTreeRoot().addGroup("study area")

        for layer_name in ["study_area_bboxes", "study_area_grid"]:
            layer: QgsVectorLayer = QgsVectorLayer(
                f"{self.gpkg_path}|layername={layer_name}", layer_name, "ogr"
            )
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer, False)
                group.addLayer(layer)
