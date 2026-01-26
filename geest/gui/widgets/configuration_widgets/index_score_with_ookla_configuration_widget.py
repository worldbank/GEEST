# -*- coding: utf-8 -*-
from qgis.core import Qgis
from qgis.PyQt.QtWidgets import QHBoxLayout, QLabel, QPushButton
from qgis.utils import iface

from geest.utilities import log_message

from .base_configuration_widget import BaseConfigurationWidget


class IndexScoreWithOOKLAConfigurationWidget(BaseConfigurationWidget):
    """
    A specialized radio button with additional widgets for IndexScore with OOKLA.
    """

    def add_internal_widgets(self) -> None:
        """
        Adds internal widgets specific to IndexScore.
        """
        try:
            self.info_label: QLabel = QLabel(
                "Fill each polygon with a fixed value, masking the results with the OOKLA Internet Connectivity Layer. "
                "For more detailed analysis, you can configure upload and download speed thresholds in the settings."
            )
            self.info_label.setWordWrap(True)
            self.internal_layout.addWidget(self.info_label)

            # Add button to open Ookla settings
            button_layout = QHBoxLayout()
            self.ookla_settings_button = QPushButton("⚙️ Configure Ookla Speed Thresholds")
            self.ookla_settings_button.clicked.connect(self._open_ookla_settings)
            button_layout.addWidget(self.ookla_settings_button)
            button_layout.addStretch()
            self.internal_layout.addLayout(button_layout)
        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", level=Qgis.Critical)

    def _open_ookla_settings(self):
        """Opens the GeoE3 settings dialog at the Ookla settings section."""
        try:
            # Open QGIS options dialog with GeoE3 settings page
            iface.showOptionsDialog(currentPage="mOptionsPage_Geest")
        except Exception as e:
            log_message(f"Error opening Ookla settings: {e}", level=Qgis.Critical)

    def get_data(self) -> dict:
        """Return the data as a dictionary, updating attributes with current value.

        Returns:
            Dictionary containing the widget attributes.
        """
        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """Enable or disable internal widgets based on radio button state.

        Args:
            enabled: Whether to enable or disable the widgets.
        """
        try:
            self.info_label.setEnabled(enabled)
            self.ookla_settings_button.setEnabled(enabled)
        except Exception as e:
            log_message(
                f"Error in set_internal_widgets_enabled: {e}",
                tag="Geest",
                level=Qgis.Critical,
            )

    def update_widgets(self, attributes: dict) -> None:
        """Update internal widgets with the current attributes.

        Only needed in cases where a) there are internal widgets and b)
        the attributes may change externally e.g. in the datasource widget.

        Args:
            attributes: Dictionary of attributes to update the widgets with.
        """
        pass
