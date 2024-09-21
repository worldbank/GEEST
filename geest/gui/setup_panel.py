import os
import re
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QPushButton,
    QToolButton,
    QHBoxLayout,
    QFileDialog,
    QMessageBox,
    QSpacerItem,
    QSizePolicy,
)
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
from geest.core.study_area import StudyAreaProcessor


class SetupPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GEEST")
        self.working_dir = ""
        self.settings = QSettings()  # Initialize QSettings to store and retrieve settings
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Title
        # geest-banner.png
        self.banner_label = QLabel()
        self.banner_label.setPixmap(
            QPixmap(resources_path("resources", "geest-banner.png"))
        )
        layout.addWidget(self.banner_label)
        self.title_label = QLabel(
            "Geospatial Assessment of Women Employment and Business Opportunities in the Renewable Energy Sector",
            self,
        )
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        # Study Area Combobox - Filtered to polygon/multipolygon layers
        self.study_area_label = QLabel("Study Area Layer:")
        layout.addWidget(self.study_area_label)

        self.layer_combo = QgsMapLayerComboBox()
        self.layer_combo.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        layout.addWidget(self.layer_combo)

        # Area Name Field ComboBox
        self.area_name_label = QLabel("Area Name Field:")
        layout.addWidget(self.area_name_label)

        self.field_combo = QgsFieldComboBox()  # QgsFieldComboBox for selecting fields
        # Set filter to show only text fields (QVariant.String)
        # All, Date, Double, Int, LongLong, Numeric, String, Time
        self.field_combo.setFilters(QgsFieldProxyModel.String)

        layout.addWidget(self.field_combo)

        # Link the map layer combo box with the field combo box
        self.layer_combo.layerChanged.connect(self.field_combo.setLayer)

        # Directory Selector for Working Directory
        self.dir_label = QLabel(
            "Working Directory: This folder will store all the inputs and outputs for your model."
        )
        layout.addWidget(self.dir_label)

        dir_layout = QHBoxLayout()
        self.dir_display = QLabel("Choose a working directory")
        self.dir_button = QToolButton()
        self.dir_button.setText("📂")
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
            self.dir_display.setText("Choose a working directory")

        # Text for analysis preparation
        self.preparation_label = QLabel(
            "After selecting your study area layer, we will prepare the analysis region."
        )
        layout.addWidget(self.preparation_label)
        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        layout.addItem(spacer)
        # Description
        self.description_label = QLabel(
            "This plugin is built with support from the Canada Clean Energy and Forest Climate Facility (CCEFCFy), "
            "the Geospatial Operational Support Team (GOST, DECSC) for the project "
            "'Geospatial Assessment of Women Employment and Business Opportunities in the Renewable Energy Sector'.",
            self,
        )
        self.description_label.setWordWrap(True)
        layout.addWidget(self.description_label)
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
            self.settings.setValue("last_working_directory", directory)

    def on_continue(self):
        """Triggered when the Continue button is pressed."""
        layer = self.layer_combo.currentLayer()
        if not layer:
            QMessageBox.critical(self, "Error", "Please select a study area layer.")
            return

        if not self.working_dir:
            QMessageBox.critical(self, "Error", "Please select a working directory.")
            return

        field_name = self.field_combo.currentField()
        if not field_name or field_name not in layer.fields().names():
            QMessageBox.critical(self, "Error", f"Invalid area name field '{field_name}'.")
            return

        study_area_dir = self.create_study_area_directory(self.working_dir)
        if not study_area_dir:
            QMessageBox.critical(self, "Error", "Failed to create study area directory.")
            return

        # Create the processor instance and process the features
        self.process_study_area(layer, field_name, study_area_dir)

    def create_study_area_directory(self, working_dir):
        """Creates the 'study_area' directory."""
        study_area_dir = os.path.join(working_dir, "study_area")
        if not os.path.exists(study_area_dir):
            try:
                os.makedirs(study_area_dir)
            except Exception as e:
                print(f"Error creating directory: {e}")
                return None
        return study_area_dir

    def process_study_area(self, layer, field_name, study_area_dir):
        """Processes each feature in the layer to create bounding boxes and grids."""
        processor = StudyAreaProcessor(layer, self.working_dir)
        selected_features = layer.selectedFeatures()
        features = selected_features if selected_features else layer.getFeatures()

        for feature in features:
            geom = feature.geometry()
            area_name = feature[field_name]
            normalized_name = re.sub(r"\s+", "_", area_name.lower())

            if geom.isMultipart():
                processor.process_multipart_geometry(geom, normalized_name, area_name, study_area_dir)
            else:
                self.process_singlepart_geometry(geom, normalized_name, area_name, processor, study_area_dir)

        # After processing, add layers to QGIS
        processor.add_layers_to_qgis(study_area_dir)

    def process_singlepart_geometry(self, geom, normalized_name, area_name, processor, study_area_dir):
        """Processes a singlepart geometry feature."""
        bbox = geom.boundingBox()
        bbox_100m = processor.create_bbox_multiple_100m(bbox)

        bbox_file = os.path.join(study_area_dir, f"{normalized_name}.geojson")
        processor.save_bbox_to_geojson(bbox_100m, bbox_file, area_name)

        grid_file = os.path.join(study_area_dir, f"{normalized_name}_grid.geojson")
        processor.create_and_save_grid(bbox_100m, grid_file)
