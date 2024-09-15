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
    QgsCoordinateTransform,
    QgsField,
)
from qgis.PyQt.QtCore import QFileInfo, QSettings, QVariant


class GeospatialWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GEEST")
        self.working_dir = ""
        self.settings = QSettings()  # Initialize QSettings to store and retrieve settings
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

        # Set the last used working directory from QSettings
        last_used_dir = self.settings.value("last_working_directory", "")
        if last_used_dir and os.path.exists(last_used_dir):
            self.working_dir = last_used_dir
            self.dir_display.setText(self.working_dir)
        else:
            self.dir_display.setText("/path/to/working/dir")

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
        """Opens a file dialog to select the working directory and saves it using QSettings."""
        directory = QFileDialog.getExistingDirectory(self, "Select Working Directory", self.working_dir)
        if directory:
            self.working_dir = directory
            self.dir_display.setText(directory)

            # Save the selected directory to QSettings
            self.settings.setValue("last_working_directory", directory)

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
        # Check if there are any selected features
        selected_features = layer.selectedFeatures()

        # If there are no selected features, fall back to processing all features
        features = selected_features if selected_features else layer.getFeatures()

        for feature in features:
            geom = feature.geometry()

            # Get area name and normalize for file names
            area_name = feature[field_name]
            normalized_name = re.sub(r"\s+", "_", area_name.lower())

            if geom.isMultipart():
                parts = geom.asGeometryCollection()  # Get all parts of the multipart
                part_count = 1  # Start counting parts for filename suffixes
                for part in parts:
                    # Calculate bounding box for each part
                    bbox = part.boundingBox()
                    bbox_100m = self.create_bbox_multiple_100m(bbox)

                    # Save each part with a unique filename suffix (e.g., _1.geojson, _2.geojson)
                    bbox_file = os.path.join(study_area_dir, f"{normalized_name}_{part_count}.geojson")
                    self.save_bbox_to_geojson(bbox_100m, bbox_file, area_name)

                    # Generate and save the 100m grid for each part
                    grid_file = os.path.join(study_area_dir, f"{normalized_name}_{part_count}_grid.geojson")
                    self.create_and_save_grid(bbox_100m, grid_file)

                    part_count += 1
            else:
                # Singlepart geometry, process as usual
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
        # Define the source CRS (assumed to be in the layer's CRS) and target CRS (EPSG:3857)
        crs_src = QgsCoordinateReferenceSystem(self.layer_combo.currentLayer().crs())  # Get the CRS of the selected layer
        crs_dst = QgsCoordinateReferenceSystem("EPSG:3857")  # EPSG:3857 (meters)

        # Create the coordinate transformation
        transform = QgsCoordinateTransform(crs_src, crs_dst, QgsProject.instance())

        # Transform the bounding box to the target CRS (EPSG:3857)
        x_min, y_min = transform.transform(bbox.xMinimum(), bbox.yMinimum())
        x_max, y_max = transform.transform(bbox.xMaximum(), bbox.yMaximum())

        # Adjust bbox dimensions to be exact multiples of 100m
        def make_multiple(val, mult):
            return mult * round(val / mult)

        x_min = make_multiple(x_min, 100)
        y_min = make_multiple(y_min, 100)
        x_max = make_multiple(x_max, 100)
        y_max = make_multiple(y_max, 100)

        # Create and return the adjusted bounding box in EPSG:3857
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
        
        # Create an in-memory vector layer for the grid (Polygon type)
        grid_layer = QgsVectorLayer("Polygon?crs=EPSG:3857", "grid", "memory")
        provider = grid_layer.dataProvider()

        # Set up attributes
        provider.addAttributes([QgsField("id", QVariant.Int)])
        grid_layer.updateFields()

        # Create a grid by iterating over the bounding box and generating 100x100m squares
        x_min = bbox.xMinimum()
        x_max = bbox.xMaximum()
        y_min = bbox.yMinimum()
        y_max = bbox.yMaximum()

        step = 100  # 100m grid size
        feature_id = 0

        for x in range(int(x_min), int(x_max), step):
            for y in range(int(y_min), int(y_max), step):
                rect = QgsRectangle(x, y, x + step, y + step)
                feature = QgsFeature()
                feature.setGeometry(QgsGeometry.fromRect(rect))
                feature.setAttributes([feature_id])
                provider.addFeature(feature)
                feature_id += 1

        # Commit the changes to the in-memory layer
        grid_layer.updateExtents()

        # Save the grid layer to a GeoJSON file
        QgsVectorFileWriter.writeAsVectorFormat(grid_layer, filepath, "utf-8", driverName="GeoJSON")

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
