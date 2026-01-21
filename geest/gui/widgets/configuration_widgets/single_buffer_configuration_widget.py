# -*- coding: utf-8 -*-
"""📦 Single Buffer Configuration Widget module.

This module contains functionality for single buffer configuration widget.
"""

import traceback

from qgis.core import Qgis
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QHBoxLayout, QLabel, QSpinBox

from geest.core.workflows.mappings import MAPPING_REGISTRY
from geest.utilities import log_message

from .base_configuration_widget import BaseConfigurationWidget


class SingleBufferConfigurationWidget(BaseConfigurationWidget):
    """
    A specialized radio button with additional QSpinBox buffer distance.
    """

    def _add_mapping_thresholds_table(self) -> None:
        """
        Adds a table showing scale-specific buffer distance from the mappings module.
        """
        self.mapping_buffer_distance = None
        try:
            analysis_scale = self.attributes.get("analysis_scale") or "national"
            factor_id = self.attributes.get("factor_id")
            factor_name = self.attributes.get("factor_name") or "Single Buffer Analysis"

            mapping = MAPPING_REGISTRY.get(factor_id) if factor_id else None
            if not mapping:
                return

            config = mapping.get(analysis_scale, mapping.get("national"))
            if not config:
                return

            buffer_distance = config.get("buffer_distance")
            scores = config.get("scores", {})
            if buffer_distance is not None:
                self.mapping_buffer_distance = buffer_distance

            inside_score = scores.get("intersects", 0)
            outside_score = scores.get("no_intersection", 0)

            html = f"""
            <p><b>{factor_name} ({analysis_scale.title()} Scale)</b></p>
            <table border='1' cellpadding='4' cellspacing='0'>
                <tr><th>Distance Range (m)</th><th>Score</th></tr>
                <tr><td>≤ {buffer_distance}</td><td>{inside_score}</td></tr>
                <tr><td>&gt; {buffer_distance}</td><td>{outside_score}</td></tr>
            </table>
            <p><i>Note: You can override this default below</i></p>
            """

            self.mapping_table_label = QLabel()
            self.mapping_table_label.setWordWrap(True)
            self.mapping_table_label.setTextFormat(Qt.RichText)
            self.mapping_table_label.setText(html)
            self.internal_layout.addWidget(self.mapping_table_label)

        except Exception as e:
            log_message(f"Error adding mapping thresholds table: {e}", level=Qgis.Warning)
            log_message(traceback.format_exc(), level=Qgis.Warning)

    def add_internal_widgets(self) -> None:
        """
        Adds internal widgets specific to self.set_internal_widgets_visible(self.isChecked()) - in this case there are none.
        """
        try:

            self._add_mapping_thresholds_table()

            # Travel Increments input
            self.buffer_distance_layout = QHBoxLayout()
            self.buffer_distance_label = QLabel("Buffer Distance (m):")
            self.buffer_distance_input = QSpinBox()
            self.buffer_distance_input.setRange(0, 100000)
            self.buffer_distance_layout.addWidget(self.buffer_distance_label)
            self.buffer_distance_layout.addWidget(self.buffer_distance_input)
            default_distance = self.attributes.get("default_single_buffer_distance", 0)
            buffer_distance = self.attributes.get("single_buffer_point_layer_distance", default_distance)
            if buffer_distance == 0:
                buffer_distance = default_distance
            if self.mapping_buffer_distance is not None and buffer_distance == default_distance:
                buffer_distance = self.mapping_buffer_distance
            try:
                self.buffer_distance_input.setValue(int(buffer_distance))
            except (ValueError, TypeError):
                self.buffer_distance_input.setValue(int(default_distance))

            # Add all layouts to the main layout
            self.internal_layout.addLayout(self.buffer_distance_layout)
            self.buffer_distance_input.valueChanged.connect(self.update_data)

        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", level=Qgis.Critical)
            log_message(traceback.format_exc(), level=Qgis.Critical)

    def get_data(self) -> dict:
        """
        Return the data as a dictionary, updating attributes with current value.
        """
        if not self.isChecked():
            return None

        self.attributes["single_buffer_point_layer_distance"] = self.buffer_distance_input.value()

        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets based on the state of the radio button.
        """
        try:
            self.buffer_distance_input.setEnabled(enabled)
            self.buffer_distance_label.setEnabled(enabled)
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
