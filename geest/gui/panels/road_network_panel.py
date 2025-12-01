# -*- coding: utf-8 -*-
"""📦 Road Network Panel module.

This module contains functionality for road network panel.
"""
import os
import traceback

from qgis.core import (
    Qgis,
    QgsFeedback,
    QgsMapLayerProxyModel,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QSettings, pyqtSignal, pyqtSlot
from qgis.PyQt.QtGui import QFont
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
        self.setWindowTitle("GEEST")
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
        """⚙️ Set crs.

        Args:
            crs: Crs.
        """
        self._crs = crs

    def initUI(self):
        """⚙️ Initui."""
        self.custom_label = CustomBannerLabel(
            "The Gender Enabling Environments Spatial Tool",
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
        self.load_road_layer_button.clicked.connect(self.load_road_layer)
        self.download_active_transport_button.clicked.connect(self.download_active_transport_button_clicked)

        self.next_button.clicked.connect(self.on_next_button_clicked)
        self.previous_button.clicked.connect(self.on_previous_button_clicked)

        self.progress_bar.setVisible(False)
        self.child_progress_bar.setVisible(False)

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
        """Load a road network layer from a file."""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Shapefile (*.shp);;GeoPackage (*.gpkg)")
        if file_dialog.exec_():
            file_path = file_dialog.selectedFiles()[0]
            layer = QgsVectorLayer(file_path, "Road Network", "ogr")
            if not layer.isValid():
                QMessageBox.critical(self, "Error", "Could not load the road network layer.")
                return
            # Load the layer in QGIS
            QgsProject.instance().addMapLayer(layer)
            self.road_layer_combo.setLayer(layer)

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
