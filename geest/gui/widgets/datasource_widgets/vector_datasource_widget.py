# -*- coding: utf-8 -*-
"""📦 Vector Datasource Widget module.

This module contains functionality for vector datasource widget.
"""

import os
import urllib.parse

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsMapLayerProxyModel,
    QgsProject,
    QgsRectangle,
    QgsVectorLayer,
)
from qgis.gui import QgsMapLayerComboBox
from qgis.PyQt.QtCore import QSettings, Qt
from qgis.PyQt.QtGui import QFont, QIcon
from qgis.PyQt.QtWidgets import (
    QFileDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QToolButton,
)

from geest.core.osm_downloaders import OSMDownloadType
from geest.core.tasks.osm_downloader_task import OSMDownloaderTask
from geest.utilities import log_message, resources_path

from .base_datasource_widget import BaseDataSourceWidget
from .download_task_controls import DownloadTaskControls


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
            self.osm_button_text = "Download from OSM"
            self.osm_tooltip = "Download data from OpenStreetMap"

            # Check for OSM download eligibility for both multi-buffer and single-buffer point indicators
            if self.attributes.get("use_multi_buffer_point", 0) or self.attributes.get("use_single_buffer_point", 0):
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

                elif (
                    "kindergarten" in item_id
                    or "childcare" in item_id
                    or "kindergarten" in item_name
                    or "childcare" in item_name
                    or "kindergarten" in indicator_text
                    or "childcare" in indicator_text
                ):
                    self.should_add_osm_widget = True
                    self.osm_download_type = OSMDownloadType.KINDERGARTEN
                    self.osm_tooltip = "Download kindergarten and childcare facilities from OpenStreetMap"
                    log_message(f"OSM widget (KINDERGARTEN) will be added for indicator: {item_id}", level=Qgis.Info)

                elif (
                    "primary" in item_id
                    or "school" in item_id
                    or "primary" in item_name
                    or "school" in item_name
                    or "primary" in indicator_text
                    or "school" in indicator_text
                ):
                    self.should_add_osm_widget = True
                    self.osm_download_type = OSMDownloadType.PRIMARY_SCHOOL
                    self.osm_tooltip = "Download primary schools from OpenStreetMap"
                    log_message(f"OSM widget (PRIMARY_SCHOOL) will be added for indicator: {item_id}", level=Qgis.Info)

                elif (
                    "pharmacy" in item_id
                    or "pharmacies" in item_id
                    or "pharmacy" in item_name
                    or "pharmacies" in item_name
                    or "pharmacy" in indicator_text
                    or "pharmacies" in indicator_text
                ):
                    self.should_add_osm_widget = True
                    self.osm_download_type = OSMDownloadType.PHARMACY
                    self.osm_tooltip = "Download pharmacies from OpenStreetMap"
                    log_message(f"OSM widget (PHARMACY) will be added for indicator: {item_id}", level=Qgis.Info)

                elif (
                    "grocery" in item_id
                    or "groceries" in item_id
                    or "market" in item_id
                    or "grocery" in item_name
                    or "groceries" in item_name
                    or "market" in item_name
                    or "grocery" in indicator_text
                    or "groceries" in indicator_text
                    or "market" in indicator_text
                ):
                    self.should_add_osm_widget = True
                    self.osm_download_type = OSMDownloadType.GROCERY
                    self.osm_tooltip = "Download grocery stores and markets from OpenStreetMap"
                    log_message(f"OSM widget (GROCERY) will be added for indicator: {item_id}", level=Qgis.Info)

                elif (
                    "green" in item_id
                    or "park" in item_id
                    or "garden" in item_id
                    or "green" in item_name
                    or "park" in item_name
                    or "garden" in item_name
                    or "green" in indicator_text
                    or "park" in indicator_text
                    or "garden" in indicator_text
                ):
                    self.should_add_osm_widget = True
                    self.osm_download_type = OSMDownloadType.GREEN_SPACE
                    self.osm_tooltip = "Download green spaces and parks from OpenStreetMap"
                    log_message(f"OSM widget (GREEN_SPACE) will be added for indicator: {item_id}", level=Qgis.Info)

                elif (
                    "hospital" in item_id
                    or "clinic" in item_id
                    or "health" in item_id
                    or "hospital" in item_name
                    or "clinic" in item_name
                    or "health" in item_name
                    or "hospital" in indicator_text
                    or "clinic" in indicator_text
                    or "health" in indicator_text
                ):
                    self.should_add_osm_widget = True
                    self.osm_download_type = OSMDownloadType.HEALTH_FACILITY
                    self.osm_tooltip = "Download hospitals and clinics from OpenStreetMap"
                    log_message(f"OSM widget (HEALTH_FACILITY) will be added for indicator: {item_id}", level=Qgis.Info)

                elif "water" in item_id or "water" in item_name or "water" in indicator_text:
                    self.should_add_osm_widget = True
                    self.osm_download_type = OSMDownloadType.WATER_POINT
                    self.osm_tooltip = "Download water points and water infrastructure from OpenStreetMap"
                    log_message(f"OSM widget (WATER_POINT) will be added for indicator: {item_id}", level=Qgis.Info)

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
            self.osm_disclaimer_label = None
            self.osm_spinner_label = None
            self.osm_spinner_movie = None
            self.osm_button_container = None
            self.osm_controls = None
            if self.should_add_osm_widget:
                self.osm_controls = DownloadTaskControls(
                    button_text=self.osm_button_text,
                    tooltip=self.osm_tooltip,
                    click_handler=self.start_osm_download,
                )
                self.osm_button_container = self.osm_controls.container
                self.osm_download_button = self.osm_controls.button
                self.osm_spinner_label = self.osm_controls.spinner_label
                self.osm_spinner_movie = self.osm_controls.spinner_movie

                log_message(
                    f"OSM download button created for indicator: {self.attributes.get('id', 'unknown')}",
                    level=Qgis.Info,
                )

                # Create inline disclaimer label
                self.osm_disclaimer_label = QLabel()
                self.osm_disclaimer_label.setText(
                    "Disclaimer: The OSM downloader may return a mix of point and polygon geometries depending on how features "
                    "are mapped in OpenStreetMap. Polygon features should be converted to points (e.g., centroids) and merged "
                    "with the downloaded points to form a complete point input layer for this indicator."
                )
                self.osm_disclaimer_label.setWordWrap(True)
                # Style the disclaimer to match the screenshot
                disclaimer_font = QFont()
                disclaimer_font.setPointSize(9)
                self.osm_disclaimer_label.setFont(disclaimer_font)
                self.osm_disclaimer_label.setStyleSheet("QLabel { color: #333333; margin-top: 4px; }")

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
        Opens a file dialog to select a vector file and stores the last directory in QSettings.
        """
        try:
            settings = QSettings()
            last_dir = settings.value("GeoE3/lastShapefileDir", "")

            # Open file dialog to select a vector file
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Vector File",
                last_dir,
                "GeoPackage and Shapefiles (*.gpkg *.shp);;GeoPackage (*.gpkg);;Shapefiles (*.shp)",
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
                settings.setValue("GeoE3/lastShapefileDir", os.path.dirname(file_path))

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

    def start_osm_download(self) -> None:
        """Start OSM data download process using proper QgsTask integration."""
        log_message("Starting OSM download...", tag="GeoE3", level=Qgis.Info)

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

        # Check for study area geopackage
        study_area_dir = os.path.join(working_directory, "study_area")
        gpkg_path = os.path.join(study_area_dir, "study_area.gpkg")

        if not os.path.exists(gpkg_path):
            QMessageBox.warning(
                self,
                "Study Area Required",
                "Please create a study area first before downloading OSM data.\n\n"
                "Use 'Create New Project' to define your study area.",
            )
            return

        # Load study area extent from geopackage (most reliable source)
        extent = QgsRectangle()
        study_area_layer = QgsVectorLayer(f"{gpkg_path}|layername=study_area_bboxes", "temp_bbox", "ogr")

        if study_area_layer.isValid() and study_area_layer.featureCount() > 0:
            extent = study_area_layer.extent()
            source_crs = study_area_layer.crs()

            # Transform extent to EPSG:4326 (required by Overpass API)
            if source_crs.authid() != "EPSG:4326":
                transform = QgsCoordinateTransform(
                    source_crs,
                    QgsCoordinateReferenceSystem("EPSG:4326"),
                    project,
                )
                extent = transform.transformBoundingBox(extent)
                log_message(
                    f"Using study area extent, transformed from {source_crs.authid()} to EPSG:4326",
                    tag="GeoE3",
                    level=Qgis.Info,
                )
            else:
                log_message("Using study area extent (already in EPSG:4326)", tag="GeoE3", level=Qgis.Info)
        else:
            # Fallback: try to get extent from loaded project layers
            log_message(
                "Could not load study area bboxes, falling back to project layers", tag="GeoE3", level=Qgis.Warning
            )
            layers = project.mapLayers().values()
            project_crs = project.crs() if project.crs().isValid() else QgsCoordinateReferenceSystem("EPSG:4326")

            if layers:
                for layer in layers:
                    if layer.extent().isFinite():
                        if extent.isEmpty():
                            extent = layer.extent()
                        else:
                            extent.combineExtentWith(layer.extent())

                if not extent.isEmpty() and extent.isFinite() and project_crs.authid() != "EPSG:4326":
                    transform = QgsCoordinateTransform(
                        project_crs,
                        QgsCoordinateReferenceSystem("EPSG:4326"),
                        project,
                    )
                    extent = transform.transformBoundingBox(extent)

        # Final validation
        if extent.isEmpty() or not extent.isFinite():
            QMessageBox.warning(
                self,
                "Invalid Extent",
                "Could not determine a valid extent for OSM download.\n\n"
                "Please ensure your study area is properly configured.",
            )
            return

        if self.osm_download_type is None:
            log_message("No OSM download type set", tag="GeoE3", level=Qgis.Critical)
            return

        filename = f"osm_{self.osm_download_type.value}"
        output_file_path = os.path.join(study_area_dir, f"{filename}.gpkg")
        output_crs = QgsCoordinateReferenceSystem("EPSG:4326")

        log_message(f"Output directory: {study_area_dir}", tag="GeoE3", level=Qgis.Info)
        log_message(f"Filename: {filename}", tag="GeoE3", level=Qgis.Info)
        log_message(f"Full output file path: {output_file_path}", tag="GeoE3", level=Qgis.Info)
        log_message(f"Extent: {extent.asWktPolygon()}", tag="GeoE3", level=Qgis.Info)
        log_message(f"Output CRS: {output_crs.authid()}", tag="GeoE3", level=Qgis.Info)

        if self.osm_download_button:
            self.osm_controls.set_running()

        try:
            # Create task using proper QgsTask-based approach
            self.osm_task = OSMDownloaderTask(
                osm_download_type=self.osm_download_type,
                extents=extent,
                output_path=output_file_path,
                crs=output_crs,
                use_cache=False,
                delete_gpkg=True,
            )

            # Track if error already occurred to avoid duplicate messages
            self._osm_error_handled = False

            # Connect signals
            self.osm_task.progress_updated.connect(self.update_button_progress)
            self.osm_task.error_occurred.connect(self.on_osm_download_error)
            self.osm_task.taskCompleted.connect(lambda: self.on_osm_download_finished(output_file_path))
            self.osm_task.taskTerminated.connect(self.on_osm_download_terminated)

            # Add to QGIS task manager (proper architecture)
            QgsApplication.taskManager().addTask(self.osm_task)

            log_message("OSM download task added to QGIS task manager", tag="GeoE3", level=Qgis.Info)
        except Exception as e:
            log_message(f"Error starting OSM download: {e}", tag="GeoE3", level=Qgis.Critical)
            import traceback

            log_message(traceback.format_exc(), tag="GeoE3", level=Qgis.Critical)

            if self.osm_download_button:
                self.osm_controls.set_error(str(e))

            QMessageBox.warning(self, "Error", f"Failed to start download: {str(e)}")

    def update_button_progress(self, message: str):
        """Update button text to show download progress.

        Args:
            message: Progress message from the download task.
        """
        log_message(message, tag="GeoE3", level=Qgis.Info)
        if self.osm_download_button:
            self.osm_controls.update_progress(message)

    def on_osm_download_finished(self, gpkg_path: str) -> None:
        """Handle completion of OSM download.

        Args:
            gpkg_path: Path to the downloaded GeoPackage file.
        """
        log_message(f"OSM download completed: {gpkg_path}", tag="GeoE3", level=Qgis.Info)

        self._stop_spinner()
        if os.path.isdir(gpkg_path):
            error_msg = f"Expected a file but received a directory: {gpkg_path}"
            log_message(f"Error: {error_msg}", tag="GeoE3", level=Qgis.Critical)
            if self.osm_download_button:
                self.osm_controls.set_error(error_msg)
            QMessageBox.warning(self, "OSM Download Error", error_msg)
            return

        if not os.path.exists(gpkg_path):
            error_msg = f"Download completed but output file not found: {gpkg_path}"
            log_message(f"Error: {error_msg}", tag="GeoE3", level=Qgis.Critical)
            if self.osm_download_button:
                self.osm_controls.set_not_found(gpkg_path)
            QMessageBox.warning(self, "OSM Download Error", error_msg)
            return

        layer_name = os.path.splitext(os.path.basename(gpkg_path))[0]
        layer = QgsVectorLayer(gpkg_path, layer_name, "ogr")

        if layer.isValid():
            QgsProject.instance().addMapLayer(layer)
            log_message(f"Loaded OSM layer: {layer_name}", tag="GeoE3", level=Qgis.Info)
            self.layer_combo.setLayer(layer)

            if self.osm_download_button:
                self.osm_controls.set_downloaded()
        else:
            error_msg = f"Downloaded file exists but could not be loaded as a valid layer: {gpkg_path}"
            log_message(f"Failed to load layer: {error_msg}", tag="GeoE3", level=Qgis.Critical)
            if self.osm_download_button:
                self.osm_controls.set_load_failed(gpkg_path)
            QMessageBox.warning(
                self,
                "OSM Layer Load Failed",
                f"The OSM data was downloaded but could not be loaded.\n\n"
                f"File: {gpkg_path}\n\n"
                "The file may be corrupted or empty. Try downloading again.",
            )

    def on_osm_download_error(self, error_message: str) -> None:
        """Handle OSM download errors.

        Args:
            error_message: The error message from the download task.
        """
        log_message(f"OSM download error: {error_message}", tag="GeoE3", level=Qgis.Critical)

        # Mark that we've handled an error to avoid duplicate message from taskTerminated
        self._osm_error_handled = True

        self._stop_spinner()
        if self.osm_download_button:
            self.osm_controls.set_download_failed(error_message)

        # Show error message to user
        QMessageBox.warning(
            self,
            "OSM Download Failed",
            f"The OSM data download failed.\n\n{error_message}\n\n"
            "You can try again by clicking the download button.",
        )

    def on_osm_download_terminated(self) -> None:
        """Handle OSM download task termination (cancellation).

        Only shows a message if an error wasn't already handled.
        """
        # Skip if error was already handled (avoids duplicate message boxes)
        if getattr(self, "_osm_error_handled", False):
            log_message("OSM task terminated after error - skipping duplicate message", tag="GeoE3")
            return

        log_message("OSM download was cancelled by user", tag="GeoE3", level=Qgis.Warning)

        self._stop_spinner()
        if self.osm_download_button:
            self.osm_controls.set_cancelled()

    def _stop_spinner(self) -> None:
        """Stop the spinner animation and hide it."""
        if self.osm_controls:
            self.osm_controls.stop_spinner()

    def reset_osm_button(self) -> None:
        """Reset OSM download button to initial state."""
        if self.osm_controls:
            self.osm_controls.reset()

    def get_osm_download_button(self):
        """
        Returns the OSM download button container (button + spinner) if created, None otherwise.

        Returns:
            QWidget or None: The container widget with OSM download button and spinner
        """
        return self.osm_button_container

    def get_osm_disclaimer_label(self):
        """
        Returns the OSM disclaimer label if it was created, None otherwise.

        Returns:
            QLabel or None: The OSM disclaimer label widget
        """
        return self.osm_disclaimer_label

    def update_attributes(self):
        """Update the attributes dict to match the current state of the widget.

        The attributes dict is a reference so any tree item attributes will be updated directly.
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
