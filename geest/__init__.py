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

import time
from typing import Optional

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QMessageBox, QPushButton, QAction, QDockWidget
from qgis.core import Qgis

#from .geest import Geest
#from .core import RenderQueue, setting
from .core import setting, JSONValidator
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

        #self.render_queue: Optional[RenderQueue] = None
        self.run_action: Optional[QAction] = None
        self.debug_action: Optional[QAction] = None
        self.options_factory = None

    def initGui(self):  # pylint: disable=missing-function-docstring

        #self.render_queue = RenderQueue()
        icon = QIcon(resources_path("resources", "geest-main.svg"))

        # Validate our json schema first
        #validator = JSONValidator('resources/schema.json', 'resources/model.json')
        #validator.validate_json()

        self.run_action = QAction(icon, "GEEST", self.iface.mainWindow())
        self.run_action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.run_action)
        self.dock_widget = GeestDock(parent=self.iface.mainWindow(), json_file=resources_path("resources", "model.json"))
        self.dock_widget.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        #self.dock_widget.setWidget(Geest(self.iface.mainWindow(), self.iface))
        self.dock_widget.setFloating(False)
        self.dock_widget.setFeatures(QDockWidget.DockWidgetMovable)
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)
        # If you change debug_mode to true, after clicking
        # this toolbutton, QGIS will block until it can attach
        # to the remote debugger
        debug_mode = int(setting(key="debug_mode", default=0))
        if debug_mode:
            debug_icon = QIcon(resources_path("icons", "geest-debug.svg"))
            self.debug_action = QAction(
                debug_icon, "GEEST Debug Mode", self.iface.mainWindow()
            )
            self.debug_action.triggered.connect(self.debug)
            self.iface.addToolBarIcon(self.debug_action)

        self.options_factory = GeestOptionsFactory()
        self.iface.registerOptionsWidgetFactory(self.options_factory)

    def debug(self):
        """
        Enters debug mode
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

    def unload(self):  # pylint: disable=missing-function-docstring
        self.iface.removeToolBarIcon(self.run_action)
        self.iface.unregisterOptionsWidgetFactory(self.options_factory)
        self.options_factory = None
        del self.run_action
        if self.debug_action:
            self.iface.removeToolBarIcon(self.debug_action)
            del self.debug_action

    def run(self):
        """
        Shows the workbench dialog
        """
        dialog = Geest(
            parent=self.iface.mainWindow(),
            iface=self.iface,
            render_queue=self.render_queue,
        )
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.show()

    def display_information_message_bar(
        self,
        title=None,
        message=None,
        more_details=None,
        button_text="Show details ...",
        duration=8,
    ):
        """
        Display an information message bar.
        :param title: The title of the message bar.
        :type title: basestring
        :param message: The message inside the message bar.
        :type message: basestring
        :param more_details: The message inside the 'Show details' button.
        :type more_details: basestring
        :param button_text: Text of the button if 'more_details' is not empty.
        :type button_text: basestring
        :param duration: The duration for the display, default is 8 seconds.
        :type duration: int
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

    def display_information_message_box(self, parent=None, title=None, message=None):
        """
        Display an information message box.
        :param title: The title of the message box.
        :type title: basestring
        :param message: The message inside the message box.
        :type message: basestring
        """
        QMessageBox.information(parent, title, message)
