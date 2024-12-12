from PyQt5.QtWidgets import (
    QWidget,
)
from qgis.core import Qgis

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtGui import QPixmap
from geest.core.tasks import OrsCheckerTask
from geest.utilities import get_ui_class, resources_path
from geest.utilities import log_message
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

    def on_next_button_clicked(self):
        self.switch_to_next_tab.emit()
