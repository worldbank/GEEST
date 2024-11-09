import os
from PyQt5.QtWidgets import QWidget, QFileDialog, QMessageBox, QComboBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontMetrics
from qgis.core import (
    QgsMessageLog,
    Qgis,
)
from qgis.PyQt.QtCore import QSettings, pyqtSignal
from qgis.PyQt.QtGui import QPixmap
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

        # Populate combo with elided paths and full paths as data
        for project_path in reversed(recent_projects):
            self.add_project_to_combo(project_path)

        # Set the current project if a recent one is available
        if last_working_directory and last_working_directory in recent_projects:
            self.previous_project_combo.setCurrentText(
                self.elide_path(last_working_directory)
            )
            self.load_project()  # Automatically load the last used project
        else:
            self.working_dir = self.previous_project_combo.currentText()
            self.set_project_directory()

        # Set tooltip on hover to show the full path
        self.previous_project_combo.setToolTip(self.working_dir)
        self.previous_project_combo.currentIndexChanged.connect(self.update_tooltip)
        self.previous_project_combo.installEventFilter(
            self
        )  # handle resizes for eliding the combo text
        self.previous_project_combo.setSizeAdjustPolicy(
            QComboBox.AdjustToMinimumContentsLengthWithIcon
        )
        self.previous_project_combo.setMinimumContentsLength(
            10
        )  # or another length that fits your needs

    def add_project_to_combo(self, project_path: str):
        """Add a project path to the combo with elided text and full path as data."""
        elided_text = self.elide_path(project_path)
        self.previous_project_combo.addItem(elided_text, project_path)

    def elide_path(self, path: str) -> str:
        """Return an elided version of the path, keeping the end visible.

        This helps with very long file paths not forcing the combo box to be very wide.

        You may not notice any difference on many systems.
        """
        metrics = QFontMetrics(self.previous_project_combo.font())
        available_width = self.previous_project_combo.width() - 20  # Add padding
        elided_text = metrics.elidedText(path, Qt.ElideLeft, available_width)
        return elided_text

    def eventFilter(self, obj, event):
        if obj == self.previous_project_combo and event.type() == event.Resize:
            # Reapply elision for all items in the combo box on resize
            for index in range(self.previous_project_combo.count()):
                full_path = self.previous_project_combo.itemData(index)
                elided_text = self.elide_path(full_path)
                QgsMessageLog.logMessage(
                    f"Full text  : {full_path}", tag="Geest", level=Qgis.Info
                )
                QgsMessageLog.logMessage(
                    f"Elided text: {elided_text}", tag="Geest", level=Qgis.Info
                )
                self.previous_project_combo.setItemText(index, elided_text)
        return super().eventFilter(obj, event)

    def update_tooltip(self):
        """Update tooltip with the full path of the current item."""
        full_path = self.previous_project_combo.currentData()
        self.previous_project_combo.setToolTip(full_path)

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

    def update_recent_projects(self, new_project: str):
        """Update the recent projects list in QSettings."""
        recent_projects = self.settings.value("recent_projects", [])
        if new_project not in recent_projects:
            recent_projects.append(new_project)
        self.settings.setValue("recent_projects", recent_projects)

        # Update the combo box with the new project
        self.previous_project_combo.clear()
        for project_path in reversed(recent_projects):
            self.add_project_to_combo(project_path)

    def load_project(self):
        """Load the project from the working directory."""
        self.working_dir = self.previous_project_combo.currentData()
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
