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
from qgis.PyQt.QtCore import QSettings, Qt, QTimer
from qgis.PyQt.QtGui import QFont, QIcon, QMovie
from qgis.PyQt.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QToolButton,
    QWidget,
)

from geest.core.osm_downloaders import OSMDownloadType
from geest.core.tasks.osm_downloader_task import OSMDownloaderTask
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
            if self.should_add_osm_widget:
                # Create container widget for button and spinner
                self.osm_button_container = QWidget()
                container_layout = QHBoxLayout(self.osm_button_container)
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setSpacing(6)

                self.osm_download_button = QPushButton(self.osm_button_text)
                self.osm_download_button.setToolTip(self.osm_tooltip)
                self.osm_download_button.setStyleSheet("padding: 5px 10px;")
                self.osm_download_button.clicked.connect(self.start_osm_download)

                # Create spinner label with animated gif
                self.osm_spinner_label = QLabel()
                self.osm_spinner_movie = QMovie(resources_path("resources", "throbber.gif"))
                # Scale the spinner to match button height
                self.osm_spinner_movie.setScaledSize(
                    self.osm_spinner_movie.currentPixmap().size().scaled(24, 24, Qt.KeepAspectRatio)
                )
                self.osm_spinner_label.setMovie(self.osm_spinner_movie)
                self.osm_spinner_label.setVisible(False)  # Hidden initially

                container_layout.addWidget(self.osm_download_button)
                container_layout.addWidget(self.osm_spinner_label)
                container_layout.addStretch()

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

    def start_osm_download(self) -> None:
        """Start OSM data download process using proper QgsTask integration."""
        log_message("Starting OSM download...", tag="Geest", level=Qgis.Info)

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
                    tag="Geest",
                    level=Qgis.Info,
                )
            else:
                log_message("Using study area extent (already in EPSG:4326)", tag="Geest", level=Qgis.Info)
        else:
            # Fallback: try to get extent from loaded project layers
            log_message(
                "Could not load study area bboxes, falling back to project layers", tag="Geest", level=Qgis.Warning
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
            self.osm_download_button.setStyleSheet("padding: 5px 10px;")
            # Start the spinner animation
            if self.osm_spinner_label and self.osm_spinner_movie:
                self.osm_spinner_label.setVisible(True)
                self.osm_spinner_movie.start()

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

            # Connect signals
            self.osm_task.progress_updated.connect(self.update_button_progress)
            self.osm_task.error_occurred.connect(self.on_osm_download_error)
            self.osm_task.taskCompleted.connect(lambda: self.on_osm_download_finished(output_file_path))
            self.osm_task.taskTerminated.connect(lambda: self.on_osm_download_error("Download was cancelled"))

            # Add to QGIS task manager (proper architecture)
            QgsApplication.taskManager().addTask(self.osm_task)

            log_message("OSM download task added to QGIS task manager", tag="Geest", level=Qgis.Info)
        except Exception as e:
            log_message(f"Error starting OSM download: {e}", tag="Geest", level=Qgis.Critical)
            import traceback

            log_message(traceback.format_exc(), tag="Geest", level=Qgis.Critical)

            if self.osm_download_button:
                self.osm_download_button.setEnabled(True)
                self.osm_download_button.setText("Download from OSM")
            # Stop the spinner on error
            self._stop_spinner()

            QMessageBox.warning(self, "Error", f"Failed to start download: {str(e)}")

    def update_button_progress(self, message: str):
        """Update button text to show download progress."""
        log_message(message, tag="Geest", level=Qgis.Info)
        if self.osm_download_button:
            if "Processing" in message:
                self.osm_download_button.setText("Processing...")
            elif "complete" in message.lower():
                self.osm_download_button.setText("Complete!")

    def on_osm_download_finished(self, gpkg_path: str) -> None:
        """Handle completion of OSM download."""
        log_message(f"OSM download completed: {gpkg_path}", tag="Geest", level=Qgis.Info)

        self._stop_spinner()
        if os.path.isdir(gpkg_path):
            error_msg = f"Expected a file but received a directory: {gpkg_path}"
            log_message(f"Error: {error_msg}", tag="Geest", level=Qgis.Critical)
            if self.osm_download_button:
                self.osm_download_button.setText("Error!")
                self.osm_download_button.setStyleSheet("background-color: #ffcccc; padding: 5px 10px;")
                self.osm_download_button.setEnabled(True)
                self.osm_download_button.setToolTip(f"Error: {error_msg}")
            QMessageBox.warning(self, "OSM Download Error", error_msg)
            return

        if not os.path.exists(gpkg_path):
            error_msg = f"Download completed but output file not found: {gpkg_path}"
            log_message(f"Error: {error_msg}", tag="Geest", level=Qgis.Critical)
            if self.osm_download_button:
                self.osm_download_button.setText("Not Found!")
                self.osm_download_button.setStyleSheet("background-color: #ffcccc; padding: 5px 10px;")
                self.osm_download_button.setEnabled(True)
                self.osm_download_button.setToolTip(f"Error: {error_msg}")
            QMessageBox.warning(self, "OSM Download Error", error_msg)
            return

        layer_name = os.path.splitext(os.path.basename(gpkg_path))[0]
        layer = QgsVectorLayer(gpkg_path, layer_name, "ogr")

        if layer.isValid():
            QgsProject.instance().addMapLayer(layer)
            log_message(f"Loaded OSM layer: {layer_name}", tag="Geest", level=Qgis.Info)
            self.layer_combo.setLayer(layer)

            if self.osm_download_button:
                self.osm_download_button.setText("Downloaded!")
                self.osm_download_button.setStyleSheet("background-color: #ccffcc; padding: 5px 10px;")
                QTimer.singleShot(2000, lambda: self.reset_osm_button())
        else:
            error_msg = f"Downloaded file exists but could not be loaded as a valid layer: {gpkg_path}"
            log_message(f"Failed to load layer: {error_msg}", tag="Geest", level=Qgis.Critical)
            if self.osm_download_button:
                self.osm_download_button.setText("Load Failed!")
                self.osm_download_button.setStyleSheet("background-color: #ffcccc; padding: 5px 10px;")
                self.osm_download_button.setEnabled(True)
                self.osm_download_button.setToolTip(f"Error: {error_msg}")
            QMessageBox.warning(
                self,
                "OSM Layer Load Failed",
                f"The OSM data was downloaded but could not be loaded.\n\n"
                f"File: {gpkg_path}\n\n"
                "The file may be corrupted or empty. Try downloading again.",
            )

    def on_osm_download_error(self, error_message: str) -> None:
        """Handle OSM download errors."""
        log_message(f"OSM download error: {error_message}", tag="Geest", level=Qgis.Critical)

        self._stop_spinner()
        if self.osm_download_button:
            self.osm_download_button.setText("Download Failed!")
            self.osm_download_button.setStyleSheet("background-color: #ffcccc; padding: 5px 10px;")
            self.osm_download_button.setEnabled(True)
            # Set tooltip with error details so user can hover to see what went wrong
            self.osm_download_button.setToolTip(f"Error: {error_message}\n\nClick to retry.")

        # Show error message to user
        QMessageBox.warning(
            self,
            "OSM Download Failed",
            f"The OSM data download failed.\n\n{error_message}\n\n"
            "You can try again by clicking the download button.",
        )

    def _stop_spinner(self) -> None:
        """Stop the spinner animation and hide it."""
        if self.osm_spinner_movie:
            self.osm_spinner_movie.stop()
        if self.osm_spinner_label:
            self.osm_spinner_label.setVisible(False)

    def reset_osm_button(self) -> None:
        """Reset OSM download button to initial state."""
        if self.osm_download_button:
            self.osm_download_button.setText("Download from OSM")
            self.osm_download_button.setStyleSheet("padding: 5px 10px;")
            self.osm_download_button.setEnabled(True)
            self.osm_download_button.setToolTip(self.osm_tooltip)  # Restore original tooltip
        self._stop_spinner()

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
