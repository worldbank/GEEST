from PyQt5.QtWidgets import (
    QWidget,
)
from qgis.core import QgsMessageLog, Qgis, QPainter
from qgis.PyQt import uic

from qgis.PyQt.QtCore import QSettings, pyqtSignal
from qgis.PyQt.QtGui import QPixmap
from geest.core.tasks import OrsCheckerTask
from geest.utilities import get_ui_class, resources_path
from geest.core import setting, set_setting

FORM_CLASS = get_ui_class("intro_panel_base.ui")


class IntroPanel(FORM_CLASS, QWidget):
    switch_to_next_tab = pyqtSignal()  # Signal to notify the parent to switch tabs

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GEEST")
        # Dynamically load the .ui file
        self.setupUi(self)
        QgsMessageLog.logMessage(f"Loading intro panel", tag="Geest", level=Qgis.Info)
        self.initUI()

    def initUI(self):
        self.banner_label.setPixmap(
            QPixmap(resources_path("resources", "geest-banner.png"))
        )
        self.next_button.clicked.connect(self.on_next_button_clicked)

    def on_next_button_clicked(self):
        self.switch_to_next_tab.emit()
