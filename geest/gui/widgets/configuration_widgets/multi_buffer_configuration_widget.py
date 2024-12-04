from qgis.PyQt.QtWidgets import (
    QLabel,
    QGroupBox,
    QRadioButton,
    QHBoxLayout,
    QLineEdit,
)

from qgis.core import Qgis
from .base_configuration_widget import BaseConfigurationWidget
from geest.utilities import log_message


class MultiBufferConfigurationWidget(BaseConfigurationWidget):
    """
    A widget to define inputs for an open route services routing request.
    """

    def add_internal_widgets(self) -> None:
        """
        Adds internal widgets specific to self.set_internal_widgets_visible(self.isChecked()) - in this case there are none.
        """
        try:
            log_message("Adding internal widgets for MultiBufferConfigurationWidget")
            # log_message(f"Attributes: {self.attributes}")
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
            if self.attributes.get("multi_buffer_travel_distances", False):
                self.increments_input.setText(
                    self.attributes["multi_buffer_travel_distances"]
                )
            else:
                self.increments_input.setText(
                    self.attributes.get("default_multi_buffer_distances", "")
                )

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
            import traceback

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
            tooltip_text = (
                "Input cannot be empty. Please enter a comma-separated list of numbers."
            )
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
                tooltip_text = (
                    "Values greater than 60 minutes are not allowed for time units."
                )
                self.increments_input.setToolTip(tooltip_text)
                self.increments_input.setStyleSheet("border: 1px solid red")
                return False

            # If all checks pass, set border to green and clear the tooltip
            self.increments_input.setStyleSheet("border: 1px solid green")
            self.increments_input.setToolTip("All values are valid.")
            return True

        except ValueError:
            tooltip_text = (
                "Invalid entry. Please enter a comma-separated list of numbers."
            )
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
