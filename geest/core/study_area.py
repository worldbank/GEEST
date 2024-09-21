import os
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox
from qgis.core import (
    QgsMapLayerProxyModel,
    QgsFieldProxyModel,
    QgsWkbTypes,
    QgsProject,
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
    QgsRectangle,
    QgsFeature,
    QgsGeometry,
    QgsVectorFileWriter,
    QgsCoordinateTransform,
    QgsField,
)
from qgis.PyQt.QtCore import QFileInfo, QSettings, QVariant
from qgis.PyQt.QtGui import QPixmap
from geest.utilities import resources_path


class StudyAreaProcessor:
    def __init__(self, layer, working_dir):
        self.layer = layer
        self.working_dir = working_dir

    def create_bbox_multiple_100m(self, bbox):
        """Adjusts bounding box dimensions to be a multiple of 100m."""
        crs_src = QgsCoordinateReferenceSystem(self.layer.crs())  # Source CRS
        crs_dst = QgsCoordinateReferenceSystem("EPSG:3857")  # EPSG:3857 (meters)
        transform = QgsCoordinateTransform(crs_src, crs_dst, QgsProject.instance())

        # Transform the bounding box
        x_min, y_min = transform.transform(bbox.xMinimum(), bbox.yMinimum())
        x_max, y_max = transform.transform(bbox.xMaximum(), bbox.yMaximum())

        # Adjust bbox dimensions to be exact multiples of 100m
        def make_multiple(val, mult):
            return mult * round(val / mult)

        x_min = make_multiple(x_min, 100)
        y_min = make_multiple(y_min, 100)
        x_max = make_multiple(x_max, 100)
        y_max = make_multiple(y_max, 100)

        return QgsRectangle(x_min, y_min, x_max, y_max)

    def save_bbox_to_geojson(self, bbox, filepath, area_name):
        """Saves the bounding box to a GeoJSON file."""
        bbox_layer = QgsVectorLayer("Polygon?crs=EPSG:3857", "bbox", "memory")
        provider = bbox_layer.dataProvider()
        bbox_layer.startEditing()
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromRect(bbox))
        feature.setAttributes([area_name])
        provider.addFeatures([feature])
        bbox_layer.commitChanges()

        # Save to file
        QgsVectorFileWriter.writeAsVectorFormat(
            bbox_layer, filepath, "utf-8", driverName="GeoJSON"
        )

    def create_and_save_grid(self, bbox, filepath):
        """Creates a 100m grid over the bounding box and saves it as a GeoJSON file."""
        grid_layer = QgsVectorLayer("Polygon?crs=EPSG:3857", "grid", "memory")
        provider = grid_layer.dataProvider()

        # Set up attributes
        provider.addAttributes([QgsField("id", QVariant.Int)])
        grid_layer.updateFields()

        x_min = bbox.xMinimum()
        x_max = bbox.xMaximum()
        y_min = bbox.yMinimum()
        y_max = bbox.yMaximum()
        step = 100
        feature_id = 0

        for x in range(int(x_min), int(x_max), step):
            for y in range(int(y_min), int(y_max), step):
                rect = QgsRectangle(x, y, x + step, y + step)
                feature = QgsFeature()
                feature.setGeometry(QgsGeometry.fromRect(rect))
                feature.setAttributes([feature_id])
                provider.addFeature(feature)
                feature_id += 1

        grid_layer.updateExtents()

        # Save to file
        QgsVectorFileWriter.writeAsVectorFormat(
            grid_layer, filepath, "utf-8", driverName="GeoJSON"
        )

    def process_multipart_geometry(self, geom, normalized_name, area_name, study_area_dir):
        """Processes each part of a multipart geometry feature."""
        parts = geom.asGeometryCollection()
        part_count = 1
        for part in parts:
            bbox = part.boundingBox()
            bbox_100m = self.create_bbox_multiple_100m(bbox)

            # Save bounding box
            bbox_file = os.path.join(study_area_dir, f"{normalized_name}_{part_count}.geojson")
            self.save_bbox_to_geojson(bbox_100m, bbox_file, area_name)

            # Save grid
            grid_file = os.path.join(study_area_dir, f"{normalized_name}_{part_count}_grid.geojson")
            self.create_and_save_grid(bbox_100m, grid_file)

            part_count += 1

    def add_layers_to_qgis(self, directory):
        """Adds the generated layers to QGIS."""
        group = QgsProject.instance().layerTreeRoot().addGroup("study area")

        for file in os.listdir(directory):
            if file.endswith(".geojson"):
                layer = QgsVectorLayer(
                    os.path.join(directory, file), QFileInfo(file).baseName(), "ogr"
                )
                QgsProject.instance().addMapLayer(layer, False)
                group.addLayer(layer)
