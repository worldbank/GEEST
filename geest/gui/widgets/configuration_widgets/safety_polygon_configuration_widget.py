import os
from qgis.PyQt.QtWidgets import (
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QSpinBox,
)
from qgis.PyQt.QtWidgets import QSizePolicy
from qgis.core import Qgis
from .base_configuration_widget import BaseConfigurationWidget
from geest.utilities import log_message


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
            self.info_label = QLabel("Classify polygons according to safety levels")
            self.internal_layout.addWidget(self.info_label)
            self.table_widget = QTableWidget()
            self.table_widget.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding
            )
            # Stop the label being editable
            self.table_widget.setEditTriggers(QTableWidget.NoEditTriggers)
            self.internal_layout.addWidget(self.table_widget)
            self.table_widget.setColumnCount(2)
            self.table_widget.setColumnWidth(1, 80)
            self.table_widget.horizontalHeader().setStretchLastSection(False)
            self.table_widget.horizontalHeader().setSectionResizeMode(
                0, self.table_widget.horizontalHeader().Stretch
            )

            return self.populate_table()
            self.internal_layout.addWidget(self.table_widget)

        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", level=Qgis.Critical)
            import traceback

            log_message(traceback.format_exc(), level=Qgis.Critical)

    def populate_table(self):

        self.table_widget.setHorizontalHeaderLabels(["Name", "Value 0-100"])
        safety_classes = self.attributes.get(
            f"classify_safety_polygon_into_classes_unique_values", {}
        )
        if not isinstance(safety_classes, dict):
            safety_classes = {}
            # remove any item from the safety_classes where the key is not a string
        safety_classes = {k: v for k, v in safety_classes.items() if isinstance(k, str)}
        self.table_widget.setRowCount(len(safety_classes))

        def validate_value(value):
            return 0 <= value <= 100

        log_message(f"Classes: {safety_classes}")
        # iterate over the dict and populate the table
        for row, (class_name, value) in enumerate(safety_classes.items()):
            if row >= self.table_widget.rowCount():
                continue

            if not isinstance(class_name, str):
                continue

            if not isinstance(value, (int, float)) or not 0 <= value <= 100:
                value = 0

            name_item = QTableWidgetItem(class_name)
            value_item = QSpinBox()
            self.table_widget.setItem(row, 0, name_item)
            value_item.setRange(0, 100)  # Set spinner range
            value_item.setValue(value)  # Default value
            self.table_widget.setCellWidget(row, 1, value_item)

            def on_value_changed(value):
                # Color handling for current cell
                if value is None or not (0 <= value <= 100):
                    value_item.setStyleSheet("color: red;")
                    value_item.setValue(0)
                else:
                    value_item.setStyleSheet("color: black;")
                self.update_cell_colors()
                self.update_data()

            value_item.valueChanged.connect(on_value_changed)

            # Call update_cell_colors after all rows are created
            self.update_cell_colors()

    def update_cell_colors(self):
        # Check if all values are zero
        all_zeros = True
        for r in range(self.table_widget.rowCount()):
            spin_widget = self.table_widget.cellWidget(r, 1)
            if spin_widget and spin_widget.value() != 0:
                all_zeros = False
                break

        # Color all cells based on all-zeros check
        for r in range(self.table_widget.rowCount()):
            spin_widget = self.table_widget.cellWidget(r, 1)
            if spin_widget:
                spin_widget.setStyleSheet(
                    "color: red;" if all_zeros else "color: black;"
                )

    def table_to_dict(self):
        updated_attributes = {}
        for row in range(self.table_widget.rowCount()):
            spin_widget = self.table_widget.cellWidget(row, 1)
            value = None
            if spin_widget and spin_widget.value():
                value = spin_widget.value()
            name_item = self.table_widget.item(row, 0)
            class_name = str(name_item.text())
            updated_attributes[class_name] = value

        log_message(f"Updated attributes {updated_attributes}")
        return updated_attributes

    def get_data(self) -> dict:
        """
        Retrieves and returns the current state of the widget, including selected polygon layers or shapefiles.

        Returns:
            dict: A dictionary containing the current attributes of the polygon layers and/or shapefiles.
        """
        if not self.isChecked():
            return None

        # Serialize the self.table_widget back into the classify_polygon_into_classes_unique_values attribute
        updated_attributes = self.table_to_dict()

        self.attributes["classify_safety_polygon_into_classes_unique_values"] = (
            updated_attributes
        )
        # log_message("------------------------------------")
        # log_message("------------------------------------")
        # log_message(f"Attributes: {self.attributes}")
        # log_message("------------------------------------")
        # log_message("------------------------------------")
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
        log_message("Updating widgets for SafetyPolygonConfigurationWidget")
        self.attributes = attributes
        self.table_widget.clear()
        self.populate_table()
