from qgis.PyQt.QtWidgets import (
    QLabel,
)
from qgis.core import Qgis
from geest.utilities import log_message
from .base_configuration_widget import BaseConfigurationWidget


#
# This combines the point per cell, polyline per cell and polygon per cell
# widgets that are in combined widgets. The reason for this is that
# when working at the factor level, it can have indicators requiring different
# spatial data types, but the user should only select one configuration type.
# The logic for whether to accept point, line or polygons will be implemented in the
# datasource widget.
#
class FeaturePerCellConfigurationWidget(BaseConfigurationWidget):
    """
    A widget to define inputs counting features per cell.
    """

    # Normally we dont need to reimplement the __init__ method, but in this case we need to
    # change the label text next to the radio button
    def __init__(self, analysis_mode: str, attributes: dict) -> None:
        humanised_label = "Feature per cell"
        super().__init__(
            humanised_label=humanised_label,  # In this special case we override the label
            analysis_mode=analysis_mode,
            attributes=attributes,
        )

    def add_internal_widgets(self) -> None:
        """
        Adds internal widgets specific to self.set_internal_widgets_visible(self.isChecked()) - in this case there are none.
        """
        try:
            self.info_label = QLabel("Count features per cell.")
            self.internal_layout.addWidget(self.info_label)
        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", level=Qgis.Critical)
            import traceback

            log_message(traceback.format_exc(), level=Qgis.Critical)

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
