import os
from qgis.PyQt.QtWidgets import (
    QLineEdit,
    QToolButton,
    QFileDialog,
)
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QSettings, Qt

from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox
from qgis.core import (
    QgsMapLayerProxyModel,
    QgsProject,
    QgsFieldProxyModel,
    QgsVectorLayer,
    QgsWkbTypes,
    Qgis,
)

from .base_datasource_widget import BaseDataSourceWidget
from geest.utilities import log_message, resources_path


class VectorAndFieldDataSourceWidget(BaseDataSourceWidget):
    """
    A specialized widget for choosing a vector layer (without a field selection).

    Subclass this widget to specify the geometry type to filter the QgsMapLayerComboBox.
    """

    def add_internal_widgets(self) -> None:
        """
        Adds internal widgets specific to vector layer selection

        """
        self.settings = QSettings()

        try:
            self.layer_combo = QgsMapLayerComboBox()
            filter = None
            if self.attributes.get("use_classify_polygon_into_classes", 0):
                filter = QgsMapLayerProxyModel.PolygonLayer
            elif self.attributes.get("use_classify_safety_polygon_into_classes", 0):
                filter = QgsMapLayerProxyModel.PolygonLayer
            else:
                filter = QgsMapLayerProxyModel.PointLayer

            self.layer_combo = QgsMapLayerComboBox()
            self.layer_combo.setFilters(filter)
            self.layer_combo.setAllowEmptyLayer(True)
            # Insert placeholder text at the top (only visually, not as a selectable item)
            self.layer_combo.setCurrentIndex(-1)  # Ensure no selection initially
            self.layer_combo.setEditable(
                True
            )  # Make editable temporarily for placeholder
            self.layer_combo.lineEdit().setPlaceholderText(
                "Select item"
            )  # Add placeholder text

            # Disable editing after setting placeholder (ensures only layer names are selectable)
            self.layer_combo.lineEdit().setReadOnly(True)
            self.layer_combo.setEditable(
                False
            )  # Lock back to non-editable after setting placeholder

            self.layout.addWidget(self.layer_combo)

            # Set the selected QgsVectorLayer in QgsMapLayerComboBox
            layer_id = self.attributes.get(f"{self.widget_key}_layer_id", None)
            if layer_id:
                layer = QgsProject.instance().mapLayer(layer_id)
                if layer:
                    self.layer_combo.setLayer(layer)

            # For when the user prefers to choose a path to a shapefile
            self.shapefile_line_edit = QLineEdit()
            self.shapefile_line_edit.setVisible(False)  # Hide initially

            # Add clear button inside the line edit
            self.clear_button = QToolButton(self.shapefile_line_edit)
            clear_icon = QIcon(resources_path("resources", "icons", "clear.svg"))
            self.clear_button.setIcon(clear_icon)
            self.clear_button.setToolTip("Clear")
            self.clear_button.setCursor(Qt.ArrowCursor)
            self.clear_button.setStyleSheet("border: 0px; padding: 0px;")
            self.clear_button.clicked.connect(self.clear_shapefile)
            self.clear_button.setVisible(False)

            self.shapefile_line_edit.textChanged.connect(
                lambda text: self.clear_button.setVisible(bool(text))
            )
            self.shapefile_line_edit.textChanged.connect(self.resize_clear_button)

            # Add a button to select a shapefile
            self.shapefile_button = QToolButton()
            self.shapefile_button.setText("...")
            self.shapefile_button.clicked.connect(self.select_shapefile)
            if self.attributes.get(f"{self.widget_key}_shapefile", False):
                self.shapefile_line_edit.setText(
                    self.attributes[f"{self.widget_key}_shapefile"]
                )
                self.shapefile_line_edit.setVisible(True)
                self.layer_combo.setVisible(False)
            else:
                self.layer_combo.setVisible(True)

            self.layout.addWidget(self.shapefile_line_edit)
            self.resize_clear_button()
            self.layout.addWidget(self.shapefile_button)

            # Adds a dropdown to select a specific field from the selected shapefile.
            field_type = QgsFieldProxyModel.Numeric
            if self.attributes.get("id", None) == "Street_Lights":
                field_type = QgsFieldProxyModel.String
            self.field_selection_combo = QgsFieldComboBox()
            self.field_selection_combo.setFilters(
                field_type
            )  # Filter for numeric fields
            self.field_selection_combo.setEnabled(
                False
            )  # Disable initially until a layer is selected
            # self.field_selection_combo.setMinimumWidth(150)  # Set a reasonable minimum width
            # self.field_selection_combo.setSizeAdjustPolicy(QgsFieldComboBox.AdjustToContents)
            self.layout.addWidget(self.field_selection_combo)

            # Emit the data_changed signal when any widget is changed
            self.layer_combo.currentIndexChanged.connect(self.update_attributes)
            self.shapefile_line_edit.textChanged.connect(self.update_attributes)
            # Connect signals to update the fields when user changes selections
            self.layer_combo.layerChanged.connect(self.update_field_combo)
            self.shapefile_line_edit.textChanged.connect(self.update_field_combo)

            # Connect the field combo box to update the attributes when a field is selected
            self.field_selection_combo.currentIndexChanged.connect(
                self.update_selected_field
            )

            self.update_field_combo()  # Populate fields for the initially selected layer

        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", level=Qgis.Critical)
            import traceback

            log_message(traceback.format_exc(), level=Qgis.Critical)

    def resizeEvent(self, event):
        """
        Handle resize events for the parent container.

        Args:
            event: The resize event.
        """
        super().resizeEvent(event)
        self.resize_clear_button()

    def resize_clear_button(self):
        """Reposition the clear button when the line edit is resized."""
        log_message("Resizing clear button")
        # Position the clear button inside the line edit
        frame_width = self.shapefile_line_edit.style().pixelMetric(
            self.shapefile_line_edit.style().PM_DefaultFrameWidth
        )
        self.shapefile_line_edit.setStyleSheet(
            f"QLineEdit {{ padding-right: {self.clear_button.sizeHint().width() + frame_width}px; }}"
        )
        sz = self.clear_button.sizeHint()
        self.clear_button.move(
            self.shapefile_line_edit.width() - sz.width() - frame_width - 5, 6
        )

    def select_shapefile(self):
        """
        Opens a file dialog to select a shapefile and stores the last directory in QSettings.
        """
        try:
            settings = QSettings()
            last_dir = settings.value("Geest/lastShapefileDir", "")

            # Open file dialog to select a shapefile
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Shapefile", last_dir, "Shapefiles (*.shp)"
            )

            if file_path:
                # Update the line edit with the selected file path
                # ⚠️ Be careful about changing the order of the following lines
                #   It could cause the clear button to render in the incorrect place
                self.layer_combo.setVisible(False)
                self.shapefile_line_edit.setVisible(True)
                self.shapefile_line_edit.setText(file_path)
                # Trigger resize event explicitly
                self.resizeEvent(None)
                # Save the directory of the selected file to QSettings
                settings.setValue("Geest/lastShapefileDir", os.path.dirname(file_path))

        except Exception as e:
            log_message(f"Error selecting shapefile: {e}", level=Qgis.Critical)

    def clear_shapefile(self):
        """
        Clears the shapefile line edit and hides it along with the clear button.
        """
        self.shapefile_line_edit.clear()
        self.shapefile_line_edit.setVisible(False)
        self.layer_combo.setVisible(True)
        self.layer_combo.setFocus()
        self.update_attributes()

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

            vector_layer = QgsVectorLayer(shapefile_path, "layer", "ogr")
            if not vector_layer.isValid():
                log_message(f"Failed to load shapefile: {shapefile_path}")
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

    def update_selected_field(self) -> None:
        """
        Updates the selected field in the attributes dictionary when the field selection changes.
        """
        if not self.field_selection_combo.isEnabled():
            self.attributes[f"{self.widget_key}_selected_field"] = None
            self.data_changed.emit(self.attributes)
            return

        selected_field = self.field_selection_combo.currentText()
        self.attributes[f"{self.widget_key}_selected_field"] = selected_field

        # Store the selected field in QSettings
        self.settings.setValue(f"{self.widget_key}_selected_field", selected_field)
        if self.attributes.get("id", None) == "Street_Lights":
            # retrieve the unique values for the selected field
            vector_layer = self.layer_combo.currentLayer()
            idx = vector_layer.fields().indexOf(selected_field)
            values = vector_layer.uniqueValues(idx)
            values_dict = {}

            #  list the data type of each value
            for value in values:
                # log_message(f"{type(value)} value {value}")
                # Dont remove this! It cleans to contents to remove QVariants
                # introduced from empty table rows!
                if isinstance(value, str):
                    values_dict[value] = None
            # Preserve existing values if they exist
            existing_values = self.attributes.get(
                f"{self.widget_key}_unique_values", {}
            )

            for key in values_dict.keys():
                if key not in existing_values:
                    values_dict[key] = None
                else:
                    values_dict[key] = existing_values[key]
            log_message(f"Existing values: {existing_values}")
            log_message(f"New      values: {values_dict}")
            # will drop any keys in the json item that are not in values_dict
            self.attributes[f"{self.widget_key}_unique_values"] = values_dict
        self.data_changed.emit(self.attributes)

    def update_field_combo(self) -> None:
        """
        Updates the field combo box when the layer or shapefile is changed.
        """
        # Store the currently selected field
        previous_field = self.settings.value(f"{self.widget_key}_selected_field", None)

        if self.layer_combo.currentLayer():
            # Populate field combo from the selected  layer
            self.field_selection_combo.setLayer(self.layer_combo.currentLayer())
            self.field_selection_combo.setEnabled(True)
        elif self.shapefile_line_edit.text():
            # If shapefile is provided, populate the field combo
            self._populate_field_combo(self.shapefile_line_edit.text())
            self.layer_combo.setCurrentIndex(-1)  # Clear the layer combo selection

        # After the field combo is repopulated, re-select the previously selected field if it exists
        if previous_field and self.field_selection_combo.findText(previous_field) != -1:
            self.field_selection_combo.setCurrentText(previous_field)

    def update_attributes(self):
        """
        Updates the attributes dict to match the current state of the widget.

        The attributes dict is a reference so any tree item attributes will be updated directly.

        Returns:
            None
        """
        layer = self.layer_combo.currentLayer()
        if not layer:
            self.attributes[f"{self.widget_key}_layer"] = None
        else:
            self.attributes[f"{self.widget_key}_layer_name"] = layer.name()
            self.attributes[f"{self.widget_key}_layer_source"] = layer.source()
            self.attributes[f"{self.widget_key}_layer_provider_type"] = (
                layer.providerType()
            )
            self.attributes[f"{self.widget_key}_layer_crs"] = (
                layer.crs().authid()
            )  # Coordinate Reference System
            self.attributes[f"{self.widget_key}_layer_wkb_type"] = (
                QgsWkbTypes.displayString(layer.wkbType())
            )  # Geometry type (e.g., Point, Polygon)
            self.attributes[f"{self.widget_key}_layer_id"] = (
                layer.id()
            )  # Unique ID of the layer
        self.attributes[f"{self.widget_key}_shapefile"] = (
            self.shapefile_line_edit.text()
        )
        self.data_changed.emit(self.attributes)
