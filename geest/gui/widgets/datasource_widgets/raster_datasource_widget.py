import os
from qgis.PyQt.QtWidgets import (
    QLineEdit,
    QToolButton,
    QFileDialog,
)
from qgis.gui import QgsMapLayerComboBox
from qgis.core import (
    QgsMapLayerProxyModel,
    QgsProject,
)
from qgis.PyQt.QtCore import QSettings
from .base_datasource_widget import BaseDataSourceWidget
from geest.utilities import log_message


class RasterDataSourceWidget(BaseDataSourceWidget):
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
            self.settings = QSettings()

            # Raster Layer Section
            self._add_raster_layer_widgets()
            # Connect signals to update the data when user changes selections
            self.raster_layer_combo.currentIndexChanged.connect(self.update_attributes)
            self.raster_line_edit.textChanged.connect(self.update_attributes)

        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", "Geest")
            import traceback

            log_message(traceback.format_exc(), "Geest")

    def _add_raster_layer_widgets(self) -> None:
        """
        Adds the widgets for selecting the raster layer, including a `QgsMapLayerComboBox` and input.
        """
        # Raster Layer ComboBox (Filtered to raster layers)
        self.raster_layer_combo = QgsMapLayerComboBox()
        self.raster_layer_combo.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.raster_layer_combo.setToolTip(
            "Raster chosen from file system will have preference"
        )
        self.layout.addWidget(self.raster_layer_combo)

        # Restore previously selected raster layer
        raster_layer_id = self.attributes.get(f"{self.widget_key}_layer_id", None)
        if raster_layer_id:
            raster_layer = QgsProject.instance().mapLayer(raster_layer_id)
            if raster_layer:
                self.raster_layer_combo.setLayer(raster_layer)

        # Input for Raster Layer
        self.raster_line_edit = QLineEdit()
        self.raster_line_edit.setVisible(False)  # Hide initially
        self.raster_button = QToolButton()
        self.raster_button.setText("...")
        self.raster_button.clicked.connect(self.select_raster)
        if self.attributes.get(f"{self.widget_key}_raster", False):
            self.raster_line_edit.setText(self.attributes[f"{self.widget_key}_raster"])
        self.layout.addWidget(self.raster_line_edit)
        self.layout.addWidget(self.raster_button)
        self.raster_button.setToolTip(
            "Raster chosen from file system will have preference"
        )

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
                self.raster_line_edit.setVisible(True)
                self.settings.setValue(
                    "Geest/lastRasterDir", os.path.dirname(file_path)
                )

        except Exception as e:
            log_message(f"Error selecting raster: {e}", "Geest")

    def update_attributes(self):
        """
        Updates the attributes dict to match the current state of the widget.

        The attributes dict is a reference so any tree item attributes will be updated directly.

        Returns:
            None
        """

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
