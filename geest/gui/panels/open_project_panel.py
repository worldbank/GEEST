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

FORM_CLASS = get_ui_class("open_project_panel_base.ui")


class OpenProjectPanel(FORM_CLASS, QWidget):
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
        QgsMessageLog.logMessage(
            f"Loading open project panel", tag="Geest", level=Qgis.Info
        )
        self.initUI()

    def initUI(self):
        self.banner_label.setPixmap(
            QPixmap(resources_path("resources", "geest-banner.png"))
        )
        self.dir_button.clicked.connect(self.select_directory)
        self.open_project_button.clicked.connect(self.load_project)
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
