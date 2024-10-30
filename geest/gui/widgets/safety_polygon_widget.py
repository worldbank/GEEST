from qgis.PyQt.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QToolButton,
    QFileDialog,
)
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox
from qgis.core import (
    QgsMessageLog,
    QgsMapLayerProxyModel,
    QgsProject,
    QgsVectorLayer,
    QgsFieldProxyModel,
)
from qgis.PyQt.QtCore import QSettings
import os

from .base_indicator_widget import BaseIndicatorWidget


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
            self.widget_key = "classify_poly_into_classes"
            self.settings = QSettings()

            # Polygon Layer Section
            self._add_polygon_layer_widgets()

            # Add Field Selection Dropdown
            self._add_field_selection_widgets()

            # Add the main layout to the widget's layout
            self.layout.addLayout(self.main_layout)

            # Connect signals to update the data when user changes selections
            self.polygon_layer_combo.currentIndexChanged.connect(self.update_data)
            self.polygon_shapefile_line_edit.textChanged.connect(self.update_data)
            # Connect signals to update the data when user changes selections
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
            QgsMessageLog.logMessage(f"Error in add_internal_widgets: {e}", "Geest")
            import traceback

            QgsMessageLog.logMessage(traceback.format_exc(), "Geest")

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
        polygon_layer_id = self.attributes.get(
            f"{self.widget_key} Polygon_layer_id", None
        )
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
        if self.attributes.get(f"{self.widget_key} Polygon_shapefile", False):
            self.polygon_shapefile_line_edit.setText(
                self.attributes[f"{self.widget_key} Polygon_shapefile"]
            )
        self.polygon_shapefile_layout.addWidget(self.polygon_shapefile_line_edit)
        self.polygon_shapefile_layout.addWidget(self.polygon_shapefile_button)
        self.main_layout.addLayout(self.polygon_shapefile_layout)

    def _add_field_selection_widgets(self) -> None:
        """
        Adds a dropdown to select a specific field from the selected shapefile.
        """
        self.field_selection_label = QLabel("Select Field:")
        self.main_layout.addWidget(self.field_selection_label)

        self.field_selection_combo = QgsFieldComboBox()
        self.field_selection_combo.setFilters(
            QgsFieldProxyModel.Numeric
        )  # Filter for numeric fields
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
            QgsMessageLog.logMessage(f"Error selecting polygon shapefile: {e}", "Geest")

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
                QgsMessageLog.logMessage(
                    f"Failed to load shapefile: {shapefile_path}", "Geest"
                )
                return

            # Set the vector layer on the field selection combo box, which will automatically populate it
            self.field_selection_combo.setLayer(vector_layer)
            self.field_selection_combo.setEnabled(True)  # Enable once layer is valid

            # Reapply the previously selected field if it exists
            if (
                previous_field
                and self.field_selection_combo.findText(previous_field) != -1
            ):
                self.field_selection_combo.setCurrentText(previous_field)

        except Exception as e:
            QgsMessageLog.logMessage(f"Error populating field combo: {e}", "Geest")

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
            QgsMessageLog.logMessage(
                f"Error in set_internal_widgets_enabled: {e}", "Geest"
            )
