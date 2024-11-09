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
    switch_to_load_project_tab = (
        pyqtSignal()
    )  # Signal to notify the parent to switch tabs
    switch_to_create_project_tab = (
        pyqtSignal()
    )  # Signal to notify the parent to switch tabs

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GEEST")
        # Dynamically load the .ui file
        self.setupUi(self)
        QgsMessageLog.logMessage(f"Loading setup panel", tag="Geest", level=Qgis.Info)
        self.initUI()

    def initUI(self):
        self.banner_label.setPixmap(
            QPixmap(resources_path("resources", "geest-banner.png"))
        )
        self.open_existing_project_button.clicked.connect(self.load_project)
        self.create_new_project_button.clicked.connect(self.create_project)

    def load_project(self):
        self.switch_to_load_project_tab.emit()

    def create_project(self):
        self.switch_to_create_project_tab.emit()
