from PyQt5.QtWidgets import (
    QWidget,
)
from qgis.core import (
    Qgis,
)
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtGui import QPixmap
from geest.core.tasks import StudyAreaProcessingTask, OrsCheckerTask
from geest.utilities import get_ui_class, resources_path, log_message
from geest.core import WorkflowQueueManager
from geest.gui.widgets import CustomBannerLabel

FORM_CLASS = get_ui_class("setup_panel_base.ui")


class SetupPanel(FORM_CLASS, QWidget):
    switch_to_load_project_tab = (
        pyqtSignal()
    )  # Signal to notify the parent to switch tabs
    switch_to_create_project_tab = (
        pyqtSignal()
    )  # Signal to notify the parent to switch tabs
    switch_to_previous_tab = pyqtSignal()  # Signal to notify the parent to switch tabs

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GEEST")
        # Dynamically load the .ui file
        self.setupUi(self)
        log_message(f"Loading setup panel")
        self.initUI()

    def initUI(self):
        self.banner_label.setPixmap(
            QPixmap(resources_path("resources", "geest-banner.png"))
        )
        self.open_existing_project_button.clicked.connect(self.load_project)
        self.create_new_project_button.clicked.connect(self.create_project)
        self.previous_button.clicked.connect(self.on_previous_button_clicked)

    def load_project(self):
        self.switch_to_load_project_tab.emit()

    def create_project(self):
        self.switch_to_create_project_tab.emit()

    def on_previous_button_clicked(self):
        self.switch_to_previous_tab.emit()
