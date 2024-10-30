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


class PolygonWidget(BaseIndicatorWidget):
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
            self.widget_key = "polygon_per_cell"

            # Polygon Layer Section
            self._add_polygon_layer_widgets()

            # Add the main layout to the widget's layout
            self.layout.addLayout(self.main_layout)

            # Connect signals to update the data when user changes selections
            self.polygon_layer_combo.currentIndexChanged.connect(self.update_data)
            self.polygon_shapefile_line_edit.textChanged.connect(self.update_data)

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
            f"{self.widget_key}_polygon_layer_id", None
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
        if self.attributes.get(f"{self.widget_key}_polygon_shapefile", False):
            self.polygon_shapefile_line_edit.setText(
                self.attributes[f"{self.widget_key}_polygon_shapefile"]
            )
        self.polygon_shapefile_layout.addWidget(self.polygon_shapefile_line_edit)
        self.polygon_shapefile_layout.addWidget(self.polygon_shapefile_button)
        self.main_layout.addLayout(self.polygon_shapefile_layout)

    def select_polygon_shapefile(self) -> None:
        """
        Opens a file dialog to select a shapefile for the polygon (paths) layer and updates the QLineEdit with the file path.
        """
        try:
            settings = QSettings()
            last_dir = settings.value("Geest/lastShapefileDir", "")

            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Polygon Shapefile", last_dir, "Shapefiles (*.shp)"
            )
            if file_path:
                self.polygon_shapefile_line_edit.setText(file_path)
                settings.setValue("Geest/lastShapefileDir", os.path.dirname(file_path))

        except Exception as e:
            QgsMessageLog.logMessage(f"Error selecting polygon shapefile: {e}", "Geest")

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

        return self.attributes

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
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error in set_internal_widgets_enabled: {e}", "Geest"
            )
