# -*- coding: utf-8 -*-
"""OSM Download Widget module.

This module provides a reusable widget for downloading OSM data.
"""
import os
from typing import Optional

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsFeedback,
    QgsProject,
    QgsRectangle,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import pyqtSignal, QThread
from qgis.PyQt.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from geest.core.osm_downloaders import OSMDownloadType, OSMDownloaderFactory
from geest.utilities import log_message


class OSMDownloadWorker(QThread):
    """Worker thread for downloading OSM data."""

    finished = pyqtSignal(str)  # Emits the path to the downloaded gpkg
    error = pyqtSignal(str)  # Emits error message
    progress = pyqtSignal(str)  # Emits progress messages

    def __init__(
        self,
        download_type: OSMDownloadType,
        extents: QgsRectangle,
        output_path: str,
        output_crs: QgsCoordinateReferenceSystem,
        filename: str,
    ):
        super().__init__()
        self.download_type = download_type
        self.extents = extents
        self.output_path = output_path
        self.output_crs = output_crs
        self.filename = filename
        self.feedback = QgsFeedback()

    def run(self):
        """Execute the download in a separate thread."""
        try:
            self.progress.emit("Downloading OSM data...")

            # Create downloader using factory
            downloader = OSMDownloaderFactory.get_osm_downloader(
                download_type=self.download_type,
                extents=self.extents,
                output_path=self.output_path,
                output_crs=self.output_crs,
                filename=self.filename,
                use_cache=False,
                delete_gpkg=True,
                feedback=self.feedback,
            )

            self.progress.emit("Processing OSM data...")

            # Process the response and create gpkg
            downloader.process_response()

            # The output file path is already the full path (not a directory)
            if os.path.exists(self.output_path):
                self.progress.emit("Download complete!")
                self.finished.emit(self.output_path)
            else:
                self.error.emit("Download completed but output file not found")

        except Exception as e:
            log_message(f"OSM download error: {e}", tag="Geest", level=Qgis.Critical)
            self.error.emit(str(e))

    def cancel(self):
        """Cancel the download."""
        if self.feedback:
            self.feedback.cancel()


class OSMDownloadWidget(QWidget):
    """Reusable widget for downloading OSM data.

    Signals:
        download_completed: Emitted when download finishes successfully, passes layer path
    """

    download_completed = pyqtSignal(str)  # Emits path to downloaded gpkg

    def __init__(
        self,
        download_type: OSMDownloadType,
        title: str = "OpenStreetMap Data",
        parent: Optional[QWidget] = None,
    ):
        """Initialize the OSM download widget.

        Args:
            download_type: The type of OSM data to download
            title: Title for the group box
            parent: Parent widget
        """
        super().__init__(parent)
        self.download_type = download_type
        self.worker = None
        self.init_ui(title)

    def init_ui(self, title: str):
        """Initialize the user interface."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)

        # Download button - match default button styling
        self.download_button = QPushButton("Download from OpenStreetMap")
        self.download_button.clicked.connect(self.start_download)
        main_layout.addWidget(self.download_button)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(6)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setTextVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setVisible(False)
        self.status_label.setStyleSheet("QLabel { font-size: 9pt; }")
        main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)

    def start_download(self):
        """Start the OSM download process."""
        # Get the project CRS and extent
        project = QgsProject.instance()
        if not project:
            self.show_error("No QGIS project loaded")
            return

        # Use project CRS or default to EPSG:4326
        crs = project.crs() if project.crs().isValid() else QgsCoordinateReferenceSystem("EPSG:4326")

        # Get extent from all layers in the project
        extent = QgsRectangle()
        layers = project.mapLayers().values()

        if layers:
            for layer in layers:
                if layer.extent().isFinite():
                    if extent.isEmpty():
                        extent = layer.extent()
                    else:
                        extent.combineExtentWith(layer.extent())

        # If no layers or extent is still empty, use full world extent
        if extent.isEmpty() or not extent.isFinite():
            extent = QgsRectangle(-180, -90, 180, 90)
            log_message("Using world extent for OSM download", tag="Geest", level=Qgis.Warning)

        # Create output directory in temp
        import tempfile

        output_path = tempfile.mkdtemp(prefix="geest_osm_")
        filename = f"osm_{self.download_type.value}"

        # Update UI
        self.download_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.status_label.setText("Preparing download...")

        # Create and start worker thread
        self.worker = OSMDownloadWorker(
            download_type=self.download_type,
            extents=extent,
            output_path=output_path,
            output_crs=crs,
            filename=filename,
        )
        self.worker.finished.connect(self.on_download_finished)
        self.worker.error.connect(self.on_download_error)
        self.worker.progress.connect(self.on_download_progress)
        self.worker.start()

    def on_download_progress(self, message: str):
        """Handle progress updates."""
        self.status_label.setText(message)

    def on_download_finished(self, gpkg_path: str):
        """Handle successful download completion."""
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Download complete: {os.path.basename(gpkg_path)}")
        self.status_label.setStyleSheet("QLabel { color: green; }")
        self.download_button.setEnabled(True)

        # Load the layer into QGIS
        layer_name = os.path.splitext(os.path.basename(gpkg_path))[0]
        layer = QgsVectorLayer(gpkg_path, layer_name, "ogr")

        if layer.isValid():
            QgsProject.instance().addMapLayer(layer)
            log_message(f"Loaded OSM layer: {layer_name}", tag="Geest", level=Qgis.Info)
            self.download_completed.emit(gpkg_path)
        else:
            self.show_error("Failed to load downloaded layer")

    def on_download_error(self, error_message: str):
        """Handle download errors."""
        self.progress_bar.setVisible(False)
        self.download_button.setEnabled(True)
        self.show_error(f"Download failed: {error_message}")

    def show_error(self, message: str):
        """Display an error message."""
        self.status_label.setText(message)
        self.status_label.setStyleSheet("QLabel { color: red; }")
        self.status_label.setVisible(True)
        log_message(message, tag="Geest", level=Qgis.Warning)

    def cleanup(self):
        """Clean up resources."""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
