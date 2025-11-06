#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test suite for settings module."""

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

import unittest
from collections import OrderedDict
from unittest.mock import MagicMock, patch

from geest.core.settings import deep_convert_dict, set_setting, setting


class TestSettings(unittest.TestCase):
    """Test suite for settings module."""

    def test_deep_convert_dict_simple(self):
        """Test deep_convert_dict with simple dict."""
        input_dict = {"key1": "value1", "key2": "value2"}
        result = deep_convert_dict(input_dict)
        self.assertEqual(result, input_dict)
        self.assertIsInstance(result, dict)

    def test_deep_convert_dict_ordered(self):
        """Test deep_convert_dict with OrderedDict."""
        input_dict = OrderedDict([("key1", "value1"), ("key2", "value2")])
        result = deep_convert_dict(input_dict)
        self.assertEqual(result, {"key1": "value1", "key2": "value2"})
        self.assertIsInstance(result, dict)
        self.assertNotIsInstance(result, OrderedDict)

    def test_deep_convert_dict_nested(self):
        """Test deep_convert_dict with nested OrderedDict."""
        input_dict = OrderedDict(
            [
                ("key1", "value1"),
                ("key2", OrderedDict([("nested1", "nestedvalue1")])),
            ]
        )
        result = deep_convert_dict(input_dict)
        self.assertEqual(
            result, {"key1": "value1", "key2": {"nested1": "nestedvalue1"}}
        )
        self.assertIsInstance(result, dict)
        self.assertIsInstance(result["key2"], dict)
        self.assertNotIsInstance(result["key2"], OrderedDict)

    def test_deep_convert_dict_non_dict(self):
        """Test deep_convert_dict with non-dict value."""
        input_value = "simple string"
        result = deep_convert_dict(input_value)
        self.assertEqual(result, input_value)

    @patch("geest.core.settings.QSettings")
    def test_setting_with_default(self, mock_qsettings):
        """Test setting function with default value."""
        mock_settings_instance = MagicMock()
        mock_settings_instance.value.return_value = None
        mock_qsettings.return_value = mock_settings_instance

        result = setting("test_key", default="default_value")

        self.assertEqual(result, "default_value")

    @patch("geest.core.settings.QSettings")
    @patch("geest.core.settings.QgsProject")
    def test_set_setting(self, mock_project, mock_qsettings):
        """Test set_setting function."""
        mock_settings_instance = MagicMock()
        mock_qsettings.return_value = mock_settings_instance

        mock_project_instance = MagicMock()
        mock_project.instance.return_value = mock_project_instance

        set_setting("test_key", "test_value")

        mock_settings_instance.setValue.assert_called()


if __name__ == "__main__":
    unittest.main()
