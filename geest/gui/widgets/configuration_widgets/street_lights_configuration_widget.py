import os
from qgis.PyQt.QtWidgets import (
    QLabel,
)
from geest.utilities import log_message
from .base_configuration_widget import BaseConfigurationWidget


class StreetLightsConfigurationWidget(BaseConfigurationWidget):
    """
    Street light locations configuration options (currently none)
    """

    def add_internal_widgets(self) -> None:
        try:
            self.info_label = QLabel("Point locations representing street lights")
            self.layout.addWidget(self.info_label)

        except Exception as e:
            log_message(
                f"Error in add_internal_widgets: {e}", tag="Geest", level=Qgis.Critical
            )
            import traceback

            log_message(traceback.format_exc(), tag="Geest", level=Qgis.Critical)

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
