from qgis.PyQt.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QToolButton,
    QFileDialog,
)
from qgis.gui import QgsMapLayerComboBox
from qgis.core import (
    QgsMessageLog,
    QgsMapLayerProxyModel,
    QgsProject,
)
from qgis.PyQt.QtCore import QSettings
import os

from .base_indicator_widget import BaseIndicatorWidget


class RasterReclassificationWidget(BaseIndicatorWidget):
    """

    A widget for selecting a raster (area) layer with options for inputs.

    This widget provides one `QgsMapLayerComboBox` components for selecting raster layers,
    as well as `QLineEdit` and `QToolButton` components to allow the user to specify paths for
    each layer. The user can choose layers either from the QGIS project or provide externals.

    Attributes:
        widget_key (str): The key identifier for this widget.
        raster_layer_combo (QgsMapLayerComboBox): A combo box for selecting the raster layer.
        raster_line_edit (QLineEdit): Line edit for entering/selecting a raster layer.
    """

    def add_internal_widgets(self) -> None:
        """
        Adds the internal widgets required for selecting raster layers and their correspondings.
        This method is called during the widget initialization and sets up the layout for the UI components.
        """
        try:
            self.main_layout = QVBoxLayout()
            self.widget_key = "use_environmental_hazards"
            self.settings = QSettings()

            # Raster Layer Section
            self._add_raster_layer_widgets()

            # Add the main layout to the widget's layout
            self.layout.addLayout(self.main_layout)

            # Connect signals to update the data when user changes selections
            self.raster_layer_combo.currentIndexChanged.connect(self.update_data)
            self.raster_line_edit.textChanged.connect(self.update_data)

        except Exception as e:
            QgsMessageLog.logMessage(f"Error in add_internal_widgets: {e}", "Geest")
            import traceback

            QgsMessageLog.logMessage(traceback.format_exc(), "Geest")

    def _add_raster_layer_widgets(self) -> None:
        """
        Adds the widgets for selecting the raster layer, including a `QgsMapLayerComboBox` and input.
        """
        self.raster_layer_label = QLabel("Raster Layer - will have preference")
        self.main_layout.addWidget(self.raster_layer_label)
        # Raster Layer ComboBox (Filtered to raster layers)
        self.raster_layer_combo = QgsMapLayerComboBox()
        self.raster_layer_combo.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.main_layout.addWidget(self.raster_layer_combo)

        # Restore previously selected raster layer
        raster_layer_id = self.attributes.get(
            f"{self.widget_key}_raster_layer_id", None
        )
        if raster_layer_id:
            raster_layer = QgsProject.instance().mapLayer(raster_layer_id)
            if raster_layer:
                self.raster_layer_combo.setLayer(raster_layer)

        # Input for Raster Layer
        self.raster_layout = QHBoxLayout()
        self.raster_line_edit = QLineEdit()
        self.raster_button = QToolButton()
        self.raster_button.setText("...")
        self.raster_button.clicked.connect(self.select_raster)
        if self.attributes.get(f"{self.widget_key}_raster_layer", False):
            self.raster_line_edit.setText(
                self.attributes[f"{self.widget_key}_raster_layer"]
            )
        self.raster_layout.addWidget(self.raster_line_edit)
        self.raster_layout.addWidget(self.raster_button)
        self.main_layout.addLayout(self.raster_layout)

    def select_raster(self) -> None:
        """
        Opens a file dialog to select a for the raster (paths) layer and updates the QLineEdit with the file path.
        """
        try:
            last_dir = self.settings.value("Geest/lastRasterDir", "")

            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Raster Layer", last_dir, "Rasters (*.vrt *.tif *.asc)"
            )
            if file_path:
                self.raster_line_edit.setText(file_path)
                self.settings.setValue(
                    "Geest/lastRasterDir", os.path.dirname(file_path)
                )

        except Exception as e:
            QgsMessageLog.logMessage(f"Error selecting raster: {e}", "Geest")

    def get_data(self) -> dict:
        """
        Retrieves and returns the current state of the widget, including selected raster layers ors.

        Returns:
            dict: A dictionary containing the current attributes of the raster layers and/ors.
        """
        if not self.isChecked():
            return None

        # Collect data for the raster layer
        raster_layer = self.raster_layer_combo.currentLayer()
        if raster_layer:
            self.attributes[f"{self.widget_key}_layer_name"] = raster_layer.name()
            self.attributes[f"{self.widget_key}_layer_source"] = raster_layer.source()
            self.attributes[f"{self.widget_key}_layer_provider_type"] = (
                raster_layer.providerType()
            )
            self.attributes[f"{self.widget_key}_layer_crs"] = (
                raster_layer.crs().authid()
            )
            self.attributes[f"{self.widget_key}_layer_id"] = raster_layer.id()
        self.attributes[f"{self.widget_key}_raster"] = self.raster_line_edit.text()

        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets (raster layers) based on the state of the radio button.

        Args:
            enabled (bool): Whether to enable or disable the internal widgets.
        """
        try:
            self.raster_layer_combo.setEnabled(enabled)
            self.raster_line_edit.setEnabled(enabled)
            self.raster_button.setEnabled(enabled)
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error in set_internal_widgets_enabled: {e}", "Geest"
            )
