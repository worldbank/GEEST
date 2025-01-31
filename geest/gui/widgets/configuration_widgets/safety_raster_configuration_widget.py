from qgis.PyQt.QtWidgets import (
    QLabel,
)
from .base_configuration_widget import BaseConfigurationWidget
from geest.utilities import log_message
from qgis.core import Qgis


class SafetyRasterConfigurationWidget(BaseConfigurationWidget):
    """

    A widget for configuring safety indicators based on a raster.
    """

    def add_internal_widgets(self) -> None:
        """
        This method is called during the widget initialization and sets up the layout for the UI components.

        This component only provides a label as selecting a raster is the only thing needed.
        """
        try:
            self.info_label = QLabel("A raster layer representing safety")
            self.internal_layout.addWidget(self.info_label)
        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", level=Qgis.Critical)
            import traceback

            log_message(traceback.format_exc(), level=Qgis.Critical)

    def get_data(self) -> dict:
        """

        Returns:
            dict: A dictionary containing the current attributes of the raster layers and/ors.
        """
        if not self.isChecked():
            return None

        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets (raster layers) based on the state of the radio button.

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
