# coding=utf-8

"""Utilities for AnimationWorkbench."""

__copyright__ = "Copyright 2022, Tim Sutton"
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
import logging
import inspect
from datetime import datetime
import tempfile
import re
import platform
import subprocess

from qgis.PyQt.QtCore import QUrl, QSettings, QRect
from qgis.PyQt import uic
from qgis.core import QgsMessageLog, Qgis, QgsProject, QgsLayerTreeGroup, QgsVectorLayer
from qgis.PyQt.QtWidgets import QApplication
from qgis.core import QgsProject, Qgis
from geest.core import setting


def log_window_geometry(geometry):
    """
    Creates an ASCII-art diagram of the dialog's dimensions based on the
    given geometry (a QRect) and logs it with log_message in QGIS.

    Example output:

    +-------------------- 500 px -------------------+
    |                                               |
    |                                               300 px
    |                                               |
    +-----------------------------------------------+

    """
    try:
        if type(geometry) == QRect:
            rect = geometry
        else:
            rect = geometry.rect()
    except AttributeError:
        log_message("Could not get geometry from dialog", level=Qgis.Warning)
        log_message(type(geometry), level=Qgis.Warning)
        return

    w = rect.width()
    h = rect.height()
    char_width = 20 - len(str(w))
    top_line = f"\n+{'-'*char_width} {w} px {'-'*20}+"
    middle_line = f"|{' ' * 47}{h} px"
    bottom_line = f"+{'-'*47}+\n"

    diagram = (
        f"{top_line}\n"
        f"|                                               |\n"
        f"{middle_line}\n"
        f"|                                               |\n"
        f"{bottom_line}"
    )

    log_message(diagram)


def get_free_memory_mb():
    """
    Attempt to return the free system memory in MB (approx).
    Uses only modules from the Python standard library.
    """
    system = platform.system()

    # --- Windows ---
    if system == "Windows":
        try:
            import ctypes.wintypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.wintypes.DWORD),
                    ("dwMemoryLoad", ctypes.wintypes.DWORD),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            memoryStatus = MEMORYSTATUSEX()
            memoryStatus.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memoryStatus))
            return memoryStatus.ullAvailPhys / (1024 * 1024)
        except Exception:
            pass

    # --- Linux ---
    elif system == "Linux":
        # /proc/meminfo is a common place to get memory info on Linux
        try:
            with open("/proc/meminfo") as f:
                meminfo = f.read()
                match = re.search(r"^MemAvailable:\s+(\d+)\skB", meminfo, re.MULTILINE)
                if match:
                    return float(match.group(1)) / 1024.0
        except Exception:
            pass

    # --- macOS (Darwin) ---
    elif system == "Darwin":
        # One approach is to parse the output of the 'vm_stat' command
        try:
            vm_stat = subprocess.check_output(["vm_stat"]).decode("utf-8")
            page_size = 4096  # Usually 4096 bytes
            free_pages = 0
            # Look for "Pages free: <number>"
            match = re.search(r"Pages free:\s+(\d+).", vm_stat)
            if match:
                free_pages = int(match.group(1))
            return free_pages * page_size / (1024.0 * 1024.0)
        except Exception:
            pass

    # If none of the above worked or on an unsupported OS, return 0.0
    return 0.0


def log_layer_count():
    """
    Append the number of layers in the project and a timestamp to a text file,
    along with free system memory (approximate), using only standard library dependencies.
    """
    # Count QGIS layers
    layer_count = len(QgsProject.instance().mapLayers())

    # Gather system free memory (MB)
    free_memory_mb = get_free_memory_mb()

    # Create a timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Compose the log entry text
    log_entry = f"{timestamp} - Layer count: {layer_count} - Free memory: {free_memory_mb:.2f} MB\n"

    # Send to QGIS log (optional)
    log_message(log_entry, level=Qgis.Info, tag="LayerCount")

    # Also write to a log file in the system temp directory
    tmp_dir = tempfile.gettempdir()
    log_file_path = os.path.join(tmp_dir, "geest_layer_count_log.txt")
    with open(log_file_path, "a") as log_file:
        log_file.write(log_entry)


def resources_path(*args):
    """Get the path to our resources folder.

    .. versionadded:: 2.0

    Note that in version 2.0 we removed the use of Qt Resource files in
    favour of directly accessing on-disk resources.

    :param args List of path elements e.g. ['img', 'logos', 'image.png']
    :type args: str

    :return: Absolute path to the resources folder.
    :rtype: str
    """
    path = os.path.dirname(__file__)
    path = os.path.abspath(path)
    for item in args:
        path = os.path.abspath(os.path.join(path, item))

    return path


def resource_url(path):
    """Get the a local filesystem url to a given resource.

    .. versionadded:: 1.0

    Note that we dont use Qt Resource files in
    favour of directly accessing on-disk resources.

    :param path: Path to resource e.g. /home/timlinux/foo/bar.png
    :type path: str

    :return: A valid file url e.g. file:///home/timlinux/foo/bar.png
    :rtype: str
    """
    url = QUrl.fromLocalFile(path)
    return str(url.toString())


def get_ui_class(ui_file):
    """Get UI Python class from .ui file.

       Can be filename.ui or subdirectory/filename.ui

    :param ui_file: The file of the ui in safe.gui.ui
    :type ui_file: str
    """
    os.path.sep.join(ui_file.split("/"))
    ui_file_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            # os.pardir,
            "ui",
            ui_file,
        )
    )
    return uic.loadUiType(ui_file_path)[0]


def log_message(
    message: str, level: int = Qgis.Info, tag: str = "Geest", force: bool = False
) -> None:
    """
    Logs a message to both QgsMessageLog and a text file,
    including the caller's class or module name and line number.

    Args:
        message (str): The message to log.
        level (int): The logging level (Qgis.Info, Qgis.Warning, Qgis.Critical).
        tag (str): The tag for the message.
        force (bool): If True, log the message even if verbose_mode is off.
    """
    verbose_mode = setting(key="verbose_mode", default=0)
    if not verbose_mode and not force:
        return
    # Retrieve caller information
    caller_frame = inspect.stack()[1]
    caller_module = inspect.getmodule(caller_frame[0])
    caller_name = caller_module.__name__ if caller_module else "Unknown"
    line_number = caller_frame.lineno

    # Combine caller information with message
    full_message = f"[{caller_name}:{line_number}] {message}"

    # Log to QGIS Message Log if it is critical or force is true
    if level == Qgis.Critical or force:
        QgsMessageLog.logMessage(full_message, tag=tag, level=level)

    # Log to the file with appropriate logging level
    if level == Qgis.Info:
        logging.info(full_message)
    elif level == Qgis.Warning:
        logging.warning(full_message)
    elif level == Qgis.Critical:
        logging.critical(full_message)
    else:
        logging.debug(full_message)


def geest_layer_ids():
    """Get a list of the layer ids in the Geest group.

    This is useful for filtering layers in the layer combo boxes.

    e.g.:

    layer_ids = geest_layer_ids()
    def custom_filter(layer):
        return layer.id() not in layer_ids
    map_layer_combo.setFilters(QgsMapLayerProxyModel.CustomLayerFilter)
    map_layer_combo.proxyModel().setCustomFilterFunction(custom_filter)

    """
    # Get the layer tree root
    root = QgsProject.instance().layerTreeRoot()

    # Find the "Geest" group
    geest_group = root.findGroup("Geest")
    if not geest_group:
        # No group named "Geest," no need to filter
        return

    # Recursively collect IDs of all layers in the "Geest" group
    def collect_layer_ids(group: QgsLayerTreeGroup) -> set:
        layer_ids = set()
        for child in group.children():
            if isinstance(child, QgsLayerTreeGroup):
                # Recursively collect from subgroups
                layer_ids.update(collect_layer_ids(child))
            elif hasattr(child, "layerId"):  # Check if the child is a layer
                layer_ids.add(child.layerId())
        return layer_ids

    geest_layer_ids = collect_layer_ids(geest_group)

    return geest_layer_ids


def is_qgis_dark_theme_active() -> bool:
    """
    Determines if QGIS is using the Night Mapping theme or a dark theme.

    Checks:
    1. QGIS settings for the Night Mapping theme.
    2. Application palette for dark mode.
    3. Stylesheet for references to 'nightmapping'.

    Returns:
        bool: True if Night Mapping theme or a dark theme is active, False otherwise.
    """
    # 1. Check QGIS settings for Night Mapping theme
    settings = QSettings()
    theme_name = settings.value("UI/Theme", "").lower()
    if theme_name == "nightmapping":
        return True

    # 2. Access the application instance
    app = QApplication.instance()
    if not app:
        return False

    # Check the application palette for dark colors
    palette = app.palette()
    window_color = palette.color(palette.Window)
    text_color = palette.color(palette.WindowText)
    if window_color.lightness() < text_color.lightness():
        return True

    # 3. Check the stylesheet for 'nightmapping' references
    stylesheet = app.styleSheet()
    if "nightmapping" in stylesheet.lower():
        return True

    # Default to False if none of the conditions are met
    return False


def linear_interpolation(
    value: float,
    output_min: float,
    output_max: float,
    domain_min: float,
    domain_max: float,
) -> float:
    """
    Scales a value using linear interpolation.

    Parameters:
        value (float): The value to scale.
        output_min (float): The minimum of the output range.
        output_max (float): The maximum of the output range.
        domain_min (float): The minimum of the input range.
        domain_max (float): The maximum of the input range.

    Returns:
        float: The scaled value.
    """
    if domain_min == domain_max:
        raise ValueError("domain_min and domain_max cannot be the same value.")
    if value > domain_max:
        return output_max
    # Compute the scaled value
    scale = (value - domain_min) / (domain_max - domain_min)
    result = output_min + scale * (output_max - output_min)
    # Clamp the value to the output range
    if result < output_min:
        return output_min
    if result > output_max:
        return output_max
    return result


def vector_layer_type(layer: QgsVectorLayer) -> str:
    """
    Determines if a given QgsVectorLayer is a GeoPackage or a Shapefile.

    Args:
        layer (QgsVectorLayer): The QGIS vector layer.

    Returns:
        str: The type of layer ('GPKG', 'SHP', or 'Unknown').
    """
    if not layer.isValid():
        return "Invalid layer"

    # Get the source string and split at the pipe
    source = layer.source().lower()
    base_source = source.split("|")[0]  # Ignore anything after the first pipe

    # Check the file extension
    if base_source.endswith(".gpkg"):
        return "GPKG"
    elif base_source.endswith(".shp"):
        return "SHP"
    else:
        return "Unknown"


def version():
    """Return the version of the plugin."""
    metadata_file = os.path.join(os.path.dirname(__file__), "metadata.txt")
    version = "Unknown"
    try:
        with open(metadata_file, "r") as f:
            for line in f:
                if line.startswith("version="):
                    version = line.split("=")[1].strip()
                    break
    except FileNotFoundError:
        log_message("metadata.txt file not found", level=Qgis.Warning)
    return version
