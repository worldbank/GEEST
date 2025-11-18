#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test suite for i18n module."""

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
from unittest.mock import MagicMock, patch

from geest.core.i18n import setup_translation, tr


class TestI18n(unittest.TestCase):
    """Test suite for i18n module."""

    @patch("geest.core.i18n.QgsSettings")
    @patch("geest.core.i18n.QLocale")
    @patch("geest.core.i18n.QFileInfo")
    def test_setup_translation_with_valid_locale(self, mock_file_info, mock_qlocale, mock_qsettings):
        """Test setup_translation with valid locale."""
        # Mock settings to return a locale
        mock_settings_instance = MagicMock()
        mock_settings_instance.value.return_value = "en_US"
        mock_qsettings.return_value = mock_settings_instance

        # Mock locale
        mock_locale_instance = MagicMock()
        mock_locale_instance.name.return_value = "en_US"
        mock_qlocale.return_value = mock_locale_instance

        # Mock file info to indicate file exists
        mock_file_instance = MagicMock()
        mock_file_instance.exists.return_value = True
        mock_file_instance.absoluteFilePath.return_value = "/path/to/translation.qm"
        mock_file_info.return_value = mock_file_instance

        locale, path = setup_translation()

        self.assertEqual(locale, "en_US")
        self.assertEqual(path, "/path/to/translation.qm")

    @patch("geest.core.i18n.QgsSettings")
    @patch("geest.core.i18n.QLocale")
    @patch("geest.core.i18n.QFileInfo")
    def test_setup_translation_file_not_exists(self, mock_file_info, mock_qlocale, mock_qsettings):
        """Test setup_translation when translation file doesn't exist."""
        # Mock settings to return a locale
        mock_settings_instance = MagicMock()
        mock_settings_instance.value.return_value = "xx_XX"
        mock_qsettings.return_value = mock_settings_instance

        # Mock locale
        mock_locale_instance = MagicMock()
        mock_locale_instance.name.return_value = "xx_XX"
        mock_qlocale.return_value = mock_locale_instance

        # Mock file info to indicate file doesn't exist
        mock_file_instance = MagicMock()
        mock_file_instance.exists.return_value = False
        mock_file_info.return_value = mock_file_instance

        locale, path = setup_translation()

        self.assertEqual(locale, "xx_XX")
        self.assertIsNone(path)

    @patch("geest.core.i18n.QApplication")
    def test_tr_function(self, mock_qapp):
        """Test tr function for translation."""
        mock_qapp.translate.return_value = "Translated text"

        result = tr("Test text", "TestContext")

        mock_qapp.translate.assert_called_once_with("TestContext", "Test text")
        self.assertEqual(result, "Translated text")

    @patch("geest.core.i18n.QApplication")
    def test_tr_function_default_context(self, mock_qapp):
        """Test tr function with default context."""
        mock_qapp.translate.return_value = "Translated text"

        result = tr("Test text")

        mock_qapp.translate.assert_called_once_with("@default", "Test text")
        self.assertEqual(result, "Translated text")


if __name__ == "__main__":
    unittest.main()
