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


class PolylineWidget(BaseIndicatorWidget):
    """
    A widget for selecting a polyline (paths) layer with options for shapefile inputs.

    This widget provides one `QgsMapLayerComboBox` components for selecting polyline layers,
    as well as `QLineEdit` and `QToolButton` components to allow the user to specify shapefile paths for
    each layer. The user can choose layers either from the QGIS project or provide external shapefiles.

    Attributes:
        widget_key (str): The key identifier for this widget.
        polyline_layer_combo (QgsMapLayerComboBox): A combo box for selecting the polyline layer.
        polyline_shapefile_line_edit (QLineEdit): Line edit for entering/selecting a polyline layer shapefile.
    """

    def add_internal_widgets(self) -> None:
        """
        Adds the internal widgets required for selecting polyline layers and their corresponding shapefiles.
        This method is called during the widget initialization and sets up the layout for the UI components.
        """
        try:
            self.main_layout = QVBoxLayout()
            self.widget_key = "polyline_per_cell"

            # Polyline Layer Section
            self._add_polyline_layer_widgets()

            # Add the main layout to the widget's layout
            self.layout.addLayout(self.main_layout)

            # Connect signals to update the data when user changes selections
            self.polyline_layer_combo.currentIndexChanged.connect(self.update_data)
            self.polyline_shapefile_line_edit.textChanged.connect(self.update_data)

        except Exception as e:
            QgsMessageLog.logMessage(f"Error in add_internal_widgets: {e}", "Geest")
            import traceback

            QgsMessageLog.logMessage(traceback.format_exc(), "Geest")

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
            f"{self.widget_key}_polyline_layer_id", None
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
        if self.attributes.get(f"{self.widget_key}_polyline_shapefile", False):
            self.polyline_shapefile_line_edit.setText(
                self.attributes[f"{self.widget_key}_polyline_shapefile"]
            )
        self.polyline_shapefile_layout.addWidget(self.polyline_shapefile_line_edit)
        self.polyline_shapefile_layout.addWidget(self.polyline_shapefile_button)
        self.main_layout.addLayout(self.polyline_shapefile_layout)

    def select_polyline_shapefile(self) -> None:
        """
        Opens a file dialog to select a shapefile for the polyline (paths) layer and updates the QLineEdit with the file path.
        """
        try:
            settings = QSettings()
            last_dir = settings.value("Geest/lastShapefileDir", "")

            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Polyline Shapefile", last_dir, "Shapefiles (*.shp)"
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
        Retrieves and returns the current state of the widget, including selected polyline layers or shapefiles.

        Returns:
            dict: A dictionary containing the current attributes of the polyline layers and/or shapefiles.
        """
        if not self.isChecked():
            return None

        # Collect data for the polyline layer
        polyline_layer = self.polyline_layer_combo.currentLayer()
        if polyline_layer:
            self.attributes[f"{self.widget_key}_layer_name"] = polyline_layer.name()
            self.attributes[f"{self.widget_key}_layer_source"] = polyline_layer.source()
            self.attributes[f"{self.widget_key}_layer_provider_type"] = (
                polyline_layer.providerType()
            )
            self.attributes[f"{self.widget_key}_layer_crs"] = (
                polyline_layer.crs().authid()
            )
            self.attributes[f"{self.widget_key}_layer_wkb_type"] = (
                polyline_layer.wkbType()
            )
            self.attributes[f"{self.widget_key}_layer_id"] = polyline_layer.id()
        self.attributes[f"{self.widget_key}_shapefile"] = (
            self.polyline_shapefile_line_edit.text()
        )

        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets (polyline layers) based on the state of the radio button.

        Args:
            enabled (bool): Whether to enable or disable the internal widgets.
        """
        try:
            self.polyline_layer_combo.setEnabled(enabled)
            self.polyline_shapefile_line_edit.setEnabled(enabled)
            self.polyline_shapefile_button.setEnabled(enabled)
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error in set_internal_widgets_enabled: {e}", "Geest"
            )
