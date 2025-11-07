# -*- coding: utf-8 -*-
"""📦 Setup Panel module.

This module contains functionality for setup panel.
"""
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QWidget
from qgis.PyQt.QtCore import pyqtSignal

from geest.gui.widgets import CustomBannerLabel
from geest.utilities import (
    get_ui_class,
    linear_interpolation,
    log_message,
    resources_path,
)

FORM_CLASS = get_ui_class("setup_panel_base.ui")


class SetupPanel(FORM_CLASS, QWidget):
    """🎯 Setup Panel.
    """
    switch_to_load_project_tab = pyqtSignal()  # Signal to notify the parent to switch tabs
    switch_to_create_project_tab = pyqtSignal()  # Signal to notify the parent to switch tabs
    switch_to_previous_tab = pyqtSignal()  # Signal to notify the parent to switch tabs

    def __init__(self):
        """🏗️ Initialize the instance.
        """
        super().__init__()
        self.setWindowTitle("GEEST")
        # Dynamically load the .ui file
        self.setupUi(self)
        log_message("Loading setup panel")
        self.initUI()

    def initUI(self):
        """⚙️ Initui.
        """
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
        """⚙️ Load project.
        """
        self.switch_to_load_project_tab.emit()

    def create_project(self):
        """⚙️ Create project.
        """
        self.switch_to_create_project_tab.emit()

    def on_previous_button_clicked(self):
        """⚙️ On previous button clicked.
        """
        self.switch_to_previous_tab.emit()

    def resizeEvent(self, event):
        """⚙️ Resizeevent.
        
        Args:
            event: Event.
        """
        self.set_font_size()
        super().resizeEvent(event)

    def set_font_size(self):
        """⚙️ Set font size.
        """
        # Scale the font size to fit the text in the available space
        # log_message(f"Label Width: {self.description.rect().width()}")
        # scale the font size linearly from 16 pt to 8 ps as the width of the panel decreases
        font_size = int(linear_interpolation(self.description.rect().width(), 12, 16, 400, 600))
        # log_message(f"Label Font Size: {font_size}")
        self.description.setFont(QFont("Arial", font_size))
