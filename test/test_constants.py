#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test suite for constants module."""

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

from geest.core.constants import APPLICATION_NAME, GDAL_OUTPUT_DATA_TYPE


class TestConstants(unittest.TestCase):
    """Test suite for constants module."""

    def test_application_name(self):
        """Test that application name is defined correctly."""
        self.assertEqual(APPLICATION_NAME, "Geest")
        self.assertIsInstance(APPLICATION_NAME, str)
        self.assertGreater(len(APPLICATION_NAME), 0)

    def test_gdal_output_data_type(self):
        """Test that GDAL output data type is defined correctly."""
        self.assertEqual(GDAL_OUTPUT_DATA_TYPE, 6)  # Float32
        self.assertIsInstance(GDAL_OUTPUT_DATA_TYPE, int)
        self.assertGreater(GDAL_OUTPUT_DATA_TYPE, 0)


if __name__ == "__main__":
    unittest.main()
