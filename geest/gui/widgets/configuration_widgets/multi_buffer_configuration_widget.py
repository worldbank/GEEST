from qgis.PyQt.QtWidgets import (
    QLabel,
    QGroupBox,
    QRadioButton,
    QHBoxLayout,
    QLineEdit,
)

from .base_configuration_widget import BaseConfigurationWidget
from qgis.core import QgsMessageLog


class MultiBufferConfigurationWidget(BaseConfigurationWidget):
    """
    A widget to define inputs for an open route services routing request.
    """

    def add_internal_widgets(self) -> None:
        """
        Adds internal widgets specific to self.set_internal_widgets_visible(self.isChecked()) - in this case there are none.
        """
        try:
            QgsMessageLog.logMessage(
                "Adding internal widgets for MultiBufferConfigurationWidget", "Geest"
            )
            QgsMessageLog.logMessage(f"Attributes: {self.attributes}", "Geest")
            # Travel Mode group
            self.travel_mode_group = QGroupBox("Travel Mode:")
            self.travel_mode_layout = QHBoxLayout()
            self.walking_radio = QRadioButton("Walking")
            self.driving_radio = QRadioButton("Driving")
            if self.attributes.get("multi_buffer_travel_mode", "") == "Walking":
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
            self.time_radio = QRadioButton("Time (seconds)")
            if self.attributes.get("multi_buffer_travel_units", "") == "Distance":
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
            self.layout.addWidget(self.travel_mode_group)
            self.layout.addWidget(self.measurement_group)
            self.layout.addLayout(self.travel_increments_layout)

            # Emit the data_changed signal when any widget is changed
            self.time_radio.toggled.connect(self.update_data)
            self.distance_radio.toggled.connect(self.update_data)
            self.walking_radio.toggled.connect(self.update_data)
            self.driving_radio.toggled.connect(self.update_data)
            self.increments_input.textChanged.connect(self.update_data)

        except Exception as e:
            QgsMessageLog.logMessage(f"Error in add_internal_widgets: {e}", "Geest")
            import traceback

            QgsMessageLog.logMessage(traceback.format_exc(), "Geest")

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
            QgsMessageLog.logMessage(
                f"Error in set_internal_widgets_enabled: {e}", "Geest"
            )
