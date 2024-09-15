import os
import re
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QPushButton,
    QHBoxLayout,
    QFileDialog,
    QMessageBox,
)
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox
from qgis.core import (
    QgsMapLayerProxyModel,
    QgsWkbTypes,
    QgsProject,
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
    QgsRectangle,
    QgsFeature,
    QgsGeometry,
    QgsVectorFileWriter,
)
from qgis.PyQt.QtCore import QFileInfo


class GeospatialWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GEEST")
        self.working_dir = ""
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Title
        self.title_label = QLabel(
            "Geospatial Assessment of Women Employment and Business Opportunities in the Renewable Energy Sector",
            self,
        )
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        # Description
        self.description_label = QLabel(
            "With support from the [Canada Clean Energy and Forest Climate Facility (CCEFCFy)], "
            "the [Geospatial Operational Support Team (GOST, DECSC)] launched the project "
            '"Geospatial Assessment of Women Employment and Business Opportunities in the Renewable Energy Sector."',
            self,
        )
        self.description_label.setWordWrap(True)
        layout.addWidget(self.description_label)

        # Study Area Combobox - Filtered to polygon/multipolygon layers
        self.study_area_label = QLabel("Study Area Layer:")
        layout.addWidget(self.study_area_label)

        self.layer_combo = QgsMapLayerComboBox()
        self.layer_combo.setFilters(QgsMapLayerProxyModel.VectorLayer)
        #self.layer_combo.setFilterExpression(
        #    f"geometry_type={QgsWkbTypes.PolygonGeometry} OR geometry_type={QgsWkbTypes.MultiPolygonGeometry}"
        #)
        layout.addWidget(self.layer_combo)

        # Area Name Field ComboBox
        self.area_name_label = QLabel("Area Name Field:")
        layout.addWidget(self.area_name_label)

        self.field_combo = QgsFieldComboBox()  # QgsFieldComboBox for selecting fields
        layout.addWidget(self.field_combo)

        # Link the map layer combo box with the field combo box
        self.layer_combo.layerChanged.connect(self.field_combo.setLayer)

        # Directory Selector for Working Directory
        self.dir_label = QLabel("Working Directory:")
        layout.addWidget(self.dir_label)

        dir_layout = QHBoxLayout()
        self.dir_display = QLabel("/path/to/working/dir")
        self.dir_button = QPushButton("Select Directory")
        self.dir_button.clicked.connect(self.select_directory)
        dir_layout.addWidget(self.dir_display)
        dir_layout.addWidget(self.dir_button)
        layout.addLayout(dir_layout)

        # Text for analysis preparation
        self.preparation_label = QLabel(
            "After selecting your study area layer, we will prepare the analysis region."
        )
        layout.addWidget(self.preparation_label)

        # Continue Button
        self.continue_button = QPushButton("Continue")
        self.continue_button.clicked.connect(self.on_continue)
        layout.addWidget(self.continue_button)

        self.setLayout(layout)

    def select_directory(self):
        """Opens a file dialog to select the working directory."""
        directory = QFileDialog.getExistingDirectory(self, "Select Working Directory")
        if directory:
            self.working_dir = directory
            self.dir_display.setText(directory)

    def on_continue(self):
        """Triggered when the Continue button is pressed. Handles analysis preparation."""
        # Ensure a study layer and working directory are selected
        layer = self.layer_combo.currentLayer()
        if not layer:
            QMessageBox.critical(self, "Error", "Please select a study area layer.")
            return

        if not self.working_dir:
            QMessageBox.critical(self, "Error", "Please select a working directory.")
            return

        # Validate that the area name field exists
        field_name = self.field_combo.currentField()  # Get the selected field name
        if not field_name or field_name not in layer.fields().names():
            QMessageBox.critical(
                self, "Error", f"Invalid area name field '{field_name}'."
            )
            return

        # Create the subdirectory 'study_area'
        study_area_dir = os.path.join(self.working_dir, "study_area")
        if not os.path.exists(study_area_dir):
            os.makedirs(study_area_dir)

        # Deconstruct polygons into parts and process each
        features = layer.getFeatures()
        for feature in features:
            geom = feature.geometry()

            # Get area name and normalize for file names
            area_name = feature[field_name]
            normalized_name = re.sub(r"\s+", "_", area_name.lower())

            # Calculate bounding box and ensure it's a multiple of 100m
            bbox = geom.boundingBox()
            bbox_100m = self.create_bbox_multiple_100m(bbox)

            # Save the bounding box as a GeoJSON file
            bbox_file = os.path.join(study_area_dir, f"{normalized_name}.geojson")
            self.save_bbox_to_geojson(bbox_100m, bbox_file, area_name)

            # Generate and save the 100m grid
            grid_file = os.path.join(study_area_dir, f"{normalized_name}_grid.geojson")
            self.create_and_save_grid(bbox_100m, grid_file)

        # Add the created layers to QGIS in a new layer group
        self.add_layers_to_qgis(study_area_dir)

    def create_bbox_multiple_100m(self, bbox):
        """Adjusts bounding box dimensions to be a multiple of 100m."""
        # Convert coordinates to EPSG:3857 (meters)
        crs = QgsCoordinateReferenceSystem("EPSG:3857")
        bbox = bbox.reproject(crs)

        # Adjust bbox dimensions to be exact multiples of 100m
        def make_multiple(val, mult):
            return mult * round(val / mult)

        x_min = make_multiple(bbox.xMinimum(), 100)
        y_min = make_multiple(bbox.yMinimum(), 100)
        x_max = make_multiple(bbox.xMaximum(), 100)
        y_max = make_multiple(bbox.yMaximum(), 100)

        return QgsRectangle(x_min, y_min, x_max, y_max)

    def save_bbox_to_geojson(self, bbox, filepath, area_name):
        """Saves the bounding box to a GeoJSON file with the area name as an attribute."""
        # Create vector layer for the bounding box
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
        """Creates a 100m grid over the bounding box and saves it to a GeoJSON file."""
        grid_layer = QgsGridGenerator.createGridLayer(
            bbox, 100, 100, QgsCoordinateReferenceSystem("EPSG:3857")
        )
        QgsVectorFileWriter.writeAsVectorFormat(
            grid_layer, filepath, "utf-8", driverName="GeoJSON"
        )

    def add_layers_to_qgis(self, directory):
        """Adds the generated layers to QGIS in a new layer group."""
        group = QgsProject.instance().layerTreeRoot().addGroup("study area")

        for file in os.listdir(directory):
            if file.endswith(".geojson"):
                layer = QgsVectorLayer(
                    os.path.join(directory, file), QFileInfo(file).baseName(), "ogr"
                )
                QgsProject.instance().addMapLayer(layer, False)
                group.addLayer(layer)
