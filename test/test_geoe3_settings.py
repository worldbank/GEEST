# -*- coding: utf-8 -*-
"""Smoke/regression tests for the GeoE3 settings panel.

Constructs the real GeoE3Settings widget (loaded from
geoe3_settings_base.ui) to catch widget-name/.ui mistakes that a plain
code review can miss - e.g. a QSpinBox added to the .ui file under one
object name while the Python side reads/writes a different one.
"""
import unittest
from unittest.mock import patch

from geest.gui.geoe3_settings import GeoE3Settings


class TestH3PyramidStepsSettings(unittest.TestCase):
    """National and local are separate spinboxes/settings - see tree_panel's text."""

    def test_defaults_to_three(self):
        with patch("geest.gui.geoe3_settings.setting", side_effect=lambda key, default=None: default):
            widget = GeoE3Settings()
        self.assertEqual(widget.h3_pyramid_steps_national.value(), 3)
        self.assertEqual(widget.h3_pyramid_steps_local.value(), 3)

    def test_reads_the_configured_values_independently(self):
        def fake_setting(key, default=None):
            return {"h3_pyramid_steps_national": 5, "h3_pyramid_steps_local": 2}.get(key, default)

        with patch("geest.gui.geoe3_settings.setting", side_effect=fake_setting):
            widget = GeoE3Settings()
        self.assertEqual(widget.h3_pyramid_steps_national.value(), 5)
        self.assertEqual(widget.h3_pyramid_steps_local.value(), 2)

    def test_apply_writes_both_spinbox_values(self):
        with patch("geest.gui.geoe3_settings.setting", side_effect=lambda key, default=None: default):
            widget = GeoE3Settings()
        widget.h3_pyramid_steps_national.setValue(7)
        widget.h3_pyramid_steps_local.setValue(4)

        with patch("geest.gui.geoe3_settings.set_setting") as mock_set_setting:
            widget.apply()

        mock_set_setting.assert_any_call(key="h3_pyramid_steps_national", value=7)
        mock_set_setting.assert_any_call(key="h3_pyramid_steps_local", value=4)


if __name__ == "__main__":
    unittest.main()
