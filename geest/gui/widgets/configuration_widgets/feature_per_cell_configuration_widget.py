from qgis.PyQt.QtWidgets import (
    QLabel,
)

from .base_configuration_widget import BaseConfigurationWidget
from qgis.core import QgsMessageLog


#
# This combines the point per cell, polyline per cell and polygon per cell
# widgets that are in combined widgets. The reason for this is that
# when working at the factor level, it can have indicators requiring different
# spatial data types, but the user should only select on configuration type.
# The logic for whether to accept point, line or polygons will be implemented in the
# datasource widget.
#
class FeaturePerCellConfigurationWidget(BaseConfigurationWidget):
    """
    A widget to define inputs for an open route services routing request.
    """

    # Normally we dont need to reimplement the __init__ method, but in this case we need to
    # change the label text next to the radio button
    def __init__(self, label_text: str, attributes: dict) -> None:
        humanised_label = "Feature per cell"
        super().__init__(humanised_label, attributes)

    def add_internal_widgets(self) -> None:
        """
        Adds internal widgets specific to self.set_internal_widgets_visible(self.isChecked()) - in this case there are none.
        """
        try:
            self.label = QLabel("Count features per cell.")
            self.layout.addWidget(self.layout)
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

        return None  # Important to return None in this case as we dont want to assign
        # different analysis modes to the indicators because this config widget is a
        # special case where it caters for 3 different analysis modes.

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets based on the state of the radio button.
        """
        try:
            self.label.setEnabled(enabled)
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error in set_internal_widgets_enabled: {e}", "Geest"
            )
