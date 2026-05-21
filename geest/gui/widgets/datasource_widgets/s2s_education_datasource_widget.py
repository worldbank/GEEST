# -*- coding: utf-8 -*-
"""S2S-backed Education datasource widget."""

import os

from qgis.core import QgsApplication, QgsMapLayerProxyModel, QgsVectorLayer
from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QMessageBox

from geest.core import S2STaskGate
from geest.core.constants import DEFAULT_S2S_EDUCATION_URBANIZATION_FIELDS
from geest.core.tasks import S2SDownloaderTask

from .s2s_datasource_widget import S2SDataSourceWidget


class S2SEducationDataSourceWidget(S2SDataSourceWidget):
    """Education-specific S2S datasource widget with fixed field configuration."""

    OUTPUT_FILENAME = "s2s_education"

    def add_internal_widgets(self) -> None:
        """Build controls and hide manual S2S fields input for Education."""
        super().add_internal_widgets()
        if hasattr(self, "layer_combo"):
            self.layer_combo.setFilters(QgsMapLayerProxyModel.PointLayer | QgsMapLayerProxyModel.PolygonLayer)
        default_fields_text = ",".join(DEFAULT_S2S_EDUCATION_URBANIZATION_FIELDS)
        self.s2s_fields_line_edit.setText(default_fields_text)
        self.s2s_fields_line_edit.setEnabled(False)
        self.s2s_fields_line_edit.setVisible(False)

        settings = QSettings()
        working_directory = settings.value("last_working_directory", "")
        self._load_best_available_s2s_output(working_directory)

    def _load_best_available_s2s_output(self, working_directory: str) -> None:
        """Load configured output path or fallback to default Education output path."""
        configured_path = str(self.s2s_output_path or "").strip()
        candidate_paths = []
        if configured_path:
            candidate_paths.append(configured_path)

        fallback_path = self._resolve_default_s2s_output_path(working_directory)
        if fallback_path and fallback_path not in candidate_paths:
            candidate_paths.append(fallback_path)

        for candidate in candidate_paths:
            if not candidate or not os.path.exists(candidate):
                continue

            layer_name = os.path.splitext(os.path.basename(candidate))[0]
            output_layer = self._load_or_reuse_vector_layer(candidate, layer_name)
            if output_layer is None:
                continue

            self.s2s_output_path = candidate
            self._switch_to_layer_mode(output_layer)
            self.s2s_controls.set_downloaded()
            self.update_attributes()
            return

    @staticmethod
    def _resolve_default_s2s_output_path(working_directory: str) -> str:
        """Resolve the standard Education S2S output path."""
        if not working_directory:
            return ""
        return os.path.join(working_directory, "study_area", f"{S2SEducationDataSourceWidget.OUTPUT_FILENAME}.gpkg")

    def fetch_from_s2s(self) -> None:
        """Fetch Education S2S dataset using fixed output and field configuration."""
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

        aoi_layer = QgsVectorLayer(f"{study_area_gpkg}|layername=study_area_bboxes", "study_area_bboxes", "ogr")
        if not aoi_layer.isValid() or aoi_layer.featureCount() == 0:
            QMessageBox.warning(
                self,
                "Invalid Study Area",
                "Could not load study_area_bboxes from study_area.gpkg.",
            )
            return

        aoi_feature = self._build_aoi_feature(aoi_layer)
        if not aoi_feature:
            QMessageBox.warning(
                self,
                "Invalid AOI",
                "Failed to build AOI feature from study area geometry.",
            )
            return

        fields = list(DEFAULT_S2S_EDUCATION_URBANIZATION_FIELDS)
        self.s2s_output_path = os.path.join(working_directory, "study_area", f"{self.OUTPUT_FILENAME}.gpkg")

        gate_label = "widget:education"
        token = S2STaskGate.acquire(gate_label)
        if not token:
            active = S2STaskGate.active_label() or "another panel"
            QMessageBox.information(
                self,
                "S2S Busy",
                f"Another S2S download is currently running ({active}). Please wait for it to finish.",
            )
            return
        self._s2s_gate_token = token

        self.s2s_controls.set_running()
        self.s2s_status_label.setText("Fetching S2S data...")

        self._s2s_error_handled = False
        self.s2s_task = S2SDownloaderTask(
            aoi=aoi_feature,
            fields=fields,
            working_dir=working_directory,
            filename=self.OUTPUT_FILENAME,
            spatial_join_method="centroid",
            geometry="point",
            delete_existing=True,
        )

        self.s2s_task.progress_updated.connect(self._on_s2s_progress)
        self.s2s_task.error_occurred.connect(self._on_s2s_error)
        self.s2s_task.taskCompleted.connect(self._on_s2s_completed)
        self.s2s_task.taskTerminated.connect(self._on_s2s_terminated)
        QgsApplication.taskManager().addTask(self.s2s_task)

    def update_attributes(self):
        """Persist fixed Education S2S fields and common metadata."""
        super().update_attributes()
        self.attributes["s2s_fields"] = list(DEFAULT_S2S_EDUCATION_URBANIZATION_FIELDS)
        self.attributes["s2s_fields_text"] = ",".join(DEFAULT_S2S_EDUCATION_URBANIZATION_FIELDS)
