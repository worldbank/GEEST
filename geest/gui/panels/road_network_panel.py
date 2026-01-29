# -*- coding: utf-8 -*-
"""📦 Road Network Panel module.

This module contains functionality for road network panel.
"""

import os
import traceback

from qgis import processing
from qgis.core import (
    Qgis,
    QgsFeedback,
    QgsMapLayerProxyModel,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QSettings, pyqtSignal, pyqtSlot
from qgis.PyQt.QtGui import QFont, QPixmap
from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox, QWidget

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
        self.setupUi(self)
        log_message("Loading setup panel")
        self.initUI()
        self._reference_layer = None
        self._crs = None
        self._message_bar = None  # Will be set by parent dock

    def show_error_message(self, message, details=None):
        """Show an error message box when workflow queue manager reports an error."""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Error")
        msg_box.setText(message)
        if details:
            msg_box.setDetailedText(details)
        msg_box.exec_()
        self.enable_widgets()  # Re-enable widgets in case they were disabled

    @pyqtSlot(str)
    def working_directory_changed(self, new_directory):
        """Change the working directory and load the model.json if available."""
        log_message(f"Working directory changed to {new_directory}")
        self.working_directory = new_directory

    def set_working_directory(self, working_directory):
        """Set the working directory for the task."""
        log_message(f"Setting the working directory to {working_directory}")
        if working_directory is None or working_directory == "":
            raise Exception("Invalid working directory: None or empty string")
        if not os.path.exists(working_directory):
            raise Exception(f"Invalid working directory: {working_directory}")
        if not os.path.isdir(working_directory):
            raise Exception(f"Invalid working directory: {working_directory}")
        self.working_directory = working_directory

    def set_reference_layer(self, layer):
        """⚙️ Set reference layer.

        Args:
            layer: Layer.
        """
        self._reference_layer = layer

    def set_crs(self, crs):
        """⚙️ Set crs and re-validate current layer.

        Args:
            crs: Crs.
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
            resources_path("resources", "geest-banner.png"),
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

    def update_road_layer_status(self):
        """Update status icon and tooltip based on layer validity and CRS match.

        Validates:
        - Layer exists and is selected
        - Layer is valid and can be loaded
        - Layer CRS matches project CRS (if project CRS is set)

        Shows appropriate icon and tooltip for each validation state.
        """
        road_layer = self.road_layer_combo.currentLayer()

        # Case 1: No layer selected
        if not road_layer:
            self.layer_status_label.setPixmap(QPixmap(resources_path("resources", "icons", "failed.svg")))
            self.layer_status_label.setToolTip("No road network layer selected")
            return

        # Case 2: Layer invalid
        if not road_layer.isValid():
            self.layer_status_label.setPixmap(QPixmap(resources_path("resources", "icons", "failed.svg")))
            self.layer_status_label.setToolTip("Layer is invalid or cannot be loaded")
            return

        # Case 3: CRS mismatch (if project CRS is set)
        if self._crs and road_layer.crs() != self._crs:
            self.layer_status_label.setPixmap(QPixmap(resources_path("resources", "icons", "failed.svg")))
            self.layer_status_label.setToolTip(
                f"CRS mismatch: Layer is {road_layer.crs().authid()} " f"but project is {self._crs.authid()}"
            )
            return

        # Case 4: All checks passed
        self.layer_status_label.setPixmap(QPixmap(resources_path("resources", "icons", "completed-success.svg")))
        if self._crs:
            self.layer_status_label.setToolTip(f"Road network is valid and CRS matches project ({self._crs.authid()})")
        else:
            self.layer_status_label.setToolTip("Road network is valid")

    def emit_road_layer_change(self):
        """⚙️ Emit road layer change."""
        road_layer = self.road_layer_combo.currentLayer()
        if road_layer:
            self.road_network_layer_path_changed.emit(road_layer.source())
        else:
            self.road_network_layer_path_changed.emit(None)

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

    def load_road_layer(self):
        """Load a road network layer from a file with auto-reprojection if needed.

        If the loaded layer's CRS doesn't match the project CRS, it will be
        automatically reprojected and saved to working_directory/study_area/road_network_reprojected.gpkg
        """
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Shapefile (*.shp);;GeoPackage (*.gpkg)")

        if not file_dialog.exec_():
            return

        file_path = file_dialog.selectedFiles()[0]
        layer = QgsVectorLayer(file_path, "Road Network", "ogr")

        if not layer.isValid():
            QMessageBox.critical(self, "Error", "Could not load the road network layer.")
            return

        # Check if reprojection is needed
        if self._crs and layer.crs() != self._crs:
            log_message(
                f"Road network CRS ({layer.crs().authid()}) doesn't match "
                f"project CRS ({self._crs.authid()}). Auto-reprojecting...",
                level=Qgis.Info,
            )

            # Validate working directory
            if not self.working_directory:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Working directory not set. Cannot reproject layer.",
                )
                return

            try:
                reprojected_path = os.path.join(
                    self.working_directory,
                    "study_area",
                    "road_network_reprojected.gpkg",
                )

                # Ensure output directory exists
                os.makedirs(os.path.dirname(reprojected_path), exist_ok=True)

                # Run reprojection
                result = processing.run(
                    "native:reprojectlayer",
                    {"INPUT": layer, "TARGET_CRS": self._crs, "OUTPUT": reprojected_path},
                )

                if not (result and "OUTPUT" in result):
                    QMessageBox.critical(self, "Error", f"Failed to reproject layer to {self._crs.authid()}")
                    return

                # Load reprojected layer
                reprojected_layer = QgsVectorLayer(reprojected_path, "Road Network (Reprojected)", "ogr")

                if not reprojected_layer.isValid():
                    QMessageBox.critical(self, "Error", "Reprojected layer is invalid")
                    return

                # Use reprojected layer instead
                layer = reprojected_layer
                log_message(
                    f"Road network successfully reprojected to {self._crs.authid()}",
                    level=Qgis.Info,
                )

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error during reprojection: {str(e)}")
                return

        # Load layer into QGIS and select it
        QgsProject.instance().addMapLayer(layer)
        self.road_layer_combo.setLayer(layer)

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

        # Load the layer
        layer = QgsVectorLayer(layer_path, "Road Network", "ogr")
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

    def disable_widgets(self):
        """Disable all widgets in the panel."""
        for widget in self.findChildren(QWidget):
            widget.setEnabled(False)

    def enable_widgets(self):
        """Enable all widgets in the panel."""
        for widget in self.findChildren(QWidget):
            widget.setEnabled(True)

    def download_active_transport_button_clicked(self):
        """Triggered when the Download Active Transport button is pressed."""
        if self._reference_layer is None:
            QMessageBox.critical(
                self,
                "Error",
                "No boundary (reference) layer is set, unable to continue.",
            )
            return
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
                tag="Geest",
                level=Qgis.Info,
            )
            network_layer_path_with_layer = f"{network_layer_path}|layername=active_transport_network"
            layer = QgsVectorLayer(network_layer_path_with_layer, "Active Transport Network", "ogr")
            if layer.isValid():
                # Load the layer in QGIS and select it
                QgsProject.instance().addMapLayer(layer)
                self.road_layer_combo.setLayer(layer)
                if self._message_bar:
                    self._message_bar.pushMessage(
                        "GEEST",
                        "Active transport network loaded from cache (already downloaded)",
                        level=Qgis.Info,
                        duration=5,
                    )
                return
            else:
                # File exists but is invalid - remove it and re-download
                log_message(
                    "Existing active transport network file is invalid, will re-download",
                    tag="Geest",
                    level=Qgis.Warning,
                )
                os.remove(network_layer_path)

        # Create the processor instance and process the features
        debug_env = int(os.getenv("GEEST_DEBUG", 0))
        feedback = QgsFeedback()  # Used to cancel tasks and measure subtask progress
        try:
            log_message("Creating OSM Active Transport Downloader Task")
            processor = OSMDownloaderTask(
                reference_layer=self._reference_layer,
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
        """Slot to be called when the download task progress is updated."""
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
            tag="Geest",
            level=Qgis.Info,
        )
        network_layer_path = os.path.join(self.working_directory, "study_area", "active_transport_network.gpkg")
        network_layer_path = f"{network_layer_path}|layername=active_transport_network"
        log_message(f"Loading active transport network layer from {network_layer_path}")
        layer = QgsVectorLayer(network_layer_path, "Active Transport Network", "ogr")
        if not layer.isValid():
            QMessageBox.critical(self, "Error", "Could not load the active transport network layer.")
            return
        # Load the layer in QGIS
        QgsProject.instance().addMapLayer(layer)
        self.progress_bar.setVisible(False)
        self.child_progress_bar.setVisible(False)
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
