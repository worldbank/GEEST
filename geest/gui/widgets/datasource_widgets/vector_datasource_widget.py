# -*- coding: utf-8 -*-
"""📦 Vector Datasource Widget module.

This module contains functionality for vector datasource widget.
"""
import os
import urllib.parse

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsMapLayerProxyModel,
    QgsProject,
    QgsRectangle,
)
from qgis.gui import QgsMapLayerComboBox
from qgis.PyQt.QtCore import QSettings, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QFileDialog, QLineEdit, QPushButton, QToolButton

from geest.core.osm_downloaders import OSMDownloadType
from geest.gui.widgets import OSMDownloadWidget
from geest.utilities import log_message, resources_path

from .base_datasource_widget import BaseDataSourceWidget


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
            tooltip = ""
            if self.attributes.get("use_single_buffer_point", 0):
                filter = QgsMapLayerProxyModel.PointLayer
                tooltip = "A point layer that will be buffered with a single buffer."
            elif self.attributes.get("use_point_per_cell", 0):
                filter = QgsMapLayerProxyModel.PointLayer
                tooltip = "A point layer whose points will be counted per cell."
            elif self.attributes.get("use_multi_buffer_point", 0):
                filter = QgsMapLayerProxyModel.PointLayer
                tooltip = "A point layer whose points will buffered with multiple buffers."
            elif self.attributes.get("use_street_lights", 0):
                filter = QgsMapLayerProxyModel.PointLayer
            elif self.attributes.get("use_osm_transport_polyline_per_cell", 0):
                # Putting this before use polyline layer means that
                # it will be used with priority over a simple line layer
                filter = QgsMapLayerProxyModel.LineLayer
                tooltip = "An OSM line layer whose features will be classified and the most beneficial category assigned to the cell."
            elif self.attributes.get("use_polyline_per_cell", 0):
                filter = QgsMapLayerProxyModel.LineLayer
                tooltip = "A line layer whose features will be counted per cell."
            else:
                filter = QgsMapLayerProxyModel.PolygonLayer
                tooltip = "A polygon layer whose features will be counted per cell."

            # Determine if OSM download widget should be added based on indicator type
            self.should_add_osm_widget = False
            self.osm_download_type = None
            self.osm_button_text = "Get from OSM"
            self.osm_tooltip = "Download data from OpenStreetMap"

            if self.attributes.get("use_multi_buffer_point", 0):
                item_id = self.attributes.get("id", "").lower()
                item_name = self.attributes.get("name", "").lower()
                indicator_text = self.attributes.get("indicator", "").lower()

                if (
                    "public" in item_id
                    or "transport" in item_id
                    or "public" in item_name
                    or "transport" in item_name
                    or "public" in indicator_text
                    or "transport" in indicator_text
                ):
                    self.should_add_osm_widget = True
                    self.osm_download_type = OSMDownloadType.PUBLIC_TRANSPORT
                    self.osm_tooltip = "Download public transport data from OpenStreetMap"
                    log_message(
                        f"OSM widget (PUBLIC_TRANSPORT) will be added for indicator: {item_id}", level=Qgis.Info
                    )

                elif (
                    "education" in item_id
                    or "school" in item_id
                    or "training" in item_id
                    or "education" in item_name
                    or "school" in item_name
                    or "training" in item_name
                    or "education" in indicator_text
                    or "school" in indicator_text
                    or "training" in indicator_text
                ):
                    self.should_add_osm_widget = True
                    self.osm_download_type = OSMDownloadType.EDUCATION
                    self.osm_tooltip = "Download education facilities from OpenStreetMap"
                    log_message(f"OSM widget (EDUCATION) will be added for indicator: {item_id}", level=Qgis.Info)

                elif (
                    "financial" in item_id
                    or "bank" in item_id
                    or "finance" in item_id
                    or "financial" in item_name
                    or "bank" in item_name
                    or "finance" in item_name
                    or "financial" in indicator_text
                    or "bank" in indicator_text
                    or "finance" in indicator_text
                ):
                    self.should_add_osm_widget = True
                    self.osm_download_type = OSMDownloadType.FINANCIAL
                    self.osm_tooltip = "Download financial services from OpenStreetMap"
                    log_message(f"OSM widget (FINANCIAL) will be added for indicator: {item_id}", level=Qgis.Info)

            self.layer_combo = QgsMapLayerComboBox()
            self.layer_combo.setAllowEmptyLayer(True)
            # Insert placeholder text at the top (only visually, not as a selectable item)
            self.layer_combo.setCurrentIndex(-1)  # Ensure no selection initially
            self.layer_combo.setEditable(True)  # Make editable temporarily for placeholder
            self.layer_combo.setToolTip(tooltip)
            self.layer_combo.lineEdit().setPlaceholderText("Select item")  # Add placeholder text

            # Disable editing after setting placeholder (ensures only layer names are selectable)
            self.layer_combo.lineEdit().setReadOnly(True)
            self.layer_combo.setEditable(False)  # Lock back to non-editable after setting placeholder

            self.layer_combo.setFilters(filter)

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

            self.shapefile_line_edit.textChanged.connect(lambda text: self.clear_button.setVisible(bool(text)))
            self.shapefile_line_edit.textChanged.connect(self.resize_clear_button)
            # Add a button to select a shapefile
            self.shapefile_button = QToolButton()
            self.shapefile_button.setText("...")
            self.shapefile_button.clicked.connect(self.select_shapefile)

            if self.attributes.get(f"{self.widget_key}_shapefile", False):
                self.shapefile_line_edit.setText(urllib.parse.unquote(self.attributes[f"{self.widget_key}_shapefile"]))
                self.shapefile_line_edit.setVisible(True)
                self.layer_combo.setVisible(False)
            else:
                self.layer_combo.setVisible(True)

            # Add widgets directly to self.layout (which is already QHBoxLayout)
            self.layout.setSpacing(6)
            self.layout.addWidget(self.layer_combo, 2)
            self.layout.addWidget(self.shapefile_line_edit, 2)
            self.layout.addWidget(self.shapefile_button, 0)

            # Create OSM download button (added to separate table column by dialog)
            self.osm_download_button = None
            if self.should_add_osm_widget:
                self.osm_download_button = QPushButton(self.osm_button_text)
                self.osm_download_button.setToolTip(self.osm_tooltip)
                self.osm_download_button.clicked.connect(self.start_osm_download)
                log_message(
                    f"OSM download button created for indicator: {self.attributes.get('id', 'unknown')}",
                    level=Qgis.Info,
                )

            # Add stretch to push everything to the left
            self.layout.addStretch(1)

            self.resize_clear_button()

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
            f"QLineEdit {{ padding-right: {self.clear_button.sizeHint().width() + frame_width}px; }}"  # noqa E702,E202,E201
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
            file_path, _ = QFileDialog.getOpenFileName(self, "Select Shapefile", last_dir, "Shapefiles (*.shp)")

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

    def start_osm_download(self):
        """Start OSM data download process."""
        log_message("Starting OSM download...", tag="Geest", level=Qgis.Info)

        from qgis.PyQt.QtWidgets import QMessageBox
        from qgis.PyQt.QtCore import QSettings
        from geest.gui.widgets.osm_download_widget import OSMDownloadWorker

        project = QgsProject.instance()
        if not project:
            QMessageBox.warning(self, "Error", "No QGIS project loaded")
            return

        settings = QSettings()
        working_directory = settings.value("last_working_directory", "")
        if not working_directory or not os.path.exists(working_directory):
            QMessageBox.warning(
                self, "Error", "No valid working directory found. Please create or open a project first."
            )
            return

        # Calculate extent from all project layers
        extent = QgsRectangle()
        layers = project.mapLayers().values()
        project_crs = project.crs() if project.crs().isValid() else QgsCoordinateReferenceSystem("EPSG:4326")

        if layers:
            for layer in layers:
                if layer.extent().isFinite():
                    if extent.isEmpty():
                        extent = layer.extent()
                    else:
                        extent.combineExtentWith(layer.extent())

        if extent.isEmpty() or not extent.isFinite():
            extent = QgsRectangle(-180, -90, 180, 90)
            log_message("Using world extent for OSM download", tag="Geest", level=Qgis.Warning)
        else:
            # Transform extent to EPSG:4326 (required by Overpass API)
            if project_crs.authid() != "EPSG:4326":
                transform = QgsCoordinateTransform(
                    project_crs,
                    QgsCoordinateReferenceSystem("EPSG:4326"),
                    project,
                )
                extent = transform.transformBoundingBox(extent)
                log_message(
                    f"Transformed extent from {project_crs.authid()} to EPSG:4326", tag="Geest", level=Qgis.Info
                )

        study_area_dir = os.path.join(working_directory, "study_area")
        if not os.path.exists(study_area_dir):
            QMessageBox.warning(self, "Error", "Study area directory not found. Please create a project first.")
            return

        if self.osm_download_type is None:
            log_message("No OSM download type set", tag="Geest", level=Qgis.Critical)
            return

        filename = f"osm_{self.osm_download_type.value}"
        output_file_path = os.path.join(study_area_dir, f"{filename}.gpkg")
        output_crs = QgsCoordinateReferenceSystem("EPSG:4326")

        log_message(f"Output directory: {study_area_dir}", tag="Geest", level=Qgis.Info)
        log_message(f"Filename: {filename}", tag="Geest", level=Qgis.Info)
        log_message(f"Full output file path: {output_file_path}", tag="Geest", level=Qgis.Info)
        log_message(f"Extent: {extent.asWktPolygon()}", tag="Geest", level=Qgis.Info)
        log_message(f"Output CRS: {output_crs.authid()}", tag="Geest", level=Qgis.Info)

        if self.osm_download_button:
            self.osm_download_button.setEnabled(False)
            self.osm_download_button.setText("Downloading...")
            self.osm_download_button.setStyleSheet("")

        try:
            self.osm_worker = OSMDownloadWorker(
                download_type=self.osm_download_type,
                extents=extent,
                output_path=output_file_path,
                output_crs=output_crs,
                filename=filename,
            )
            self.osm_worker.finished.connect(self.on_osm_download_finished)
            self.osm_worker.error.connect(self.on_osm_download_error)
            self.osm_worker.progress.connect(self.update_button_progress)
            self.osm_worker.start()

            log_message("OSM download started in background", tag="Geest", level=Qgis.Info)
        except Exception as e:
            log_message(f"Error starting OSM download: {e}", tag="Geest", level=Qgis.Critical)
            import traceback

            log_message(traceback.format_exc(), tag="Geest", level=Qgis.Critical)

            if self.osm_download_button:
                self.osm_download_button.setEnabled(True)
                self.osm_download_button.setText("Get from OSM")

            QMessageBox.warning(self, "Error", f"Failed to start download: {str(e)}")

    def update_button_progress(self, message: str):
        """Update button text to show download progress."""
        log_message(message, tag="Geest", level=Qgis.Info)
        if self.osm_download_button:
            if "Processing" in message:
                self.osm_download_button.setText("Processing...")
            elif "complete" in message.lower():
                self.osm_download_button.setText("Complete!")

    def on_osm_download_finished(self, gpkg_path: str):
        """Handle completion of OSM download."""
        from qgis.core import QgsVectorLayer
        import os

        log_message(f"OSM download completed: {gpkg_path}", tag="Geest", level=Qgis.Info)

        if os.path.isdir(gpkg_path):
            log_message(
                f"Error: Received directory path instead of file: {gpkg_path}", tag="Geest", level=Qgis.Critical
            )
            if self.osm_download_button:
                self.osm_download_button.setText("Error!")
                self.osm_download_button.setStyleSheet("background-color: #ffcccc;")
                self.osm_download_button.setEnabled(True)
            return

        if not os.path.exists(gpkg_path):
            log_message(f"Error: File does not exist: {gpkg_path}", tag="Geest", level=Qgis.Critical)
            if self.osm_download_button:
                self.osm_download_button.setText("Not Found!")
                self.osm_download_button.setStyleSheet("background-color: #ffcccc;")
                self.osm_download_button.setEnabled(True)
            return

        layer_name = os.path.splitext(os.path.basename(gpkg_path))[0]
        layer = QgsVectorLayer(gpkg_path, layer_name, "ogr")

        if layer.isValid():
            QgsProject.instance().addMapLayer(layer)
            log_message(f"Loaded OSM layer: {layer_name}", tag="Geest", level=Qgis.Info)
            self.layer_combo.setLayer(layer)

            if self.osm_download_button:
                self.osm_download_button.setText("Downloaded!")
                self.osm_download_button.setStyleSheet("background-color: #ccffcc;")
                from qgis.PyQt.QtCore import QTimer

                QTimer.singleShot(2000, lambda: self.reset_osm_button())
        else:
            log_message(f"Failed to load layer from: {gpkg_path}", tag="Geest", level=Qgis.Critical)
            if self.osm_download_button:
                self.osm_download_button.setText("Load Failed!")
                self.osm_download_button.setStyleSheet("background-color: #ffcccc;")
                self.osm_download_button.setEnabled(True)

    def on_osm_download_error(self, error_message: str):
        """Handle OSM download errors."""
        log_message(f"OSM download error: {error_message}", tag="Geest", level=Qgis.Critical)

        if self.osm_download_button:
            self.osm_download_button.setText("Download Failed!")
            self.osm_download_button.setStyleSheet("background-color: #ffcccc;")
            self.osm_download_button.setEnabled(True)

    def reset_osm_button(self):
        """Reset OSM download button to initial state."""
        if self.osm_download_button:
            self.osm_download_button.setText("Get from OSM")
            self.osm_download_button.setStyleSheet("")
            self.osm_download_button.setEnabled(True)

    def get_osm_download_button(self):
        """
        Returns the OSM download button if it was created, None otherwise.

        Returns:
            QPushButton or None: The OSM download button
        """
        return self.osm_download_button

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
            self.attributes[f"{self.widget_key}_layer_provider_type"] = layer.providerType()
            self.attributes[f"{self.widget_key}_layer_crs"] = layer.crs().authid()  # Coordinate Reference System
            self.attributes[f"{self.widget_key}_layer_wkb_type"] = (
                layer.wkbType()
            )  # Geometry type (e.g., Point, Polygon)
            self.attributes[f"{self.widget_key}_layer_id"] = layer.id()  # Unique ID of the layer

        # Encode the shapefile path to handle spaces and special characters
        shapefile_path = self.shapefile_line_edit.text()
        self.attributes[f"{self.widget_key}_shapefile"] = urllib.parse.quote(shapefile_path)
