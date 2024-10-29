import os
import json
import platform
import shutil
from PyQt5.QtWidgets import (
    QWidget,
    QFileDialog,
    QMessageBox,
)
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox
from qgis.core import (
    QgsMapLayerProxyModel,
    QgsFieldProxyModel,
    QgsVectorLayer,
    QgsProject,
    QgsApplication,
    QgsMessageLog,
    Qgis,
    QgsProject,
    QgsProcessingContext,
    QgsFeedback,
)
from qgis.PyQt import uic

from qgis.PyQt.QtCore import QSettings, pyqtSignal
from qgis.PyQt.QtGui import QPixmap
from geest.core.tasks import StudyAreaProcessingTask, OrsCheckerTask
from geest.utilities import get_ui_class, resources_path
from geest.core import WorkflowQueueManager

FORM_CLASS = get_ui_class("setup_panel_base.ui")


class SetupPanel(FORM_CLASS, QWidget):
    switch_to_next_tab = pyqtSignal()  # Signal to notify the parent to switch tabs

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GEEST")
        # For running study area processing in a separate thread
        self.queue_manager = WorkflowQueueManager(pool_size=1)

        self.working_dir = ""
        self.settings = (
            QSettings()
        )  # Initialize QSettings to store and retrieve settings
        # Dynamically load the .ui file
        self.setupUi(self)
        QgsMessageLog.logMessage(f"Loading setup panel", tag="Geest", level=Qgis.Info)
        self.initUI()

    def initUI(self):
        self.banner_label.setPixmap(
            QPixmap(resources_path("resources", "geest-banner.png"))
        )
        self.open_project_group.setVisible(False)
        self.dir_button.clicked.connect(self.select_directory)
        self.open_project_button.clicked.connect(self.load_project)
        # self.layer_combo = QgsMapLayerComboBox()
        self.layer_combo.setFilters(QgsMapLayerProxyModel.PolygonLayer)

        # self.field_combo = QgsFieldComboBox()  # QgsFieldComboBox for selecting fields
        self.field_combo.setFilters(QgsFieldProxyModel.String)

        # Link the map layer combo box with the field combo box
        self.layer_combo.layerChanged.connect(self.field_combo.setLayer)
        self.field_combo.setLayer(self.layer_combo.currentLayer())
        self.world_map_button.clicked.connect(self.add_world_map)
        self.create_project_directory_button.clicked.connect(
            self.create_new_project_folder
        )
        self.prepare_project_button.clicked.connect(self.create_project)
        self.new_project_group.setVisible(False)

        # Load the last used working directory from QSettings
        recent_projects = self.settings.value("recent_projects", [])
        last_working_directory = self.settings.value("last_working_directory", "")
        self.previous_project_combo.addItems(
            reversed(recent_projects)
        )  # Add recent projects to the combo
        if last_working_directory and last_working_directory in recent_projects:
            self.previous_project_combo.setCurrentText(last_working_directory)
            self.load_project()  # Automatically load the last used project
        else:
            self.working_dir = self.previous_project_combo.currentText()
            self.set_project_directory()

        self.progress_bar.setVisible(False)

    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select Working Directory", self.working_dir
        )
        if directory:
            self.working_dir = directory
            self.update_recent_projects(directory)  # Update recent projects
            self.settings.setValue(
                "last_working_directory", directory
            )  # Update last used project
            self.set_project_directory()

    def create_new_project_folder(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Create New Project Folder", self.working_dir
        )
        if directory:
            self.working_dir = directory
            self.update_recent_projects(directory)  # Update recent projects
            self.settings.setValue(
                "last_working_directory", directory
            )  # Update last used project
        self.set_project_directory()

    def set_project_directory(self):
        """
        Updates the UI based on the selected working directory.
        If the directory contains 'model.json', shows a message and hides layer/field selectors.
        Otherwise, shows the layer/field selectors.
        """
        model_path = os.path.join(self.working_dir, "model.json")

    def add_world_map(self):
        """Adds the built-in QGIS world map to the canvas."""
        # Use QgsApplication.prefixPath() to get the correct path
        qgis_prefix = QgsApplication.prefixPath()

        # Check the platform to get the correct path
        if platform.system() == "Windows":
            # For Windows
            layer_path = os.path.join(
                qgis_prefix, "resources", "data", "world_map.gpkg"
            )
        else:
            # For macOS and Linux
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

    def load_project(self):
        """Load the project from the working directory."""
        self.working_dir = self.previous_project_combo.currentText()
        model_path = os.path.join(self.working_dir, "model.json")
        if os.path.exists(model_path):
            self.settings.setValue(
                "last_working_directory", self.working_dir
            )  # Update last used project
            # Switch to the next tab if an existing project is found
            self.switch_to_next_tab.emit()
        else:
            QMessageBox.critical(
                self, "Error", "Selected project does not contain a model.json file."
            )

    def create_project(self):
        """Triggered when the Continue button is pressed."""
        if self.use_boundary_crs.isChecked():
            crs = self.layer_combo.currentLayer().crs()
        else:
            crs = None
        model_path = os.path.join(self.working_dir, "model.json")
        if os.path.exists(model_path):
            self.settings.setValue(
                "last_working_directory", self.working_dir
            )  # Update last used project
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
            # open the model.json to set the analysis cell size, then close it again
            with open(model_path, "r") as f:
                model = json.load(f)
                model["analysis_cell_size_m"] = self.cell_size_spinbox.value()
            with open(model_path, "w") as f:
                json.dump(model, f)

            # Create the processor instance and process the features
            debug_env = int(os.getenv("GEEST_DEBUG", 0))
            context = QgsProcessingContext()
            context.setProject(QgsProject.instance())
            feedback = QgsFeedback()
            try:

                processor = StudyAreaProcessingTask(
                    name="Study Area Processing",
                    layer=layer,
                    field_name=field_name,
                    cell_size_m=self.cell_size_spinbox.value(),
                    crs=crs,
                    working_dir=self.working_dir,
                    context=context,
                    feedback=feedback,
                )
                # Hook up the QTask feedback signal to the progress bar
                processor.progressChanged.connect(self.progress_updated)
                processor.taskCompleted.connect(self.on_task_completed)

                if debug_env:
                    processor.process_study_area()
                else:
                    self.queue_manager.add_task(processor)
                    self.queue_manager.start_processing()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error processing study area: {e}")
                return

            # Move this to its own button
            # try:
            #    checker = OrsCheckerTask(url="https://api.openrouteservice.org")
            #    self.queue_manager.add_task(checker)
            #    self.queue_manager.start_processing()
            # except Exception as e:
            #    QMessageBox.critical(self, "Error", f"Error checking ORS: {e}")
            #    return
            # Update the last used project after processing
            self.settings.setValue("last_working_directory", self.working_dir)

    def progress_updated(self, progress):
        """Slot to be called when the task progress is updated."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(int(progress))

    def on_task_completed(self):
        """Slot to be called when the task completes successfully."""
        QgsMessageLog.logMessage(
            "*** Study area processing completed successfully. ***",
            tag="Geest",
            level=Qgis.Info,
        )
        self.progress_bar.setVisible(False)
        self.switch_to_next_tab.emit()

    def update_recent_projects(self, directory):
        """Updates the recent projects list with the new directory."""
        recent_projects = self.settings.value("recent_projects", [])

        if directory in recent_projects:
            recent_projects.remove(
                directory
            )  # Remove if already in the list (to reorder)

        recent_projects.insert(0, directory)  # Add to the top of the list

        # Limit the list to a certain number of recent projects (e.g., 15)
        if len(recent_projects) > 15:
            recent_projects = recent_projects[:15]

        # Save back to QSettings
        self.settings.setValue("recent_projects", recent_projects)

        # Update the combo box
        self.previous_project_combo.clear()
        self.previous_project_combo.addItems(reversed(recent_projects))
