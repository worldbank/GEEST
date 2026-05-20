# -*- coding: utf-8 -*-
"""Space2Stats prefetch panel."""

import json
import os
from datetime import datetime
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
from qgis.PyQt.QtCore import QTimer, pyqtSignal
from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtWidgets import QMessageBox, QWidget

from geest.core.constants import (
    DEFAULT_S2S_EDUCATION_URBANIZATION_FIELDS,
    DEFAULT_S2S_ENV_HAZARD_FIELDS,
    DEFAULT_S2S_NTL_FIELD,
)
from geest.core.s2s_task_gate import S2STaskGate
from geest.core.tasks import S2SDownloaderTask
from geest.gui.widgets import CustomBannerLabel
from geest.utilities import get_ui_class, linear_interpolation, log_message, resources_path

FORM_CLASS = get_ui_class("s2s_panel_base.ui")


class S2SPanel(FORM_CLASS, QWidget):
    """Panel that optionally prefetches S2S datasets after project creation."""

    switch_to_next_tab = pyqtSignal()
    switch_to_previous_tab = pyqtSignal()
    PREFETCH_MAX_ATTEMPTS = 4
    PREFETCH_INTER_JOB_DELAY_MS = 750
    PREFETCH_CHUNK_SIZE = 3000
    PREFETCH_CHUNK_THRESHOLD = 50000

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
        self._s2s_prefetch_last_error_message = ""
        self._s2s_prefetch_hex_ids: List[str] = []
        self._s2s_gate_token = None
        self._s2s_prefetch_warning_keys = set()
        self._s2s_prefetch_retry_timer_pending = False

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

        self._s2s_prefetch_hex_ids = self._load_study_area_h3_indexes()

        jobs, warnings = self._prepare_s2s_prefetch_jobs(model)
        self._s2s_prefetch_warnings = warnings
        self._s2s_prefetch_updates = []
        self._s2s_prefetch_warning_keys = set()
        self._s2s_prefetch_retry_timer_pending = False

        completed_jobs = set(self._load_prefetch_completed_jobs(model))
        pending_jobs: List[Dict] = []
        resumed_count = 0

        for job in jobs:
            job_with_mode = self._job_with_fetch_mode(job, model)
            existing_output = self._existing_s2s_output_path(job_with_mode)
            if self._is_existing_s2s_output_valid(
                existing_output,
                job_with_mode.get("fields", []),
                job_with_mode.get("filename", ""),
            ):
                self._s2s_prefetch_updates.append(
                    {
                        "indicator_ids": job_with_mode["indicator_ids"],
                        "output_path": existing_output,
                        "metadata": job_with_mode["metadata"],
                    }
                )
                completed_jobs.add(job_with_mode["filename"])
                self._clear_prefetch_job_state(job_with_mode["filename"], model=model)
                resumed_count += 1
                continue

            if job_with_mode["filename"] in completed_jobs:
                completed_jobs.remove(job_with_mode["filename"])

            job_with_mode["attempt"] = 1
            pending_jobs.append(job_with_mode)

        self._store_prefetch_completed_jobs(model, completed_jobs)
        self._write_model(model)

        if resumed_count:
            self._append_prefetch_warning(f"Resuming prefetch: {resumed_count} datasets already available.")

        if not jobs:
            if warnings:
                QMessageBox.information(self, "S2S Fetch", "\n".join(warnings))
            return False

        if not pending_jobs:
            self.processing_info_label.setText("All S2S datasets already available.")
            self.processing_info_label.setVisible(True)
            self.progress_bar.setVisible(True)
            self.progress_bar.setMinimum(0)
            self.progress_bar.setMaximum(100)
            self.progress_bar.setValue(100)
            self._finalize_s2s_prefetch()
            return True

        self._s2s_prefetch_jobs = pending_jobs
        self._s2s_prefetch_index = 0
        self._s2s_prefetch_task = None
        self.processing_info_label.setText("Fetching S2S data for regional indicators...")
        self.processing_info_label.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)

        self.previous_button.setEnabled(False)
        self.next_button.setEnabled(False)
        self.prefetch_s2s_checkbox.setEnabled(False)

        self._schedule_next_s2s_prefetch_job(aoi_feature, 0)
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
                        if hazard_field == DEFAULT_S2S_NTL_FIELD:
                            hazard_field = ""
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

                        if not fields and indicator_id.lower() == "education":
                            fields = list(DEFAULT_S2S_EDUCATION_URBANIZATION_FIELDS)

                        unique_fields = []
                        for field in fields:
                            if field not in unique_fields:
                                unique_fields.append(field)

                        if not unique_fields:
                            warnings.append(f"Skipped {indicator_id}: no s2s_fields configured.")
                            continue

                        sanitized_id = indicator_id.lower().replace(" ", "_").replace("-", "_")
                        filename = f"s2s_polygon_per_cell_{sanitized_id}"
                        if indicator_id.lower() == "education":
                            filename = "s2s_education"
                        jobs.append(
                            {
                                "type": "polygon_per_cell",
                                "indicator_ids": [indicator_id],
                                "fields": unique_fields,
                                "filename": filename,
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
        mode_text = " (chunked)" if job.get("fetch_mode") == "hex_ids" else ""
        self.processing_info_label.setText(f"Fetching S2S dataset {job_index}/{total}: {job['filename']}{mode_text}")
        self.progress_bar.setFormat(f"S2S {job_index}/{total}: %p%")

        self._s2s_prefetch_task = S2SDownloaderTask(
            aoi=aoi_feature,
            fields=job["fields"],
            working_dir=self.working_dir,
            filename=job["filename"],
            spatial_join_method="centroid",
            geometry="point",
            delete_existing=True,
            mode=job.get("fetch_mode", "aoi"),
            hex_ids=job.get("hex_ids"),
            chunk_size=job.get("chunk_size", self.PREFETCH_CHUNK_SIZE),
            start_chunk_index=job.get("start_chunk_index", 0),
            append_existing=bool(job.get("start_chunk_index", 0) > 0),
        )
        self._s2s_prefetch_task.progress_updated.connect(self._on_s2s_prefetch_progress_message)
        self._s2s_prefetch_task.progressChanged.connect(self._on_s2s_prefetch_progress_value)
        self._s2s_prefetch_task.error_occurred.connect(self._on_s2s_prefetch_error)
        if job.get("fetch_mode") == "hex_ids":
            self._s2s_prefetch_task.chunk_completed.connect(
                lambda current_chunk, total_chunks, current_job=job: self._on_s2s_prefetch_chunk_completed(
                    current_job,
                    current_chunk,
                    total_chunks,
                )
            )
        self._s2s_prefetch_error_for_current_task = False
        self._s2s_prefetch_last_error_message = ""
        self._s2s_prefetch_task.taskCompleted.connect(
            lambda aoi=aoi_feature, current_job=job: self._on_s2s_prefetch_task_completed(current_job, aoi)
        )
        self._s2s_prefetch_task.taskTerminated.connect(
            lambda aoi=aoi_feature, current_job=job: self._on_s2s_prefetch_task_terminated(current_job, aoi)
        )

        gate_label = f"prefetch:{job.get('filename', '')}"
        token = S2STaskGate.acquire(gate_label)
        if not token:
            active = S2STaskGate.active_label() or "another panel"
            if active == gate_label:
                self.processing_info_label.setText(f"S2S prefetch already running for {job.get('filename', '')}.")
            else:
                self.processing_info_label.setText(f"S2S prefetch waiting: another S2S download is running ({active}).")
            self._schedule_next_s2s_prefetch_job(aoi_feature, 3000)
            return
        self._s2s_gate_token = token

        QgsApplication.taskManager().addTask(self._s2s_prefetch_task)

    def _on_s2s_prefetch_progress_message(self, message: str) -> None:
        """Update status label with S2S task progress text."""
        self.processing_info_label.setText(message)

    def _on_s2s_prefetch_progress_value(self, progress: float) -> None:
        """Update progress bar from S2S task progress."""
        self.progress_bar.setValue(int(progress))

    def _on_s2s_prefetch_chunk_completed(self, job: dict, current_chunk: int, total_chunks: int) -> None:
        """Persist chunk progress for resumable chunked prefetch jobs."""
        model = self._read_model()
        if not model:
            return

        state = {
            "mode": "hex_ids",
            "total_chunks": int(total_chunks),
            "next_chunk_index": int(current_chunk),
            "chunk_size": int(job.get("chunk_size", self.PREFETCH_CHUNK_SIZE)),
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
        self._store_prefetch_job_state(model, job.get("filename", ""), state)
        self._write_model(model)

    def _on_s2s_prefetch_error(self, message: str) -> None:
        """Record non-blocking S2S prefetch errors."""
        self._s2s_prefetch_error_for_current_task = True
        self._s2s_prefetch_last_error_message = message

    def _on_s2s_prefetch_task_completed(self, job: dict, aoi_feature: dict) -> None:
        """Handle successful S2S prefetch task and run next."""
        self._release_s2s_gate()
        output_path = os.path.join(self.working_dir, "study_area", f"{job['filename']}.gpkg")
        if os.path.exists(output_path):
            self._s2s_prefetch_updates.append(
                {
                    "indicator_ids": job["indicator_ids"],
                    "output_path": output_path,
                    "metadata": job["metadata"],
                }
            )
            self._mark_prefetch_job_completed(job["filename"])
            self._clear_prefetch_job_state(job["filename"])
        else:
            self._append_prefetch_warning(f"S2S output not found for {job['filename']}.")

        self._s2s_prefetch_index += 1
        self._schedule_next_s2s_prefetch_job(aoi_feature, self.PREFETCH_INTER_JOB_DELAY_MS)

    def _on_s2s_prefetch_task_terminated(self, job: dict, aoi_feature: dict) -> None:
        """Handle terminated S2S prefetch tasks and continue queue."""
        self._release_s2s_gate()
        if self._s2s_prefetch_error_for_current_task and self._is_transient_prefetch_error(
            self._s2s_prefetch_last_error_message
        ):
            attempt = int(job.get("attempt", 1))
            if attempt < self.PREFETCH_MAX_ATTEMPTS:
                next_attempt = attempt + 1
                delay_ms = self._retry_delay_ms(next_attempt)
                job["attempt"] = next_attempt
                self.processing_info_label.setText(
                    f"S2S unavailable for {job['filename']} - retrying "
                    f"{next_attempt}/{self.PREFETCH_MAX_ATTEMPTS} in {delay_ms / 1000:.1f}s..."
                )
                self._schedule_next_s2s_prefetch_job(aoi_feature, delay_ms)
                return

        if self._s2s_prefetch_error_for_current_task:
            self._append_prefetch_warning(
                self._s2s_prefetch_last_error_message or f"S2S prefetch failed: {job['filename']}"
            )
        else:
            self._append_prefetch_warning(f"S2S prefetch task terminated: {job['filename']}")

        self._s2s_prefetch_index += 1
        self._schedule_next_s2s_prefetch_job(aoi_feature, self.PREFETCH_INTER_JOB_DELAY_MS)

    def _schedule_next_s2s_prefetch_job(self, aoi_feature: dict, delay_ms: int) -> None:
        """Schedule next prefetch job with optional delay."""
        delay = max(0, int(delay_ms))
        if delay == 0:
            self._s2s_prefetch_retry_timer_pending = False
            self._run_next_s2s_prefetch_job(aoi_feature)
            return

        if self._s2s_prefetch_retry_timer_pending:
            return

        self._s2s_prefetch_retry_timer_pending = True

        def _run_delayed():
            self._s2s_prefetch_retry_timer_pending = False
            self._run_next_s2s_prefetch_job(aoi_feature)

        QTimer.singleShot(delay, _run_delayed)

    def _release_s2s_gate(self) -> None:
        """Release global S2S gate lock for panel prefetch task."""
        if self._s2s_gate_token:
            S2STaskGate.release(self._s2s_gate_token)
            self._s2s_gate_token = None

    def _append_prefetch_warning(self, message: str) -> None:
        """Append a warning once, preventing duplicate warning spam."""
        normalized = str(message or "").strip()
        if not normalized:
            return
        if normalized in self._s2s_prefetch_warning_keys:
            return
        self._s2s_prefetch_warning_keys.add(normalized)
        self._s2s_prefetch_warnings.append(normalized)

    def _existing_s2s_output_path(self, job: dict) -> str:
        """Return expected output path for a prefetch job."""
        return os.path.join(self.working_dir, "study_area", f"{job['filename']}.gpkg")

    @staticmethod
    def _is_existing_s2s_output_valid(output_path: str, fields: List[str], layer_name: str) -> bool:
        """Return True when an existing S2S output has required fields and features."""
        if not output_path or not os.path.exists(output_path):
            return False

        layer = QgsVectorLayer(f"{output_path}|layername={layer_name}", layer_name, "ogr")
        if not layer.isValid():
            layer = QgsVectorLayer(output_path, layer_name, "ogr")
        if not layer.isValid() or layer.featureCount() <= 0:
            return False

        required_fields = ["hex_id"] + [field for field in fields if field != "hex_id"]
        layer_fields = layer.fields()
        for field in required_fields:
            if layer_fields.indexFromName(field) == -1:
                return False
        return True

    @staticmethod
    def _is_transient_prefetch_error(message: str) -> bool:
        """Return True when a prefetch error should be retried."""
        lowered = str(message or "").lower()
        return (
            "503" in lowered
            or "temporarily unavailable" in lowered
            or "server error (502)" in lowered
            or "server error (504)" in lowered
            or "no http status code" in lowered
            or "timed out" in lowered
            or "timeout" in lowered
            or "connection" in lowered
        )

    @staticmethod
    def _retry_delay_ms(attempt: int) -> int:
        """Return exponential retry delay for a retry attempt number."""
        if attempt <= 2:
            return 2000
        if attempt == 3:
            return 5000
        return 10000

    @staticmethod
    def _load_prefetch_completed_jobs(model: dict) -> List[str]:
        """Read persisted completed prefetch job filenames from model."""
        completed = model.get("s2s_prefetch_completed_jobs", [])
        if not isinstance(completed, list):
            return []
        return [str(name).strip() for name in completed if str(name).strip()]

    @staticmethod
    def _store_prefetch_completed_jobs(model: dict, completed_jobs) -> None:
        """Persist completed prefetch job filenames in model."""
        sorted_names = sorted({str(name).strip() for name in completed_jobs if str(name).strip()})
        model["s2s_prefetch_completed_jobs"] = sorted_names

    @staticmethod
    def _load_prefetch_job_state(model: dict, filename: str) -> dict:
        """Read persisted prefetch state for a specific job filename."""
        if not filename:
            return {}
        state = model.get("s2s_prefetch_job_state", {})
        if not isinstance(state, dict):
            return {}
        job_state = state.get(filename, {})
        return job_state if isinstance(job_state, dict) else {}

    @staticmethod
    def _store_prefetch_job_state(model: dict, filename: str, state: dict) -> None:
        """Persist prefetch checkpoint state for a specific job."""
        if not filename:
            return
        all_state = model.get("s2s_prefetch_job_state", {})
        if not isinstance(all_state, dict):
            all_state = {}
        all_state[filename] = state
        model["s2s_prefetch_job_state"] = all_state

    def _clear_prefetch_job_state(self, filename: str, model: dict = None) -> None:
        """Clear persisted checkpoint state for a specific job."""
        if not filename:
            return

        model_in_use = model if model is not None else self._read_model()
        if not model_in_use:
            return

        all_state = model_in_use.get("s2s_prefetch_job_state", {})
        if not isinstance(all_state, dict) or filename not in all_state:
            return

        all_state.pop(filename, None)
        model_in_use["s2s_prefetch_job_state"] = all_state
        if model is None:
            self._write_model(model_in_use)

    def _load_study_area_h3_indexes(self) -> List[str]:
        """Load H3 indexes from study_area_grid for chunked prefetch mode."""
        gpkg_path = os.path.join(self.working_dir, "study_area", "study_area.gpkg")
        layer = QgsVectorLayer(f"{gpkg_path}|layername=study_area_grid", "study_area_grid", "ogr")
        if not layer.isValid() or layer.featureCount() == 0:
            return []

        field_index = layer.fields().indexFromName("h3_index")
        if field_index == -1:
            return []

        values = set()
        for feature in layer.getFeatures():
            hex_id = str(feature["h3_index"] or "").strip()
            if hex_id:
                values.add(hex_id)
        return sorted(values)

    def _job_with_fetch_mode(self, job: dict, model: dict) -> dict:
        """Return a prefetch job enriched with fetch mode and resume state."""
        enriched = dict(job)
        use_chunked = self._should_use_chunked_prefetch()

        if use_chunked:
            state = self._load_prefetch_job_state(model, enriched.get("filename", ""))
            start_chunk_index = int(state.get("next_chunk_index", 0)) if isinstance(state, dict) else 0
            enriched["fetch_mode"] = "hex_ids"
            enriched["hex_ids"] = list(self._s2s_prefetch_hex_ids)
            enriched["chunk_size"] = self.PREFETCH_CHUNK_SIZE
            enriched["start_chunk_index"] = max(0, start_chunk_index)
        else:
            enriched["fetch_mode"] = "aoi"
            enriched["start_chunk_index"] = 0

        return enriched

    def _should_use_chunked_prefetch(self) -> bool:
        """Return True when H3 coverage is large enough to use chunked S2S mode."""
        return len(self._s2s_prefetch_hex_ids) > self.PREFETCH_CHUNK_THRESHOLD

    def _mark_prefetch_job_completed(self, filename: str) -> None:
        """Mark a prefetch job as completed and persist to model."""
        model = self._read_model()
        if not model:
            return

        completed_jobs = set(self._load_prefetch_completed_jobs(model))
        completed_jobs.add(filename)
        self._store_prefetch_completed_jobs(model, completed_jobs)
        self._write_model(model)

    def _finalize_s2s_prefetch(self) -> None:
        """Write S2S prefetch metadata into model and continue flow."""
        model = self._read_model()
        if model:
            try:
                self._apply_s2s_updates_to_model(model, self._s2s_prefetch_updates)
                self._write_model(model)
            except Exception as error:
                self._append_prefetch_warning(f"Failed to store S2S prefetch metadata: {error}")

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
