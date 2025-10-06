# coding=utf-8

"""Init for Geest."""

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
import tempfile
import unittest
from shutil import which
from typing import Optional

from qgis.core import Qgis, QgsProject
from qgis.PyQt.QtCore import QSettings, Qt, pyqtSignal
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QAction,
    QApplication,
    QComboBox,
    QDialog,
    QDockWidget,
    QFileDialog,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

# Import your plugin components here
from .core import setting
from .gui import GeestDock, GeestOptionsFactory
from .gui.overlays import LayerDescriptionItem, PieChartItem
from .utilities import log_message, resources_path, version

# Set up logging - see utilites.py log_message for usage
# use log_message instead of QgsMessageLog.logMessage everywhere please....
temp_dir = tempfile.gettempdir()
# Use a timestamp to ensure unique log file names
datestamp = datetime.datetime.now().strftime("%Y%m%d")
log_path_env = os.getenv("GEEST_LOG", 0)
if log_path_env:
    log_file_path = log_path_env
else:
    log_file_path = os.path.join(temp_dir, f"geest_logfile_{datestamp}.log")
logging.basicConfig(
    filename=log_file_path,
    filemode="a",  # Append mode
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.DEBUG,
)
date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
log_message("»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»", force=True)
log_message(f"Geest started at {date}", force=True)
version = version()
log_message(f"Geest Version: {version}")
log_message(f"Logging output to: {log_file_path}", force=True)
log_message(f"log_path_env: {log_path_env}", force=True)
log_message("»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»»", force=True)
log_message("QGIS Version: {}".format(Qgis.QGIS_VERSION), force=True)


def classFactory(iface):  # pylint: disable=missing-function-docstring
    return GeestPlugin(iface)


class GeestPlugin:
    """
    GEEST 2 plugin interface
    """

    project_changed = pyqtSignal()

    def __init__(self, iface):
        self.iface = iface
        self.run_action = None  # type: Optional[QAction]
        self.debug_action = None  # type: Optional[QAction]
        self.options_factory = None
        self.dock_widget = None
        # Initialize profiler attributes
        self.profiler = None
        self.profiler_action = None
        self.save_profile_action = None
        self.is_profiling = False

    def initGui(self):  # pylint: disable=missing-function-docstring
        """
        Initialize the GUI elements of the plugin.
        """
        icon = QIcon(resources_path("resources", "geest-main.svg"))
        self.run_action = QAction(icon, "GEEST Settings", self.iface.mainWindow())
        self.run_action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.run_action)
        self.debug_running = False
        self.label_overlay = None  # for rendering info over the canvas
        self.pie_overlay = None  # for rendering pie chart over the canvas
        # Create the dock widget
        self.dock_widget = GeestDock(
            parent=self.iface.mainWindow(),
            json_file=resources_path("resources", "model.json"),
        )
        # Dont remove this, needed for geometry restore....
        self.dock_widget.setObjectName("GeestDockWidget")  # Set a unique object name
        self.dock_widget.setFeatures(
            QDockWidget.DockWidgetClosable  # noqa: W503
            | QDockWidget.DockWidgetMovable  # noqa: W503
            | QDockWidget.DockWidgetFloatable  # noqa: W503
        )
        QgsProject.instance().readProject.connect(self.dock_widget.qgis_project_changed)

        # This is mainly useful when reloading the plugin - check if we have a
        # project loaded and if there is a model.json file associated with it
        # If there is, we load that and set the tab to the tree panel
        self.dock_widget.qgis_project_changed()

        # Restore geometry and dock area before adding to the main window
        self.restore_geometry()

        # Check the dock area; default to right dock if not set
        settings = QSettings("ESMAP", "Geest")
        dock_area = settings.value("GeestDock/area", Qt.RightDockWidgetArea, type=int)

        # Add the dock widget to the restored or default dock area
        self.iface.addDockWidget(dock_area, self.dock_widget)

        # Find all existing dock widgets in the target dock area
        existing_docks = [
            dw
            for dw in self.iface.mainWindow().findChildren(QDockWidget)
            if self.iface.mainWindow().dockWidgetArea(dw) == dock_area
        ]

        self.iface
        # Tabify the new dock before the first found dock widget, if available
        if existing_docks:
            self.iface.mainWindow().tabifyDockWidget(existing_docks[0], self.dock_widget)
        else:
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)
            legend_tab = self.iface.mainWindow().findChild(QApplication, "Legend")
            if legend_tab:
                self.iface.mainWindow().tabifyDockWidget(legend_tab, self.dock_widget)
        self.dock_widget.raise_()

        # Handle debug mode and additional settings
        developer_mode = int(setting(key="developer_mode", default=0))
        if developer_mode:
            debug_icon = QIcon(resources_path("resources", "geest-debug.svg"))
            self.debug_action = QAction(debug_icon, "GEEST Debug Mode", self.iface.mainWindow())
            self.debug_action.triggered.connect(self.debug)
            self.iface.addToolBarIcon(self.debug_action)

            tests_icon = QIcon(resources_path("resources", "run-tests.svg"))
            self.tests_action = QAction(tests_icon, "Run Tests", self.iface.mainWindow())
            self.tests_action.triggered.connect(self.run_tests)
            self.iface.addToolBarIcon(self.tests_action)

            single_test_icon = QIcon(resources_path("resources", "run-single-test.svg"))
            self.single_test_action = QAction(single_test_icon, "Run Single Test", self.iface.mainWindow())
            self.single_test_action.triggered.connect(self.run_single_test)
            self.iface.addToolBarIcon(self.single_test_action)

            # Add profiler actions for developer mode
            self.setup_profiler_actions()
        else:
            self.tests_action = None
            self.single_test_action = None
            self.debug_action = None

        debug_env = int(os.getenv("GEEST_DEBUG", 0))
        if debug_env:
            self.debug()

        self.options_factory = GeestOptionsFactory()
        self.iface.registerOptionsWidgetFactory(self.options_factory)
        self.setup_map_canvas_items()

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
                        test_dir = "/home/timlinux/dev/python/GEEST/test"
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

                            """  # noqa: E241, E272
                        )

                        log_message("Test modules unloaded")
                        break

    def setup_map_canvas_items(self):
        self.label_overlay = LayerDescriptionItem(self.iface.mapCanvas())
        experimental_features = int(os.getenv("GEEST_EXPERIMENTAL", 0))
        if experimental_features:
            self.pie_overlay = PieChartItem(self.iface.mapCanvas())

    def remove_map_canvas_items(self):
        try:
            if self.label_overlay:
                self.label_overlay.setCanvas(None)
                self.label_overlay.deleteLater()
                self.label_overlay = None
        except Exception as e:  # nosec B110
            del e
            pass  # Cleanup code - acceptable to ignore exceptions
        try:
            if self.pie_overlay:
                self.pie_overlay.setCanvas(None)
                self.pie_overlay.deleteLater()
                self.pie_overlay = None
        except Exception as e:  # nosec B110
            del e
            pass  # Cleanup code - acceptable to ignore exceptions

    def run_single_test(self):
        """Prompt user to select a single test to run in the Python console."""

        # Step 1: Discover all test cases
        test_dir = "/home/timlinux/dev/python/GEEST/test"
        loader = unittest.TestLoader()
        suite = loader.discover(start_dir=test_dir, pattern="test_*.py")

        test_names = []
        for test_group in suite:
            for test_case in test_group:
                for test in test_case:
                    test_names.append(test.id())  # e.g., test_module.ClassName.test_method

        # Step 2: Create and show dialog
        class TestPickerDialog(QDialog):
            def __init__(self, tests, parent=None):
                super().__init__(parent)
                self.setWindowTitle("Select Test to Run")
                layout = QVBoxLayout(self)
                self.combo = QComboBox()
                self.combo.addItems(tests)
                layout.addWidget(self.combo)
                run_button = QPushButton("Run Test")
                layout.addWidget(run_button)
                run_button.clicked.connect(self.accept)

            def selected_test(self):
                return self.combo.currentText()

        dialog = TestPickerDialog(test_names, self.iface.mainWindow())
        if not dialog.exec_():
            return  # Cancelled

        selected_test = dialog.selected_test()

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
        Saves the geometry and dock area of GeestDock to QSettings.
        """
        settings = QSettings("ESMAP", "Geest")

        if self.dock_widget:
            # Save geometry
            settings.setValue("GeestDock/geometry", self.dock_widget.saveGeometry())

            # Save dock area (left or right)
            dock_area = self.iface.mainWindow().dockWidgetArea(self.dock_widget)
            settings.setValue("GeestDock/area", dock_area)

    def restore_geometry(self) -> None:
        """
        Restores the geometry and dock area of GeestDock from QSettings.
        """
        settings = QSettings("ESMAP", "Geest")

        if self.dock_widget:
            # Restore geometry
            geometry = settings.value("GeestDock/geometry")
            if geometry:
                self.dock_widget.restoreGeometry(geometry)

            # Restore dock area (left or right)
            dock_area = settings.value("GeestDock/area", type=int)
            if dock_area is not None:
                self.iface.addDockWidget(dock_area, self.dock_widget)

    def setup_profiler_actions(self):
        """Set up cProfiler actions for developer mode."""
        # Create profiler start/stop action
        profile_icon = QIcon(resources_path("resources", "geest-start-profile.svg"))
        self.profiler_action = QAction(profile_icon, "Start Profiling", self.iface.mainWindow())
        self.profiler_action.triggered.connect(self.toggle_profiler)
        self.iface.addToolBarIcon(self.profiler_action)

        # Create save profile results action (initially disabled)
        save_icon = QIcon(resources_path("resources", "geest-save-profile.svg"))
        self.save_profile_action = QAction(save_icon, "Save Profile Results", self.iface.mainWindow())
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
            stop_icon = QIcon(resources_path("resources", "geest-stop-profile.svg"))
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
        file_dialog.setAcceptMode(QFileDialog.AcceptSave)
        file_dialog.setDefaultSuffix("prof")
        file_dialog.setNameFilter("Profile Data (*.prof);;Stats Text (*.txt);;All Files (*.*)")

        if file_dialog.exec_():
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
                        stats.print_callers(lambda func: "geest" in func[0])
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

        self.remove_map_canvas_items()
        self.kill_debug()
        # Save geometry before unloading
        self.save_geometry()

        # Disconnect the project changed signal
        try:
            # This was giving an error on Carlina's mac
            QgsProject.instance().readProject.disconnect(self.dock_widget.qgis_project_changed)
        except Exception as e:  # nosec B110
            del e
            pass  # Cleanup code - acceptable to ignore exceptions

        # Remove toolbar icons and clean up
        if self.run_action:
            self.iface.removeToolBarIcon(self.run_action)
            self.run_action.deleteLater()
            self.run_action = None

        if self.single_test_action:
            self.iface.removeToolBarIcon(self.single_test_action)
            self.single_test_action.deleteLater()
            self.single_test_action = None

        if self.debug_action:
            self.iface.removeToolBarIcon(self.debug_action)
            self.debug_action.deleteLater()
            self.debug_action = None

        if self.tests_action:
            self.iface.removeToolBarIcon(self.tests_action)
            self.tests_action.deleteLater()
            self.tests_action = None

        # Clean up profiler actions
        if self.profiler_action:
            self.iface.removeToolBarIcon(self.profiler_action)
            self.profiler_action.deleteLater()
            self.profiler_action = None

        if self.save_profile_action:
            self.iface.removeToolBarIcon(self.save_profile_action)
            self.save_profile_action.deleteLater()
            self.save_profile_action = None

        # Unregister options widget factory
        if self.options_factory:
            self.iface.unregisterOptionsWidgetFactory(self.options_factory)
            self.options_factory = None

        # Remove dock widget if it exists
        if self.dock_widget:
            self.iface.removeDockWidget(self.dock_widget)
            self.dock_widget.deleteLater()
            self.dock_widget = None

    def kill_debug(self):
        """Kill any running debugpy debugging sessions"""
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
                if conn.laddr.port == 9000:
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
            title="GEEST",
            message="Close this dialog then open VSCode and start your debug client.",
        )
        import multiprocessing  # pylint: disable=import-outside-toplevel

        if multiprocessing.current_process().pid > 1:
            import debugpy  # pylint: disable=import-outside-toplevel

            debugpy.listen(("127.0.0.1", 9000))  # nosec B104 - localhost only for debug
            debugpy.wait_for_client()
            self.display_information_message_bar(
                title="GEEST",
                message="Visual Studio Code debugger is now attached on port 9000",
            )
            self.debug_action.setEnabled(False)  # prevent user starting it twice
            self.debug_running = True

    def run(self):
        """
        Toggles the visibility of the dock widget.
        """
        if self.dock_widget.isVisible():
            self.dock_widget.hide()
            self.run_action.setText("Show GEEST Panel")
        else:
            self.dock_widget.show()
            self.dock_widget.raise_()
            self.run_action.setText("Hide GEEST Panel")

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
            button.pressed.connect(lambda: self.display_information_message_box(title=title, message=more_details))
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
