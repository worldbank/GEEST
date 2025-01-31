from PyQt5.QtWidgets import (
    QWidget,
)
from qgis.PyQt.QtCore import pyqtSignal
from PyQt5.QtGui import QFont
from geest.utilities import (
    get_ui_class,
    resources_path,
    log_message,
    linear_interpolation,
)
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
        self.custom_label = CustomBannerLabel(
            "The Gender Enabling Environments Spatial Tool",
            resources_path("resources", "geest-banner.png"),
        )
        parent_layout = self.banner_label.parent().layout()
        parent_layout.replaceWidget(self.banner_label, self.custom_label)
        self.banner_label.deleteLater()
        parent_layout.update()

        self.open_existing_project_button.clicked.connect(self.load_project)
        self.create_new_project_button.clicked.connect(self.create_project)
        self.previous_button.clicked.connect(self.on_previous_button_clicked)

    def load_project(self):
        self.switch_to_load_project_tab.emit()

    def create_project(self):
        self.switch_to_create_project_tab.emit()

    def on_previous_button_clicked(self):
        self.switch_to_previous_tab.emit()

    def resizeEvent(self, event):
        self.set_font_size()
        super().resizeEvent(event)

    def set_font_size(self):
        # Scale the font size to fit the text in the available space
        # log_message(f"Label Width: {self.description.rect().width()}")
        # scale the font size linearly from 16 pt to 8 ps as the width of the panel decreases
        font_size = int(
            linear_interpolation(self.description.rect().width(), 12, 16, 400, 600)
        )
        # log_message(f"Label Font Size: {font_size}")
        self.description.setFont(QFont("Arial", font_size))
