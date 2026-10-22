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

from .base_configuration_widget import BaseConfigurationWidget, legend_cell_html


class SafetyRasterConfigurationWidget(BaseConfigurationWidget):
    """
    A widget for configuring safety indicators based on a raster.

    Allows the user to choose between Jenks Natural Breaks and NOAA
    threshold classification for nighttime lights data.
    """

    def add_internal_widgets(self) -> None:
        """
        Set up the layout for the UI components.

        Adds a classification method selector (Jenks Natural Breaks vs NOAA)
        and an informational table of the scoring classes.
        """
        try:
            self.info_label = QLabel("A raster layer representing safety")
            self.internal_layout.addWidget(self.info_label)

            # --- Classification method selector ---
            self.method_group = QGroupBox("Classification Method:")
            method_layout = QHBoxLayout()
            self.jenks_radio = QRadioButton("Jenks Natural Breaks (6 classes)")
            self.noaa_radio = QRadioButton("NOAA thresholds (5 classes)")

            current_mode = self.attributes.get("ntl_classification_mode", "jenks")
            if current_mode == "noaa":
                self.noaa_radio.setChecked(True)
            else:
                self.jenks_radio.setChecked(True)

            method_layout.addWidget(self.jenks_radio)
            method_layout.addWidget(self.noaa_radio)
            self.method_group.setLayout(method_layout)
            self.internal_layout.addWidget(self.method_group)

            # Emit data_changed whenever the user changes the selection
            self.jenks_radio.toggled.connect(self.update_data)
            self.noaa_radio.toggled.connect(self.update_data)
            self.jenks_radio.toggled.connect(self._on_method_changed)
            self.noaa_radio.toggled.connect(self._on_method_changed)

            # --- Informational class table ---
            self.mapping_table_label = QLabel()
            self.mapping_table_label.setWordWrap(True)
            self.mapping_table_label.setTextFormat(Qt.TextFormat.RichText)
            self.mapping_table_label.setText(self._build_table_html(current_mode))
            self.internal_layout.addWidget(self.mapping_table_label)
        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", level=Qgis.Critical)
            import traceback

            log_message(traceback.format_exc(), level=Qgis.Critical)

    def _build_table_html(self, mode: str) -> str:
        """Build the informational class mapping table for the selected mode."""
        data_source = NIGHTTIME_LIGHTS_SAFETY.get("data_source", "Nighttime Lights")
        if mode == "noaa":
            rows = [
                f"<tr><td>1</td><td>Very Low</td><td>0 - 0.5</td><td>No / very faint light</td>{legend_cell_html(1)}</tr>",
                f"<tr><td>2</td><td>Low</td><td>0.5 - 1</td><td>Low illumination</td>{legend_cell_html(2)}</tr>",
                f"<tr><td>3</td><td>Moderate</td><td>1 - 5</td><td>Moderate illumination</td>{legend_cell_html(3)}</tr>",
                f"<tr><td>4</td><td>High</td><td>5 - 50</td><td>High illumination</td>{legend_cell_html(4)}</tr>",
                f"<tr><td>5</td><td>Very High</td><td>&gt; 50</td><td>Intense illumination</td>{legend_cell_html(5)}</tr>",
            ]
            intro = "NOAA thresholds produce 5 classes (scores 1-5)."
            example_note = "Fixed value ranges from the NASA Black Marble user guide."
            note = (
                "NOAA mode applies fixed thresholds: values are classified as 1 (0-0.5), "
                "2 (0.5-1), 3 (1-5), 4 (5-50), or 5 (>50)."
            )
        else:
            classes = NIGHTTIME_LIGHTS_SAFETY.get("classes", [])
            rows = []
            for entry in classes:
                score = entry.get("score", "")
                label = entry.get("label", "")
                value_range = entry.get("range", "")
                example = entry.get("example", "")
                rows.append(
                    f"<tr><td>{score}</td><td>{label}</td><td>{value_range}</td><td>{example}</td>"
                    f"{legend_cell_html(score)}</tr>"
                )
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
                <th>Legend</th>
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

            mode = "noaa" if self.noaa_radio.isChecked() else "jenks"
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
            dict: Attributes dict with ntl_classification_mode set to 'jenks' or 'noaa',
                  or None if the widget radio button is not checked.
        """
        if not self.isChecked():
            return None

        if self.noaa_radio.isChecked():
            self.attributes["ntl_classification_mode"] = "noaa"
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
            if mode == "noaa":
                self.noaa_radio.setChecked(True)
            else:
                self.jenks_radio.setChecked(True)
            self._on_method_changed()
        except Exception as e:
            log_message(
                f"Error in update_widgets: {e}",
                tag="GeoE3",
                level=Qgis.Critical,
            )
