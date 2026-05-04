# -*- coding: utf-8 -*-
"""Space2Stats prefetch panel."""

import json
import os
from typing import Dict, List

from qgis.core import (
    QgsApplication,
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsGeometry,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtWidgets import QMessageBox, QWidget

from geest.core.constants import DEFAULT_S2S_ENV_HAZARD_FIELDS, DEFAULT_S2S_NTL_FIELD
from geest.core.tasks import S2SDownloaderTask
from geest.gui.widgets import CustomBannerLabel
from geest.utilities import get_ui_class, linear_interpolation, log_message, resources_path

FORM_CLASS = get_ui_class("s2s_panel_base.ui")


class S2SPanel(FORM_CLASS, QWidget):
    """Panel that optionally prefetches S2S datasets after project creation."""

    switch_to_next_tab = pyqtSignal()
    switch_to_previous_tab = pyqtSignal()

    def __init__(self):
        """Initialize panel and UI."""
        super().__init__()
        self.setWindowTitle("GeoE3")
        self.working_dir = ""
        self._s2s_prefetch_jobs: List[Dict] = []
        self._s2s_prefetch_index = 0
        self._s2s_prefetch_warnings: List[str] = []
        self._s2s_prefetch_updates: List[Dict] = []
        self._s2s_prefetch_task = None
        self._s2s_prefetch_error_for_current_task = False

        self.setupUi(self)
        log_message("Loading S2S panel")
        self.init_ui()
        self.set_font_size()

    def init_ui(self) -> None:
        """Initialize controls and signals."""
        self.custom_label = CustomBannerLabel(
            "The Geospatial Enabling Environments for Employment Spatial Tool",
            resources_path("resources", "geoe3-banner.png"),
        )
        parent_layout = self.banner_label.parent().layout()
        parent_layout.replaceWidget(self.banner_label, self.custom_label)
        self.banner_label.deleteLater()
        parent_layout.update()

        self.previous_button.clicked.connect(self.on_previous_button_clicked)
        self.next_button.clicked.connect(self.on_next_button_clicked)

        self.progress_bar.setVisible(False)
        self.processing_info_label.setVisible(False)
        self.processing_info_label.setText("")

    def set_working_directory(self, working_dir: str) -> None:
        """Set working directory and restore checkbox state from model."""
        self.working_dir = working_dir or ""
        self._load_prefetch_state_from_model()

    def _load_prefetch_state_from_model(self) -> None:
        """Load persisted prefetch checkbox value from model.json."""
        model = self._read_model()
        self.prefetch_s2s_checkbox.setChecked(bool(model.get("s2s_prefetch_enabled", False)))

    def _read_model(self) -> dict:
        """Read model.json for current project."""
        if not self.working_dir:
            return {}
        model_path = os.path.join(self.working_dir, "model.json")
        if not os.path.exists(model_path):
            return {}
        try:
            with open(model_path, "r", encoding="utf-8") as model_file:
                return json.load(model_file)
        except Exception as error:
            log_message(f"Failed to read model.json in S2S panel: {error}", tag="GeoE3", level=Qgis.Warning)
            return {}

    def _write_model(self, model: dict) -> bool:
        """Write model.json for current project."""
        if not self.working_dir:
            return False
        model_path = os.path.join(self.working_dir, "model.json")
        try:
            with open(model_path, "w", encoding="utf-8") as model_file:
                json.dump(model, model_file, indent=2)
            return True
        except Exception as error:
            QMessageBox.warning(self, "S2S Fetch", f"Could not save model.json: {error}")
            return False

    def on_previous_button_clicked(self) -> None:
        """Return to project creation panel."""
        self.switch_to_previous_tab.emit()

    def on_next_button_clicked(self) -> None:
        """Run optional S2S prefetch and continue to ORS panel."""
        model = self._read_model()
        if not model:
            self.switch_to_next_tab.emit()
            return

        model["s2s_prefetch_enabled"] = self.prefetch_s2s_checkbox.isChecked()
        if not self._write_model(model):
            return

        if not self.prefetch_s2s_checkbox.isChecked():
            self.switch_to_next_tab.emit()
            return

        if model.get("analysis_scale") != "regional":
            self.switch_to_next_tab.emit()
            return

        if not self._start_s2s_prefetch(model):
            self.switch_to_next_tab.emit()

    def _start_s2s_prefetch(self, model: dict) -> bool:
        """Start S2S prefetch for regional projects."""
        study_area_gpkg = os.path.join(self.working_dir, "study_area", "study_area.gpkg")
        if not os.path.exists(study_area_gpkg):
            log_message("S2S prefetch skipped: study area geopackage missing.", tag="GeoE3", level=Qgis.Warning)
            return False

        aoi_layer = QgsVectorLayer(f"{study_area_gpkg}|layername=study_area_bboxes", "study_area_bboxes", "ogr")
        if not aoi_layer.isValid() or aoi_layer.featureCount() == 0:
            log_message("S2S prefetch skipped: study_area_bboxes unavailable.", tag="GeoE3", level=Qgis.Warning)
            return False

        aoi_feature = self._build_aoi_feature(aoi_layer)
        if not aoi_feature:
            log_message("S2S prefetch skipped: failed to build AOI feature.", tag="GeoE3", level=Qgis.Warning)
            return False

        jobs, warnings = self._prepare_s2s_prefetch_jobs(model)
        self._s2s_prefetch_warnings = warnings
        if not jobs:
            if warnings:
                QMessageBox.information(self, "S2S Fetch", "\n".join(warnings))
            return False

        self._s2s_prefetch_jobs = jobs
        self._s2s_prefetch_updates = []
        self._s2s_prefetch_index = 0
        self.processing_info_label.setText("Fetching S2S data for regional indicators...")
        self.processing_info_label.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)

        self.previous_button.setEnabled(False)
        self.next_button.setEnabled(False)
        self.prefetch_s2s_checkbox.setEnabled(False)

        self._run_next_s2s_prefetch_job(aoi_feature)
        return True

    def _prepare_s2s_prefetch_jobs(self, model: dict) -> tuple[list, list]:
        """Build a list of S2S prefetch jobs and non-blocking warnings."""
        jobs: List[Dict] = []
        warnings: List[str] = []

        ntl_indicators: List[str] = []
        ntl_field = DEFAULT_S2S_NTL_FIELD

        for dimension in model.get("dimensions", []):
            for factor in dimension.get("factors", []):
                for indicator in factor.get("indicators", []):
                    indicator_id = str(indicator.get("id", "")).strip()
                    if not indicator_id:
                        continue

                    if int(indicator.get("use_nighttime_lights", 0)) == 1:
                        ntl_indicators.append(indicator_id)
                        indicator_field = str(indicator.get("s2s_ntl_field") or "").strip()
                        if indicator_field:
                            ntl_field = indicator_field

                    if int(indicator.get("use_environmental_hazards", 0)) == 1:
                        hazard_id = indicator_id.lower()
                        hazard_field = str(indicator.get("s2s_hazard_field") or "").strip()
                        if not hazard_field:
                            hazard_field = DEFAULT_S2S_ENV_HAZARD_FIELDS.get(hazard_id, "")
                        if not hazard_field:
                            warnings.append(f"Skipped {indicator_id}: no S2S hazard field configured.")
                            continue
                        jobs.append(
                            {
                                "type": "hazard",
                                "indicator_ids": [indicator_id],
                                "fields": [hazard_field],
                                "filename": f"s2s_environmental_hazards_{hazard_id}",
                                "metadata": {"s2s_hazard_field": hazard_field, "s2s_ntl_field": ""},
                            }
                        )

                    if int(indicator.get("use_polygon_per_cell", 0)) == 1:
                        fields = indicator.get("s2s_fields", [])
                        if isinstance(fields, str):
                            fields = [token.strip() for token in fields.split(",") if token.strip()]
                        elif isinstance(fields, list):
                            fields = [str(token).strip() for token in fields if str(token).strip()]
                        else:
                            fields = []

                        unique_fields = []
                        for field in fields:
                            if field not in unique_fields:
                                unique_fields.append(field)

                        if not unique_fields:
                            warnings.append(f"Skipped {indicator_id}: no s2s_fields configured.")
                            continue

                        sanitized_id = indicator_id.lower().replace(" ", "_").replace("-", "_")
                        jobs.append(
                            {
                                "type": "polygon_per_cell",
                                "indicator_ids": [indicator_id],
                                "fields": unique_fields,
                                "filename": f"s2s_polygon_per_cell_{sanitized_id}",
                                "metadata": {
                                    "s2s_fields": unique_fields,
                                    "s2s_fields_text": ",".join(unique_fields),
                                },
                            }
                        )

        if ntl_indicators:
            jobs.insert(
                0,
                {
                    "type": "nighttime_lights",
                    "indicator_ids": ntl_indicators,
                    "fields": [ntl_field],
                    "filename": "s2s_nighttime_lights",
                    "metadata": {"s2s_ntl_field": ntl_field},
                },
            )

        return jobs, warnings

    def _run_next_s2s_prefetch_job(self, aoi_feature: dict) -> None:
        """Run next queued S2S prefetch job."""
        if self._s2s_prefetch_index >= len(self._s2s_prefetch_jobs):
            self._finalize_s2s_prefetch()
            return

        job = self._s2s_prefetch_jobs[self._s2s_prefetch_index]
        job_index = self._s2s_prefetch_index + 1
        total = len(self._s2s_prefetch_jobs)
        self.processing_info_label.setText(f"Fetching S2S dataset {job_index}/{total}: {job['filename']}")
        self.progress_bar.setFormat(f"S2S {job_index}/{total}: %p%")

        self._s2s_prefetch_task = S2SDownloaderTask(
            aoi=aoi_feature,
            fields=job["fields"],
            working_dir=self.working_dir,
            filename=job["filename"],
            spatial_join_method="centroid",
            geometry="point",
            delete_existing=True,
        )
        self._s2s_prefetch_task.progress_updated.connect(self._on_s2s_prefetch_progress_message)
        self._s2s_prefetch_task.progressChanged.connect(self._on_s2s_prefetch_progress_value)
        self._s2s_prefetch_task.error_occurred.connect(self._on_s2s_prefetch_error)
        self._s2s_prefetch_error_for_current_task = False
        self._s2s_prefetch_task.taskCompleted.connect(
            lambda aoi=aoi_feature, current_job=job: self._on_s2s_prefetch_task_completed(current_job, aoi)
        )
        self._s2s_prefetch_task.taskTerminated.connect(
            lambda aoi=aoi_feature, current_job=job: self._on_s2s_prefetch_task_terminated(current_job, aoi)
        )
        QgsApplication.taskManager().addTask(self._s2s_prefetch_task)

    def _on_s2s_prefetch_progress_message(self, message: str) -> None:
        """Update status label with S2S task progress text."""
        self.processing_info_label.setText(message)

    def _on_s2s_prefetch_progress_value(self, progress: float) -> None:
        """Update progress bar from S2S task progress."""
        self.progress_bar.setValue(int(progress))

    def _on_s2s_prefetch_error(self, message: str) -> None:
        """Record non-blocking S2S prefetch errors."""
        self._s2s_prefetch_error_for_current_task = True
        self._s2s_prefetch_warnings.append(message)

    def _on_s2s_prefetch_task_completed(self, job: dict, aoi_feature: dict) -> None:
        """Handle successful S2S prefetch task and run next."""
        output_path = os.path.join(self.working_dir, "study_area", f"{job['filename']}.gpkg")
        if os.path.exists(output_path):
            self._s2s_prefetch_updates.append(
                {
                    "indicator_ids": job["indicator_ids"],
                    "output_path": output_path,
                    "metadata": job["metadata"],
                }
            )
        else:
            self._s2s_prefetch_warnings.append(f"S2S output not found for {job['filename']}.")

        self._s2s_prefetch_index += 1
        self._run_next_s2s_prefetch_job(aoi_feature)

    def _on_s2s_prefetch_task_terminated(self, job: dict, aoi_feature: dict) -> None:
        """Handle terminated S2S prefetch tasks and continue queue."""
        if not self._s2s_prefetch_error_for_current_task:
            self._s2s_prefetch_warnings.append(f"S2S prefetch task terminated: {job['filename']}")
        self._s2s_prefetch_index += 1
        self._run_next_s2s_prefetch_job(aoi_feature)

    def _finalize_s2s_prefetch(self) -> None:
        """Write S2S prefetch metadata into model and continue flow."""
        model = self._read_model()
        if model:
            try:
                self._apply_s2s_updates_to_model(model, self._s2s_prefetch_updates)
                self._write_model(model)
            except Exception as error:
                self._s2s_prefetch_warnings.append(f"Failed to store S2S prefetch metadata: {error}")

        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("S2S fetch complete")
        self.processing_info_label.setText("S2S fetch completed.")

        if self._s2s_prefetch_warnings:
            QMessageBox.information(self, "S2S Fetch", "\n".join(self._s2s_prefetch_warnings))

        self.previous_button.setEnabled(True)
        self.next_button.setEnabled(True)
        self.prefetch_s2s_checkbox.setEnabled(True)
        self.switch_to_next_tab.emit()

    @staticmethod
    def _apply_s2s_updates_to_model(model: dict, updates: List[Dict]) -> None:
        """Persist S2S output metadata into matching indicator attributes."""
        updates_by_indicator: Dict[str, List[Dict]] = {}
        for update in updates:
            for indicator_id in update.get("indicator_ids", []):
                updates_by_indicator.setdefault(indicator_id, []).append(update)

        for dimension in model.get("dimensions", []):
            for factor in dimension.get("factors", []):
                for indicator in factor.get("indicators", []):
                    indicator_id = indicator.get("id")
                    if indicator_id not in updates_by_indicator:
                        continue
                    for update in updates_by_indicator[indicator_id]:
                        indicator["s2s_output_path"] = update["output_path"]
                        indicator["s2s_spatial_join_method"] = "centroid"
                        for key, value in update.get("metadata", {}).items():
                            indicator[key] = value

    @staticmethod
    def _build_aoi_feature(layer: QgsVectorLayer) -> dict:
        """Build a WGS84 GeoJSON AOI feature from a vector layer."""
        geometries = []
        source_crs = layer.crs()
        target_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = None
        if source_crs.isValid() and source_crs != target_crs:
            transform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())

        for feature in layer.getFeatures():
            geometry = feature.geometry()
            if not geometry or geometry.isEmpty():
                continue
            transformed_geometry = QgsGeometry(geometry)
            if transform is not None:
                transformed_geometry.transform(transform)
            geometries.append(transformed_geometry)

        if not geometries:
            return {}

        union_geometry = QgsGeometry.unaryUnion(geometries)
        if not union_geometry or union_geometry.isEmpty():
            return {}

        return {
            "type": "Feature",
            "geometry": json.loads(union_geometry.asJson()),
            "properties": {},
        }

    def resizeEvent(self, event):
        """Handle resize events for adaptive font sizing."""
        self.set_font_size()
        super().resizeEvent(event)

    def set_font_size(self):
        """Set responsive font sizes for labels and controls."""
        font_size = int(linear_interpolation(self.description.rect().width(), 12, 16, 400, 600))
        font = QFont("Arial", font_size)

        self.description.setFont(font)
        self.prefetch_s2s_checkbox.setFont(font)
        self.prefetch_s2s_description.setFont(font)
        self.processing_info_label.setFont(font)
        self.progress_bar.setFont(QFont("Arial", 9))
