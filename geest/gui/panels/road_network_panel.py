# -*- coding: utf-8 -*-
"""📦 Road Network Panel module.

This module contains functionality for road network panel.
"""

import json
import os
import traceback

from qgis import processing
from qgis.core import (
    Qgis,
    QgsFeedback,
    QgsMapLayerProxyModel,
    QgsProject,
    QgsVectorLayer,
    QgsWkbTypes,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
)
from qgis.PyQt.QtCore import QSettings, Qt, pyqtSignal, pyqtSlot
from qgis.PyQt.QtGui import QFont, QPixmap
from qgis.PyQt.QtWidgets import QApplication, QFileDialog, QMessageBox, QWidget

from geest.core import WorkflowQueueManager
from geest.core.osm_downloaders.osm_download_type import OSMDownloadType
from geest.core.tasks import OSMDownloaderTask
from geest.gui.widgets import CustomBannerLabel
from geest.utilities import (
    get_ui_class,
    linear_interpolation,
    log_message,
    resources_path,
)

FORM_CLASS = get_ui_class("road_network_panel_base.ui")


class RoadNetworkPanel(FORM_CLASS, QWidget):
    """🎯 Road Network Panel.

    Attributes:
        queue_manager: Queue manager.
        settings: Settings.
        working_directory: Working directory.
    """

    switch_to_next_tab = pyqtSignal()  # Signal to notify the parent to switch tabs
    switch_to_previous_tab = pyqtSignal()  # Signal to notify the parent to switch tabs

    road_network_layer_path_changed = pyqtSignal(str)

    def __init__(self):
        """🏗️ Initialize the instance."""
        super().__init__()
        self.setWindowTitle("GeoE3")
        # For running study area processing in a separate thread
        self.queue_manager = WorkflowQueueManager(pool_size=1)

        # Connect the error_occurred signal to show error message
        self.queue_manager.processing_error.connect(self.show_error_message)

        self.working_directory = ""
        self.settings = QSettings()  # Initialize QSettings to store and retrieve settings
        # Dynamically load the .ui file
        self._reference_layer = None
        self._crs = None  # Study area CRS
        self._message_bar = None  # Will be set by parent dock
        self._reprojected_layers = {}  # Cache: source_path -> reprojected_layer
        self.setupUi(self)
        log_message("Loading setup panel")
        self.initUI()

    def show_error_message(self, message, details=None):
        """Show an error message box when workflow queue manager reports an error.

        Args:
            message: The error message to display.
            details: Optional detailed error information.
        """
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Error")
        msg_box.setText(message)
        if details:
            msg_box.setDetailedText(details)
        msg_box.exec_()
        self.progress_bar.setVisible(False)
        self.child_progress_bar.setVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("OSM download failed")
        self.enable_widgets()  # Re-enable widgets in case they were disabled

    @pyqtSlot(str)
    def working_directory_changed(self, new_directory):
        """Change the working directory and load the model.json if available.

        Args:
            new_directory: The new working directory path.
        """
        log_message(f"Working directory changed to {new_directory}")
        self.working_directory = new_directory

    def set_working_directory(self, working_directory):
        """Set the working directory for the task.

        Args:
            working_directory: The working directory path.

        Raises:
            Exception: If the working directory is invalid.
        """
        log_message(f"Setting the working directory to {working_directory}")
        if working_directory is None or working_directory == "":
            raise Exception("Invalid working directory: None or empty string")
        if not os.path.exists(working_directory):
            raise Exception(f"Invalid working directory: {working_directory}")
        if not os.path.isdir(working_directory):
            raise Exception(f"Invalid working directory: {working_directory}")
        self.working_directory = working_directory
        # Restore reference layer from model.json if available
        self.restore_reference_layer_from_model()

    def restore_reference_layer_from_model(self):
        """Restore reference layer from saved path in model.json."""
        if not self.working_directory:
            return
        model_path = os.path.join(self.working_directory, "model.json")
        if not os.path.exists(model_path):
            return
        try:
            with open(model_path, "r") as f:
                model = json.load(f)
            admin_source = model.get("admin_boundary_layer_source")
            if admin_source and os.path.exists(admin_source):
                base_path = admin_source.split("|")[0] if "|" in admin_source else admin_source
                layer_name = os.path.splitext(os.path.basename(base_path))[0]
                layer = QgsVectorLayer(admin_source, layer_name, "ogr")
                if layer.isValid():
                    self._reference_layer = layer
                    log_message(f"Restored reference layer from: {admin_source}", level=Qgis.Info)
                else:
                    log_message(f"Cannot restore reference layer - invalid: {admin_source}", level=Qgis.Warning)
            else:
                log_message("No reference layer path found in model.json", level=Qgis.Info)
        except Exception as e:
            log_message(f"Error restoring reference layer: {e}", level=Qgis.Warning)

    def set_reference_layer(self, layer):
        """⚙️ Set reference layer.

        Args:
            layer: Layer.
        """
        self._reference_layer = layer

    def set_crs(self, crs):
        """⚙️ Set study area CRS and re-validate current layer.

        Args:
            crs: Study area CRS (from study_area.gpkg, not QGIS project CRS).
        """
        self._crs = crs
        self.update_road_layer_status()  # Re-validate with new CRS

    def set_message_bar(self, message_bar):
        """⚙️ Set message bar reference.

        Args:
            message_bar: QgsMessageBar instance from parent dock.
        """
        self._message_bar = message_bar

    def initUI(self):
        """⚙️ Initui."""
        self.custom_label = CustomBannerLabel(
            "The Geospatial Enabling Environments for Employment Spatial Tool",
            resources_path("resources", "geoe3-banner.png"),
        )
        parent_layout = self.banner_label.parent().layout()
        parent_layout.replaceWidget(self.banner_label, self.custom_label)
        self.banner_label.deleteLater()
        parent_layout.update()

        # self.folder_status_label.setPixmap(
        #     QPixmap(resources_path("resources", "icons", "failed.svg"))
        # )
        self.road_layer_combo.setFilters(QgsMapLayerProxyModel.LineLayer)
        self.road_layer_combo.currentIndexChanged.connect(self.emit_road_layer_change)
        self.road_layer_combo.currentIndexChanged.connect(self.update_road_layer_status)
        self.load_road_layer_button.clicked.connect(self.load_road_layer)
        self.download_active_transport_button.clicked.connect(self.download_active_transport_button_clicked)

        self.next_button.clicked.connect(self.on_next_button_clicked)
        self.previous_button.clicked.connect(self.on_previous_button_clicked)

        self.progress_bar.setVisible(False)
        self.child_progress_bar.setVisible(False)

        self.update_road_layer_status()

        self.layer_status_label.setPixmap(QPixmap(resources_path("resources", "icons", "failed.svg")))

        # Start with next button disabled until a valid road layer is selected
        self._update_next_button_state()

    def update_road_layer_status(self):
        """Update status icon, tooltip, and auto-reproject if CRS mismatch detected.

        Validates:
        - Layer exists and is selected
        - Layer is valid and can be loaded
        - Layer CRS matches study area CRS (if study area CRS is set)

        If CRS mismatch is detected for a dropdown-selected layer, automatically
        reprojects the layer and updates the combo box selection.

        Shows appropriate icon and tooltip for each validation state.
        """
        road_layer = self.road_layer_combo.currentLayer()

        # Case 1: No layer selected
        if not road_layer:
            self.layer_status_label.setPixmap(QPixmap(resources_path("resources", "icons", "failed.svg")))
            self.layer_status_label.setToolTip("No road network layer selected")
        # Case 2: Layer invalid
        elif not road_layer.isValid():
            self.layer_status_label.setPixmap(QPixmap(resources_path("resources", "icons", "failed.svg")))
            self.layer_status_label.setToolTip("Layer is invalid or cannot be loaded")
        # Case 3: No study area CRS set yet
        elif not self._crs:
            self.layer_status_label.setPixmap(QPixmap(resources_path("resources", "icons", "info.svg")))
            self.layer_status_label.setToolTip(f"Layer CRS: {road_layer.crs().authid()}")
        # Case 4: CRS matches - all good
        elif road_layer.crs() == self._crs:
            self.layer_status_label.setPixmap(QPixmap(resources_path("resources", "icons", "completed-success.svg")))
            self.layer_status_label.setToolTip(f"✓ CRS matches study area: {self._crs.authid()}")
        else:
            # Case 5: CRS mismatch - check if reprojected version already exists
            existing_reprojected = self._find_existing_reprojected_layer(road_layer, self._crs)

            if existing_reprojected:
                # Use existing reprojected layer instead of creating new one
                log_message(
                    f"Using existing reprojected layer: {existing_reprojected.name()}",
                    level=Qgis.Info,
                )
                self.road_layer_combo.blockSignals(True)
                self.road_layer_combo.setLayer(existing_reprojected)
                self.road_layer_combo.blockSignals(False)
                self.layer_status_label.setPixmap(
                    QPixmap(resources_path("resources", "icons", "completed-success.svg"))
                )
                self.layer_status_label.setToolTip(f"✓ Using existing reprojected layer: {existing_reprojected.name()}")
                self.emit_road_layer_change()
            else:
                # Case 6: CRS mismatch - auto-reproject with unique filename
                log_message(
                    f"CRS mismatch detected: {road_layer.crs().authid()} != {self._crs.authid()}",
                    level=Qgis.Warning,
                )

                # Keep red icon during reprojection
                self.layer_status_label.setPixmap(QPixmap(resources_path("resources", "icons", "failed.svg")))
                self.layer_status_label.setToolTip("Reprojecting layer, please wait...")

                # Set waiting cursor to indicate processing
                QApplication.setOverrideCursor(Qt.WaitCursor)
                QApplication.processEvents()  # Update UI to show red icon + tooltip

                try:
                    # Perform automatic reprojection
                    reprojected_layer = self.reproject_selected_layer(road_layer)

                    if reprojected_layer:
                        # Block signals to prevent recursion
                        self.road_layer_combo.blockSignals(True)
                        self.road_layer_combo.setLayer(reprojected_layer)
                        self.road_layer_combo.blockSignals(False)

                        # Update success icon
                        self.layer_status_label.setPixmap(
                            QPixmap(resources_path("resources", "icons", "completed-success.svg"))
                        )
                        self.layer_status_label.setToolTip(
                            f"✓ Reprojected to study area CRS: {self._crs.authid()}\n"
                            f"Saved to: study_area/road_network_reprojected.gpkg"
                        )

                        # Emit change to update saved path in model
                        self.emit_road_layer_change()

                        log_message(
                            "Successfully reprojected road network layer",
                            level=Qgis.Info,
                        )
                    else:
                        # Reprojection failed - keep red icon with error message
                        self.layer_status_label.setPixmap(QPixmap(resources_path("resources", "icons", "failed.svg")))
                        self.layer_status_label.setToolTip(
                            f"❌ Failed to reproject layer\n"
                            f"Layer CRS: {road_layer.crs().authid()}\n"
                            f"Study area CRS: {self._crs.authid()}\n"
                            f"Please select a layer in the correct CRS or reproject manually."
                        )

                finally:
                    # Always restore cursor, even if error occurs
                    QApplication.restoreOverrideCursor()

        # Update next button state based on layer validity
        self._update_next_button_state()

    def emit_road_layer_change(self):
        """⚙️ Emit road layer change."""
        road_layer = self.road_layer_combo.currentLayer()
        if road_layer:
            self.road_network_layer_path_changed.emit(road_layer.source())
        else:
            self.road_network_layer_path_changed.emit(None)

    def _update_next_button_state(self):
        """Enable or disable next button based on road layer validity."""
        road_layer = self.road_layer_combo.currentLayer()
        has_valid_layer = road_layer is not None and road_layer.isValid()
        self.next_button.setEnabled(has_valid_layer)

    def _generate_reprojected_filename(self, source_layer, target_crs):
        """Generate unique filename based on original layer name and target CRS.

        Args:
            source_layer: The original QgsVectorLayer to reproject.
            target_crs: The target QgsCoordinateReferenceSystem.

        Returns:
            str: A unique filename prefix (without extension).
        """
        import re

        # Get base name from layer source (without extension)
        source = source_layer.source()
        base_name = os.path.splitext(os.path.basename(source))[0]
        # Sanitize for filesystem
        safe_name = re.sub(r"[^\w\-]", "_", base_name).strip("_")
        # Include target CRS to distinguish different reprojections
        crs_suffix = target_crs.authid().replace(":", "_")
        return f"{safe_name}_reprojected_{crs_suffix}"

    def _find_existing_reprojected_layer(self, source_layer, target_crs):
        """Check if this layer has already been reprojected to target CRS.

        Searches QGIS project for an existing layer that:
        1. Has a source path containing the original layer's base name
        2. Has a source path containing the target CRS suffix
        3. Actually has the target CRS

        Args:
            source_layer: The original QgsVectorLayer.
            target_crs: The target QgsCoordinateReferenceSystem.

        Returns:
            QgsVectorLayer or None: Existing reprojected layer if found, None otherwise.
        """
        source_path = source_layer.source()
        source_name = os.path.splitext(os.path.basename(source_path))[0]
        target_suffix = target_crs.authid().replace(":", "_")

        for layer in QgsProject.instance().mapLayers().values():
            if layer == source_layer:
                continue  # Skip the source layer itself
            layer_source = layer.source()
            # Check if this is a reprojected version of our source
            if source_name in layer_source and target_suffix in layer_source:
                if layer.crs() == target_crs:
                    log_message(
                        f"Found existing reprojected layer: {layer.name()} ({layer_source})",
                        level=Qgis.Info,
                    )
                    return layer
        return None

    def on_next_button_clicked(self):
        """⚙️ On next button clicked."""
        self.switch_to_next_tab.emit()

    def on_previous_button_clicked(self):
        """⚙️ On previous button clicked."""
        self.switch_to_previous_tab.emit()

    def road_network_layer_path(self):
        """⚙️ Road network layer path.

        Returns:
            The result of the operation.
        """
        if self.road_layer_combo.currentLayer() is None:
            return None
        return self.road_layer_combo.currentLayer().source()

    def _reproject_layer_to_file(self, source_layer, output_name="road_network_reprojected"):
        """Reproject a layer to study area CRS and save to study_area directory.

        Helper method used by both load_road_layer() and reproject_selected_layer().

        Args:
            source_layer: QgsVectorLayer to reproject
            output_name: Base name for output file (without extension)

        Returns:
            Tuple of (success: bool, output_path: str or None, layer: QgsVectorLayer or None)
        """
        # Validate working directory
        if not self.working_directory:
            QMessageBox.critical(
                self,
                "Error",
                "Working directory not set. Cannot reproject layer.",
            )
            return False, None, None

        try:
            reprojected_path = os.path.join(
                self.working_directory,
                "study_area",
                f"{output_name}.gpkg",
            )

            # Ensure output directory exists
            os.makedirs(os.path.dirname(reprojected_path), exist_ok=True)

            log_message(
                f"Reprojecting {source_layer.name()} from {source_layer.crs().authid()} " f"to {self._crs.authid()}",
                level=Qgis.Info,
            )

            # Run reprojection
            result = processing.run(
                "native:reprojectlayer",
                {"INPUT": source_layer, "TARGET_CRS": self._crs, "OUTPUT": reprojected_path},
            )

            if not (result and "OUTPUT" in result):
                QMessageBox.critical(self, "Error", f"Failed to reproject layer to {self._crs.authid()}")
                return False, None, None

            # Load reprojected layer - use original layer name with "(reprojected)" suffix
            reprojected_layer = QgsVectorLayer(reprojected_path, f"{source_layer.name()} (reprojected)", "ogr")

            if not reprojected_layer.isValid():
                QMessageBox.critical(self, "Error", "Reprojected layer is invalid")
                return False, None, None

            # Add to QGIS project for user visibility
            QgsProject.instance().addMapLayer(reprojected_layer)

            log_message(
                f"Layer successfully reprojected and saved to {reprojected_path}",
                level=Qgis.Info,
            )

            return True, reprojected_path, reprojected_layer

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error during reprojection: {str(e)}")
            log_message(f"Reprojection error: {str(e)}", level=Qgis.Critical)
            return False, None, None

    def load_road_layer(self):
        """Load a road network layer from a file with auto-reprojection if needed.

        If the loaded layer's CRS doesn't match the study area CRS, it will be
        automatically reprojected and saved to working_directory/study_area/
        with a unique filename based on the original layer name.
        """
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Shapefile (*.shp);;GeoPackage (*.gpkg)")

        if not file_dialog.exec_():
            return

        file_path = file_dialog.selectedFiles()[0]
        layer_name = os.path.splitext(os.path.basename(file_path))[0]
        layer = QgsVectorLayer(file_path, layer_name, "ogr")

        if not layer.isValid():
            QMessageBox.critical(self, "Error", "Could not load the road network layer.")
            return

        # Check geometry type - only accept lines (using wkbType for compatibility)
        if QgsWkbTypes.geometryType(layer.wkbType()) != QgsWkbTypes.GeometryType.LineGeometry:
            geometry_name = QgsWkbTypes.displayString(layer.wkbType())
            QMessageBox.critical(
                self,
                "Error",
                "Road network layer must be a line (polyline) layer.\n"
                f"Selected file contains: {geometry_name} geometry.\n"
                "Please select a line/polyline layer.",
            )
            return

        # Check if reprojection is needed
        if self._crs and layer.crs() != self._crs:
            # Check in-memory cache first
            source_path = layer.source()
            if source_path in self._reprojected_layers:
                cached = self._reprojected_layers[source_path]
                if cached and cached.isValid() and cached.crs() == self._crs:
                    log_message(
                        f"Using cached reprojected layer for: {layer.name()}",
                        level=Qgis.Info,
                    )
                    layer = cached
                else:
                    # Cache invalid, remove it
                    del self._reprojected_layers[source_path]

            # Check if reprojected layer already exists in project
            if layer.crs() != self._crs:
                existing = self._find_existing_reprojected_layer(layer, self._crs)
                if existing:
                    log_message(
                        f"Using existing reprojected layer: {existing.name()}",
                        level=Qgis.Info,
                    )
                    self._reprojected_layers[source_path] = existing
                    layer = existing
                else:
                    # Need to reproject
                    log_message(
                        f"Road network CRS ({layer.crs().authid()}) doesn't match "
                        f"study area CRS ({self._crs.authid()}). Auto-reprojecting...",
                        level=Qgis.Info,
                    )

                    # Generate unique filename
                    output_name = self._generate_reprojected_filename(layer, self._crs)

                    # Use helper method for reprojection
                    success, reprojected_path, reprojected_layer = self._reproject_layer_to_file(
                        layer, output_name=output_name
                    )

                    if success and reprojected_layer:
                        self._reprojected_layers[source_path] = reprojected_layer
                        layer = reprojected_layer
                    else:
                        # Error already shown by helper method
                        return

        # Load layer into QGIS and select it
        QgsProject.instance().addMapLayer(layer)
        self.road_layer_combo.setLayer(layer)

    def reproject_selected_layer(self, layer):
        """Automatically reproject a layer selected from dropdown.

        Called when user selects a layer with different CRS than study area CRS.
        This method is triggered automatically by update_road_layer_status().

        Checks for existing reprojected layers in QGIS project and in-memory cache
        before creating new reprojection.

        Args:
            layer: QgsVectorLayer with mismatched CRS

        Returns:
            Reprojected QgsVectorLayer if successful, None if failed
        """
        source_path = layer.source()

        # Check in-memory cache first
        if source_path in self._reprojected_layers:
            cached = self._reprojected_layers[source_path]
            if cached and cached.isValid() and cached.crs() == self._crs:
                log_message(
                    f"Using cached reprojected layer for: {layer.name()}",
                    level=Qgis.Info,
                )
                return cached

        # Check if reprojected layer already exists in project
        existing = self._find_existing_reprojected_layer(layer, self._crs)
        if existing:
            self._reprojected_layers[source_path] = existing
            return existing

        # Generate unique filename based on original layer name and target CRS
        output_name = self._generate_reprojected_filename(layer, self._crs)

        log_message(
            f"Auto-reprojecting dropdown selection: {layer.name()} "
            f"from {layer.crs().authid()} to {self._crs.authid()}",
            level=Qgis.Info,
        )

        success, reprojected_path, reprojected_layer = self._reproject_layer_to_file(layer, output_name=output_name)

        if success and reprojected_layer:
            # Cache the reprojected layer
            self._reprojected_layers[source_path] = reprojected_layer
            log_message(
                f"Successfully reprojected road network layer to {reprojected_path}",
                level=Qgis.Info,
            )
            return reprojected_layer
        else:
            log_message(
                "Failed to reproject road network layer",
                level=Qgis.Critical,
            )
            return None

    def restore_layer_from_path(self, layer_path):
        """Restore layer selection from saved path in model.json.

        This method is called when switching to the road network panel
        or opening an existing project to sync the UI with the saved state.

        Args:
            layer_path (str): Path to road network layer (may include |layername=)
        """
        if not layer_path:
            return

        base_path = layer_path.split("|")[0] if "|" in layer_path else layer_path

        # Case 1: Layer already loaded in QGIS - just select it
        existing_layers = [
            layer
            for layer in QgsProject.instance().mapLayers().values()
            if hasattr(layer, "source") and layer.source() == layer_path
        ]

        if existing_layers:
            self.road_layer_combo.setLayer(existing_layers[0])
            log_message(
                f"Restored road network from existing layer: {layer_path}",
                level=Qgis.Info,
            )
            self.update_road_layer_status()
            return

        # Case 2: Layer not in QGIS - need to load from disk
        if not os.path.exists(base_path):
            log_message(
                f"Cannot restore road network layer - file not found: {base_path}",
                level=Qgis.Warning,
            )
            # Clear the path from model since file doesn't exist
            self.road_network_layer_path_changed.emit("")
            return

        # Load the layer - use filename as layer name
        base_path = layer_path.split("|")[0] if "|" in layer_path else layer_path
        layer_name = os.path.splitext(os.path.basename(base_path))[0]
        layer = QgsVectorLayer(layer_path, layer_name, "ogr")
        if not layer.isValid():
            log_message(
                f"Cannot restore road network layer - invalid: {layer_path}",
                level=Qgis.Warning,
            )
            # Clear the path from model since layer is invalid
            self.road_network_layer_path_changed.emit("")
            return

        # Add to QGIS and select in combo box
        QgsProject.instance().addMapLayer(layer)
        self.road_layer_combo.setLayer(layer)
        log_message(f"Restored road network layer from path: {layer_path}", level=Qgis.Info)
        self.update_road_layer_status()

    def load_reference_layer(self):
        """Load reference (admin boundary) layer from file."""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Shapefile (*.shp);;GeoPackage (*.gpkg)")

        if not file_dialog.exec_():
            return

        file_path = file_dialog.selectedFiles()[0]
        layer_name = os.path.splitext(os.path.basename(file_path))[0]
        layer = QgsVectorLayer(file_path, layer_name, "ogr")

        if not layer.isValid():
            QMessageBox.critical(self, "Error", "Could not load the boundary layer.")
            return

        self._reference_layer = layer
        log_message(f"Loaded reference layer: {file_path}", level=Qgis.Info)

        # Save to model.json
        if self.working_directory:
            model_path = os.path.join(self.working_directory, "model.json")
            if os.path.exists(model_path):
                try:
                    with open(model_path, "r") as f:
                        model = json.load(f)
                    model["admin_boundary_layer_source"] = layer.source()
                    with open(model_path, "w") as f:
                        json.dump(model, f, indent=2)
                    log_message("Saved reference layer path to model.json", level=Qgis.Info)
                except Exception as e:
                    log_message(f"Error saving reference layer to model.json: {e}", level=Qgis.Warning)

    def disable_widgets(self):
        """Disable all widgets in the panel."""
        for widget in self.findChildren(QWidget):
            widget.setEnabled(False)

    def enable_widgets(self):
        """Enable all widgets in the panel."""
        for widget in self.findChildren(QWidget):
            widget.setEnabled(True)
        # Keep Next button gated by layer validity after any state reset.
        self._update_next_button_state()

    def _get_bbox_from_study_area(self):
        """Get bounding box from existing study_area.gpkg.

        Returns:
            tuple: (xmin, ymin, xmax, ymax) in EPSG:4326, or None if not found
        """
        if not self.working_directory:
            return None

        study_area_gpkg = os.path.join(self.working_directory, "study_area", "study_area.gpkg")
        if not os.path.exists(study_area_gpkg):
            log_message(f"Study area gpkg not found: {study_area_gpkg}", level=Qgis.Warning)
            return None

        try:
            # Read the study area layer to get bbox
            layer = QgsVectorLayer(f"{study_area_gpkg}|layername=study_area_polygons", "study_area", "ogr")
            if not layer.isValid():
                log_message("Study area layer is invalid", level=Qgis.Warning)
                return None

            # Get the bounding box in EPSG:4326
            extent = layer.extent()
            crs = layer.crs()

            # Transform to WGS84 if needed
            if crs.authid() != "EPSG:4326":
                dest_crs = QgsCoordinateReferenceSystem()
                dest_crs.createFromString("EPSG:4326")
                transform = QgsCoordinateTransform(crs, dest_crs, QgsProject.instance())
                extent = transform.transformBoundingBox(extent)

            log_message(
                f"Got bbox from study area: {extent.toString()}",
                level=Qgis.Info,
            )
            return extent
        except Exception as e:
            log_message(f"Error getting bbox from study area: {e}", level=Qgis.Warning)
            return None

    def download_active_transport_button_clicked(self):
        """Triggered when the Download Active Transport button is pressed."""
        if self._crs is None:
            QMessageBox.critical(self, "Error", "No CRS is set, unable to continue.")
            return
        if self.working_directory is None or self.working_directory == "":
            QMessageBox.critical(self, "Error", "Working directory is not set")
            return

        # Check if the layer already exists
        network_layer_path = os.path.join(self.working_directory, "study_area", "active_transport_network.gpkg")
        if os.path.exists(network_layer_path):
            # Layer already downloaded - just load it
            log_message(
                "Active transport network already exists, loading from cache",
                tag="GeoE3",
                level=Qgis.Info,
            )
            network_layer_path_with_layer = f"{network_layer_path}|layername=active_transport_network"
            layer_name = os.path.splitext(os.path.basename(network_layer_path))[0]
            layer = QgsVectorLayer(network_layer_path_with_layer, layer_name, "ogr")
            if layer.isValid():
                # Load the layer in QGIS and select it
                QgsProject.instance().addMapLayer(layer)
                self.road_layer_combo.setLayer(layer)
                if self._message_bar:
                    self._message_bar.pushMessage(
                        "GEOE3",
                        "Active transport network loaded from cache (already downloaded)",
                        level=Qgis.Info,
                        duration=5,
                    )
                return
            else:
                # File exists but is invalid - remove it and re-download
                log_message(
                    "Existing active transport network file is invalid, will re-download",
                    tag="GeoE3",
                    level=Qgis.Warning,
                )
                os.remove(network_layer_path)

        # Create the processor instance and process the features
        debug_env = int(os.getenv("GEOE3_DEBUG") or os.getenv("GEEST_DEBUG", 0))
        feedback = QgsFeedback()  # Used to cancel tasks and measure subtask progress

        # Determine what to use: reference_layer or extents from study_area
        reference_layer = self._reference_layer
        extents = None

        if reference_layer is None:
            # Try to get bbox from study_area.gpkg automatically
            extents = self._get_bbox_from_study_area()
            if extents is None:
                QMessageBox.critical(
                    self,
                    "Error",
                    "No boundary layer and no study area found. Please create a project first.",
                )
                return
            log_message("Using bbox from study area for OSM download", level=Qgis.Info)

        try:
            log_message("Creating OSM Active Transport Downloader Task")
            processor = OSMDownloaderTask(
                reference_layer=reference_layer,
                extents=extents,
                osm_download_type=OSMDownloadType.ACTIVE_TRANSPORT,
                crs=self._crs,
                working_dir=self.working_directory,
                filename="active_transport_network",
                use_cache=True,
                delete_gpkg=True,
                feedback=feedback,
            )
            log_message("OSM Active Transport Downloader Task created, setting up call backs")
            # Hook up the QTask feedback signal to the progress bar
            # Measure overall task progress from the task object itself
            processor.progressChanged.connect(self.osm_download_progress_updated)
            processor.taskCompleted.connect(self.active_transport_download_done)
            processor.taskTerminated.connect(self.active_transport_download_terminated)
            # Measure subtask progress from the feedback object
            feedback.progressChanged.connect(self.osm_extract_progress_updated)
            self.disable_widgets()
            if debug_env:
                processor.run()
            else:
                log_message("Adding task to queue manager")
                self.queue_manager.add_task(processor)
                self.queue_manager.start_processing()
                log_message("Processing started")
        except Exception as e:
            trace = traceback.format_exc()
            QMessageBox.critical(
                self, "Error", f"Error downloading active transport network for study area: {e}\n{trace}"
            )
            self.enable_widgets()
            return

    # Slot that listens for changes in the study_area task object which is used to measure overall task progress
    def osm_download_progress_updated(self, progress: float):
        """Slot to be called when the download task progress is updated.

        Args:
            progress: The download progress value.
        """
        log_message(f"\n\n\n\n\n\nProgress: {progress}\n\n\n\n\n\n\n\n")
        self.progress_bar.setVisible(True)
        self.progress_bar.setEnabled(True)
        self.progress_bar.setValue(int(progress))
        if progress == 0:
            self.progress_bar.setFormat("Fetching OSM data...")
            self.progress_bar.setMinimum(0)  # makes it bounce indefinitely
            self.progress_bar.setMaximum(0)
        else:
            self.progress_bar.setMinimum(0)
            self.progress_bar.setMaximum(100)

            # This is a sneaky hack to show the exact progress in the label
            # since QProgressBar only takes ints. See Qt docs for more info.
            # Use the 'setFormat' method to display the exact float:
            float_value_as_string = f"OSM download progress: {progress}%"
            self.progress_bar.setFormat(float_value_as_string)

    # Slot that listens for changes in the progress object which is used to measure subtask progress
    def osm_extract_progress_updated(self, progress: float):
        """⚙️ Osm extract progress updated.

        Args:
            progress: Progress.
        """
        self.child_progress_bar.setVisible(True)
        self.child_progress_bar.setEnabled(True)
        if progress == 0:
            self.progress_bar.setFormat("Extracting OSM data...")
            self.progress_bar.setMinimum(0)  # makes it bounce indefinitely
            self.progress_bar.setMaximum(0)
        else:
            self.progress_bar.setMinimum(0)
            self.progress_bar.setMaximum(100)
            self.child_progress_bar.setValue(int(progress))
            # This is a sneaky hack to show the exact progress in the label
            # since QProgressBar only takes ints. See Qt docs for more info.
            # Use the 'setFormat' method to display the exact float:
            float_value_as_string = f"OSM extract progress: {progress}%"
            self.child_progress_bar.setFormat(float_value_as_string)

    def active_transport_download_done(self):
        """⚙️ Active transport download done."""
        log_message(
            "*** OSM Active Transport download completed successfully. ***",
            tag="GeoE3",
            level=Qgis.Info,
        )
        network_layer_path = os.path.join(self.working_directory, "study_area", "active_transport_network.gpkg")
        network_layer_path = f"{network_layer_path}|layername=active_transport_network"
        log_message(f"Loading active transport network layer from {network_layer_path}")
        layer_name = os.path.splitext(os.path.basename(network_layer_path.split("|")[0]))[0]
        layer = QgsVectorLayer(network_layer_path, layer_name, "ogr")
        if not layer.isValid():
            QMessageBox.critical(self, "Error", "Could not load the active transport network layer.")
            return
        # Load the layer in QGIS
        QgsProject.instance().addMapLayer(layer)
        self.progress_bar.setVisible(False)
        self.child_progress_bar.setVisible(False)
        self.enable_widgets()

    def active_transport_download_terminated(self):
        """Handle OSM task termination and keep navigation state safe."""
        log_message(
            "OSM Active Transport download task terminated.",
            tag="GeoE3",
            level=Qgis.Warning,
        )
        self.progress_bar.setVisible(False)
        self.child_progress_bar.setVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("OSM download failed")
        self.enable_widgets()

    def resizeEvent(self, event):
        """⚙️ Resizeevent.

        Args:
            event: Event.
        """
        self.set_font_size()
        super().resizeEvent(event)

    def set_font_size(self):
        """⚙️ Set font size."""
        # Scale the font size to fit the text in the available space
        # log_message(f"Description Label Width: {self.description.rect().width()}")
        # scale the font size linearly from 16 pt to 8 ps as the width of the panel decreases
        font_size = int(linear_interpolation(self.description.rect().width(), 12, 16, 400, 600))

        # log_message(f"Description Label Font Size: {font_size}")
        self.description.setFont(QFont("Arial", font_size))
        self.description4.setFont(QFont("Arial", font_size))
        self.description6.setFont(QFont("Arial", font_size))
        self.road_layer_combo.setFont(QFont("Arial", font_size))
        self.load_road_layer_button.setFont(QFont("Arial", font_size))
        self.download_active_transport_button.setFont(QFont("Arial", font_size))
