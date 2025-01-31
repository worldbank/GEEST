import os
import json
import shutil
import traceback
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
    Qgis,
    QgsProject,
    QgsFeedback,
    QgsLayerTreeGroup,
)

from qgis.PyQt.QtCore import QSettings, pyqtSignal
from qgis.PyQt.QtGui import QPixmap, QFont
from geest.core.tasks import StudyAreaProcessingTask
from geest.utilities import get_ui_class, resources_path, linear_interpolation
from geest.core import WorkflowQueueManager
from geest.utilities import log_message
from geest.gui.widgets import CustomBannerLabel


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
        log_message(f"Loading setup panel")
        self.initUI()

    def initUI(self):
        self.custom_label = CustomBannerLabel(
            "The Gender Enabling Environments Spatial Tool",
            resources_path("resources", "geest-banner.png"),
        )
        parent_layout = self.banner_label.parent().layout()
        parent_layout.replaceWidget(self.banner_label, self.custom_label)
        self.banner_label.deleteLater()
        parent_layout.update()

        self.folder_status_label.setPixmap(
            QPixmap(resources_path("resources", "icons", "failed.svg"))
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
        project_crs = QgsProject.instance().crs().authid()
        if project_crs == "EPSG:4326" or project_crs == "":
            self.use_boundary_crs.setChecked(False)
            self.use_boundary_crs.setEnabled(False)

        self.next_button.clicked.connect(self.create_project)
        self.previous_button.clicked.connect(self.on_previous_button_clicked)

        self.load_boundary_button.clicked.connect(self.load_boundary)

        self.progress_bar.setVisible(False)
        self.child_progress_bar.setVisible(False)

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
            self.folder_status_label.setPixmap(
                QPixmap(resources_path("resources", "icons", "completed-success.svg"))
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
                self.enable_widgets()
                return
            # open the model.json to set the analysis cell size, then close it again
            with open(model_path, "r") as f:
                model = json.load(f)
                model["analysis_cell_size_m"] = self.cell_size_spinbox.value()
            with open(model_path, "w") as f:
                json.dump(model, f)

            # Create the processor instance and process the features
            debug_env = int(os.getenv("GEEST_DEBUG", 0))
            feedback = (
                QgsFeedback()
            )  # Used to cancel tasks and measure subtask progress
            try:

                processor = StudyAreaProcessingTask(
                    layer=layer,
                    field_name=field_name,
                    cell_size_m=self.cell_size_spinbox.value(),
                    crs=crs,
                    working_dir=self.working_dir,
                    feedback=feedback,
                )
                # Hook up the QTask feedback signal to the progress bar
                # Measure overall task progress from the task object itself
                processor.progressChanged.connect(self.progress_updated)
                processor.taskCompleted.connect(self.on_task_completed)
                # Measure subtask progress from the feedback object
                feedback.progressChanged.connect(self.subtask_progress_updated)
                self.disable_widgets()
                if debug_env:
                    processor.process_study_area()
                else:
                    self.queue_manager.add_task(processor)
                    self.queue_manager.start_processing()
            except Exception as e:
                trace = traceback.format_exc()
                QMessageBox.critical(
                    self, "Error", f"Error processing study area: {e}\n{trace}"
                )
                self.enable_widgets()
                return
            self.settings.setValue("last_working_directory", self.working_dir)
            self.set_working_directory.emit(self.working_dir)
            self.enable_widgets()

    def disable_widgets(self):
        """Disable all widgets in the panel."""
        for widget in self.findChildren(QWidget):
            widget.setEnabled(False)

    def enable_widgets(self):
        """Enable all widgets in the panel."""
        for widget in self.findChildren(QWidget):
            widget.setEnabled(True)

    # Slot that listens for changes in the study_area task object which is used to measure overall task progress
    def progress_updated(self, progress: float):
        """Slot to be called when the task progress is updated."""
        log_message(f"\n\n\n\n\n\n\Progress: {progress}\n\n\n\n\n\n\n\n")
        self.progress_bar.setVisible(True)
        self.progress_bar.setEnabled(True)
        self.progress_bar.setValue(int(progress))
        # This is a sneaky hack to show the exact progress in the label
        # since QProgressBar only takes ints. See Qt docs for more info.
        # Use the 'setFormat' method to display the exact float:
        float_value_as_string = f"Total progress: {progress}%"
        self.progress_bar.setFormat(float_value_as_string)
        self.add_bboxes_to_map()  # will just refresh them if already there

    # Slot that listens for changes in the progress object which is used to measure subtask progress
    def subtask_progress_updated(self, progress: float):
        self.child_progress_bar.setVisible(True)
        self.child_progress_bar.setEnabled(True)
        self.child_progress_bar.setValue(int(progress))
        # This is a sneaky hack to show the exact progress in the label
        # since QProgressBar only takes ints. See Qt docs for more info.
        # Use the 'setFormat' method to display the exact float:
        float_value_as_string = f"Current geometry progress: {progress}%"
        self.child_progress_bar.setFormat(float_value_as_string)

    def on_task_completed(self):
        """Slot to be called when the task completes successfully."""
        log_message(
            "*** Study area processing completed successfully. ***",
            tag="Geest",
            level=Qgis.Info,
        )
        self.progress_bar.setVisible(False)
        self.child_progress_bar.setVisible(False)
        self.enable_widgets()
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

    def resizeEvent(self, event):
        self.set_font_size()
        super().resizeEvent(event)

    def set_font_size(self):
        # Scale the font size to fit the text in the available space
        # log_message(f"Description Label Width: {self.description.rect().width()}")
        # scale the font size linearly from 16 pt to 8 ps as the width of the panel decreases
        font_size = int(
            linear_interpolation(self.description.rect().width(), 12, 16, 400, 600)
        )

        # log_message(f"Description Label Font Size: {font_size}")
        self.description.setFont(QFont("Arial", font_size))
        self.description2.setFont(QFont("Arial", font_size))
        self.description3.setFont(QFont("Arial", font_size))
        self.create_project_directory_button.setFont(QFont("Arial", font_size))
        self.load_boundary_button.setFont(QFont("Arial", font_size))
        self.cell_size_spinbox.setFont(QFont("Arial", font_size))
        self.layer_combo.setFont(QFont("Arial", font_size))
        self.field_combo.setFont(QFont("Arial", font_size))

    def add_bboxes_to_map(self):
        """Add the study area layers to the map.

        If it is already there we will just refrehs it.

        This provides the user with visual feedback as each geometry gets processed.

        This method is a cut and paste of the same method in tree_panel.py
        but only adds two layers (well one layer and one table) to the map.

        """
        gpkg_path = os.path.join(self.working_dir, "study_area", "study_area.gpkg")
        project = QgsProject.instance()

        # Check if 'Geest' group exists, otherwise create it
        root = project.layerTreeRoot()
        geest_group = root.findGroup("Geest Study Area")
        if geest_group is None:
            geest_group = root.insertGroup(
                0, "Geest Study Area"
            )  # Insert at the top of the layers panel

        layers = [
            "study_area_bboxes",
            "study_area_creation_status",
        ]
        for layer_name in layers:
            gpkg_layer_path = f"{gpkg_path}|layername={layer_name}"
            layer = QgsVectorLayer(gpkg_layer_path, layer_name, "ogr")

            if not layer.isValid():
                log_message(
                    f"Failed to add '{layer_name}' layer to the map.",
                    tag="Geest",
                    level=Qgis.Critical,
                )
                continue

            source_qml = resources_path("resources", "qml", f"{layer_name}.qml")
            result = layer.loadNamedStyle(source_qml)
            if result[0]:  # loadNamedStyle returns (success, error_message)
                print(f"Successfully applied QML style to layer '{layer_name}'")
            else:
                print(f"Failed to apply QML style: {result[1]}")

            # Check if a layer with the same data source exists in the correct group
            existing_layer = None
            for child in geest_group.children():
                if isinstance(child, QgsLayerTreeGroup):
                    continue
                if child.layer().source() == gpkg_layer_path:
                    existing_layer = child.layer()
                    break

            # If the layer exists, refresh it instead of removing and re-adding
            if existing_layer is not None:
                log_message(f"Refreshing existing layer: {existing_layer.name()}")
                existing_layer.reload()
            else:
                # Add the new layer to the appropriate subgroup
                QgsProject.instance().addMapLayer(layer, False)
                layer_tree_layer = geest_group.addLayer(layer)
                log_message(
                    f"Added layer: {layer.name()} to group: {geest_group.name()}"
                )
