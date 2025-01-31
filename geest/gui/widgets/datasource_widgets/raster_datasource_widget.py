import os
from qgis.PyQt.QtWidgets import (
    QLineEdit,
    QToolButton,
    QFileDialog,
)
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QSettings, Qt
from qgis.gui import QgsMapLayerComboBox
from qgis.core import (
    QgsMapLayerProxyModel,
    QgsProject,
    Qgis,
)

from .base_datasource_widget import BaseDataSourceWidget
from geest.utilities import log_message, resources_path


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
            log_message(f"Error in add_internal_widgets: {e}", level=Qgis.Critical)
            import traceback

            log_message(traceback.format_exc(), level=Qgis.Critical)

    def _add_raster_layer_widgets(self) -> None:
        """
        Adds the widgets for selecting the raster layer, including a `QgsMapLayerComboBox` and input.
        """
        # Raster Layer ComboBox (Filtered to raster layers)
        self.raster_layer_combo = QgsMapLayerComboBox()
        self.raster_layer_combo.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.raster_layer_combo.setAllowEmptyLayer(True)
        # Insert placeholder text at the top (only visually, not as a selectable item)
        self.raster_layer_combo.setCurrentIndex(-1)  # Ensure no selection initially
        self.raster_layer_combo.setEditable(
            True
        )  # Make editable temporarily for placeholder
        self.raster_layer_combo.lineEdit().setPlaceholderText(
            "Select item"
        )  # Add placeholder text

        # Disable editing after setting placeholder (ensures only layer names are selectable)
        self.raster_layer_combo.lineEdit().setReadOnly(True)
        self.raster_layer_combo.setEditable(
            False
        )  # Lock back to non-editable after setting placeholder

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

        # Add clear button inside the line edit
        self.clear_button = QToolButton(self.raster_line_edit)
        clear_icon = QIcon(resources_path("resources", "icons", "clear.svg"))
        self.clear_button.setIcon(clear_icon)
        self.clear_button.setToolTip("Clear")
        self.clear_button.setCursor(Qt.ArrowCursor)
        self.clear_button.setStyleSheet("border: 0px; padding: 0px;")
        self.clear_button.clicked.connect(self.clear_raster)
        self.clear_button.setVisible(False)

        self.raster_line_edit.textChanged.connect(
            lambda text: self.clear_button.setVisible(bool(text))
        )
        self.raster_line_edit.textChanged.connect(self.resize_clear_button)

        # File chooser button for Raster Layer
        self.raster_button = QToolButton()
        self.raster_button.setText("...")
        self.raster_button.clicked.connect(self.select_raster)

        if self.attributes.get(f"{self.widget_key}_raster", False):
            self.raster_line_edit.setText(self.attributes[f"{self.widget_key}_raster"])
            self.raster_line_edit.setVisible(True)
            self.raster_layer_combo.setVisible(False)
        else:
            self.raster_layer_combo.setVisible(True)
        self.layout.addWidget(self.raster_line_edit)
        self.resize_clear_button()

        self.layout.addWidget(self.raster_button)
        self.raster_button.setToolTip(
            "Raster chosen from file system will have preference"
        )

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
        frame_width = self.raster_line_edit.style().pixelMetric(
            self.raster_line_edit.style().PM_DefaultFrameWidth
        )
        self.raster_line_edit.setStyleSheet(
            f"QLineEdit {{ padding-right: {self.clear_button.sizeHint().width() + frame_width}px; }}"
        )
        sz = self.clear_button.sizeHint()
        self.clear_button.move(
            self.raster_line_edit.width() - sz.width() - frame_width - 5, 6
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
                # Update the line edit with the selected file path
                # ⚠️ Be careful about changing the order of the following lines
                #   It could cause the clear button to render in the incorrect place
                self.raster_layer_combo.setVisible(False)
                self.raster_line_edit.setVisible(True)
                self.raster_line_edit.setText(file_path)
                # Trigger resize event explicitly
                self.resizeEvent(None)
                # Save the directory of the selected file to QSettings
                self.settings.setValue(
                    "Geest/lastRasterDir", os.path.dirname(file_path)
                )

        except Exception as e:
            log_message(f"Error selecting raster: {e}", level=Qgis.Critical)

    def clear_raster(self):
        """
        Clears the raster line edit and hides it along with the clear button.
        """
        self.raster_line_edit.clear()
        self.raster_line_edit.setVisible(False)
        self.raster_layer_combo.setVisible(True)
        self.raster_layer_combo.setFocus()
        self.update_attributes()

    def update_attributes(self):
        """
        Updates the attributes dict to match the current state of the widget.

        The attributes dict is a reference so any tree item attributes will be updated directly.

        Returns:
            None
        """

        # Collect data for the raster layer
        raster_layer = self.raster_layer_combo.currentLayer()
        if not raster_layer:
            self.attributes[f"{self.widget_key}_layer"] = None
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
