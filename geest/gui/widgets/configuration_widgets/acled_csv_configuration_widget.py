from qgis.PyQt.QtWidgets import (
    QLabel,
    QHBoxLayout,
    QSpinBox,
)
from qgis.core import Qgis
from .base_configuration_widget import BaseConfigurationWidget
from geest.utilities import log_message


class AcledCsvConfigurationWidget(BaseConfigurationWidget):
    """
    A widget for indicating that we will be doing an ACLED CSV file based analysis.

    This widget does not provide any options other than checking it on or off.

    See also the AcledCsvLayerWidget which is used to select the CSV file.

    Attributes:
        widget_key (str): The key identifier for this widget.
    """

    def add_internal_widgets(self) -> None:
        """
        Normally this adds the internal options for this workflow type, but in this case there are none.

        This method is called during the widget initialization and sets up the layout for the UI components.
        """
        try:
            self.widget_key = "use_csv_to_point_layer"
            # impact distance input
            self.buffer_distance_layout = QHBoxLayout()
            self.buffer_distance_label = QLabel("Incident Impact Distance (m):")
            self.buffer_distance_input = QSpinBox()
            self.buffer_distance_input.setRange(0, 100000)
            self.buffer_distance_layout.addWidget(self.buffer_distance_label)
            self.buffer_distance_layout.addWidget(self.buffer_distance_input)
            # I dont think this is defined in the spreadsheet yet.
            default_distance = self.attributes.get(
                "{self.widget_key}_distance_default", 5000
            )
            buffer_distance = self.attributes.get(
                "{self.widget_key}_distance", default_distance
            )
            if buffer_distance == 0:
                buffer_distance = default_distance
            try:
                self.buffer_distance_input.setValue(int(buffer_distance))
            except (ValueError, TypeError):
                self.buffer_distance_input.setValue(int(default_distance))

            # Add all layouts to the main layout
            self.internal_layout.addLayout(self.buffer_distance_layout)
            self.buffer_distance_input.valueChanged.connect(self.update_data)

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

        self.attributes[f"{self.widget_key}_distance"] = (
            self.buffer_distance_input.value()
        )

        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets based on the state of the radio button.
        """
        try:
            self.buffer_distance_input.setEnabled(enabled)
            self.buffer_distance_label.setEnabled(enabled)
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
