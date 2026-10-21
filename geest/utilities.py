# coding=utf-8

"""Utilities for GEOE3."""

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

import inspect
import logging
import os
import platform
import re
import subprocess  # nosec B404
import tempfile
from datetime import datetime

from osgeo import gdal, ogr, osr
from qgis.core import (
    Qgis,
    QgsLayerTreeGroup,
    QgsMessageLog,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QRect, QSettings, QUrl
from qgis.PyQt.QtGui import QPalette, QPixmap
from qgis.PyQt.QtWidgets import QApplication

from geest.core.settings import setting

# Small joining words that stay lowercase in a title unless they are the
# first or last word.
_TITLE_CASE_STOP_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "but",
    "by",
    "for",
    "if",
    "in",
    "nor",
    "of",
    "on",
    "or",
    "so",
    "the",
    "to",
    "up",
    "with",
    "yet",
    "vs",
}


def title_case(text: str) -> str:
    """Convert text to Title Case for display.

    Every word is capitalised except small joining words, which stay
    lowercase unless they are the first or last word. Tokens that are
    already all-caps (e.g. ``WBL``, ``ACLED``) and tokens containing digits
    are preserved as-is, so acronyms are not mangled the way ``str.title()``
    would. Apostrophes are handled correctly (``Women's``, not ``Women'S``).

    Args:
        text: The string to convert.

    Returns:
        The string converted to title case.
    """
    words = re.split(r"([^A-Za-z0-9']+)", text)
    word_indices = [i for i, part in enumerate(words) if part and part[0].isalnum()]
    total_words = len(word_indices)
    for position, index in enumerate(word_indices):
        part = words[index]
        if part.isupper() or not part.isalpha():
            # Preserve acronyms (e.g. WBL, ACLED) and tokens with digits.
            continue
        lower = part.lower()
        if lower in _TITLE_CASE_STOP_WORDS and 0 < position < total_words - 1:
            continue
        words[index] = lower[:1].upper() + lower[1:]
    return "".join(words)


def theme_background_image() -> QPixmap:
    """🔄 Theme background image.

    Returns:
        The result of the operation.
    """
    # Load the background image
    if is_qgis_dark_theme_active():
        background_image = QPixmap(resources_path("resources", "images", "background-dark.png"))
    else:
        background_image = QPixmap(resources_path("resources", "images", "background.png"))
    return background_image


def theme_stylesheet() -> str:
    """
    Returns the appropriate stylesheet based on whether the QGIS dark theme is active.

    Returns:
        str: The stylesheet for the active theme (light or dark).
    """
    # 🚩 Be careful: One mistake in the style sheet and none of the
    # subsequent rules will evaluate. If you are changing something,
    # try move it to the top and check that all the subsequent rules work still...
    light_theme_stylesheet = f"""
        QPushButton {{
            background-color: rgba(62, 121, 155, 180);
            color: #ffffff;
            border: 1px solid #3E799B;
            border-radius: 3px;
            padding: 4px 8px;
        }}
        QPushButton:hover {{
            background-color: rgba(62, 121, 155, 220);
        }}
        QPushButton:pressed {{
            background-color: rgba(45, 90, 117, 255);
        }}
        QToolTip {{
            color: #000000;
            background-color: #FFFFDC;
            border: 1px solid black;
            border-radius: 2px; /* Rounded corners */
            padding: 0px;
        }}
        QMenu {{
            background-color: #ffffff; /* Solid white background */
            color: #000000;            /* Text color */
            border: 1px solid #aaa;
            border-radius: 6px;
        }}

        QDialog {{
            background-color: rgba(255, 255, 255, 255);
            color: #000000;
        }}
        QDockWidget, QDialog {{
            background-image: url({resources_path("resources", "images", "background.png")});
            background-repeat: no-repeat;
            background-position: center;
        }}
        QMenu::item {{
            padding: 5px 20px;
        }}

        QMenu::item:selected {{
            background-color: #f0f0f0;
        }}
        QTreeView, QTableWidget {{
            background-color: rgba(0, 0, 0, 0);
            border: 1px solid #aaa;
        }}
        QScrollArea {{
            background-color: rgba(0, 0, 0, 0);
        }}
        QScrollArea > QWidget > QWidget {{
            background-color: rgba(0, 0, 0, 0);
        }}
        QScrollArea > QWidget > QWidget > QLabel {{
            background-color: rgba(118, 182, 178, 0);
        }}
        /* Uncomment this last rule when making a change to check that
        all rules are rendering, then comment it out again... */
        /*
        QWidget {{
            border: 2px solid red;
        }}
        */
    """  # noqa E241,E222,E221

    dark_theme_stylesheet = f"""
        QToolTip {{
            color: #ffffff;
            background-color: #333333;
            border: 1px solid #555555;
            border-radius: 8px; /* Rounded corners */
            padding: 5px;
            max-width: 200px; /* Fixed maximum width */
        }}

        QMenu {{
            background-color: #000000; /* Solid black background */
            color: #ffffff;            /* Text color */
            border: 1px solid #555555;
            border-radius: 6px;
        }}

        QDockWidget {{
            background-image: url({resources_path("resources", "images", "background-dark.png")});
            background-repeat: no-repeat;
            background-position: center;
        }}

        QMenu::item {{
            padding: 5px 20px;
        }}

        QMenu::item:selected {{
            background-color: #444444;
        }}

        QPushButton {{
            background-color: rgba(62, 121, 155, 25);
            color: #ffffff;
        }}

        QDialog {{
            background-color: rgba(118, 182, 178, 255);
            color: #000000;
        }}

        QScrollArea {{
            background: transparent;
        }}
    """  # noqa E202

    if is_qgis_dark_theme_active():
        return dark_theme_stylesheet
    else:
        return light_theme_stylesheet


def log_window_geometry(geometry) -> None:
    """
    Creates an ASCII-art diagram of the dialog's dimensions based on the
    given geometry (a QRect) and logs it with log_message in QGIS.

    Args:
        geometry: A QRect object or object with .rect() method containing the geometry information.

    Example output:

    +-------------------- 500 px -------------------+
    |                                               |
    |                                               300 px
    |                                               |
    +-----------------------------------------------+

    """
    try:
        if type(geometry) is QRect:
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
    top_line = f"\n+{'-' * char_width} {w} px {'-' * 20}+"
    middle_line = f"|{' ' * 47}{h} px"
    bottom_line = f"+{'-' * 47}+\n"

    diagram = (
        f"{top_line}\n"
        f"|                                               |\n"  # noqa E222
        f"{middle_line}\n"
        f"|                                               |\n"  # noqa E222
        f"{bottom_line}"
    )

    log_message(diagram)


def get_free_memory_mb() -> float:
    """
    Attempt to return the free system memory in MB (approx).
    Uses only modules from the Python standard library.

    Returns:
        float: Free memory in megabytes, or 0.0 if unable to determine.
    """
    system = platform.system()

    # --- Windows ---
    if system == "Windows":
        try:
            import ctypes.wintypes

            class MEMORYSTATUSEX(ctypes.Structure):
                """🎯 M E M O R Y S T A T U S E X."""

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
        except Exception:  # nosec B110
            pass  # Platform-specific memory check - fallback acceptable

    # --- Linux ---
    elif system == "Linux":
        # /proc/meminfo is a common place to get memory info on Linux
        try:
            with open("/proc/meminfo") as f:
                meminfo = f.read()
                match = re.search(r"^MemAvailable:\s+(\d+)\skB", meminfo, re.MULTILINE)
                if match:
                    return float(match.group(1)) / 1024.0
        except Exception:  # nosec B110
            pass  # Platform-specific memory check - fallback acceptable

    # --- macOS (Darwin) ---
    elif system == "Darwin":
        # One approach is to parse the output of the 'vm_stat' command
        try:
            vm_stat = subprocess.check_output(["vm_stat"]).decode("utf-8")  # nosec
            page_size = 4096  # Usually 4096 bytes
            free_pages = 0
            # Look for "Pages free: <number>"
            match = re.search(r"Pages free:\s+(\d+).", vm_stat)
            if match:
                free_pages = int(match.group(1))
            return free_pages * page_size / (1024.0 * 1024.0)
        except Exception:  # nosec B110
            pass  # Platform-specific memory check - fallback acceptable

    # If none of the above worked or on an unsupported OS, return 0.0
    return 0.0


def log_layer_count() -> None:
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
    log_entry = (
        f"""{timestamp} - Layer count: {layer_count} - Free memory: {free_memory_mb:.2f} MB\n"""  # noqa E501,E297,E222
    )

    # Send to QGIS log (optional)
    log_message(log_entry, level=Qgis.Info, tag="LayerCount")

    # Also write to a log file in the system temp directory
    tmp_dir = tempfile.gettempdir()
    log_file_path = os.path.join(tmp_dir, "geoe3_layer_count_log.txt")
    with open(log_file_path, "a") as log_file:
        log_file.write(log_entry)


def resources_path(*args) -> str:
    """Get the path to our resources folder.

    .. versionadded:: 2.0

    Note that in version 2.0 we removed the use of Qt Resource files in
    favour of directly accessing on-disk resources.

    Args:
        *args: List of path elements e.g. ['img', 'logos', 'image.png']

    Returns:
        str: Absolute path to the resources folder.
    """
    path = os.path.dirname(__file__)
    path = os.path.abspath(path)
    for item in args:
        path = os.path.abspath(os.path.join(path, item))

    return path


def resource_url(path: str) -> str:
    """Get the a local filesystem url to a given resource.

    .. versionadded:: 1.0

    Note that we dont use Qt Resource files in
    favour of directly accessing on-disk resources.

    Args:
        path (str): Path to resource e.g. /home/timlinux/foo/bar.png

    Returns:
        str: A valid file url e.g. file:///home/timlinux/foo/bar.png
    """
    url = QUrl.fromLocalFile(path)
    return str(url.toString())


def get_ui_class(ui_file: str):
    """Get UI Python class from .ui file.

       Can be filename.ui or subdirectory/filename.ui

    Args:
        ui_file (str): The file of the ui in safe.gui.ui

    Returns:
        The UI class from the .ui file.
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


def log_message(message: str, level: int = Qgis.Info, tag: str = "GeoE3", force: bool = False) -> None:
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
    if not verbose_mode and not force and level != Qgis.Critical:
        return
    # Retrieve caller information
    caller_frame = inspect.stack()[1]
    caller_module = inspect.getmodule(caller_frame[0])
    caller_name = caller_module.__name__ if caller_module else "Unknown"
    line_number = caller_frame.lineno

    # Combine caller information with message
    full_message = f"[{caller_name}: {line_number}] {message}"

    # Log to QGIS Message Log if it is critical or force is true
    if level == Qgis.Critical or force:
        QgsMessageLog.logMessage(full_message, tag=tag, level=level)

    # Log to the file with appropriate logging level
    # codeql[python/clear-text-logging-sensitive-data] - General logging utility; callers responsible for masking sensitive data
    if level == Qgis.Info:
        logging.info(full_message)
    elif level == Qgis.Warning:
        logging.warning(full_message)
    elif level == Qgis.Critical:
        logging.critical(full_message)
    else:
        logging.debug(full_message)


_SQLITE_SAFETY_OPTION_KEYS = ("OGR_SQLITE_JOURNAL", "OGR_SQLITE_SYNCHRONOUS", "SQLITE_USE_OGR_VFS")


def apply_sqlite_write_safety_options() -> dict:
    """Configure safer SQLite options for GeoPackage access and return the prior values.

    These GDAL config options are process-wide, so callers must snapshot the
    return value and pass it to :func:`restore_sqlite_write_safety_options`
    once their GeoPackage access is done.

    Returns:
        dict: The previous value of each option, for restoration.
    """
    previous = {key: gdal.GetConfigOption(key) for key in _SQLITE_SAFETY_OPTION_KEYS}

    gdal.SetConfigOption("OGR_SQLITE_JOURNAL", "WAL")
    gdal.SetConfigOption("OGR_SQLITE_SYNCHRONOUS", "NORMAL")
    # SQLITE_USE_OGR_VFS must stay OFF: the OGR VSI layer does not implement
    # SQLite file locking, so with it enabled, concurrent connections to the
    # same GeoPackage (e.g. a workflow's AreaIterator reads interleaved with
    # grid_column_utils writes, especially across several indicators run
    # back-to-back in one dimension) can interleave page writes unprotected
    # and corrupt the GeoPackage or hand back a stale/freed dataset handle -
    # seen in the field as a Windows access violation inside getFeatures().
    gdal.SetConfigOption("SQLITE_USE_OGR_VFS", "NO")
    return previous


def restore_sqlite_write_safety_options(previous: dict) -> None:
    """Restore GDAL SQLite options captured by :func:`apply_sqlite_write_safety_options`.

    Args:
        previous: The dict returned by apply_sqlite_write_safety_options.
    """
    for key, value in previous.items():
        gdal.SetConfigOption(key, value)


def geoe3_layer_ids():
    """Get a list of the layer ids in the GeoE3 group.

    This is useful for filtering layers in the layer combo boxes.

    e.g.:

    layer_ids = geoe3_layer_ids()
    def custom_filter(layer):
        return layer.id() not in layer_ids
    map_layer_combo.setFilters(QgsMapLayerProxyModel.CustomLayerFilter)
    map_layer_combo.proxyModel().setCustomFilterFunction(custom_filter)

    """
    # Get the layer tree root
    root = QgsProject.instance().layerTreeRoot()

    # Find the "GeoE3" group
    geoe3_group = root.findGroup("GeoE3")
    if not geoe3_group:
        # No group named "GeoE3," no need to filter
        return

    # Recursively collect IDs of all layers in the "GeoE3" group
    def collect_layer_ids(group: QgsLayerTreeGroup) -> set:
        """🔄 Collect layer ids.

        Args:
            group: Group.

        Returns:
            The result of the operation.
        """
        layer_ids = set()
        for child in group.children():
            if isinstance(child, QgsLayerTreeGroup):
                # Recursively collect from subgroups
                layer_ids.update(collect_layer_ids(child))
            elif hasattr(child, "layerId"):  # Check if the child is a layer
                layer_ids.add(child.layerId())
        return layer_ids

    geoe3_layer_ids = collect_layer_ids(geoe3_group)

    return geoe3_layer_ids


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
    # Scoped enum form works on both PyQt5 and PyQt6 (QGIS 3.x and 4.x)
    window_color = palette.color(QPalette.ColorRole.Window)
    text_color = palette.color(QPalette.ColorRole.WindowText)
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

    Args:
        value (float): The value to scale.
        output_min (float): The minimum of the output range.
        output_max (float): The maximum of the output range.
        domain_min (float): The minimum of the input range.
        domain_max (float): The maximum of the input range.

    Returns:
        float: The scaled value.

    Raises:
        ValueError: If domain_min and domain_max are the same value.
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


def open_with_system_handler(path: str) -> None:
    """Open a file or folder with the default system application, detached.

    This must never block the calling (QGIS main) thread and must never
    join the viewer to QGIS's process group: subprocess.run freezes the
    event loop until the viewer exits, leaving QGIS unresponsive behind
    the viewer window, and force-closing the viewer then takes QGIS down
    with it.

    Args:
        path (str): File or directory to open.
    """
    try:
        if os.name == "nt":  # Windows
            os.startfile(path)  # nosec B606
            return
        opener = "open" if platform.system().lower() == "darwin" else "xdg-open"
        subprocess.Popen(  # nosec B603 B607
            [opener, path],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        log_message(f"Could not open '{path}' with the system handler: {e}", level=Qgis.Warning)


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


def version() -> str:
    """Return the version of the plugin.

    Returns:
        str: The version string from metadata.txt.
    """
    metadata_file = os.path.join(os.path.dirname(__file__), "metadata.txt")
    version = "Unknown"
    try:
        with open(metadata_file, "r") as f:
            for line in f:
                # Handle both "version=" and "version ="
                if line.strip().startswith("version"):
                    version = line.split("=")[1].strip().strip('"').strip("'")
                    break
    except FileNotFoundError:
        log_message("metadata.txt file not found", level=Qgis.Warning)
    return version


##########################################################################
# CRS / UTM calculation
##########################################################################
def calculate_utm_zone_from_layer(layer) -> str:
    """
    Determine a UTM zone from the centroid of a layer's bounding box.
    Reprojected into WGS84 if possible. Return EPSG code.

    Args:
        layer: A QGIS vector or raster layer.

    Returns:
        str: UTM zone EPSG code, or None if layer is invalid.
    """
    if layer is None:
        return None
    # Get the layer's extent
    extent = layer.extent()
    bbox = (extent.xMinimum(), extent.xMaximum(), extent.yMinimum(), extent.yMaximum())

    # Get the source EPSG code from the layer
    source_epsg = layer.crs().authid().split(":")[-1] if layer.crs().authid() else None

    # Calculate the UTM zone
    utm_zone = calculate_utm_zone(bbox, source_epsg)
    return utm_zone


def calculate_utm_zone(bbox: tuple, source_epsg: str = None) -> str:
    """
    Determine a UTM zone from the centroid of (xmin, xmax, ymin, ymax),
    reprojected into WGS84 if possible. Return EPSG code.

    Args:
        bbox (tuple): Bounding box as (xmin, xmax, ymin, ymax).
        source_epsg (str): Source EPSG code. Defaults to None.

    Returns:
        str: UTM zone EPSG code.
    """
    xmin, xmax, ymin, ymax = bbox
    log_message("Bounding box: %s, %s, %s, %s" % (xmin, xmax, ymin, ymax))
    cx = xmin + (0.5 * (xmax - xmin))
    cy = ymin + (0.5 * (ymax - ymin))
    log_message("Centroid: %s, %s" % (cx, cy))
    # If there's no source SRS, we'll assume it's already lat/lon
    if not source_epsg:
        # fallback if no known EPSG
        log_message("Source has no EPSG, defaulting to a naive assumption of WGS84 bounding box.")
        lon, lat = cx, cy
    else:
        # We have a known EPSG, so transform centroid to WGS84
        src_ref = osr.SpatialReference()
        src_ref.ImportFromEPSG(int(source_epsg))
        wgs84_ref = osr.SpatialReference()
        wgs84_ref.ImportFromEPSG(4326)
        ct = osr.CoordinateTransformation(src_ref, wgs84_ref)
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(cx, cy)
        point.Transform(ct)
        lon = point.GetX()
        lat = point.GetY()
        log_message("Transformed centroid: %s, %s" % (lon, lat))

    # Standard formula for UTM zone
    utm_zone = int((lon + 180) // 6) + 1
    log_message("UTM zone: %s" % utm_zone)
    # We guess north or south
    if lat >= 0:
        zone = 32600 + utm_zone  # Northern Hemisphere
    else:
        zone = 32700 + utm_zone  # Southern Hemisphere
    log_message("EPSG code: %s" % zone)
    return zone
