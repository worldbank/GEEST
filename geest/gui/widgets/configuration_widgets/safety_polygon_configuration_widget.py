import os
from qgis.PyQt.QtWidgets import (
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QSpinBox,
)
from qgis.core import Qgis
from .base_configuration_widget import BaseConfigurationWidget
from geest.utilities import log_message
from qgis.PyQt.QtGui import QBrush, QColor


class SafetyPolygonConfigurationWidget(BaseConfigurationWidget):
    """

    A widget for selecting a polygon (area) layer with options for shapefile inputs.

    This widget provides one `QgsMapLayerComboBox` components for selecting polygon layers,
    as well as `QLineEdit` and `QToolButton` components to allow the user to specify shapefile paths for
    each layer. The user can choose layers either from the QGIS project or provide external shapefiles.

    A further line edit is created for the user to tweak the scores of the unique valies in the selected field.

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
            self.info_label = QLabel("Classify polygons accoring to safety levels")
            self.layout.addWidget(self.info_label)
            self.table_widget = QTableWidget()
            self.layout.addWidget(self.table_widget)
            self.table_widget.setColumnCount(2)
            self.table_widget.setHorizontalHeaderLabels(["Name", "Value"])

            classes = self.attributes.get(
                f"classify_poly_into_classes_unique_values", []
            )
            self.table_widget.setRowCount(len(classes))

            def validate_value(value):
                return 0 <= value <= 6

            for row, class_name in enumerate(classes):
                name_item = QTableWidgetItem(class_name)
                value_item = QSpinBox()
                value_item.setRange(0, 6)

                def on_value_change(value, row=row):
                    if not validate_value(value):
                        self.table_widget.item(row, 1).setBackground(
                            QBrush(QColor("red"))
                        )
                    else:
                        self.table_widget.item(row, 1).setBackground(
                            QBrush(QColor("white"))
                        )

                self.table_widget.setItem(row, 0, name_item)
                self.table_widget.setCellWidget(row, 1, value_item)
                value_item.valueChanged.connect(on_value_change)
            self.layout.addWidget(self.table_widget)

        except Exception as e:
            log_message(
                f"Error in add_internal_widgets: {e}", tag="Geest", level=Qgis.Critical
            )
            import traceback

            log_message(traceback.format_exc(), tag="Geest", level=Qgis.Critical)

    def get_data(self) -> dict:
        """
        Retrieves and returns the current state of the widget, including selected polygon layers or shapefiles.

        Returns:
            dict: A dictionary containing the current attributes of the polygon layers and/or shapefiles.
        """
        if not self.isChecked():
            return None

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
