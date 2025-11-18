# coding=utf-8

"""Helper functions for settings."""

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

import json
from collections import OrderedDict

from qgis.core import QgsProject
from qgis.PyQt.QtCore import QSettings

from .constants import APPLICATION_NAME
from .default_settings import default_settings


def deep_convert_dict(value):
    """Converts any OrderedDict elements in a value to
    ordinary dictionaries, safe for storage in QSettings.

    Args:
        value: value to convert.

    Returns:
        dict: Converted dictionary safe for QSettings storage.
    """
    to_ret = value
    if isinstance(value, OrderedDict):
        to_ret = dict(value)

    try:
        for k, v in to_ret.items():
            to_ret[k] = deep_convert_dict(v)
    except AttributeError:
        pass

    return to_ret


def set_general_setting(key, value, qsettings=None):
    """Set value to QSettings based on key.

    Args:
        key: Unique key for setting.
        value: Value to be saved.
        qsettings: A custom QSettings to use. If it's not defined, it will
            use the default one.
    """
    if not qsettings:
        qsettings = QSettings()

    qsettings.setValue(key, deep_convert_dict(value))


def general_setting(key, default=None, expected_type=None, qsettings=None):
    """Helper function to get a value from settings.

    Args:
        key: Unique key for setting.
        default: The default value in case of the key is not found or there
            is an error.
        expected_type: The type of object expected.
        qsettings: A custom QSettings to use. If it's not defined, it will
            use the default one.

    Returns:
        object: The value of the key in the setting.

    Note:
        The API for QSettings to get a value is different for PyQt and Qt C++.
        In PyQt we can specify the expected type.
        See: http://pyqt.sourceforge.net/Docs/PyQt4/qsettings.html#value
    """
    if qsettings is None:
        qsettings = QSettings()
    try:
        if isinstance(expected_type, type):
            return qsettings.value(key, default, type=expected_type)
        return qsettings.value(key, default)

    except TypeError:
        # LOGGER.debug('exception %s' % e)
        # LOGGER.debug('%s %s %s' % (key, default, expected_type))
        return qsettings.value(key, default)


def delete_general_setting(key, qsettings=None):
    """Delete setting from QSettings.

    Args:
        key: unique key for setting.
        qsettings: A custom QSettings to use. If it's not defined, it will
            use the default one.
    """
    if not qsettings:
        qsettings = QSettings()

    qsettings.remove(key)


def set_setting(key, value, qsettings=None, store_in_project=False):
    """Set value to QSettings based on key in workbench scope.

    Args:
        key: Unique key for setting.
        value: Value to be saved.
        qsettings: A custom QSettings to use. If it's not defined, it will
            use the default one.
        store_in_project: Whether to store the setting in the project.
    """
    full_key = "%s/%s" % (APPLICATION_NAME, key)
    set_general_setting(full_key, value, qsettings)

    if store_in_project:
        QgsProject.instance().writeEntry("geest", key, str(value))


def setting(
    key,
    default=None,
    expected_type=None,
    qsettings=None,
    prefer_project_setting=False,
):
    """Helper function to get a value from settings under workbench scope.

    Args:
        key: Unique key for setting.
        default: The default value in case of the key is not found or there
            is an error.
        expected_type: The type of object expected.
        qsettings: A custom QSettings to use. If it's not defined, it will
            use the default one.
        prefer_project_setting: Whether to prefer project settings over general settings.

    Returns:
        object: The value of the key in the setting.
    """
    if default is None:
        default = default_settings.get(key, None)

    if prefer_project_setting:
        val, ok = QgsProject.instance().readEntry("geest", key)
        if ok:
            return val

    full_key = "%s/%s" % (APPLICATION_NAME, key)
    return general_setting(full_key, default, expected_type, qsettings)


def delete_setting(key, qsettings=None):
    """Delete setting from QSettings under workbench scope.

    Args:
        key: Unique key for setting.
        qsettings: A custom QSettings to use. If it's not defined, it will
            use the default one.
    """
    full_key = "%s/%s" % (APPLICATION_NAME, key)
    delete_general_setting(full_key, qsettings)


def export_setting(file_path, qsettings=None):
    """Export workbench's setting to a file.

    Args:
        file_path: The file to write the exported setting.
        qsettings: A custom QSettings to use. If it's not defined, it will
            use the default one.

    Returns:
        dict: A dictionary of the exported settings.
    """
    settings = {}

    if not qsettings:
        qsettings = QSettings()

    qsettings.beginGroup("geest")
    all_keys = qsettings.allKeys()
    qsettings.endGroup()

    for key in all_keys:
        settings[key] = setting(key, qsettings=qsettings)

    def custom_default(obj):
        """Custom default serializer for JSON export.

        Args:
            obj: Object to serialize.

        Raises:
            TypeError: If object cannot be serialized.

        Returns:
            str: Empty string for null objects.
        """
        if obj is None or (hasattr(obj, "isNull") and obj.isNull()):
            return ""
        raise TypeError

    with open(file_path, "w", encoding="utf8") as json_file:
        json.dump(settings, json_file, indent=2, default=custom_default)

    return settings


def import_setting(file_path, qsettings=None):
    """Import workbench's setting from a file.

    Args:
        file_path: The file to read the imported setting.
        qsettings: A custom QSettings to use. If it's not defined, it will
            use the default one.

    Returns:
        dict: A dictionary of the imported settings.
    """
    with open(file_path, "r", encoding="utf8") as f:
        settings = json.load(f)

    if not qsettings:
        qsettings = QSettings()

    # Clear the previous setting
    qsettings.beginGroup("geest")
    qsettings.remove("")
    qsettings.endGroup()

    for key, value in list(settings.items()):
        set_setting(key, value, qsettings=qsettings)

    return settings
