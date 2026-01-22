# -*- coding: utf-8 -*-
"""📦 Multi Buffer Configuration Widget module.

This module contains functionality for multi buffer configuration widget.
"""

import json
import os
import traceback

from qgis.core import Qgis
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QLineEdit, QRadioButton

from geest.core.settings import setting
from geest.core.workflows.mappings import MAPPING_REGISTRY
from geest.utilities import log_message

from .base_configuration_widget import BaseConfigurationWidget


class MultiBufferConfigurationWidget(BaseConfigurationWidget):
    """
    A widget to define inputs for an open route services routing request.
    """

    def _add_mapping_thresholds_table(self) -> None:
        """
        Adds a table showing scale-specific thresholds from the mappings module.
        """
        self.mapping_thresholds = None
        try:
            log_message(
                f"_add_mapping_thresholds_table called with attributes: {self.attributes.get('id')}", level=Qgis.Info
            )

            # Get analysis scale from model.json
            working_dir = setting("last_working_directory", "")
            model_path = os.path.join(working_dir, "model.json")

            analysis_scale = self.attributes.get("analysis_scale") or "national"
            if os.path.exists(model_path):
                try:
                    with open(model_path, "r") as f:
                        model = json.load(f)
                        analysis_scale = model.get("analysis_scale", analysis_scale)
                    log_message(f"Analysis scale from model.json: {analysis_scale}", level=Qgis.Info)
                except Exception as e:
                    log_message(f"Could not read analysis_scale from model.json: {e}", level=Qgis.Warning)

            # Get factor ID from attributes (injected by FactorConfigurationWidget)
            # Indicators have their own ID, but we need the parent factor's ID.
            indicator_id = self.attributes.get("id")
            factor_id = self.attributes.get("factor_id")
            log_message(f"Indicator ID from attributes: {indicator_id}", level=Qgis.Info)
            log_message(f"Factor ID from attributes: {factor_id}", level=Qgis.Info)

            # Fallback: try to find factor_id by searching model.json
            if not factor_id and os.path.exists(model_path):
                try:
                    with open(model_path, "r") as f:
                        model = json.load(f)
                        # Search for this indicator in the model and get its parent factor
                        for dimension in model.get("dimensions", []):
                            for factor in dimension.get("factors", []):
                                for indicator in factor.get("indicators", []):
                                    if indicator.get("id") == indicator_id:
                                        factor_id = factor.get("id")
                                        log_message(f"Found parent factor ID: {factor_id}", level=Qgis.Info)
                                        break
                                if factor_id:
                                    break
                            if factor_id:
                                break
                except Exception as e:
                    log_message(f"Error searching for parent factor: {e}", level=Qgis.Warning)

            if not factor_id:
                log_message(f"No parent factor ID found for indicator: {indicator_id}", level=Qgis.Warning)
                return  # No factor ID, skip table

            mapping = MAPPING_REGISTRY.get(factor_id)

            log_message(f"Mapping lookup for '{factor_id}': {mapping is not None}", level=Qgis.Info)

            if not mapping:
                log_message(
                    f"No mapping found for factor: {factor_id}. Available mappings: {list(MAPPING_REGISTRY.keys())}",
                    level=Qgis.Warning,
                )
                return  # No mapping found for this factor

            # Get scale-specific config
            config = mapping.get(analysis_scale, mapping.get("national"))

            if not config:
                return  # No config found

            # Get factor name from attributes; fallback to model.json lookup.
            factor_name = self.attributes.get("factor_name") or "Multi-Buffer Analysis"
            if factor_name == "Multi-Buffer Analysis" and os.path.exists(model_path):
                try:
                    with open(model_path, "r") as f:
                        model = json.load(f)
                        for dimension in model.get("dimensions", []):
                            for factor in dimension.get("factors", []):
                                if factor.get("id") == factor_id:
                                    factor_name = factor.get("name", factor_name)
                                    break
                except Exception:
                    pass

            thresholds = config.get("thresholds", [])
            scores = config.get("scores", [])
            if thresholds:
                self.mapping_thresholds = thresholds

            # Generate HTML table
            html = f"""
            <p><b>{factor_name} ({analysis_scale.title()} Scale)</b></p>
            <table border='1' cellpadding='4' cellspacing='0'>
                <tr><th>Distance Range (m)</th><th>Score</th></tr>
            """

            # Build distance ranges
            for i, score in enumerate(scores):
                if i == 0:
                    distance_range = f"0 - {thresholds[0]}"
                elif i < len(thresholds):
                    distance_range = f"{thresholds[i-1]} - {thresholds[i]}"
                else:
                    distance_range = f"> {thresholds[-1]}"

                html += f"<tr><td>{distance_range}</td><td>{score}</td></tr>"

            html += "</table>"
            html += "<p><i>Note: You can override these defaults below</i></p>"

            # Display table
            self.mapping_table_label = QLabel()
            self.mapping_table_label.setWordWrap(True)
            self.mapping_table_label.setTextFormat(Qt.RichText)
            self.mapping_table_label.setText(html)
            self.internal_layout.addWidget(self.mapping_table_label)

            log_message(f"✓ Thresholds table added successfully for {factor_name}", level=Qgis.Info)

        except Exception as e:
            log_message(f"Error adding mapping thresholds table: {e}", level=Qgis.Warning)
            log_message(traceback.format_exc(), level=Qgis.Warning)

    def add_internal_widgets(self) -> None:
        """
        Adds internal widgets specific to self.set_internal_widgets_visible(self.isChecked()) - in this case there are none.
        """
        try:
            log_message("Adding internal widgets for MultiBufferConfigurationWidget")
            # log_message(f"Attributes: {self.attributes}")

            # Add mapping thresholds table at the top
            self._add_mapping_thresholds_table()

            # Travel Mode group
            self.travel_mode_group = QGroupBox("Travel Mode:")
            self.travel_mode_layout = QHBoxLayout()
            self.walking_radio = QRadioButton("Walking")
            self.driving_radio = QRadioButton("Driving")
            if self.attributes.get("multi_buffer_travel_mode", "") != "Driving":
                self.walking_radio.setChecked(True)
            else:
                self.driving_radio.setChecked(True)  # Default selection
            self.travel_mode_layout.addWidget(self.walking_radio)
            self.travel_mode_layout.addWidget(self.driving_radio)
            self.travel_mode_group.setLayout(self.travel_mode_layout)

            # Measurement group
            self.measurement_group = QGroupBox("Measurement:")
            self.measurement_layout = QHBoxLayout()
            self.distance_radio = QRadioButton("Distance (meters)")
            self.time_radio = QRadioButton("Time (minutes)")
            if self.attributes.get("multi_buffer_travel_units", "") != "Time":
                self.distance_radio.setChecked(True)
            else:
                self.time_radio.setChecked(True)  # Default selection
            self.measurement_layout.addWidget(self.distance_radio)
            self.measurement_layout.addWidget(self.time_radio)
            self.measurement_group.setLayout(self.measurement_layout)

            # Travel Increments input
            self.travel_increments_layout = QHBoxLayout()
            self.increments_label = QLabel("Travel Increments:")
            self.increments_input = QLineEdit("")
            self.travel_increments_layout.addWidget(self.increments_label)
            self.travel_increments_layout.addWidget(self.increments_input)
            default_distances = self.attributes.get("default_multi_buffer_distances", "")
            user_distances = self.attributes.get("multi_buffer_travel_distances")
            has_user_override = bool(user_distances) and user_distances != default_distances
            if has_user_override:
                self.increments_input.setText(user_distances)
            elif self.mapping_thresholds:
                self.increments_input.setText(", ".join(str(x) for x in self.mapping_thresholds))
            else:
                self.increments_input.setText(default_distances)

            # Add all layouts to the main layout
            self.internal_layout.addWidget(self.travel_mode_group)
            self.internal_layout.addWidget(self.measurement_group)
            self.internal_layout.addLayout(self.travel_increments_layout)

            # Emit the data_changed signal when any widget is changed
            self.time_radio.toggled.connect(self.update_data)
            self.distance_radio.toggled.connect(self.update_data)
            self.walking_radio.toggled.connect(self.update_data)
            self.driving_radio.toggled.connect(self.update_data)
            self.increments_input.textChanged.connect(self.update_data)

            # Connect the validation method to radio buttons to revalidate on state change
            self.time_radio.toggled.connect(self.validate_increments_input)
            self.distance_radio.toggled.connect(self.validate_increments_input)
            self.increments_input.textChanged.connect(self.validate_increments_input)

        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", level=Qgis.Critical)
            log_message(traceback.format_exc(), level=Qgis.Critical)

    def validate_increments_input(self) -> bool:
        """
        Validates the increments input line edit.
        Ensures it is a comma-separated list of unique, non-negative numbers.
        If the units are set to time, ensures no number is greater than 3600.
        Provides tooltips for specific violations.
        """
        input_text = self.increments_input.text().strip()

        # Reset tool tip and border style for each validation check
        self.increments_input.setToolTip("")
        self.increments_input.setStyleSheet("")

        if not input_text:
            tooltip_text = "Input cannot be empty. Please enter a comma-separated list of numbers."
            self.increments_input.setToolTip(tooltip_text)
            self.increments_input.setStyleSheet("border: 1px solid red")
            return False

        try:
            # Parse and validate each entry
            values = [float(value.strip()) for value in input_text.split(",")]

            # Check for negative values
            if any(value < 0 for value in values):
                tooltip_text = "Negative values are not allowed in travel increments."
                self.increments_input.setToolTip(tooltip_text)
                self.increments_input.setStyleSheet("border: 1px solid red")
                return False

            # Check for duplicate values
            if len(values) != len(set(values)):
                tooltip_text = "Duplicate values are not allowed in travel increments."
                self.increments_input.setToolTip(tooltip_text)
                self.increments_input.setStyleSheet("border: 1px solid red")
                return False

            # Check for values greater than 60 mins (3600s) if in time mode
            if self.time_radio.isChecked() and any(value > 60 for value in values):
                tooltip_text = "Values greater than 60 minutes are not allowed for time units."
                self.increments_input.setToolTip(tooltip_text)
                self.increments_input.setStyleSheet("border: 1px solid red")
                return False

            # If all checks pass, set border to green and clear the tooltip
            self.increments_input.setStyleSheet("border: 1px solid green")
            self.increments_input.setToolTip("All values are valid.")
            return True

        except ValueError:
            tooltip_text = "Invalid entry. Please enter a comma-separated list of numbers."
            self.increments_input.setToolTip(tooltip_text)
            self.increments_input.setStyleSheet("border: 1px solid red")
            return False

    def get_data(self) -> dict:
        """
        Return the data as a dictionary, updating attributes with current value.
        """
        if not self.isChecked():
            return None

        if self.walking_radio.isChecked():
            self.attributes["multi_buffer_travel_mode"] = "Walking"
        else:
            self.attributes["multi_buffer_travel_mode"] = "Driving"

        if self.distance_radio.isChecked():
            self.attributes["multi_buffer_travel_units"] = "Distance"
        else:
            self.attributes["multi_buffer_travel_units"] = "Time"

        self.attributes["multi_buffer_travel_distances"] = self.increments_input.text()

        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets based on the state of the radio button.
        """
        try:
            self.distance_radio.setEnabled(enabled)
            self.time_radio.setEnabled(enabled)
            self.walking_radio.setEnabled(enabled)
            self.driving_radio.setEnabled(enabled)
            self.increments_input.setEnabled(enabled)
            self.increments_label.setEnabled(enabled)
            self.travel_mode_group.setEnabled(enabled)
            self.measurement_group.setEnabled(enabled)
            self.travel_increments_layout.setEnabled(enabled)
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
