# coding=utf-8

"""Init for Geest2."""

__copyright__ = "Copyright 2024, Tim Sutton"
__license__ = "GPL version 3"
__email__ = "tim@kartoza.com"
__revision__ = "$Format:%H$"

# -----------------------------------------------------------
# Copyright (C) 2022 Tim Sutton
# -----------------------------------------------------------
# Licensed under the terms of GNU GPL 3
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# ---------------------------------------------------------------------

import os
import time
from typing import Optional

from qgis.PyQt.QtCore import Qt, QSettings
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QMessageBox, QPushButton, QAction, QDockWidget
from qgis.core import Qgis

# Import your plugin components here
from .core import setting  # , JSONValidator
from .utilities import resources_path
from .gui import GeestOptionsFactory, GeestDock


def classFactory(iface):  # pylint: disable=missing-function-docstring
    return GeestPlugin(iface)


class GeestPlugin:
    """
    GEEST 2 plugin interface
    """

    def __init__(self, iface):
        self.iface = iface
        self.run_action: Optional[QAction] = None
        self.debug_action: Optional[QAction] = None
        self.options_factory = None
        self.dock_widget = None

    def initGui(self):  # pylint: disable=missing-function-docstring
        """
        Initialize the GUI elements of the plugin.
        """
        icon = QIcon(resources_path("resources", "geest-main.svg"))
        self.run_action = QAction(icon, "GEEST", self.iface.mainWindow())
        self.run_action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.run_action)
        
        # Create the dock widget
        self.dock_widget = GeestDock(
            parent=self.iface.mainWindow(),
            json_file=resources_path("resources", "model.json"),
        )
        self.dock_widget.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.dock_widget.setFloating(False)
        self.dock_widget.setFeatures(QDockWidget.DockWidgetMovable)
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)

        # Restore geometry of dock widget
        self.restore_geometry()

        # Handle debug mode and additional settings
        debug_mode = int(setting(key="debug_mode", default=0))
        if debug_mode:
            debug_icon = QIcon(resources_path("resources", "geest-debug.svg"))
            self.debug_action = QAction(
                debug_icon, "GEEST Debug Mode", self.iface.mainWindow()
            )
            self.debug_action.triggered.connect(self.debug)
            self.iface.addToolBarIcon(self.debug_action)
        
        debug_env = int(os.getenv("GEEST_DEBUG", 0))
        if debug_env:
            self.debug()

        self.options_factory = GeestOptionsFactory()
        self.iface.registerOptionsWidgetFactory(self.options_factory)

    def save_geometry(self) -> None:
        """
        Saves the geometry of all relevant widgets to QSettings.
        """
        settings = QSettings()
        
        if self.dock_widget:
            # Save geometry of the dock widget
            settings.setValue("Geest/dockWidgetGeometry", self.dock_widget.saveGeometry())

    def restore_geometry(self) -> None:
        """
        Restores the geometry of all relevant widgets from QSettings.
        """
        settings = QSettings()

        if self.dock_widget:
            geometry = settings.value("Geest/dockWidgetGeometry")
            if geometry:
                self.dock_widget.restoreGeometry(geometry)


    def unload(self):  # pylint: disable=missing-function-docstring
        """
        Unload the plugin from QGIS.
        Removes all added actions, widgets, and options to ensure a clean unload.
        """
        # Save geometry before unloading
        self.save_geometry()
        
        # Remove toolbar icons
        if self.run_action:
            self.iface.removeToolBarIcon(self.run_action)
            self.run_action.deleteLater()
            self.run_action = None

        if self.debug_action:
            self.iface.removeToolBarIcon(self.debug_action)
            self.debug_action.deleteLater()
            self.debug_action = None

        # Unregister options widget factory
        if self.options_factory:
            self.iface.unregisterOptionsWidgetFactory(self.options_factory)
            self.options_factory = None

        # Remove dock widget if it exists
        if self.dock_widget:
            self.iface.removeDockWidget(self.dock_widget)
            self.dock_widget.deleteLater()
            self.dock_widget = None

    def debug(self):
        """
        Enters debug mode.
        Shows a message to attach a debugger to the process.
        """
        self.display_information_message_box(
            title="GEEST",
            message="Close this dialog then open VSCode and start your debug client.",
        )
        time.sleep(2)
        import multiprocessing  # pylint: disable=import-outside-toplevel

        if multiprocessing.current_process().pid > 1:
            import debugpy  # pylint: disable=import-outside-toplevel

            debugpy.listen(("0.0.0.0", 9000))
            debugpy.wait_for_client()
            self.display_information_message_bar(
                title="GEEST",
                message="Visual Studio Code debugger is now attached on port 9000",
            )

    def run(self):
        """
        Shows the settings dialog.
        """
        self.iface.showOptionsDialog(
            parent=self.iface.mainWindow(), currentPage="geest"
        )

    def display_information_message_bar(
        self,
        title: Optional[str] = None,
        message: Optional[str] = None,
        more_details: Optional[str] = None,
        button_text: str = "Show details ...",
        duration: int = 8,
    ) -> None:
        """
        Display an information message bar.
        :param title: The title of the message bar.
        :param message: The message inside the message bar.
        :param more_details: The message inside the 'Show details' button.
        :param button_text: Text of the button if 'more_details' is not empty.
        :param duration: The duration for the display, default is 8 seconds.
        """
        self.iface.messageBar().clearWidgets()
        widget = self.iface.messageBar().createMessage(title, message)

        if more_details:
            button = QPushButton(widget)
            button.setText(button_text)
            button.pressed.connect(
                lambda: self.display_information_message_box(
                    title=title, message=more_details
                )
            )
            widget.layout().addWidget(button)

        self.iface.messageBar().pushWidget(widget, Qgis.Info, duration)

    def display_information_message_box(
        self, parent=None, title: Optional[str] = None, message: Optional[str] = None
    ) -> None:
        """
        Display an information message box.
        :param title: The title of the message box.
        :param message: The message inside the message box.
        """
        QMessageBox.information(parent, title, message)
