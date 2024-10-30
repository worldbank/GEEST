import os
from qgis.PyQt.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QToolButton,
    QFileDialog,
    QSpinBox,
)
from qgis.gui import QgsMapLayerComboBox

from .base_indicator_widget import BaseIndicatorWidget
from qgis.core import QgsMessageLog, QgsMapLayerProxyModel, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QSettings


class SingleBufferDistanceWidget(BaseIndicatorWidget):
    """
    A specialized radio button with additional QSpinBox buffer distance.
    """

    def add_internal_widgets(self) -> None:
        """
        Adds internal widgets specific to self.set_internal_widgets_visible(self.isChecked()) - in this case there are none.
        """
        try:
            self.main_layout = QVBoxLayout()

            # Point Layer Combobox - Filtered to point layers
            self.point_layer_label = QLabel(
                "Point Layer - shapefile will have preference"
            )
            self.main_layout.addWidget(self.point_layer_label)

            self.layer_combo = QgsMapLayerComboBox()
            self.layer_combo.setFilters(QgsMapLayerProxyModel.PointLayer)
            self.main_layout.addWidget(self.layer_combo)

            # Set the selected QgsVectorLayer in QgsMapLayerComboBox
            layer_id = self.attributes.get("single_buffer_point_layer_id", None)
            if layer_id:
                layer = QgsProject.instance().mapLayer(layer_id)
                if layer:
                    self.layer_combo.setLayer(layer)
            layer_id = self.attributes.get("single_buffer_point_layer_id")
            layer = QgsProject.instance().mapLayer(layer_id)

            if layer and isinstance(layer, QgsVectorLayer):
                self.layer_combo.setLayer(layer)

            # Add shapefile selection (QLineEdit and QToolButton)
            self.shapefile_layout = QHBoxLayout()
            self.shapefile_line_edit = QLineEdit()
            self.shapefile_button = QToolButton()
            self.shapefile_button.setText("...")
            self.shapefile_button.clicked.connect(self.select_shapefile)
            if self.attributes.get("single_buffer_point_layer_shapefile", False):
                self.shapefile_line_edit.setText(
                    self.attributes["single_buffer_point_layer_shapefile"]
                )
            self.shapefile_layout.addWidget(self.shapefile_line_edit)
            self.shapefile_layout.addWidget(self.shapefile_button)
            self.main_layout.addLayout(self.shapefile_layout)

            # Travel Increments input
            self.buffer_distance_layout = QHBoxLayout()
            self.buffer_distance_label = QLabel("Buffer Distance (m):")
            self.buffer_distance_input = QSpinBox()
            self.buffer_distance_input.setRange(0, 100000)
            self.buffer_distance_layout.addWidget(self.buffer_distance_label)
            self.buffer_distance_layout.addWidget(self.buffer_distance_input)
            default_distance = self.attributes.get(
                "default_single_buffer_travel_distance", 0
            )
            buffer_distance = self.attributes.get(
                "single_buffer_point_layer_distance", default_distance
            )
            try:
                self.buffer_distance_input.setValue(int(buffer_distance))
            except (ValueError, TypeError):
                self.buffer_distance_input.setValue(int(default_distance))

            # Add all layouts to the main layout
            self.main_layout.addLayout(self.buffer_distance_layout)
            self.layout.addLayout(self.main_layout)

            # Emit the data_changed signal when any widget is changed
            self.layer_combo.currentIndexChanged.connect(self.update_data)
            self.buffer_distance_input.valueChanged.connect(self.update_data)

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

                # Save the directory of the selected file to QSettings
                settings.setValue("Geest/lastShapefileDir", os.path.dirname(file_path))

        except Exception as e:
            QgsMessageLog.logMessage(f"Error selecting shapefile: {e}", "Geest")

    def get_data(self) -> dict:
        """
        Return the data as a dictionary, updating attributes with current value.
        """
        if not self.isChecked():
            return None

        layer = self.layer_combo.currentLayer()
        if not layer:
            self.attributes["single_buffer_point_layer"] = None
        else:
            self.attributes["single_buffer_point_layer_name"] = layer.name()
            self.attributes["single_buffer_point_layer_source"] = layer.source()
            self.attributes["single_buffer_point_layer_provider_type"] = (
                layer.providerType()
            )
            self.attributes["single_buffer_point_layer_crs"] = (
                layer.crs().authid()
            )  # Coordinate Reference System
            self.attributes["single_buffer_point_layer_wkb_type"] = (
                layer.wkbType()
            )  # Geometry type (e.g., Point, Polygon)
            self.attributes["single_buffer_point_layer_id"] = (
                layer.id()
            )  # Unique ID of the layer

        self.attributes["single_buffer_point_layer_distance"] = (
            self.buffer_distance_input.text()
        )
        self.attributes["single_buffer_point_layer_shapefile"] = (
            self.shapefile_line_edit.text()
        )

        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets based on the state of the radio button.
        """
        try:
            self.layer_combo.setEnabled(enabled)
            self.buffer_distance_input.setEnabled(enabled)
            self.buffer_distance_label.setEnabled(enabled)
            self.point_layer_label.setEnabled(enabled)
            self.buffer_distance_layout.setEnabled(enabled)
            self.shapefile_line_edit.setEnabled(enabled)
            self.shapefile_button.setEnabled(enabled)
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error in set_internal_widgets_enabled: {e}", "Geest"
            )
