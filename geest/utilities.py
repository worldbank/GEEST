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
from qgis.PyQt.QtCore import QUrl, QSettings
from qgis.PyQt import uic
from qgis.core import QgsMessageLog, Qgis, QgsProject
from qgis.PyQt.QtWidgets import QApplication
from geest.core import setting


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
    including the caller's class or module name and line number."""
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

    # Log to QGIS Message Log
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
