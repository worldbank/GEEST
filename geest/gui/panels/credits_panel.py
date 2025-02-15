from PyQt5.QtWidgets import (
    QWidget,
)
from qgis.core import Qgis

from qgis.PyQt.QtCore import QUrl, pyqtSignal
from qgis.PyQt.QtGui import QFont, QDesktopServices
from geest.utilities import (
    get_ui_class,
    resources_path,
    log_message,
    linear_interpolation,
)
from geest.gui.widgets import CustomBannerLabel

FORM_CLASS = get_ui_class("credits_panel_base.ui")


class CreditsPanel(FORM_CLASS, QWidget):
    switch_to_next_tab = pyqtSignal()  # Signal to notify the parent to switch tabs
    switch_to_previous_tab = pyqtSignal()  # Signal to notify the parent to switch tabs

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GEEST")
        # Dynamically load the .ui file
        self.setupUi(self)
        log_message(f"Loading Credits panel")
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
        self.previous_button.clicked.connect(self.on_previous_button_clicked)
        self.description.linkActivated.connect(self.open_link_in_browser)
        self.set_font_size()

    def on_next_button_clicked(self):
        self.switch_to_next_tab.emit()

    def on_previous_button_clicked(self):
        self.switch_to_previous_tab.emit()

    def open_link_in_browser(self, url: str):
        """Open the given URL in the user's default web browser using QDesktopServices."""
        QDesktopServices.openUrl(QUrl(url))

    def repaint(self):
        self.set_font_size()
        super().repaint()

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
        self.description.repaint()
