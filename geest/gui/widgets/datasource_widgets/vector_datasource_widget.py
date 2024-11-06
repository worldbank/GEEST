import os
from qgis.PyQt.QtWidgets import (
    QLineEdit,
    QToolButton,
    QFileDialog,
)
from qgis.gui import QgsMapLayerComboBox

from .base_datasource_widget import BaseDataSourceWidget
from qgis.core import QgsMessageLog, QgsMapLayerProxyModel, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QSettings


class VectorDataSourceWidget(BaseDataSourceWidget):
    """
    A specialized widget for choosing a vector layer (without a field selection).

    Subclass this widget to specify the geometry type to filter the QgsMapLayerComboBox.
    """

    def add_internal_widgets(self) -> None:
        """
        Adds internal widgets specific to vector layer selection

        """
        try:
            self.layer_combo = QgsMapLayerComboBox()
            self.layer_combo.setFilters(QgsMapLayerProxyModel.PointLayer)
            self.layout.addWidget(self.layer_combo)

            # Set the selected QgsVectorLayer in QgsMapLayerComboBox
            layer_id = self.attributes.get(f"{self.widget_key}_layer_id", None)
            if layer_id:
                layer = QgsProject.instance().mapLayer(layer_id)
                if layer:
                    self.layer_combo.setLayer(layer)

            self.shapefile_line_edit = QLineEdit()
            self.shapefile_line_edit.setVisible(False)  # Hide initially

            self.shapefile_button = QToolButton()
            self.shapefile_button.setText("...")
            self.shapefile_button.clicked.connect(self.select_shapefile)
            if self.attributes.get(f"{self.widget_key}_shapefile", False):
                self.shapefile_line_edit.setText(
                    self.attributes[f"{self.widget_key}_shapefile"]
                )
            self.layout.addWidget(self.shapefile_line_edit)
            self.layout.addWidget(self.shapefile_button)

            # Emit the data_changed signal when any widget is changed
            self.layer_combo.currentIndexChanged.connect(self.update_data)
            self.shapefile_line_edit.textChanged.connect(self.update_data)

        except Exception as e:
            QgsMessageLog.logMessage(f"Error in add_internal_widgets: {e}", "Geest")
            import traceback

            QgsMessageLog.logMessage(traceback.format_exc(), "Geest")

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
                self.shapefile_line_edit.setText(file_path)
                self.shapefile_line_edit.setVisible(True)
                # Save the directory of the selected file to QSettings
                settings.setValue("Geest/lastShapefileDir", os.path.dirname(file_path))

        except Exception as e:
            QgsMessageLog.logMessage(f"Error selecting shapefile: {e}", "Geest")

    def get_data(self) -> dict:
        """
        Return the data as a dictionary, updating attributes with current value.
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
                layer.wkbType()
            )  # Geometry type (e.g., Point, Polygon)
            self.attributes[f"{self.widget_key}_layer_id"] = (
                layer.id()
            )  # Unique ID of the layer
        self.attributes[f"{self.widget_key}_shapefile"] = (
            self.shapefile_line_edit.text()
        )

        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets based on the state of the radio button.
        """
        try:
            self.layer_combo.setEnabled(enabled)
            self.shapefile_line_edit.setEnabled(enabled)
            self.shapefile_button.setEnabled(enabled)
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error in set_internal_widgets_enabled: {e}", "Geest"
            )
