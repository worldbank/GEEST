# -*- coding: utf-8 -*-
"""📦 Open Project Panel module.

This module contains functionality for open project panel.
"""
import json
import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import QComboBox, QFileDialog, QWidget
from qgis.core import Qgis  # noqa F401
from qgis.PyQt.QtCore import QSettings, pyqtSignal
from qgis.PyQt.QtGui import QFont

from geest.core import WorkflowQueueManager
from geest.gui.widgets import CustomBannerLabel
from geest.utilities import (
    get_ui_class,
    linear_interpolation,
    log_message,
    resources_path,
)

FORM_CLASS = get_ui_class("open_project_panel_base.ui")


class OpenProjectPanel(FORM_CLASS, QWidget):
    """🎯 Open Project Panel.

    Attributes:
        queue_manager: Queue manager.
        settings: Settings.
        working_dir: Working dir.
    """

    switch_to_next_tab = pyqtSignal()  # Signal to notify the parent to switch tabs
    switch_to_previous_tab = pyqtSignal()  # Signal to notify the parent to switch tabs
    set_working_directory = pyqtSignal(str)  # Signal to set the working directory
    women_considerations_changed_signal = pyqtSignal()  # Signal when women considerations toggle changes

    def __init__(self):
        """🏗️ Initialize the instance."""
        super().__init__()
        self.setWindowTitle("GeoE3")
        # For running study area processing in a separate thread
        self.queue_manager = WorkflowQueueManager(pool_size=1)

        self.working_dir = ""
        self.settings = QSettings()  # Initialize QSettings to store and retrieve settings
        # Dynamically load the .ui file
        self.setupUi(self)
        log_message("Loading open project panel")
        self.initUI()

    def initUI(self):
        """⚙️ Initui."""
        self.custom_label = CustomBannerLabel(
            "The Geospatial Enabling Environments for Employment Spatial Tool",
            resources_path("resources", "geest-banner.png"),
        )
        parent_layout = self.banner_label.parent().layout()
        parent_layout.replaceWidget(self.banner_label, self.custom_label)
        self.banner_label.deleteLater()
        parent_layout.update()

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
            # Find the index with matching data (full path) instead of relying on text matching
            for i in range(self.previous_project_combo.count()):
                if self.previous_project_combo.itemData(i) == last_working_directory:
                    self.previous_project_combo.setCurrentIndex(i)
                    break
            self.load_project()  # Automatically load the last used project
        elif self.previous_project_combo.count() > 0:
            self.load_project(self.previous_project_combo.currentData())

        # Set tooltip on hover to show the full path
        self.previous_project_combo.setToolTip(self.working_dir)
        self.previous_project_combo.currentIndexChanged.connect(self.update_tooltip)
        self.previous_project_combo.currentIndexChanged.connect(self.on_previous_project_changed)
        self.previous_project_combo.installEventFilter(self)  # handle resizes for eliding the combo text
        self.previous_project_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.previous_project_combo.setMinimumContentsLength(10)
        self.previous_button.clicked.connect(self.on_previous_button_clicked)

        # Set up women considerations toggle
        self.women_considerations_checkbox.stateChanged.connect(self.women_considerations_changed)
        self.women_considerations_checkbox.stateChanged.connect(self.save_women_considerations_settings)
        self.eplex_score_spinbox.valueChanged.connect(self.save_women_considerations_settings)
        # Initialize visibility
        self.women_considerations_changed()

    def on_previous_button_clicked(self):
        """⚙️ On previous button clicked."""
        self.switch_to_previous_tab.emit()

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
        """⚙️ Eventfilter.

        Args:
            obj: Obj.
            event: Event.

        Returns:
            The result of the operation.
        """
        if obj == self.previous_project_combo and event.type() == event.Resize:
            # Reapply elision for all items in the combo box on resize
            for index in range(self.previous_project_combo.count()):
                full_path = self.previous_project_combo.itemData(index)
                elided_text = self.elide_path(full_path)
                log_message(f"Full text  : {full_path}")  # noqa E203
                log_message(f"Elided text : {elided_text}")  # noqa E203
                self.previous_project_combo.setItemText(index, elided_text)
        return super().eventFilter(obj, event)

    def update_tooltip(self):
        """Update tooltip with the full path of the current item."""
        full_path = self.previous_project_combo.currentData()
        self.previous_project_combo.setToolTip(full_path)

    def on_previous_project_changed(self, index=None):
        """Refresh panel state when a previous project is selected."""
        self.working_dir = self.previous_project_combo.currentData()
        self.reload_women_considerations_state()

    def select_directory(self):
        """⚙️ Select directory."""
        directory = QFileDialog.getExistingDirectory(self, "Select Working Directory", self.working_dir)
        if directory:
            self.working_dir = directory
            self.update_recent_projects(directory)  # Update recent projects
            self.settings.setValue("last_working_directory", directory)  # Update last used project

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

    def load_project(self, working_directory=None):
        """Load the project from the working directory."""
        if not working_directory:
            self.working_dir = self.previous_project_combo.currentData()
        else:
            self.working_dir = working_directory
        if not self.working_dir:
            self.switch_to_previous_tab.emit()
            return
        model_path = os.path.join(self.working_dir, "model.json")
        if os.path.exists(model_path):
            # Load women considerations settings from model.json
            self.reload_women_considerations_state()

            self.settings.setValue("last_working_directory", self.working_dir)  # Update last used project
            # Switch to the next tab if an existing project is found
            self.switch_to_next_tab.emit()
            self.set_working_directory.emit(self.working_dir)
        else:
            self.switch_to_previous_tab.emit()
            # QMessageBox.critical(
            #    self, "Error", "Selected project does not contain a model.json file."
            # )

    def showEvent(self, event):
        """Reload checkbox state when panel is shown.

        Args:
            event: Show event.
        """
        super().showEvent(event)
        log_message(
            f"showEvent: Panel shown, working_dir={self.working_dir}",
            tag="Geest",
            level=Qgis.Info,
        )
        # Reload women considerations state from model.json when panel is shown
        self.reload_women_considerations_state()

    def resizeEvent(self, event):
        """⚙️ Resizeevent.

        Args:
            event: Event.
        """
        self.set_font_size()
        super().resizeEvent(event)

    def set_font_size(self):
        """⚙️ Set font size."""
        # Scale the font size to fit the text in the available space
        # log_message(f"Label Width: {self.label.rect().width()}")
        # scale the font size linearly from 16 pt to 8 ps as the width of the panel decreases
        font_size = int(linear_interpolation(self.label.rect().width(), 12, 16, 400, 600))
        # log_message(f"Label Font Size: {font_size}")
        self.label.setFont(QFont("Arial", font_size))

    def reload_women_considerations_state(self):
        """Reload women considerations checkbox state from model.json."""
        if not self.working_dir:
            log_message(
                "reload_women_considerations_state: working_dir not set, returning early",
                tag="Geest",
                level=Qgis.Info,
            )
            return

        model_path = os.path.join(self.working_dir, "model.json")
        if not os.path.exists(model_path):
            log_message(
                f"reload_women_considerations_state: model.json not found at {model_path}",
                tag="Geest",
                level=Qgis.Warning,
            )
            return

        try:
            with open(model_path, "r") as f:
                model_data = json.load(f)
            # Load women considerations enabled state
            women_considerations_enabled = None
            for dimension in model_data.get("dimensions", []):
                if dimension.get("id") == "contextual":
                    women_considerations_enabled = dimension.get("women_considerations_enabled")
                    break
            if women_considerations_enabled is None:
                women_considerations_enabled = model_data.get("women_considerations_enabled", True)
            log_message(
                f"reload_women_considerations_state: Loaded from model.json - women_considerations_enabled={women_considerations_enabled}",
                tag="Geest",
                level=Qgis.Info,
            )

            # Load EPLEX score from the EPLEX indicator in the Contextual dimension
            eplex_score = 0.0
            for dimension in model_data.get("dimensions", []):
                if dimension.get("id") == "contextual":
                    for factor in dimension.get("factors", []):
                        if factor.get("id") == "eplex":
                            for indicator in factor.get("indicators", []):
                                if indicator.get("id") == "eplex_score_indicator":
                                    eplex_score = indicator.get("eplex_score", 0.0)
                                    break
                            break
                    break

            # Block signals while setting values to avoid triggering save
            self.women_considerations_checkbox.blockSignals(True)
            self.eplex_score_spinbox.blockSignals(True)

            log_message(
                f"reload_women_considerations_state: Setting checkbox to {women_considerations_enabled}, spinbox to {eplex_score}",
                tag="Geest",
                level=Qgis.Info,
            )
            self.women_considerations_checkbox.setChecked(women_considerations_enabled)
            self.eplex_score_spinbox.setValue(eplex_score)

            # Unblock signals
            self.women_considerations_checkbox.blockSignals(False)
            self.eplex_score_spinbox.blockSignals(False)

            # Update visibility
            self.women_considerations_changed()
            # Notify tree panel to re-apply women considerations logic on load.
            self.women_considerations_changed_signal.emit()

        except Exception as e:
            log_message(
                f"Error reloading women considerations state: {e}",
                tag="Geest",
                level=Qgis.Critical,
            )
            import traceback

            log_message(traceback.format_exc(), level=Qgis.Critical)

    def women_considerations_changed(self):
        """Handle women considerations checkbox change."""
        is_checked = self.women_considerations_checkbox.isChecked()
        log_message(f"Women considerations changed: {is_checked}", tag="Geest", level=Qgis.Info)

        # Show EPLEX widgets when women considerations is NOT selected
        show_eplex = not is_checked
        self.eplex_label.setVisible(show_eplex)
        self.eplex_description.setVisible(show_eplex)
        self.eplex_score_spinbox.setVisible(show_eplex)

    def save_women_considerations_settings(self):
        """Save women considerations settings to model.json."""
        if not self.working_dir:
            return

        model_path = os.path.join(self.working_dir, "model.json")
        if not os.path.exists(model_path):
            return

        try:
            # Read model.json
            with open(model_path, "r") as f:
                model_data = json.load(f)

            # Update settings
            women_considerations_enabled = self.women_considerations_checkbox.isChecked()
            model_data["women_considerations_enabled"] = women_considerations_enabled

            # Save EPLEX score to the EPLEX indicator in the Contextual dimension
            eplex_score_value = self.eplex_score_spinbox.value()
            for dimension in model_data.get("dimensions", []):
                if dimension.get("id") == "contextual":
                    dimension["women_considerations_enabled"] = women_considerations_enabled
                    dimension["eplex_score"] = eplex_score_value
                    for factor in dimension.get("factors", []):
                        if factor.get("id") == "eplex":
                            for indicator in factor.get("indicators", []):
                                if indicator.get("id") == "eplex_score_indicator":
                                    indicator["eplex_score"] = eplex_score_value
                                    break
                            break
                    break

            # Write back to model.json
            with open(model_path, "w") as f:
                json.dump(model_data, f, indent=2)

            log_message(
                f"Saved women considerations: enabled={model_data['women_considerations_enabled']}, eplex={eplex_score_value}",
                tag="Geest",
                level=Qgis.Info,
            )

            # Emit signal to trigger TreePanel to re-apply women considerations logic
            self.women_considerations_changed_signal.emit()
        except Exception as e:
            log_message(
                f"Error saving women considerations to model.json: {e}",
                tag="Geest",
                level=Qgis.Critical,
            )
