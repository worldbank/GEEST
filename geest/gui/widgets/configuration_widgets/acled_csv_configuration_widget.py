from qgis.core import Qgis
from geest.utilities import log_message
from .base_configuration_widget import BaseConfigurationWidget


class AcledCsvConfigurationWidget(BaseConfigurationWidget):
    """
    A widget for indicating that we will be doing an ACLED CSV file based analysis.

    This widget does not provide any options other than checking it on or off.

    See also the AcledCsvLayerWidget which is used to select the CSV file.

    Attributes:
        widget_key (str): The key identifier for this widget.
        csv_file_line_edit (QLineEdit): Line edit for entering/selecting a CSV file.
    """

    def add_internal_widgets(self) -> None:
        """
        Normally this adds the internal options for this workflow type, but in this case there are none.

        This method is called during the widget initialization and sets up the layout for the UI components.
        """
        try:
            self.widget_key = "use_csv_to_point_layer"

        except Exception as e:
            log_message(
                f"Error in add_internal_widgets: {e}", tag="Geest", level=Qgis.Critical
            )
            import traceback

            log_message(traceback.format_exc(), tag="Geest", level=Qgis.Critical)

    def get_data(self) -> dict:
        """
        Retrieves and returns the current state of the widget

        Returns:
            dict: A dictionary containing the current attributes of the widget.
        """
        if not self.isChecked():
            return None

        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets (CSV file input) based on the state of the radio button.

        Args:
            enabled (bool): Whether to enable or disable the internal widgets.
        """
        pass
