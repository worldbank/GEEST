# -*- coding: utf-8 -*-
"""GEOE3 GUI widgets."""

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

from qgis.core import Qgis
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QRadioButton

from geest.core.workflows.mappings import NIGHTTIME_LIGHTS_SAFETY
from geest.utilities import log_message

from .base_configuration_widget import BaseConfigurationWidget


class SafetyRasterConfigurationWidget(BaseConfigurationWidget):
    """
    A widget for configuring safety indicators based on a raster.

    Allows the user to choose between Jenks Natural Breaks and Binary
    classification for nighttime lights data.
    """

    def add_internal_widgets(self) -> None:
        """
        Set up the layout for the UI components.

        Adds a classification method selector (Jenks Natural Breaks vs Binary)
        and an informational table of the scoring classes.
        """
        try:
            self.info_label = QLabel("A raster layer representing safety")
            self.internal_layout.addWidget(self.info_label)

            # --- Classification method selector ---
            self.method_group = QGroupBox("Classification Method:")
            method_layout = QHBoxLayout()
            self.jenks_radio = QRadioButton("Jenks Natural Breaks (6 classes)")
            self.binary_radio = QRadioButton("Binary (dark / lit)")

            current_mode = self.attributes.get("ntl_classification_mode", "jenks")
            if current_mode == "binary":
                self.binary_radio.setChecked(True)
            else:
                self.jenks_radio.setChecked(True)

            method_layout.addWidget(self.jenks_radio)
            method_layout.addWidget(self.binary_radio)
            self.method_group.setLayout(method_layout)
            self.internal_layout.addWidget(self.method_group)

            # Emit data_changed whenever the user changes the selection
            self.jenks_radio.toggled.connect(self.update_data)
            self.binary_radio.toggled.connect(self.update_data)
            self.jenks_radio.toggled.connect(self._on_method_changed)
            self.binary_radio.toggled.connect(self._on_method_changed)

            # --- Informational class table ---
            self.mapping_table_label = QLabel()
            self.mapping_table_label.setWordWrap(True)
            self.mapping_table_label.setTextFormat(Qt.RichText)
            self.mapping_table_label.setText(self._build_table_html(current_mode))
            self.internal_layout.addWidget(self.mapping_table_label)
        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", level=Qgis.Critical)
            import traceback

            log_message(traceback.format_exc(), level=Qgis.Critical)

    def _build_table_html(self, mode: str) -> str:
        """Build the informational class mapping table for the selected mode."""
        data_source = NIGHTTIME_LIGHTS_SAFETY.get("data_source", "Nighttime Lights")
        if mode == "binary":
            rows = [
                "<tr><td>0</td><td>No Access</td><td>= 0</td><td>No light</td></tr>",
                "<tr><td>5</td><td>Very High</td><td>> 0</td><td>Light detected</td></tr>",
            ]
            intro = "Binary mode produces 2 classes using an exact zero boundary."
            example_note = "Example values shown are illustrative for binary light presence classification."
            note = (
                "Binary mode applies a strict zero boundary: values <= 0 map to class 0, and values > 0 map to class 5."
            )
        else:
            classes = NIGHTTIME_LIGHTS_SAFETY.get("classes", [])
            rows = []
            for entry in classes:
                score = entry.get("score", "")
                label = entry.get("label", "")
                value_range = entry.get("range", "")
                example = entry.get("example", "")
                rows.append(f"<tr><td>{score}</td><td>{label}</td><td>{value_range}</td><td>{example}</td></tr>")
            intro = "Jenks Natural Breaks produces 6 classes (scores 0-5)."
            example_note = NIGHTTIME_LIGHTS_SAFETY.get("example_note", "")
            note = NIGHTTIME_LIGHTS_SAFETY.get("note", "")

        return f"""
        <p><b>Nighttime Lights ({data_source})</b></p>
        <p><i>{intro}</i></p>
        <table border='1' cellpadding='4' cellspacing='0'>
            <tr>
                <th>GEOE3 Class</th>
                <th>Description</th>
                <th>NTL Value Range</th>
                <th>Example</th>
            </tr>
            {''.join(rows)}
        </table>
        <p style='margin-top: 10px;'><small><i>{example_note}</i></small></p>
        <p style='margin-top: 5px;'><small>{note}</small></p>
        """

    def _on_method_changed(self) -> None:
        """Update the informational table when the method selection changes."""
        try:
            if not hasattr(self, "mapping_table_label"):
                return

            mode = "binary" if self.binary_radio.isChecked() else "jenks"
            self.mapping_table_label.setText(self._build_table_html(mode))
        except Exception as e:
            log_message(
                f"Error in _on_method_changed: {e}",
                tag="GeoE3",
                level=Qgis.Critical,
            )

    def get_data(self) -> dict:
        """
        Return attributes updated with the current classification mode selection.

        Returns:
            dict: Attributes dict with ntl_classification_mode set to 'jenks' or 'binary',
                  or None if the widget radio button is not checked.
        """
        if not self.isChecked():
            return None

        if self.binary_radio.isChecked():
            self.attributes["ntl_classification_mode"] = "binary"
        else:
            self.attributes["ntl_classification_mode"] = "jenks"

        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enable or disable internal widgets based on the outer radio button state.

        Args:
            enabled: Whether to enable or disable the internal widgets.
        """
        try:
            self.info_label.setEnabled(enabled)
            self.method_group.setEnabled(enabled)
        except Exception as e:
            log_message(
                f"Error in set_internal_widgets_enabled: {e}",
                tag="GeoE3",
                level=Qgis.Critical,
            )

    def update_widgets(self, attributes: dict) -> None:
        """
        Sync the classification method radio buttons from an updated attributes dict.

        Args:
            attributes: Updated attributes dict, expected to contain ntl_classification_mode.
        """
        try:
            self.attributes = attributes
            mode = attributes.get("ntl_classification_mode", "jenks")
            if mode == "binary":
                self.binary_radio.setChecked(True)
            else:
                self.jenks_radio.setChecked(True)
            self._on_method_changed()
        except Exception as e:
            log_message(
                f"Error in update_widgets: {e}",
                tag="GeoE3",
                level=Qgis.Critical,
            )
