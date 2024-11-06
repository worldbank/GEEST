import os

from qgis.PyQt.QtWidgets import (
    QDoubleSpinBox,
    QToolButton,
    QFileDialog,
)
from qgis.gui import QgsMapLayerComboBox
from qgis.core import (
    QgsMessageLog,
    QgsMapLayerProxyModel,
    QgsProject,
)
from qgis.PyQt.QtCore import QSettings

from .base_datasource_widget import BaseDataSourceWidget


class FixedValueDataSourceWidget(BaseDataSourceWidget):
    """

    A widget for selecting a fixed value that will generate a raster with that value filling it.

    This widget provides a single spinbox with a value range 0-100. The value will internally be
    reclassified to 0-5 for the final raster produced.

    Attributes:
        widget_key (str): The key identifier for this widget.
        value widget (QDoubleSpinBox): A spinbox for selecting the fixed value.
    """

    def add_internal_widgets(self) -> None:
        """
        Adds the internal widgets required for selecting raster layers and their correspondings.
        This method is called during the widget initialization and sets up the layout for the UI components.
        """
        try:
            self.settings = QSettings()

            # Raster Layer Section
            self._add_raster_layer_widgets()
            # Connect signals to update the data when user changes selections
            self.spin_box.valueChanged.connect(self.update_data)

        except Exception as e:
            QgsMessageLog.logMessage(f"Error in add_internal_widgets: {e}", "Geest")
            import traceback

            QgsMessageLog.logMessage(traceback.format_exc(), "Geest")

    def _add_raster_layer_widgets(self) -> None:
        """
        Adds the widgets for selecting the raster layer, including a `QgsMapLayerComboBox` and input.
        """
        self.spin_box = QDoubleSpinBox()
        self.spin_box.setRange(0, 100)
        self.spin_box.setSingleStep(1)
        self.spin_box.setValue(100)
        self.layout.addWidget(self.spin_box)

        # Restore previously set value
        value = self.attributes.get(f"default_index_score", None)

    def get_data(self) -> dict:
        """
        Retrieves and returns the current state of the widget, including selected raster layers.

        Returns:
            dict: A dictionary containing the current attributes of the raster layers and/ors.
        """
        if not self.isChecked():
            return None

        # Collect data for the raster layer
        value = self.spin_box.value()
        self.attributes["default_index_score"] = value

        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets (raster layers) based on the state of the radio button.

        Args:
            enabled (bool): Whether to enable or disable the internal widgets.
        """
        try:
            self.spin_box.setEnabled(enabled)
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error in set_internal_widgets_enabled: {e}", "Geest"
            )
