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

from geest.core.workflows.mappings import MAPPING_REGISTRY
from geest.utilities import log_message

from .base_configuration_widget import BaseConfigurationWidget


class StreetLightsConfigurationWidget(BaseConfigurationWidget):
    """
    Street light locations configuration options (currently none)
    """

    def _add_mapping_thresholds_table(self) -> None:
        """
        Adds a table showing scale-specific streetlight scoring from the mappings module.
        """
        try:
            analysis_scale = self.attributes.get("analysis_scale") or "national"
            factor_id = self.attributes.get("factor_id")
            indicator_id = self.attributes.get("id")
            factor_name = self.attributes.get("factor_name") or "Streetlights Safety"

            mapping = MAPPING_REGISTRY.get(factor_id) if factor_id else None
            if not mapping and indicator_id:
                mapping = MAPPING_REGISTRY.get(indicator_id)
            if not mapping:
                return

            config = mapping.get(analysis_scale, mapping.get("national"))
            if not config:
                return

            buffer_distance = config.get("buffer_distance", "")
            buffer_type = config.get("buffer_type", "")
            scoring_method = config.get("scoring_method", "")
            scores = config.get("scores", {})
            percentage_scores = config.get("percentage_scores", {})

            buffer_label = f"{buffer_distance} {buffer_type}"

            rows = []
            if percentage_scores:
                min_values = sorted(percentage_scores.keys())
                for index, min_pct in enumerate(min_values):
                    score = percentage_scores[min_pct]
                    next_min = min_values[index + 1] if index + 1 < len(min_values) else None
                    if next_min is None:
                        range_label = f"{min_pct}-100%"
                    elif min_pct == 0 and next_min == 1:
                        range_label = "0%"
                    else:
                        range_label = f"{min_pct}-{next_min - 1}%"
                    rows.append(f"<tr><td>{range_label}</td><td>{score}</td></tr>")
            elif scores:
                inside_score = scores.get("intersects_buffer", 0)
                outside_score = scores.get("no_intersection", 0)
                rows.append(f"<tr><td>≤ {buffer_label}</td><td>{inside_score}</td></tr>")
                rows.append(f"<tr><td>&gt; {buffer_label}</td><td>{outside_score}</td></tr>")

            html = f"""
            <p><b>{factor_name} ({analysis_scale.title()} Scale)</b></p>
            <p>Buffer: {buffer_label} ({scoring_method})</p>
            <table border='1' cellpadding='4' cellspacing='0'>
                <tr><th>Range</th><th>Score</th></tr>
                {''.join(rows)}
            </table>
            """

            self.mapping_table_label = QLabel()
            self.mapping_table_label.setWordWrap(True)
            self.mapping_table_label.setTextFormat(Qt.RichText)
            self.mapping_table_label.setText(html)
            self.internal_layout.addWidget(self.mapping_table_label)

        except Exception as e:
            log_message(f"Error adding mapping thresholds table: {e}", level=Qgis.Warning)
            import traceback

            log_message(traceback.format_exc(), level=Qgis.Warning)

    def add_internal_widgets(self) -> None:
        """⚙️ Add internal widgets.

        Returns:
            The result of the operation.
        """
        try:
            self.info_label = QLabel("Point locations representing street lights")
            self.internal_layout.addWidget(self.info_label)
            self._add_mapping_thresholds_table()

        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", level=Qgis.Critical)
            import traceback

            log_message(traceback.format_exc(), level=Qgis.Critical)

    def get_data(self) -> dict:
        """
        Retrieves and returns the current state of the widget.

        Returns:
            dict: A dictionary containing the current attributes
        """
        if not self.isChecked():
            return None

        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets (both point and polyline layers) based on the state of the radio button.

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
