# -*- coding: utf-8 -*-
"""Nighttime lights raster datasource widget with an in-app download button."""

import os

from qgis.core import Qgis, QgsApplication, QgsCoordinateReferenceSystem, QgsVectorLayer
from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QLabel, QMessageBox, QSizePolicy

from geest.core.constants import NTL_VNL_DATASET_PAGE_URL, NTL_VNL_SOURCE_LABEL
from geest.core.tasks import NTLDownloaderTask
from geest.utilities import log_message

from .download_task_controls import DownloadTaskControls
from .raster_datasource_widget import RasterDataSourceWidget


class NTLDownloadRasterDataSourceWidget(RasterDataSourceWidget):
    """Raster datasource widget for national/local nighttime lights with a download button.

    Fetches the latest annual VIIRS nighttime lights composite (OpenGeoHub
    mirror, no login required) cropped to the study area, following the
    same button/QgsTask pattern used by the S2S downloaders.
    """

    def add_internal_widgets(self) -> None:
        """Build raster controls and append the nighttime lights download controls."""
        super().add_internal_widgets()

        self.ntl_controls = DownloadTaskControls(
            button_text="Download Nighttime Lights",
            tooltip="Download the latest annual VIIRS nighttime lights composite for the study area",
            click_handler=self.fetch_nighttime_lights,
        )
        self.layout.addWidget(self.ntl_controls.container)

        self.ntl_status_label = QLabel()
        self.ntl_status_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.ntl_status_label.setMinimumWidth(90)
        self.ntl_status_label.setMaximumWidth(170)
        self.layout.addWidget(self.ntl_status_label)

        self._add_source_link(NTL_VNL_DATASET_PAGE_URL, NTL_VNL_SOURCE_LABEL)

        self.ntl_task = None

    def fetch_nighttime_lights(self) -> None:
        """Download the latest nighttime lights composite cropped to the study area."""
        settings = QSettings()
        working_directory = settings.value("last_working_directory", "")
        if not working_directory or not os.path.exists(working_directory):
            QMessageBox.warning(
                self,
                "No Working Directory",
                "No valid working directory found. Please create or open a project first.",
            )
            return

        study_area_gpkg = os.path.join(working_directory, "study_area", "study_area.gpkg")
        if not os.path.exists(study_area_gpkg):
            QMessageBox.warning(
                self,
                "Study Area Required",
                "Study area GeoPackage not found. Please create a project first.",
            )
            return

        bbox_layer = QgsVectorLayer(f"{study_area_gpkg}|layername=study_area_bboxes", "study_area_bboxes", "ogr")
        if not bbox_layer.isValid() or bbox_layer.featureCount() == 0:
            QMessageBox.warning(
                self,
                "Invalid Study Area",
                "Could not load study_area_bboxes from study_area.gpkg.",
            )
            return

        extent = bbox_layer.extent()
        crs: QgsCoordinateReferenceSystem = bbox_layer.crs()

        self.ntl_controls.set_running()
        self._set_ntl_status("Fetching nighttime lights data...")

        self.ntl_task = NTLDownloaderTask(
            extent=extent,
            extent_crs_authid=crs.authid(),
            working_dir=working_directory,
            filename="nighttime_lights_annual",
        )
        self.ntl_task.progress_updated.connect(self._on_ntl_progress)
        self.ntl_task.error_occurred.connect(self._on_ntl_error)
        self.ntl_task.taskCompleted.connect(self._on_ntl_completed)
        self.ntl_task.taskTerminated.connect(self._on_ntl_terminated)
        QgsApplication.taskManager().addTask(self.ntl_task)

    def _on_ntl_progress(self, message: str) -> None:
        """Update nighttime lights status text from task progress."""
        self._set_ntl_status(message)
        self.ntl_controls.update_progress(message)

    def _on_ntl_error(self, message: str) -> None:
        """Handle nighttime lights task errors."""
        self._set_ntl_status("Nighttime lights download failed")
        self.ntl_controls.set_download_failed(message)
        QMessageBox.warning(self, "Nighttime Lights Download Failed", message)

    def _on_ntl_terminated(self) -> None:
        """Handle cancelled/terminated nighttime lights tasks."""
        self._set_ntl_status("Nighttime lights task terminated")
        self.ntl_controls.set_cancelled()

    def _on_ntl_completed(self) -> None:
        """Load the downloaded raster after a successful nighttime lights task."""
        output_path = self.ntl_task.output_path
        if not os.path.exists(output_path):
            self._set_ntl_status("Nighttime lights output not found")
            self.ntl_controls.set_not_found(output_path)
            return

        self.raster_layer_combo.setVisible(False)
        self.raster_line_edit.setVisible(True)
        self.raster_line_edit.setText(output_path)
        self.resizeEvent(None)

        self._set_ntl_status("Nighttime lights downloaded")
        self.ntl_controls.set_downloaded()
        self.update_attributes()
        log_message(f"Nighttime lights raster loaded from {output_path}", level=Qgis.Info)

    def _set_ntl_status(self, message: str) -> None:
        """Set status label text when available."""
        if hasattr(self, "ntl_status_label") and self.ntl_status_label is not None:
            self.ntl_status_label.setText(message)
