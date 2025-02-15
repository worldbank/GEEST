from PyQt5.QtWidgets import (
    QWidget,
)
from qgis.core import Qgis

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtGui import QFont
from geest.core.tasks import OrsCheckerTask
from geest.utilities import (
    get_ui_class,
    resources_path,
    log_message,
    linear_interpolation,
)
from geest.gui.widgets import CustomBannerLabel

FORM_CLASS = get_ui_class("intro_panel_base.ui")


class IntroPanel(FORM_CLASS, QWidget):
    switch_to_next_tab = pyqtSignal()  # Signal to notify the parent to switch tabs

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GEEST")
        # Dynamically load the .ui file
        self.setupUi(self)
        log_message(f"Loading intro panel")
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
        self.next_button.clicked.connect(self.on_next_button_clicked)
        self.set_font_size()

    def on_next_button_clicked(self):
        self.switch_to_next_tab.emit()

    def resizeEvent(self, event):
        self.set_font_size()
        super().resizeEvent(event)

    def set_font_size(self):
        # Scale the font size to fit the text in the available space
        # log_message(f"Intro Label Width: {self.intro_label.rect().width()}")
        # scale the font size linearly from 16 pt to 8 ps as the width of the panel decreases
        font_size = int(
            linear_interpolation(self.intro_label.rect().width(), 12, 16, 400, 600)
        )
        # log_message(f"Intro Label Font Size: {font_size}")
        self.intro_label.setFont(QFont("Arial", font_size))
