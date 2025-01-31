import os
from qgis.PyQt.QtWidgets import (
    QLineEdit,
    QToolButton,
    QFileDialog,
)
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QSettings, Qt
from qgis.gui import QgsMapLayerComboBox
from .base_datasource_widget import BaseDataSourceWidget
from qgis.core import QgsMapLayerProxyModel, QgsProject, Qgis
from geest.utilities import log_message, resources_path


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
            # check the attributes to decide what feature types to
            # filter for.
            filter = None
            if self.attributes.get("use_single_buffer_point", 0):
                filter = QgsMapLayerProxyModel.PointLayer
            elif self.attributes.get("use_point_per_cell", 0):
                filter = QgsMapLayerProxyModel.PointLayer
            elif self.attributes.get("use_multi_buffer_point", 0):
                filter = QgsMapLayerProxyModel.PointLayer
            elif self.attributes.get("use_street_lights", 0):
                filter = QgsMapLayerProxyModel.PointLayer
            elif self.attributes.get("use_polyline_per_cell", 0):
                filter = QgsMapLayerProxyModel.LineLayer
            else:
                filter = QgsMapLayerProxyModel.PolygonLayer
            self.layer_combo = QgsMapLayerComboBox()
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

            self.layer_combo.setFilters(filter)
            self.layout.addWidget(self.layer_combo)

            # Set the selected QgsVectorLayer in QgsMapLayerComboBox
            layer_id = self.attributes.get(f"{self.widget_key}_layer_id", None)
            if layer_id:
                layer = QgsProject.instance().mapLayer(layer_id)
                if layer:
                    self.layer_combo.setLayer(layer)

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

            # Emit the data_changed signal when any widget is changed
            self.layer_combo.currentIndexChanged.connect(self.update_attributes)
            self.shapefile_line_edit.textChanged.connect(self.update_attributes)

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
            self.shapefile_line_edit.width() - sz.width() - frame_width - 5,
            self.shapefile_line_edit.height() - sz.height() - frame_width,
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
                layer.wkbType()
            )  # Geometry type (e.g., Point, Polygon)
            self.attributes[f"{self.widget_key}_layer_id"] = (
                layer.id()
            )  # Unique ID of the layer
        self.attributes[f"{self.widget_key}_shapefile"] = (
            self.shapefile_line_edit.text()
        )
