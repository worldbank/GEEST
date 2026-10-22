# -*- coding: utf-8 -*-
"""Urban/rural share configuration widget.

A radio-button configuration entry for the S2S urban/rural population-share
mode. The measure (urban vs rural) is chosen in the data-source dropdown; this
widget only explains the mode.
"""

from qgis.core import Qgis
from qgis.PyQt.QtWidgets import QLabel

from geest.utilities import log_message

from .base_configuration_widget import BaseConfigurationWidget


class UrbanRuralShareConfigurationWidget(BaseConfigurationWidget):
    """Radio button plus a short description for the S2S urban/rural share mode."""

    def add_internal_widgets(self) -> None:
        """Add the descriptive label."""
        try:
            self.info_label: QLabel = QLabel(
                "Score the urban or rural population share from the S2S population layer. "
                "Choose the measure in the data-source dropdown."
            )
            self.info_label.setWordWrap(True)
            self.internal_layout.addWidget(self.info_label)
        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", "GeoE3", level=Qgis.Critical)

    def get_data(self) -> dict:
        """Return the data as a dictionary, updating attributes with current value."""
        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """Enables or disables the internal widgets based on the radio button state."""
        try:
            self.info_label.setEnabled(enabled)
        except Exception as e:
            log_message(
                f"Error in set_internal_widgets_enabled: {e}",
                tag="GeoE3",
                level=Qgis.Critical,
            )

    def update_widgets(self, attributes: dict) -> None:
        """Updates the internal widgets with the current attributes."""
        pass
