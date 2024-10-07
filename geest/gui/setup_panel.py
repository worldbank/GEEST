import os
import shutil
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
    QgsVectorLayer,
    QgsProject,
    QgsApplication,
)
from qgis.PyQt.QtCore import QSettings, pyqtSignal
from qgis.PyQt.QtGui import QPixmap
from geest.utilities import resources_path
from geest.core.study_area import StudyAreaProcessingTask


class SetupPanel(QWidget):
    switch_to_next_tab = pyqtSignal()  # Signal to notify the parent to switch tabs

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GEEST")
        self.working_dir = ""
        self.settings = (
            QSettings()
        )  # Initialize QSettings to store and retrieve settings
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Title
        self.banner_label = QLabel()
        self.banner_label.setScaledContents(True)  # Allow image scaling
        self.banner_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
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

        # Directory Selector for Working Directory
        self.dir_label = QLabel(
            "Working Directory: This folder will store all the outputs for your analysis."
        )
        layout.addWidget(self.dir_label)

        dir_layout = QHBoxLayout()
        self.dir_display = QLabel("Choose a working directory")
        self.dir_button = QToolButton()
        self.dir_button.setText("📂")
        self.dir_button.clicked.connect(self.select_directory)
        dir_layout.addWidget(self.dir_button)
        dir_layout.addWidget(self.dir_display)

        layout.addLayout(dir_layout)

        # Existing project label
        self.existing_project_label = QLabel(
            "This directory contains an existing project."
        )
        self.existing_project_label.setVisible(False)
        layout.addWidget(self.existing_project_label)

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
        self.field_combo.setFilters(QgsFieldProxyModel.String)
        layout.addWidget(self.field_combo)

        # Link the map layer combo box with the field combo box
        self.layer_combo.layerChanged.connect(self.field_combo.setLayer)

        # Easter egg label and button for adding the QGIS world map
        self.world_map_label = QLabel(
            "No boundaries layer? Add the default QGIS world map to your canvas! Be sure to select just the country or areas of interest before pressing continue."
        )
        self.world_map_label.setWordWrap(True)
        self.world_map_button = QPushButton("Add World Map")
        self.world_map_button.clicked.connect(self.add_world_map)
        self.world_map_label.setVisible(False)
        self.world_map_button.setVisible(False)
        layout.addWidget(self.world_map_label)
        layout.addWidget(self.world_map_button)

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

        # Set the last used working directory from QSettings
        last_used_dir = self.settings.value("last_working_directory", "")
        if last_used_dir and os.path.exists(last_used_dir):
            self.working_dir = last_used_dir
            self.dir_display.setText(self.working_dir)
            self.update_for_working_directory()

    def select_directory(self):
        """Opens a file dialog to select the working directory and updates the UI based on its contents."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Working Directory", self.working_dir
        )
        if directory:
            self.working_dir = directory
            self.dir_display.setText(directory)
            self.settings.setValue("last_working_directory", directory)
            self.update_for_working_directory()

    def update_for_working_directory(self):
        """
        Updates the UI based on the selected working directory.
        If the directory contains 'model.json', shows a message and hides layer/field selectors.
        Otherwise, shows the layer/field selectors.
        """
        model_path = os.path.join(self.working_dir, "model.json")
        if os.path.exists(model_path):
            # Existing project
            self.existing_project_label.setVisible(True)
            self.study_area_label.setVisible(False)
            self.layer_combo.setVisible(False)
            self.area_name_label.setVisible(False)
            self.field_combo.setVisible(False)
            self.preparation_label.setVisible(False)
            self.world_map_label.setVisible(False)
            self.world_map_button.setVisible(False)
        else:
            # New project
            self.existing_project_label.setVisible(False)
            self.study_area_label.setVisible(True)
            self.layer_combo.setVisible(True)
            self.area_name_label.setVisible(True)
            self.field_combo.setVisible(True)
            self.preparation_label.setVisible(True)

            # Check if there are any polygon layers in the project
            if not self.layer_combo.count():
                # No available polygon layers, show world map option
                self.world_map_label.setVisible(True)
                self.world_map_button.setVisible(True)
            else:
                # Layers available, hide world map option
                self.world_map_label.setVisible(False)
                self.world_map_button.setVisible(False)

    def add_world_map(self):
        """Adds the built-in QGIS world map to the canvas."""
        # Use QgsApplication.prefixPath() to get the correct path
        qgis_prefix = QgsApplication.prefixPath()
        layer_path = os.path.join(
            qgis_prefix, "share", "qgis", "resources", "data", "world_map.gpkg"
        )

        if not os.path.exists(layer_path):
            QMessageBox.critical(
                self, "Error", f"Could not find world map file at {layer_path}."
            )
            return

        full_layer_path = f"{layer_path}|layername=countries"
        world_map_layer = QgsVectorLayer(full_layer_path, "World Map", "ogr")

        if not world_map_layer.isValid():
            QMessageBox.critical(self, "Error", "Could not load the world map layer.")
            return

        QgsProject.instance().addMapLayer(world_map_layer)

    def on_continue(self):
        """Triggered when the Continue button is pressed."""
        model_path = os.path.join(self.working_dir, "model.json")
        if os.path.exists(model_path):
            # Switch to the next tab if an existing project is found
            self.switch_to_next_tab.emit()
        else:
            # Process the study area if no model.json exists
            layer = self.layer_combo.currentLayer()
            if not layer:
                QMessageBox.critical(self, "Error", "Please select a study area layer.")
                return

            if not self.working_dir:
                QMessageBox.critical(
                    self, "Error", "Please select a working directory."
                )
                return

            field_name = self.field_combo.currentField()
            if not field_name or field_name not in layer.fields().names():
                QMessageBox.critical(
                    self, "Error", f"Invalid area name field '{field_name}'."
                )
                return

            # Copy default model.json if not present
            default_model_path = resources_path("resources", "model.json")
            try:
                shutil.copy(default_model_path, model_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to copy model.json: {e}")
                return

            # Create the processor instance and process the features
            try:
                processor = StudyAreaProcessingTask(
                    name="Study Area Processing",
                    layer=layer,
                    field_name=field_name,
                    working_dir=self.working_dir,
                )
                processor.process_study_area()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error processing study area: {e}")
                return
