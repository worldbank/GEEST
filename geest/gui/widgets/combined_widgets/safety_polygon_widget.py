import os
from qgis.PyQt.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
)
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox
from qgis.core import (
    QgsMapLayerProxyModel,
    QgsProject,
    QgsVectorLayer,
    QgsFieldProxyModel,
    Qgis,
)
from qgis.PyQt.QtCore import QSettings
from .base_indicator_widget import BaseIndicatorWidget
from geest.utilities import log_message


class SafetyPolygonWidget(BaseIndicatorWidget):
    """

    A widget for selecting a polygon (area) layer with options for shapefile inputs.

    This widget provides one `QgsMapLayerComboBox` components for selecting polygon layers,
    as well as `QLineEdit` and `QToolButton` components to allow the user to specify shapefile paths for
    each layer. The user can choose layers either from the QGIS project or provide external shapefiles.

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
            self.main_layout = QVBoxLayout()
            self.widget_key = "classify_safety_polygon_into_classes"
            self.settings = QSettings()

            # Polygon Layer Section
            self._add_polygon_layer_widgets()

            # Add Field Selection Dropdown
            self._add_field_selection_widgets()

            # Add the main layout to the widget's layout
            self.layout.addLayout(self.main_layout)

            self.table_widget = QTableWidget()
            self.table_widget.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding
            )
            # Stop the label being editable
            self.table_widget.setEditTriggers(QTableWidget.NoEditTriggers)
            self.layout.addWidget(self.table_widget)
            self.table_widget.setColumnCount(2)
            self.table_widget.setHorizontalHeaderLabels(["Name", "Value 0-100"])
            self.table_widget.setColumnWidth(1, 80)
            self.table_widget.horizontalHeader().setStretchLastSection(False)
            self.table_widget.horizontalHeader().setSectionResizeMode(
                0, self.table_widget.horizontalHeader().Stretch
            )

            safety_classes = self.attributes.get(
                f"classify_safety_polygon_into_classes_unique_values", {}
            )
            if not isinstance(safety_classes, dict):
                safety_classes = {}
            # remove any item from the safety_classes where the key is not a string
            safety_classes = {
                k: v for k, v in safety_classes.items() if isinstance(k, str)
            }
            self.table_widget.setRowCount(len(safety_classes))

            def validate_value(value):
                return 0 <= value <= 100

            try:
                log_message(f"Classes: {safety_classes}")
            except Exception as e:
                log_message(
                    f"Error in logging safety classes: {e}", level=Qgis.Critical
                )
                pass
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

                value_item.valueChanged.connect(on_value_changed)
            self.layout.addWidget(self.table_widget)

            # Connect signals to update the data when user changes selections
            self.polygon_layer_combo.currentIndexChanged.connect(self.update_data)
            self.polygon_shapefile_line_edit.textChanged.connect(self.update_data)
            # Connect signals to update the fields when user changes selections
            self.polygon_layer_combo.layerChanged.connect(self.update_field_combo)
            self.polygon_shapefile_line_edit.textChanged.connect(
                self.update_field_combo
            )

            # Connect the field combo box to update the attributes when a field is selected
            self.field_selection_combo.currentIndexChanged.connect(
                self.update_selected_field
            )

            self.update_field_combo()  # Populate fields for the initially selected layer

        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", level=Qgis.Critical)
            import traceback

            log_message(traceback.format_exc(), level=Qgis.Critical)

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

    def _add_polygon_layer_widgets(self) -> None:
        """
        Adds the widgets for selecting the polygon layer, including a `QgsMapLayerComboBox` and shapefile input.
        """
        self.polygon_layer_label = QLabel(
            "Polygon Layer - shapefile will have preference"
        )
        self.main_layout.addWidget(self.polygon_layer_label)
        # Polygon Layer ComboBox (Filtered to polygon layers)
        self.polygon_layer_combo = QgsMapLayerComboBox()
        self.polygon_layer_combo.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.main_layout.addWidget(self.polygon_layer_combo)

        # Restore previously selected polygon layer
        polygon_layer_id = self.attributes.get(f"{self.widget_key}_layer_id", None)
        if polygon_layer_id:
            polygon_layer = QgsProject.instance().mapLayer(polygon_layer_id)
            if polygon_layer:
                self.polygon_layer_combo.setLayer(polygon_layer)

        # _shapefile Input for Polygon Layer
        self.polygon_shapefile_layout = QHBoxLayout()
        self.polygon_shapefile_line_edit = QLineEdit()
        self.polygon_shapefile_button = QToolButton()
        self.polygon_shapefile_button.setText("...")
        self.polygon_shapefile_button.clicked.connect(self.select_polygon_shapefile)
        if self.attributes.get(f"{self.widget_key}_shapefile", False):
            self.polygon_shapefile_line_edit.setText(
                self.attributes[f"{self.widget_key}_shapefile"]
            )
        self.polygon_shapefile_layout.addWidget(self.polygon_shapefile_line_edit)
        self.polygon_shapefile_layout.addWidget(self.polygon_shapefile_button)
        self.main_layout.addLayout(self.polygon_shapefile_layout)

    def _add_field_selection_widgets(self) -> None:
        """
        Adds a dropdown to select a specific field from the selected shapefile.
        """
        self.field_selection_label = QLabel("Select Field")
        self.main_layout.addWidget(self.field_selection_label)

        self.field_selection_combo = QgsFieldComboBox()
        self.field_selection_combo.setFilters(QgsFieldProxyModel.String)
        self.field_selection_combo.setEnabled(
            False
        )  # Disable initially until a layer is selected
        self.main_layout.addWidget(self.field_selection_combo)

    def select_polygon_shapefile(self) -> None:
        """
        Opens a file dialog to select a shapefile for the polygon (paths) layer and updates the QLineEdit with the file path.
        """
        try:
            last_dir = self.settings.value("Geest/lastShapefileDir", "")

            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Polygon Shapefile", last_dir, "Shapefiles (*.shp)"
            )
            if file_path:
                self.polygon_shapefile_line_edit.setText(file_path)
                self.settings.setValue(
                    "Geest/lastShapefileDir", os.path.dirname(file_path)
                )

                # Load the shapefile as a QgsVectorLayer and populate the fields dropdown
                self._populate_field_combo(file_path)

        except Exception as e:
            log_message(
                f"Error selecting polygon shapefile: {e}",
                tag="Geest",
                level=Qgis.Critical,
            )

    def _populate_field_combo(self, shapefile_path: str) -> None:
        """
        Loads the shapefile and populates the field selection combo box with the field names.

        Args:
            shapefile_path (str): The path to the shapefile.
        """
        try:
            # Store the currently selected field
            previous_field = self.settings.value(
                f"{self.widget_key}_selected_field", None
            )

            vector_layer = QgsVectorLayer(shapefile_path, "polygon_layer", "ogr")
            if not vector_layer.isValid():
                log_message(f"Failed to load shapefile: {shapefile_path}", "Geest")
                return

            # Set the vector layer on the field selection combo box, which will automatically populate it
            QgsProject.instance().addMapLayer(vector_layer, False)
            self.field_selection_combo.setLayer(vector_layer)
            self.field_selection_combo.setEnabled(True)  # Enable once layer is valid

            # Reapply the previously selected field if it exists
            if (
                previous_field
                and self.field_selection_combo.findText(previous_field) != -1
            ):
                self.field_selection_combo.setCurrentText(previous_field)

        except Exception as e:
            log_message(f"Error populating field combo: {e}", level=Qgis.Critical)

    def update_field_combo(self) -> None:
        """
        Updates the field combo box when the polygon layer or shapefile is changed.
        """
        # Store the currently selected field
        previous_field = self.settings.value(f"{self.widget_key}_selected_field", None)

        if self.polygon_layer_combo.currentLayer():
            # Populate field combo from the selected polygon layer
            self.field_selection_combo.setLayer(self.polygon_layer_combo.currentLayer())
            self.field_selection_combo.setEnabled(True)
        elif self.polygon_shapefile_line_edit.text():
            # If shapefile is provided, populate the field combo
            self._populate_field_combo(self.polygon_shapefile_line_edit.text())

        # After the field combo is repopulated, re-select the previously selected field if it exists
        if previous_field and self.field_selection_combo.findText(previous_field) != -1:
            self.field_selection_combo.setCurrentText(previous_field)

    def get_data(self) -> dict:
        """
        Retrieves and returns the current state of the widget, including selected polygon layers or shapefiles.

        Returns:
            dict: A dictionary containing the current attributes of the polygon layers and/or shapefiles.
        """
        if not self.isChecked():
            return None
        updated_attributes = self.table_to_dict()

        self.attributes["classify_safety_polygon_into_classes_unique_values"] = (
            updated_attributes
        )
        # Collect data for the polygon layer
        polygon_layer = self.polygon_layer_combo.currentLayer()
        if polygon_layer:
            self.attributes[f"{self.widget_key}_layer_name"] = polygon_layer.name()
            self.attributes[f"{self.widget_key}_layer_source"] = polygon_layer.source()
            self.attributes[f"{self.widget_key}_layer_provider_type"] = (
                polygon_layer.providerType()
            )
            self.attributes[f"{self.widget_key}_layer_crs"] = (
                polygon_layer.crs().authid()
            )
            self.attributes[f"{self.widget_key}_layer_wkb_type"] = (
                polygon_layer.wkbType()
            )
            self.attributes[f"{self.widget_key}_layer_id"] = polygon_layer.id()
        self.attributes[f"{self.widget_key}_shapefile"] = (
            self.polygon_shapefile_line_edit.text()
        )
        # Get the selected field if field combo box is enabled
        selected_field = (
            self.field_selection_combo.currentText()
            if self.field_selection_combo.isEnabled()
            else None
        )
        self.attributes[f"{self.widget_key}_selected_field"] = selected_field

        return self.attributes

    def update_selected_field(self) -> None:
        """
        Updates the selected field in the attributes dictionary when the field selection changes.
        """
        if self.field_selection_combo.isEnabled():
            selected_field = self.field_selection_combo.currentText()
            self.attributes[f"{self.widget_key}_selected_field"] = selected_field

            # Store the selected field in QSettings
            self.settings.setValue(f"{self.widget_key}_selected_field", selected_field)
        else:
            self.attributes[f"{self.widget_key}_selected_field"] = None

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets (polygon layers) based on the state of the radio button.

        Args:
            enabled (bool): Whether to enable or disable the internal widgets.
        """
        try:
            self.polygon_layer_combo.setEnabled(enabled)
            self.polygon_shapefile_line_edit.setEnabled(enabled)
            self.polygon_shapefile_button.setEnabled(enabled)
            self.field_selection_combo.setEnabled(
                enabled and self.field_selection_combo.count() > 0
            )
        except Exception as e:
            log_message(
                f"Error in set_internal_widgets_enabled: {e}",
                tag="Geest",
                level=Qgis.Critical,
            )
