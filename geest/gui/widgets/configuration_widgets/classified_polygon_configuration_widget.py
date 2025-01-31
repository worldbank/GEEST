import os
from qgis.PyQt.QtWidgets import (
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QSpinBox,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QBrush, QColor
from qgis.core import Qgis
from .base_configuration_widget import BaseConfigurationWidget
from geest.utilities import log_message


class ClassifiedPolygonConfigurationWidget(BaseConfigurationWidget):
    """

    A widget for selecting a polygon (area) that will be classified based on the percentage scores.

    Attributes:
        widget_key (str): The key identifier for this widget.
        polygon_layer_combo (QgsMapLayerComboBox): A combo box for selecting the polygon layer.
        polygon_shapefile_line_edit (QLineEdit): Line edit for entering/selecting a polygon layer shapefile.
    """

    def add_internal_widgets(self) -> None:
        """
        Adds the internal widgets required for selecting polygon layers and their corresponding shapefiles.
        This method is called during the widget initialization and sets up the layout for the UI components.
        """
        try:
            self.info_label = QLabel("Classify polygons accoring to percentage scores")
            self.internal_layout.addWidget(self.info_label)

        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", level=Qgis.Critical)
            import traceback

            log_message(traceback.format_exc(), level=Qgis.Critical)

    def get_data(self) -> dict:
        """
        Retrieves and returns the current state of the widget, including selected polygon layers or shapefiles.

        Returns:
            dict: A dictionary containing the current attributes of the polygon layers and/or shapefiles.
        """
        if not self.isChecked():
            return None

        # There are no configurable options in this widget (see hte accompanying vector and field data source widget)
        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets (polygon layers) based on the state of the radio button.

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
