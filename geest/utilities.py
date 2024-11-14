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
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt import uic
from qgis.core import QgsMessageLog, Qgis
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
