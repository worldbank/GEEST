# -*- coding: utf-8 -*-
"""Environmental Hazards raster datasource widget with an in-app download button."""

import os

from qgis.core import Qgis, QgsApplication, QgsCoordinateReferenceSystem, QgsVectorLayer
from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QLabel, QMessageBox, QSizePolicy

from geest.core.constants import (
    ENV_HAZARD_DOWNLOAD_SIZE_MB,
    ENV_HAZARD_SOURCE_LABELS,
    ENV_HAZARD_SOURCE_URLS,
)
from geest.core.tasks import EnvHazardDownloaderTask
from geest.utilities import log_message

from .download_task_controls import DownloadTaskControls
from .raster_datasource_widget import RasterDataSourceWidget

# Source files above this size get a confirmation prompt before downloading
# (the drought hazard raster is ~1 GB, far larger than the others).
LARGE_DOWNLOAD_WARNING_THRESHOLD_MB = 100


class EnvironmentalHazardsRasterDataSourceWidget(RasterDataSourceWidget):
    """Datasource widget for environmental hazard layers at national/local scale.

    Behaves like the generic raster datasource widget but also exposes a
    button to fetch the World Bank Data Catalog source raster directly for
    the selected hazard, cropped to the study area, following the same
    button/QgsTask pattern used by the nighttime lights downloader.
    """

    def add_internal_widgets(self) -> None:
        """Build raster controls and append the hazard download controls."""
        super().add_internal_widgets()
        hazard_id = self._hazard_id()
        label = ENV_HAZARD_SOURCE_LABELS.get(hazard_id, hazard_id)

        self.hazard_task = None
        self.hazard_controls = DownloadTaskControls(
            button_text=f"Download {label}",
            tooltip=f"Download the {label} raster from the World Bank Data Catalog for the study area",
            click_handler=self.fetch_hazard_raster,
        )
        self.layout.addWidget(self.hazard_controls.container)

        self.hazard_status_label = QLabel()
        self.hazard_status_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.hazard_status_label.setMinimumWidth(90)
        self.hazard_status_label.setMaximumWidth(170)
        self.layout.addWidget(self.hazard_status_label)

        self._add_source_link(
            ENV_HAZARD_SOURCE_URLS.get(hazard_id, ""),
            label,
        )

    def _hazard_id(self) -> str:
        """Return the lowercased indicator id for this hazard."""
        return str(self.attributes.get("id", "")).lower()

    def fetch_hazard_raster(self) -> None:
        """Download the World Bank Data Catalog hazard raster cropped to the study area."""
        hazard_id = self._hazard_id()
        label = ENV_HAZARD_SOURCE_LABELS.get(hazard_id, hazard_id)
        size_mb = ENV_HAZARD_DOWNLOAD_SIZE_MB.get(hazard_id)

        if size_mb and size_mb >= LARGE_DOWNLOAD_WARNING_THRESHOLD_MB:
            confirmed = QMessageBox.question(
                self,
                "Large Download",
                f"The {label} source raster is approximately {size_mb} MB. "
                "This may take a while depending on your connection. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirmed != QMessageBox.StandardButton.Yes:
                return

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

        self.hazard_controls.set_running()
        self._set_hazard_status(f"Fetching {label} data...")

        self.hazard_task = EnvHazardDownloaderTask(
            hazard_id=hazard_id,
            extent=extent,
            extent_crs_authid=crs.authid(),
            working_dir=working_directory,
            filename=f"{hazard_id}_hazard",
        )
        self.hazard_task.progress_updated.connect(self._on_hazard_progress)
        self.hazard_task.error_occurred.connect(self._on_hazard_error)
        self.hazard_task.taskCompleted.connect(self._on_hazard_completed)
        self.hazard_task.taskTerminated.connect(self._on_hazard_terminated)
        QgsApplication.taskManager().addTask(self.hazard_task)

    def _on_hazard_progress(self, message: str) -> None:
        """Update hazard status text from task progress."""
        self._set_hazard_status(message)
        self.hazard_controls.update_progress(message)

    def _on_hazard_error(self, message: str) -> None:
        """Handle hazard download task errors."""
        self._set_hazard_status("Hazard download failed")
        self.hazard_controls.set_download_failed(message)
        QMessageBox.warning(self, "Hazard Download Failed", message)

    def _on_hazard_terminated(self) -> None:
        """Handle cancelled/terminated hazard download tasks."""
        self._set_hazard_status("Hazard download terminated")
        self.hazard_controls.set_cancelled()

    def _on_hazard_completed(self) -> None:
        """Load the downloaded raster after a successful hazard download task."""
        output_path = self.hazard_task.output_path
        if not os.path.exists(output_path):
            self._set_hazard_status("Hazard output not found")
            self.hazard_controls.set_not_found(output_path)
            return

        self.raster_layer_combo.setVisible(False)
        self.raster_line_edit.setVisible(True)
        self.raster_line_edit.setText(output_path)
        self.resizeEvent(None)

        self._set_hazard_status("Hazard raster downloaded")
        self.hazard_controls.set_downloaded()
        self.update_attributes()
        log_message(f"Hazard raster loaded from {output_path}", level=Qgis.Info)

    def _set_hazard_status(self, message: str) -> None:
        """Set status label text when available."""
        if hasattr(self, "hazard_status_label") and self.hazard_status_label is not None:
            self.hazard_status_label.setText(message)
