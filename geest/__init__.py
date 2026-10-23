# -*- coding: utf-8 -*-
"""Init for GeoE3."""
# ruff: noqa: E402
# flake8: noqa: E402
# The sys.path modification below MUST happen before other imports
# to ensure vendored dependencies in extlibs/ are available.

from __future__ import annotations

import os as _os
import sys as _sys

# Add vendored dependencies to path BEFORE other imports
_extlibs_path = _os.path.join(_os.path.dirname(__file__), "extlibs")
if _os.path.isdir(_extlibs_path) and _extlibs_path not in _sys.path:
    _sys.path.insert(0, _extlibs_path)
del _os, _sys, _extlibs_path  # Clean up module namespace

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

import cProfile
import datetime
import io
import logging
import os
import pstats
import subprocess  # nosec B404
import sys
import tempfile
import unittest
from shutil import which
from typing import Optional

from qgis.core import Qgis, QgsProject
from qgis.PyQt.QtCore import QEvent, QObject, QSettings, Qt, pyqtSignal
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QAction,
    QApplication,
    QComboBox,
    QDialog,
    QDockWidget,
    QFileDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

# Import your plugin components here
from .core import setting
from .gui import GeoE3Dock, GeoE3OptionsFactory
from .gui.overlays import LayerDescriptionItem, PieChartItem
from .utilities import log_message, resources_path, version

# Set up logging - see utilites.py log_message for usage
# use log_message instead of QgsMessageLog.logMessage everywhere please....
temp_dir = tempfile.gettempdir()
# Use a timestamp to ensure unique log file names
datestamp = datetime.datetime.now().strftime("%Y%m%d")
log_path_env = os.getenv("GEOE3_LOG") or os.getenv("GEEST_LOG", 0)
if log_path_env:
    log_file_path = log_path_env
else:
    log_file_path = os.path.join(temp_dir, f"geoe3_logfile_{datestamp}.log")
# truncate the log

logging.basicConfig(
    filename=log_file_path,
    filemode="a",  # Append mode
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.DEBUG,
    # basicConfig() is a no-op if the root logger already has handlers -
    # and it already does by this point: the .core/.gui/.gui.overlays/
    # .utilities imports above transitively load grid_column_utils.py,
    # whose module-level log_message() banner call (if verbose_mode is
    # on) is the first logging.info/warning() call in the process,
    # implicitly self-configuring the root logger with the bare
    # stderr "lastResort" handler before we get here. force=True tears
    # down whatever got attached first and guarantees our file handler
    # wins, regardless of import order.
    force=True,
)
# Suppress PyQt uic module debug spam (push/pop widget, setting property, etc.)
logging.getLogger("PyQt5.uic").setLevel(logging.WARNING)
logging.getLogger("PyQt6.uic").setLevel(logging.WARNING)
date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
log_message("»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»", force=True)
log_message(f"GeoE3 started at {date}", force=True)
version = version()
log_message(f"GeoE3 Version: {version}")
log_message(f"Logging output to: {log_file_path}", force=True)
log_message(f"log_path_env: {log_path_env}", force=True)
log_message("»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»", force=True)
log_message("QGIS Version: {}".format(Qgis.QGIS_VERSION), force=True)


class CanvasOverlayFilter(QObject):
    """Event filter to clear overlay label when clicking on map canvas."""

    def eventFilter(self, obj, event):
        """Filter mouse press events on map canvas to clear overlay.

        Args:
            obj: The object that received the event.
            event: The event to process.

        Returns:
            False to let the event propagate normally.
        """
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            QSettings().setValue("geoe3/overlay_label", "")
            QSettings().setValue("geoe3/pie_data", "")
        return False


def _dock_area_to_int(area):
    """Portable Qt enum → int.

    PyQt5 sip enums support ``int(enum)``; PyQt6 maps DockWidgetArea to a
    pure ``enum.Flag`` where ``int(enum)`` raises and ``.value`` must be
    used instead.
    """
    try:
        return int(area)
    except TypeError:
        return int(area.value)


def _to_dock_widget_area(value):
    """Coerce a QSettings value to a valid Qt.DockWidgetArea.

    PyQt6 no longer auto-converts ints to Qt enums, and the dock area is
    persisted in QSettings as an int. Anything invalid (including
    NoDockWidgetArea) falls back to the right dock area.
    """
    valid_areas = (
        Qt.DockWidgetArea.LeftDockWidgetArea,
        Qt.DockWidgetArea.RightDockWidgetArea,
        Qt.DockWidgetArea.TopDockWidgetArea,
        Qt.DockWidgetArea.BottomDockWidgetArea,
    )
    try:
        value = int(value)
    except (TypeError, ValueError):
        return Qt.DockWidgetArea.RightDockWidgetArea
    for area in valid_areas:
        if value == _dock_area_to_int(area):
            return area
    return Qt.DockWidgetArea.RightDockWidgetArea


def classFactory(iface):  # pylint: disable=missing-function-docstring
    """🔄 Classfactory.

    Args:
        iface: Iface.

    Returns:
        The result of the operation.
    """
    return GeoE3Plugin(iface)


class GeoE3Plugin:
    """
    GEOE3 2 plugin interface.

    This class provides the main interface for the GeoE3 (Geospatial Enabling Environments for Employment Tool)
    plugin for QGIS. It handles the plugin initialization, GUI setup, debugging capabilities,
    profiling tools, and various development utilities.

    Attributes:
        iface: The QGIS interface object
        run_action: Main plugin action for showing/hiding the dock widget
        debug_action: Action for entering debug mode (developer mode only)
        options_factory: Factory for plugin options
        dock_widget: Main plugin dock widget
        profiler: cProfile profiler instance
        profiler_action: Action for starting/stopping profiling
        save_profile_action: Action for saving profiling results
        is_profiling: Boolean flag indicating if profiling is active
    """

    project_changed = pyqtSignal()

    # Class constants
    DEBUG_PORT = 9000  # Port for debugpy connection

    def __init__(self, iface):
        """🏗️ Initialize the instance.

        Args:
            iface: Iface.
        """
        self.iface = iface
        self.run_action = None
        self.debug_action = None
        self.options_factory = None
        self.dock_widget = None
        # Initialize profiler attributes
        self.profiler = None
        self.profiler_action = None
        self.save_profile_action = None
        self.is_profiling = False

    def get_test_directory(self):
        """
        Get the test directory path from GEOE3_TEST_DIR environment variable.

        This method uses the GEOE3_TEST_DIR environment variable
        (with fallback to GEEST_TEST_DIR for backward compatibility).
        Set by scripts/start_qgis.sh or scripts/start_qgis_ltr.sh to point to the project's test directory.

        Returns:
            str: Path to the test directory from environment variable

        Raises:
            ValueError: If GEOE3_TEST_DIR (or GEEST_TEST_DIR) is not set or points to invalid directory
        """
        # Get test directory from environment variable (with fallback for backward compatibility)
        env_test_dir = os.getenv("GEOE3_TEST_DIR") or os.getenv("GEEST_TEST_DIR")

        if not env_test_dir:
            raise ValueError(
                "GEOE3_TEST_DIR environment variable is not set. "
                "Please run QGIS using scripts/start_qgis.sh or scripts/start_qgis_ltr.sh"
            )

        if not os.path.exists(env_test_dir):
            raise ValueError(f"Test directory does not exist: {env_test_dir}")

        if not os.path.isdir(env_test_dir):
            raise ValueError(f"GEOE3_TEST_DIR is not a directory: {env_test_dir}")

        # Verify it contains test files
        try:
            test_files = [f for f in os.listdir(env_test_dir) if f.startswith("test_") and f.endswith(".py")]
            if not test_files:
                raise ValueError(f"No test files found in {env_test_dir}")
        except (OSError, PermissionError) as e:
            raise ValueError(f"Cannot access test directory {env_test_dir}: {e}")

        # Ensure it's in Python path for imports
        if env_test_dir not in sys.path:
            sys.path.insert(0, env_test_dir)
            log_message(f"Added test directory to Python path: {env_test_dir}")

        log_message(f"Using test directory: {env_test_dir}")
        return env_test_dir

    # objectNames of every toolbar action this plugin creates — used to
    # sweep stale instances on load so reloads never stack duplicates.
    _TOOLBAR_ACTION_NAMES = (
        "GeoE3RunAction",
        "GeoE3DebugAction",
        "GeoE3TestsAction",
        "GeoE3SingleTestAction",
        "GeoE3ProfilerAction",
        "GeoE3SaveProfileAction",
    )

    def _remove_stale_toolbar_actions(self):
        """Remove toolbar actions leaked by a previous load of the plugin."""
        for name in self._TOOLBAR_ACTION_NAMES:
            for stale in self.iface.mainWindow().findChildren(QAction, name):
                try:
                    self.iface.removeToolBarIcon(stale)
                    stale.deleteLater()
                except Exception as error:  # nosec B110
                    log_message(f"Could not remove stale action {name}: {error}")

    def initGui(self):  # pylint: disable=missing-function-docstring
        """
        Initialize the GUI elements of the plugin.
        """
        # Sweep any toolbar actions a previous load leaked (a crashed
        # initGui or an unload aborted by an exception) so plugin reloads
        # never stack duplicate buttons.
        self._remove_stale_toolbar_actions()

        icon = QIcon(resources_path("resources", "geoe3-main.svg"))
        self.run_action = QAction(icon, "GeoE3 Settings", self.iface.mainWindow())
        self.run_action.setObjectName("GeoE3RunAction")
        self.run_action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.run_action)
        self.debug_running = False
        self.label_overlay = None  # for rendering info over the canvas
        self.pie_overlay = None  # for rendering pie chart over the canvas
        # Remove any stale dock left behind by a previous load — a crashed
        # initGui, or a plugin reload racing a queued deleteLater — so
        # reloads never stack duplicate GeoE3DockWidget instances.
        for stale_dock in self.iface.mainWindow().findChildren(QDockWidget, "GeoE3DockWidget"):
            self.iface.removeDockWidget(stale_dock)
            stale_dock.setParent(None)
            stale_dock.deleteLater()

        # Create the dock widget
        self.dock_widget = GeoE3Dock(
            parent=self.iface.mainWindow(),
            json_file=resources_path("resources", "model.json"),
        )
        # Dont remove this, needed for geometry restore....
        self.dock_widget.setObjectName("GeoE3DockWidget")  # Set a unique object name
        self.dock_widget.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable  # noqa: W503
            | QDockWidget.DockWidgetFeature.DockWidgetMovable  # noqa: W503
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable  # noqa: W503
        )
        QgsProject.instance().readProject.connect(self.dock_widget.qgis_project_changed)

        # This is mainly useful when reloading the plugin - check if we have a
        # project loaded and if there is a model.json file associated with it
        # If there is, we load that and set the tab to the tree panel
        self.dock_widget.qgis_project_changed()

        # Restore geometry and dock area before adding to the main window
        self.restore_geometry()

        # Check the dock area; default to right dock if not set
        settings = QSettings("ESMAP", "GeoE3")
        dock_area = _to_dock_widget_area(
            settings.value("GeoE3Dock/area", _dock_area_to_int(Qt.DockWidgetArea.RightDockWidgetArea), type=int)
        )

        # Add the dock widget to the restored or default dock area
        self.iface.addDockWidget(dock_area, self.dock_widget)

        # Find all existing dock widgets in the target dock area
        existing_docks = [
            dw
            for dw in self.iface.mainWindow().findChildren(QDockWidget)
            if self.iface.mainWindow().dockWidgetArea(dw) == dock_area and dw is not self.dock_widget
        ]

        # Tabify the new dock before the first found dock widget, if available
        if existing_docks:
            self.iface.mainWindow().tabifyDockWidget(existing_docks[0], self.dock_widget)
        else:
            self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_widget)
            legend_tab = self.iface.mainWindow().findChild(QApplication, "Legend")
            if legend_tab:
                self.iface.mainWindow().tabifyDockWidget(legend_tab, self.dock_widget)
        self.dock_widget.raise_()

        # Handle debug mode and additional settings
        developer_mode = int(setting(key="developer_mode", default=0))
        if developer_mode:
            debug_icon = QIcon(resources_path("resources", "geoe3-debug.svg"))
            self.debug_action = QAction(debug_icon, "GEOE3 Debug Mode", self.iface.mainWindow())
            self.debug_action.setObjectName("GeoE3DebugAction")
            self.debug_action.triggered.connect(self.debug)
            self.iface.addToolBarIcon(self.debug_action)

            tests_icon = QIcon(resources_path("resources", "run-tests.svg"))
            self.tests_action = QAction(tests_icon, "Run Tests", self.iface.mainWindow())
            self.tests_action.setObjectName("GeoE3TestsAction")
            self.tests_action.triggered.connect(self.run_tests)
            self.iface.addToolBarIcon(self.tests_action)

            single_test_icon = QIcon(resources_path("resources", "run-single-test.svg"))
            self.single_test_action = QAction(single_test_icon, "Run Single Test", self.iface.mainWindow())
            self.single_test_action.setObjectName("GeoE3SingleTestAction")
            self.single_test_action.triggered.connect(self.run_single_test)
            self.iface.addToolBarIcon(self.single_test_action)

            # Add profiler actions for developer mode
            self.setup_profiler_actions()
        else:
            self.tests_action = None
            self.single_test_action = None
            self.debug_action = None

        debug_env = int(os.getenv("GEOE3_DEBUG") or os.getenv("GEEST_DEBUG", 0))
        if debug_env:
            self.debug()

        self.options_factory = GeoE3OptionsFactory()
        self.iface.registerOptionsWidgetFactory(self.options_factory)
        self.setup_map_canvas_items()

        # Install event filter to clear overlay label on canvas left-click
        self._canvas_overlay_filter = CanvasOverlayFilter()
        self.iface.mapCanvas().viewport().installEventFilter(self._canvas_overlay_filter)

    def run_tests(self):
        """Run unit tests in the python console."""

        main_window = self.iface.mainWindow()
        action = main_window.findChild(QAction, "mActionShowPythonDialog")
        action.trigger()
        log_message("Python console opened")
        for child in main_window.findChildren(QDockWidget, "PythonConsole"):
            # log_message('Python console dock widget found')
            # log_message(f'Child object name: {child.objectName()}')
            if child.objectName() == "PythonConsole":
                # log_message('Python console dock widget found')
                child.show()
                for widget in child.children():

                    widget_class_name = widget.__class__.__name__
                    # log_message(f'Widget class: {widget_class_name}')

                    if widget_class_name == "PythonConsole":
                        log_message("Running tests in the Python console")
                        # widget_members = dir(widget.console)
                        # for member in widget_members:
                        #    log_message(f'Member: {member}, Type: {type(getattr(widget, member))}')
                        shell = widget.console.shell
                        test_dir = "/home/timlinux/dev/python/GEOE3/test"
                        shell.runCommand("")
                        shell.runCommand("import unittest")
                        shell.runCommand("test_loader = unittest.TestLoader()")
                        shell.runCommand(
                            f'test_suite = test_loader.discover(start_dir="{test_dir}", pattern="test_*.py")'
                        )
                        shell.runCommand("test_runner = unittest.TextTestRunner(verbosity=2)")
                        shell.runCommand("test_runner.run(test_suite)")
                        # Unload test modules
                        shell.runCommand(
                            """
for module_name in list(sys.modules.keys()):
    if module_name.startswith("test_") or module_name.startswith("utilities_for_testing"):
        del sys.modules[module_name]

                            """
                        )  # noqa: E241, E272

                        log_message("Test modules unloaded")
                        break

    def setup_map_canvas_items(self):
        """⚙️ Setup map canvas items."""
        # TEMPORARY: Disable layer description overlay creation.
        # self.label_overlay = LayerDescriptionItem(self.iface.mapCanvas())
        self.label_overlay = None
        experimental_features = int(os.getenv("GEOE3_EXPERIMENTAL") or os.getenv("GEEST_EXPERIMENTAL", 0))
        if experimental_features:
            self.pie_overlay = PieChartItem(self.iface.mapCanvas())

    def remove_map_canvas_items(self):
        """Remove map canvas overlay items safely."""
        try:
            if self.label_overlay:
                self.label_overlay.setCanvas(None)
                self.label_overlay.deleteLater()
                self.label_overlay = None
        except (RuntimeError, AttributeError) as e:
            # Handle cases where Qt objects may have been deleted
            log_message(f"Warning during label overlay cleanup: {e}")
            self.label_overlay = None

        try:
            if self.pie_overlay:
                self.pie_overlay.setCanvas(None)
                self.pie_overlay.deleteLater()
                self.pie_overlay = None
        except (RuntimeError, AttributeError) as e:
            # Handle cases where Qt objects may have been deleted
            log_message(f"Warning during pie overlay cleanup: {e}")
            self.pie_overlay = None

    def run_single_test(self):
        """Prompt user to select a single test to run in the Python console."""

        # Step 1: Get test directory and discover test cases
        try:
            test_dir = self.get_test_directory()
        except ValueError as e:
            log_message(f"Test directory error: {e}")
            self.display_information_message_box(title="Test Directory Error", message=str(e))
            return

        loader = unittest.TestLoader()
        test_names = []
        broken_tests = []

        try:
            suite = loader.discover(start_dir=test_dir, pattern="test_*.py")

            for test_group in suite:
                for test_case in test_group:
                    try:
                        # Try to iterate through the test case
                        for test in test_case:
                            test_names.append(test.id())  # e.g., test_module.ClassName.test_method
                    except TypeError as te:
                        _ = te  # Ignore
                        # This happens when test_case is a _FailedTest (not iterable)
                        if hasattr(test_case, "id"):
                            broken_test_id = test_case.id()
                            broken_tests.append(broken_test_id)
                            log_message(f"Failed test case (import error): {broken_test_id}")
                        else:
                            broken_test_name = f"Unknown test: {test_case}"
                            broken_tests.append(broken_test_name)
                            log_message(f"Failed test case (import error): {broken_test_name}")
                        # Continue to see if other tests can be loaded
                        continue

        except (ImportError, AttributeError) as e:
            log_message(f"Error discovering tests with unittest loader: {e}")
            self.display_information_message_box(
                title="Test Discovery Error",
                message=f"Could not discover tests in {test_dir}.\n\nError: {e}\n\nThis usually means there are import errors in the test files.",
            )
            return

        # Combine working and broken tests for display
        all_test_options = []

        # Add working tests
        for test_name in test_names:
            all_test_options.append(f"✅ {test_name}")

        # Add broken tests
        for broken_test in broken_tests:
            all_test_options.append(f"❌ {broken_test} (Import Error)")

        if not all_test_options:
            self.display_information_message_box(
                title="No Tests Found",
                message=f"No test cases found in {test_dir}.\n\nPlease ensure test files follow the pattern 'test_*.py' and contain TestCase classes.",
            )
            return

        # Step 2: Create and show dialog
        class TestPickerDialog(QDialog):
            """🎯 Test Picker Dialog.

            Attributes:
                combo: Combo.
            """

            def __init__(self, tests, parent=None):
                """🏗️ Initialize the instance.

                Args:
                    tests: Tests.
                    parent: Parent.
                """
                super().__init__(parent)
                self.setWindowTitle("Select Test to Run")
                self.setMinimumWidth(500)  # Make dialog wider to accommodate status icons
                layout = QVBoxLayout(self)

                # Add info label
                info_label = QLabel("✅ = Working tests, ❌ = Tests with import errors")
                info_label.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
                layout.addWidget(info_label)

                self.combo = QComboBox()
                self.combo.addItems(tests)
                layout.addWidget(self.combo)

                run_button = QPushButton("Run Test")
                layout.addWidget(run_button)
                run_button.clicked.connect(self.accept)

            def selected_test(self):
                """⚙️ Selected test.

                Returns:
                    The result of the operation.
                """
                return self.combo.currentText()

        dialog = TestPickerDialog(all_test_options, self.iface.mainWindow())
        if not dialog.exec():
            return  # Cancelled

        selected_test = dialog.selected_test()

        # Check if the selected test is broken (has import error)
        if selected_test.startswith("❌"):
            # Try to import the test to get the specific error message
            test_name = selected_test[2:].split(" (")[0]  # Remove icon and status
            try:
                __import__(test_name.rsplit(".", 1)[0])  # Import module part only
            except Exception as import_error:
                log_message(f"Import error for selected test {test_name}: {import_error}")
                self.display_information_message_box(
                    title="Import Error",
                    message=f"Import error details for test {test_name}:\n\n{import_error}",
                )
                return
            self.display_information_message_box(
                title="Cannot Run Broken Test",
                message=f"This test has import errors and cannot be run.\n\nTest: {selected_test}\n\nPlease fix the import issues in the test file first.",
            )

            return

        # Remove the status indicator (✅) from the test name
        if selected_test.startswith("✅ "):
            selected_test = selected_test[2:]  # Remove "✅ " prefix

        # Step 3: Open Python console and inject run command
        main_window = self.iface.mainWindow()
        action = main_window.findChild(QAction, "mActionShowPythonDialog")
        action.trigger()

        for child in main_window.findChildren(QDockWidget, "PythonConsole"):
            if child.objectName() == "PythonConsole":
                child.show()
                for widget in child.children():
                    if widget.__class__.__name__ == "PythonConsole":
                        shell = widget.console.shell
                        shell.runCommand("")
                        shell.runCommand("import unittest, sys")
                        shell.runCommand(f"test_name = '{selected_test}'")
                        shell.runCommand("test_case = unittest.defaultTestLoader.loadTestsFromName(test_name)")
                        shell.runCommand("runner = unittest.TextTestRunner(verbosity=2)")
                        shell.runCommand("runner.run(test_case)")
                        shell.runCommand(
                            """
for module_name in list(sys.modules.keys()):
    if module_name.startswith("test_") or module_name.startswith("utilities_for_testing"):
        del sys.modules[module_name]
                        """
                        )
                        break

    def save_geometry(self) -> None:
        """
        Saves the geometry and dock area of GeoE3Dock to QSettings.
        """
        settings = QSettings("ESMAP", "GeoE3")

        if self.dock_widget:
            # Save geometry
            settings.setValue("GeoE3Dock/geometry", self.dock_widget.saveGeometry())

            # Save dock area (left or right) as a plain int: PyQt6 enums do
            # not round-trip through QSettings, ints do.
            dock_area = self.iface.mainWindow().dockWidgetArea(self.dock_widget)
            settings.setValue("GeoE3Dock/area", _dock_area_to_int(dock_area))

    def restore_geometry(self) -> None:
        """
        Restores the geometry and dock area of GeoE3Dock from QSettings.
        """
        settings = QSettings("ESMAP", "GeoE3")

        if self.dock_widget:
            # Restore geometry (with fallback to old GeestDock key for backward compatibility)
            geometry = settings.value("GeoE3Dock/geometry") or settings.value("GeestDock/geometry")
            if geometry:
                self.dock_widget.restoreGeometry(geometry)

            # Restore dock area (with fallback to old GeestDock key for backward compatibility)
            stored_area = settings.value("GeoE3Dock/area", type=int) or settings.value("GeestDock/area", type=int)
            if stored_area:
                self.iface.addDockWidget(_to_dock_widget_area(stored_area), self.dock_widget)

    def setup_profiler_actions(self):
        """Set up cProfiler actions for developer mode."""
        # Create profiler start/stop action
        profile_icon = QIcon(resources_path("resources", "geoe3-start-profile.svg"))
        self.profiler_action = QAction(profile_icon, "Start Profiling", self.iface.mainWindow())
        self.profiler_action.setObjectName("GeoE3ProfilerAction")
        self.profiler_action.triggered.connect(self.toggle_profiler)
        self.iface.addToolBarIcon(self.profiler_action)

        # Create save profile results action (initially disabled)
        save_icon = QIcon(resources_path("resources", "geoe3-save-profile.svg"))
        self.save_profile_action = QAction(save_icon, "Save Profile Results", self.iface.mainWindow())
        self.save_profile_action.setObjectName("GeoE3SaveProfileAction")
        self.save_profile_action.triggered.connect(self.save_profile_results)
        self.save_profile_action.setEnabled(False)
        self.iface.addToolBarIcon(self.save_profile_action)

        log_message("Profiler actions set up in developer mode")

    def toggle_profiler(self):
        """Toggle the cProfiler on/off."""
        if not self.is_profiling:
            # Start profiling
            self.profiler = cProfile.Profile()
            self.profiler.enable()
            self.is_profiling = True
            self.profiler_action.setText("Stop Profiling")
            stop_icon = QIcon(resources_path("resources", "geoe3-stop-profile.svg"))
            self.profiler_action.setIcon(stop_icon)
            self.save_profile_action.setEnabled(False)
            log_message("🔍 cProfiler started", level=Qgis.Info)
            self.display_information_message_bar(
                "Profiler",
                "cProfiler is now running. Click 'Stop Profiling' when finished.",
            )
        else:
            # Stop profiling
            self.profiler.disable()
            self.is_profiling = False
            self.profiler_action.setText("Start Profiling")
            self.save_profile_action.setEnabled(True)
            log_message("⏹️ cProfiler stopped", level=Qgis.Info)
            self.display_information_message_bar(
                "Profiler",
                "Profiling stopped. Click 'Save Profile Results' to save the data.",
                duration=15,
            )

            # Show a quick summary in the log
            s = io.StringIO()
            stats = pstats.Stats(self.profiler, stream=s).sort_stats("cumulative")
            stats.print_stats(20)  # Print top 20 time-consuming functions
            log_message("===== Profile Summary =====")
            log_message(s.getvalue())
            log_message("==========================")

    def save_profile_results(self):
        """Save the cProfiler results to a file."""
        if not self.profiler:
            self.display_information_message_bar("Error", "No profile data available.")
            return

        # Ask user for file location
        file_dialog = QFileDialog()
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        file_dialog.setDefaultSuffix("prof")
        file_dialog.setNameFilter("Profile Data (*.prof);;Stats Text (*.txt);;All Files (*.*)")

        if file_dialog.exec():
            selected_file = file_dialog.selectedFiles()[0]
            file_format = file_dialog.selectedNameFilter()

            try:
                if "prof" in file_format:
                    # Binary format for later analysis
                    self.profiler.dump_stats(selected_file)
                    message = f"Profile data saved to {selected_file}\n\nUse Python's pstats module or tools like SnakeViz to analyze."
                else:
                    # Text format
                    with open(selected_file, "w") as f:
                        stats = pstats.Stats(self.profiler, stream=f)
                        stats.sort_stats("cumulative")
                        stats.print_callers(lambda func: "geoe3" in func[0])
                        stats.print_stats()
                    message = f"Profile stats saved to {selected_file}"

                self.display_information_message_box(title="Profile Saved", message=message)
                log_message(f"💾 Profile data saved to {selected_file}", level=Qgis.Info)
            except Exception as e:
                self.display_information_message_box(
                    title="Error Saving Profile",
                    message=f"Failed to save profile data: {str(e)}",
                )
                log_message(f"Error saving profile: {e}", level=Qgis.Critical)
            # Check if pyprof2calltree is available in the path

            if which("pyprof2calltree"):
                try:
                    # Convert the profile data to a call tree format
                    kcachegrind_file = selected_file + ".calltree"
                    with open(kcachegrind_file, "w") as f:
                        stats = pstats.Stats(self.profiler)
                        stats.stream = f
                        stats.strip_dirs()
                        stats.sort_stats("cumulative")
                        stats.print_callers()
                        stats.print_stats()
                    subprocess.run(
                        [
                            "pyprof2calltree",
                            "-i",
                            selected_file,
                            "-o",
                            kcachegrind_file,
                        ],
                        check=False,
                    )  # nosec B603 B607
                    log_message(f"Call tree data saved to {kcachegrind_file}", level=Qgis.Info)
                except Exception as e:
                    log_message(
                        f"Error converting profile to call tree: {e}",
                        level=Qgis.Critical,
                    )
            else:
                log_message(
                    "pyprof2calltree is not available in the system path",
                    level=Qgis.Warning,
                )
            # Check if kcachegrind is available in the system path
            if which("kcachegrind"):
                try:
                    subprocess.Popen(["kcachegrind", f"{selected_file}.calltree"])  # nosec B603 B607
                    log_message("Opening call tree data in kcachegrind", level=Qgis.Info)
                except Exception as e:
                    log_message(f"Error opening kcachegrind: {e}", level=Qgis.Critical)
            else:
                self.display_information_message_box(
                    title="KCacheGrind Not Found",
                    message=(
                        "KCacheGrind is not installed or not available in the system path. "
                        "Please install it to view the call tree data."
                    ),
                )

    def unload(self):  # pylint: disable=missing-function-docstring
        """
        Unload the plugin from QGIS.
        Removes all added actions, widgets, and options to ensure a clean unload.
        """
        # Stop profiling if active
        if self.is_profiling and self.profiler:
            self.profiler.disable()
            self.is_profiling = False
            log_message("Profiler stopped during plugin unload")

        # Every phase below is individually guarded: one failing step must
        # never abort unload, or everything after it (toolbar actions, the
        # dock widget, the options page) leaks and duplicates on reload.
        try:
            self.remove_map_canvas_items()
        except Exception as e:  # nosec B110
            log_message(f"Warning during canvas item cleanup: {e}")
        try:
            self.kill_debug()
        except Exception as e:  # nosec B110
            log_message(f"Warning during debug cleanup: {e}")
        # Save geometry before unloading
        try:
            self.save_geometry()
        except Exception as e:  # nosec B110
            log_message(f"Warning saving dock geometry: {e}")

        # Disconnect the project changed signal
        try:
            QgsProject.instance().readProject.disconnect(self.dock_widget.qgis_project_changed)
        except Exception as e:  # nosec B110
            # Signal already disconnected, or Qt objects already deleted
            log_message(f"Warning during signal disconnection: {e}")

        # Remove toolbar icons and clean up (each guarded so one dead Qt
        # object cannot abort the rest of the cleanup)
        for action_attr in (
            "run_action",
            "single_test_action",
            "debug_action",
            "tests_action",
            "profiler_action",
            "save_profile_action",
        ):
            action = getattr(self, action_attr, None)
            if action:
                try:
                    self.iface.removeToolBarIcon(action)
                    action.deleteLater()
                except Exception as e:  # nosec B110
                    log_message(f"Warning removing {action_attr}: {e}")
            setattr(self, action_attr, None)

        # Unregister options widget factory
        try:
            if self.options_factory:
                self.iface.unregisterOptionsWidgetFactory(self.options_factory)
                self.options_factory = None
        except Exception as e:  # nosec B110
            log_message(f"Warning unregistering options factory: {e}")

        # Remove canvas event filter
        try:
            if hasattr(self, "_canvas_overlay_filter") and self._canvas_overlay_filter:
                self.iface.mapCanvas().viewport().removeEventFilter(self._canvas_overlay_filter)
                self._canvas_overlay_filter = None
        except Exception as e:  # nosec B110
            log_message(f"Warning removing canvas event filter: {e}")

        # Remove dock widget if it exists. Reparent to None before the
        # queued deleteLater so an immediate plugin reload cannot find the
        # old instance still attached to the main window.
        if self.dock_widget:
            self.iface.removeDockWidget(self.dock_widget)
            self.dock_widget.setParent(None)
            self.dock_widget.deleteLater()
            self.dock_widget = None

    def kill_debug(self):
        """Kill any running debugpy debugging sessions.

        Returns:
            bool: True if debug processes were killed, False otherwise.
        """
        try:
            # First try to use debugpy's built-in close method if available
            try:
                import debugpy

                if hasattr(debugpy, "is_client_connected") and debugpy.is_client_connected():  # noqa F841  # noqa F841
                    log_message("Closing debugpy connection via API")
                    debugpy.disconnect()
            except (ImportError, AttributeError) as e:
                log_message(f"Could not disconnect debugpy via API: {e}")

            # Now look for any debugpy processes on port 9000 and kill them
            # import signal

            import psutil

            killed = False

            # Look for connections in any state, not just LISTEN
            for conn in psutil.net_connections(kind="tcp"):
                if conn.laddr.port == self.DEBUG_PORT:
                    try:
                        process = psutil.Process(conn.pid)
                        log_message(f"Killing debug process {conn.pid}")
                        # Try SIGTERM first, then SIGKILL if necessary
                        process.terminate()
                        gone, still_alive = psutil.wait_procs([process], timeout=3)
                        if still_alive:
                            for p in still_alive:
                                p.kill()
                        killed = True
                    except (
                        psutil.NoSuchProcess,
                        psutil.AccessDenied,
                        psutil.ZombieProcess,
                    ) as e:
                        log_message(f"Error killing process {conn.pid}: {e}")

            # Reset the debug state
            self.debug_running = False
            if self.debug_action:
                self.debug_action.setEnabled(True)

            if killed:
                log_message("Debug processes successfully terminated")
            return killed
        except Exception as e:
            log_message(f"Error in kill_debug: {e}")
            return False

    def debug(self):
        """
        Enters debug mode.
        Shows a message to attach a debugger to the process.
        """
        self.kill_debug()
        self.display_information_message_box(
            title="GeoE3",
            message="Close this dialog then open VSCode and start your debug client.",
        )
        import multiprocessing  # pylint: disable=import-outside-toplevel

        if multiprocessing.current_process().pid > 1:
            import debugpy  # pylint: disable=import-outside-toplevel

            debugpy.listen(("127.0.0.1", self.DEBUG_PORT))
            debugpy.wait_for_client()
            self.display_information_message_bar(
                title="GeoE3",
                message=f"Visual Studio Code debugger is now attached on port {self.DEBUG_PORT}",
            )
            if self.debug_action:
                self.debug_action.setEnabled(False)  # prevent user starting it twice
            self.debug_running = True

    def run(self):
        """
        Toggles the visibility of the dock widget.
        """
        if self.dock_widget.isVisible():
            self.dock_widget.hide()
            self.run_action.setText("Show GeoE3 Panel")
        else:
            self.dock_widget.show()
            self.dock_widget.raise_()
            self.run_action.setText("Hide GeoE3 Panel")

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

        Args:
            title: The title of the message bar.
            message: The message inside the message bar.
            more_details: The message inside the 'Show details' button.
            button_text: Text of the button if 'more_details' is not empty.
            duration: The duration for the display, default is 8 seconds.
        """
        self.iface.messageBar().clearWidgets()
        widget = self.iface.messageBar().createMessage(title, message)

        if more_details:
            button = QPushButton(widget)
            button.setText(button_text)
            button.pressed.connect(lambda: self.display_information_message_box(title=title, message=more_details))
            widget.layout().addWidget(button)

        self.iface.messageBar().pushWidget(widget, Qgis.Info, duration)

    def display_information_message_box(
        self, parent=None, title: Optional[str] = None, message: Optional[str] = None
    ) -> None:
        """
        Display an information message box.

        Args:
            parent: The parent widget for the message box.
            title: The title of the message box.
            message: The message inside the message box.
        """
        QMessageBox.information(parent, title, message)
