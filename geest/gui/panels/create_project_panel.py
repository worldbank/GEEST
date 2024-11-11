import os
import json
import shutil
from PyQt5.QtWidgets import (
    QWidget,
    QFileDialog,
    QMessageBox,
)
from qgis.core import (
    QgsMapLayerProxyModel,
    QgsFieldProxyModel,
    QgsVectorLayer,
    QgsProject,
    QgsMessageLog,
    Qgis,
    QgsProject,
    QgsProcessingContext,
    QgsFeedback,
    QgsMessageLog,
)

from qgis.PyQt.QtCore import QSettings, pyqtSignal
from qgis.PyQt.QtGui import QPixmap
from geest.core.tasks import StudyAreaProcessingTask, OrsCheckerTask
from geest.utilities import get_ui_class, resources_path
from geest.core import WorkflowQueueManager

FORM_CLASS = get_ui_class("create_project_panel_base.ui")


class CreateProjectPanel(FORM_CLASS, QWidget):
    switch_to_next_tab = pyqtSignal()  # Signal to notify the parent to switch tabs
    switch_to_previous_tab = pyqtSignal()  # Signal to notify the parent to switch tabs

    set_working_directory = pyqtSignal(str)  # Signal to set the working directory

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
        self.layer_combo.setFilters(QgsMapLayerProxyModel.PolygonLayer)

        # self.field_combo = QgsFieldComboBox()  # QgsFieldComboBox for selecting fields
        self.field_combo.setFilters(QgsFieldProxyModel.String)

        # Link the map layer combo box with the field combo box
        self.layer_combo.layerChanged.connect(self.field_combo.setLayer)
        self.field_combo.setLayer(self.layer_combo.currentLayer())
        self.create_project_directory_button.clicked.connect(
            self.create_new_project_folder
        )
        self.next_button.clicked.connect(self.create_project)
        self.previous_button.clicked.connect(self.on_previous_button_clicked)

        self.load_boundary_button.clicked.connect(self.load_boundary)

        self.progress_bar.setVisible(False)

    def on_previous_button_clicked(self):
        self.switch_to_previous_tab.emit()

    def load_boundary(self):
        """Load a boundary layer from a file."""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Shapefile (*.shp);;GeoPackage (*.gpkg)")
        if file_dialog.exec_():
            file_path = file_dialog.selectedFiles()[0]
            layer = QgsVectorLayer(file_path, "Boundary", "ogr")
            if not layer.isValid():
                QMessageBox.critical(
                    self, "Error", "Could not load the boundary layer."
                )
                return
            # Load the layer in QGIS
            QgsProject.instance().addMapLayer(layer)
            self.layer_combo.setLayer(layer)
            self.field_combo.setLayer(layer)

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
            self.project_path_label.setText(directory)
            self.create_project_directory_button.setText("📂 Change Project Folder")

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
            self.settings.setValue("last_working_directory", self.working_dir)
            self.set_working_directory.emit(self.working_dir)

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
