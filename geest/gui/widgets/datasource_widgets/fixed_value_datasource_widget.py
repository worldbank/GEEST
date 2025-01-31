import os
from qgis.PyQt.QtWidgets import (
    QDoubleSpinBox,
)
from qgis.PyQt.QtCore import QSettings
from qgis.core import Qgis
from .base_datasource_widget import BaseDataSourceWidget
from geest.utilities import log_message


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
            self.spin_box.valueChanged.connect(self.update_attributes)

        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", level=Qgis.Critical)
            import traceback

            log_message(traceback.format_exc(), level=Qgis.Critical)

    def _add_raster_layer_widgets(self) -> None:
        """
        Adds the widgets for selecting the raster layer, including a `QgsMapLayerComboBox` and input.
        """
        self.spin_box = QDoubleSpinBox()
        self.spin_box.setRange(0, 100)
        self.spin_box.setSingleStep(1)
        self.spin_box.setValue(self.attributes.get(f"index_score", 0))
        self.layout.addWidget(self.spin_box)

    def update_attributes(self):
        """
        Updates the attributes dict to match the current state of the widget.

        The attributes dict is a reference so any tree item attributes will be updated directly.

        Returns:
            None
        """
        # Collect data for the raster layerfactorlayer_data_weighting
        value = self.spin_box.value()
        self.attributes["index_score"] = value
