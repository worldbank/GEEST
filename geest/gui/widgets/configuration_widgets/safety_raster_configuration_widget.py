# -*- coding: utf-8 -*-
"""GEEST GUI widgets."""

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
from qgis.PyQt.QtWidgets import QLabel

from geest.core.workflows.mappings import NIGHTTIME_LIGHTS_SAFETY
from geest.utilities import log_message

from .base_configuration_widget import BaseConfigurationWidget


class SafetyRasterConfigurationWidget(BaseConfigurationWidget):
    """

    A widget for configuring safety indicators based on a raster.
    """

    def add_internal_widgets(self) -> None:
        """
        This method is called during the widget initialization and sets up the layout for the UI components.

        This component only provides a label as selecting a raster is the only thing needed.
        """
        try:
            self.info_label = QLabel("A raster layer representing safety")
            self.internal_layout.addWidget(self.info_label)

            data_source = NIGHTTIME_LIGHTS_SAFETY.get("data_source", "Nighttime Lights")
            classes = NIGHTTIME_LIGHTS_SAFETY.get("classes", [])
            example_note = NIGHTTIME_LIGHTS_SAFETY.get("example_note", "")
            note = NIGHTTIME_LIGHTS_SAFETY.get("note", "")
            rows = []
            for entry in classes:
                score = entry.get("score", "")
                label = entry.get("label", "")
                value_range = entry.get("range", "")
                example = entry.get("example", "")
                rows.append(f"<tr><td>{score}</td><td>{label}</td><td>{value_range}</td><td>{example}</td></tr>")

            html = f"""
            <p><b>Nighttime Lights ({data_source})</b></p>
            <p><i>Method: Fisher-Jenks Natural Breaks</i></p>
            <table border='1' cellpadding='4' cellspacing='0'>
                <tr>
                    <th>GEEST Class</th>
                    <th>Description</th>
                    <th>NTL Value Range</th>
                    <th>Example</th>
                </tr>
                {''.join(rows)}
            </table>
            <p style='margin-top: 10px;'><small><i>{example_note}</i></small></p>
            <p style='margin-top: 5px;'><small>{note}</small></p>
            """

            self.mapping_table_label = QLabel()
            self.mapping_table_label.setWordWrap(True)
            self.mapping_table_label.setTextFormat(Qt.RichText)
            self.mapping_table_label.setText(html)
            self.internal_layout.addWidget(self.mapping_table_label)
        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", level=Qgis.Critical)
            import traceback

            log_message(traceback.format_exc(), level=Qgis.Critical)

    def get_data(self) -> dict:
        """

        Returns:
            dict: A dictionary containing the current attributes of the raster layers and/ors.
        """
        if not self.isChecked():
            return None

        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets (raster layers) based on the state of the radio button.

        Args:
            enabled (bool): Whether to enable or disable the internal widgets.
        """
        try:
            self.info_label.setEnabled(enabled)
        except Exception as e:
            log_message(
                f"Error in set_internal_widgets_enabled: {e}",
                tag="Geest",
                level=Qgis.Critical,
            )

    def update_widgets(self, attributes: dict) -> None:
        """
        Updates the internal widgets with the current attributes.

        Only needed in cases where a) there are internal widgets and b)
        the attributes may change externally e.g. in the datasource widget.
        """
        pass
