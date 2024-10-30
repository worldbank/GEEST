from qgis.PyQt.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QToolButton,
    QFileDialog,
)
from qgis.gui import QgsMapLayerComboBox
from qgis.core import QgsMessageLog, QgsMapLayerProxyModel, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QSettings
import os

from .base_indicator_widget import BaseIndicatorWidget


class PointAndPolylineWidget(BaseIndicatorWidget):
    """
    A widget for selecting a point layer and a polyline (paths) layer with options for shapefile inputs.

    This widget provides two `QgsMapLayerComboBox` components for selecting the point and polyline layers,
    as well as `QLineEdit` and `QToolButton` components to allow the user to specify shapefile paths for
    each layer. The user can choose layers either from the QGIS project or provide external shapefiles.

    Attributes:
        widget_key (str): The key identifier for this widget.
        point_layer_combo (QgsMapLayerComboBox): A combo box for selecting the point layer.
        point_shapefile_line_edit (QLineEdit): Line edit for entering/selecting a point layer shapefile.
        polyline_layer_combo (QgsMapLayerComboBox): A combo box for selecting the polyline layer.
        polyline_shapefile_line_edit (QLineEdit): Line edit for entering/selecting a polyline layer shapefile.
    """

    def add_internal_widgets(self) -> None:
        """
        Adds the internal widgets required for selecting point and polyline layers and their corresponding shapefiles.
        This method is called during the widget initialization and sets up the layout for the UI components.
        """
        try:
            self.main_layout = QVBoxLayout()
            self.widget_key = "Point and Polyline per Cell"

            # Point Layer Section
            self._add_point_layer_widgets()

            # Polyline Layer Section
            self._add_polyline_layer_widgets()

            # Add the main layout to the widget's layout
            self.layout.addLayout(self.main_layout)

            # Connect signals to update the data when user changes selections
            self.point_layer_combo.currentIndexChanged.connect(self.update_data)
            self.point_shapefile_line_edit.textChanged.connect(self.update_data)
            self.polyline_layer_combo.currentIndexChanged.connect(self.update_data)
            self.polyline_shapefile_line_edit.textChanged.connect(self.update_data)

        except Exception as e:
            QgsMessageLog.logMessage(f"Error in add_internal_widgets: {e}", "Geest")
            import traceback

            QgsMessageLog.logMessage(traceback.format_exc(), "Geest")

    def _add_point_layer_widgets(self) -> None:
        """
        Adds the widgets for selecting the point layer, including a `QgsMapLayerComboBox` and shapefile input.
        """
        self.point_layer_label = QLabel("Point Layer - shapefile will have preference")
        self.main_layout.addWidget(self.point_layer_label)

        # Point Layer ComboBox (Filtered to point layers)
        self.point_layer_combo = QgsMapLayerComboBox()
        self.point_layer_combo.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.main_layout.addWidget(self.point_layer_combo)

        # Restore previously selected point layer
        point_layer_id = self.attributes.get(f"{self.widget_key} Point_layer_id", None)
        if point_layer_id:
            point_layer = QgsProject.instance().mapLayer(point_layer_id)
            if point_layer:
                self.point_layer_combo.setLayer(point_layer)

        # _shapefile Input for Point Layer
        self.point_shapefile_layout = QHBoxLayout()
        self.point_shapefile_line_edit = QLineEdit()
        self.point_shapefile_button = QToolButton()
        self.point_shapefile_button.setText("...")
        self.point_shapefile_button.clicked.connect(self.select_point_shapefile)
        if self.attributes.get(f"{self.widget_key} Point_shapefile", False):
            self.point_shapefile_line_edit.setText(
                self.attributes[f"{self.widget_key} Point_shapefile"]
            )
        self.point_shapefile_layout.addWidget(self.point_shapefile_line_edit)
        self.point_shapefile_layout.addWidget(self.point_shapefile_button)
        self.main_layout.addLayout(self.point_shapefile_layout)

    def _add_polyline_layer_widgets(self) -> None:
        """
        Adds the widgets for selecting the polyline layer, including a `QgsMapLayerComboBox` and shapefile input.
        """
        self.polyline_layer_label = QLabel(
            "Polyline Layer - shapefile will have preference"
        )
        self.main_layout.addWidget(self.polyline_layer_label)

        # Polyline Layer ComboBox (Filtered to line layers)
        self.polyline_layer_combo = QgsMapLayerComboBox()
        self.polyline_layer_combo.setFilters(QgsMapLayerProxyModel.LineLayer)
        self.main_layout.addWidget(self.polyline_layer_combo)

        # Restore previously selected polyline layer
        polyline_layer_id = self.attributes.get(
            f"{self.widget_key} Polyline_layer_id", None
        )
        if polyline_layer_id:
            polyline_layer = QgsProject.instance().mapLayer(polyline_layer_id)
            if polyline_layer:
                self.polyline_layer_combo.setLayer(polyline_layer)

        # _shapefile Input for Polyline Layer
        self.polyline_shapefile_layout = QHBoxLayout()
        self.polyline_shapefile_line_edit = QLineEdit()
        self.polyline_shapefile_button = QToolButton()
        self.polyline_shapefile_button.setText("...")
        self.polyline_shapefile_button.clicked.connect(self.select_polyline_shapefile)
        if self.attributes.get(f"{self.widget_key} Polyline_shapefile", False):
            self.polyline_shapefile_line_edit.setText(
                self.attributes[f"{self.widget_key} Polyline_shapefile"]
            )
        self.polyline_shapefile_layout.addWidget(self.polyline_shapefile_line_edit)
        self.polyline_shapefile_layout.addWidget(self.polyline_shapefile_button)
        self.main_layout.addLayout(self.polyline_shapefile_layout)

    def select_point_shapefile(self) -> None:
        """
        Opens a file dialog to select a shapefile for the point layer and updates the QLineEdit with the file path.
        """
        try:
            settings = QSettings()
            last_dir = settings.value("Geest/lastShapefileDir", "")

            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Point_shapefile", last_dir, "Shapefiles (*.shp)"
            )
            if file_path:
                self.point_shapefile_line_edit.setText(file_path)
                settings.setValue("Geest/lastShapefileDir", os.path.dirname(file_path))

        except Exception as e:
            QgsMessageLog.logMessage(f"Error selecting point shapefile: {e}", "Geest")

    def select_polyline_shapefile(self) -> None:
        """
        Opens a file dialog to select a shapefile for the polyline (paths) layer and updates the QLineEdit with the file path.
        """
        try:
            settings = QSettings()
            last_dir = settings.value("Geest/lastShapefileDir", "")

            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Polyline_shapefile", last_dir, "Shapefiles (*.shp)"
            )
            if file_path:
                self.polyline_shapefile_line_edit.setText(file_path)
                settings.setValue("Geest/lastShapefileDir", os.path.dirname(file_path))

        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error selecting polyline shapefile: {e}", "Geest"
            )

    def get_data(self) -> dict:
        """
        Retrieves and returns the current state of the widget, including selected point and polyline layers or shapefiles.

        Returns:
            dict: A dictionary containing the current attributes of the point and polyline layers and/or shapefiles.
        """
        if not self.isChecked():
            return None

        # Collect data for the point layer
        point_layer = self.point_layer_combo.currentLayer()
        if point_layer:
            self.attributes[f"{self.widget_key} Point_layer_name"] = point_layer.name()
            self.attributes[f"{self.widget_key} Point_layer_source"] = (
                point_layer.source()
            )
            self.attributes[f"{self.widget_key} Point_layer_provider_type"] = (
                point_layer.providerType()
            )
            self.attributes[f"{self.widget_key} Point_layer_crs"] = (
                point_layer.crs().authid()
            )
            self.attributes[f"{self.widget_key} Point_layer_wkb_type"] = (
                point_layer.wkbType()
            )
            self.attributes[f"{self.widget_key} Point_layer_id"] = point_layer.id()
        self.attributes[f"{self.widget_key} Point_shapefile"] = (
            self.point_shapefile_line_edit.text()
        )

        # Collect data for the polyline layer
        polyline_layer = self.polyline_layer_combo.currentLayer()
        if polyline_layer:
            self.attributes[f"{self.widget_key} Polyline_layer_name"] = (
                polyline_layer.name()
            )
            self.attributes[f"{self.widget_key} Polyline_layer_source"] = (
                polyline_layer.source()
            )
            self.attributes[f"{self.widget_key} Polyline_layer_provider_type"] = (
                polyline_layer.providerType()
            )
            self.attributes[f"{self.widget_key} Polyline_layer_crs"] = (
                polyline_layer.crs().authid()
            )
            self.attributes[f"{self.widget_key} Polyline_layer_wkb_type"] = (
                polyline_layer.wkbType()
            )
            self.attributes[f"{self.widget_key} Polyline_layer_id"] = (
                polyline_layer.id()
            )
        self.attributes[f"{self.widget_key} Polyline_shapefile"] = (
            self.polyline_shapefile_line_edit.text()
        )

        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets (both point and polyline layers) based on the state of the radio button.

        Args:
            enabled (bool): Whether to enable or disable the internal widgets.
        """
        try:
            self.point_layer_combo.setEnabled(enabled)
            self.point_shapefile_line_edit.setEnabled(enabled)
            self.point_shapefile_button.setEnabled(enabled)
            self.polyline_layer_combo.setEnabled(enabled)
            self.polyline_shapefile_line_edit.setEnabled(enabled)
            self.polyline_shapefile_button.setEnabled(enabled)
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error in set_internal_widgets_enabled: {e}", "Geest"
            )
