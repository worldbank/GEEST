# -*- coding: utf-8 -*-
"""Space2Stats datasource widget."""

import json
import os
from typing import List

from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsGeometry,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QLabel, QLineEdit, QMessageBox, QPushButton

from geest.core.tasks import S2SDownloaderTask

from .vector_datasource_widget import VectorDataSourceWidget


class S2SDataSourceWidget(VectorDataSourceWidget):
    """Vector datasource widget with optional Space2Stats download support."""

    def add_internal_widgets(self) -> None:
        """Build base vector controls and append S2S controls."""
        super().add_internal_widgets()

        self.s2s_fields_line_edit = QLineEdit()
        self.s2s_fields_line_edit.setPlaceholderText("S2S fields (comma separated)")
        initial_fields = self.attributes.get("s2s_fields", [])
        if isinstance(initial_fields, list) and initial_fields:
            self.s2s_fields_line_edit.setText(",".join(str(field) for field in initial_fields))
        elif isinstance(self.attributes.get("s2s_field"), str):
            self.s2s_fields_line_edit.setText(self.attributes.get("s2s_field"))
        self.s2s_fields_line_edit.textChanged.connect(self.update_attributes)
        self.layout.addWidget(self.s2s_fields_line_edit)

        self.s2s_fetch_button = QPushButton("Fetch from S2S")
        self.s2s_fetch_button.clicked.connect(self.fetch_from_s2s)
        self.layout.addWidget(self.s2s_fetch_button)

        self.s2s_status_label = QLabel("S2S idle")
        self.layout.addWidget(self.s2s_status_label)

        self._s2s_error_handled = False
        self.s2s_task = None
        self.s2s_output_path = ""

    def fetch_from_s2s(self) -> None:
        """Start a background task to fetch S2S data for the study area."""
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

        fields = self._parse_fields(self.s2s_fields_line_edit.text())
        if not fields:
            QMessageBox.warning(
                self,
                "S2S Fields Required",
                "Please enter at least one S2S field (comma separated).",
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

        self.s2s_output_path = os.path.join(working_directory, "study_area", f"s2s_{self.widget_key}.gpkg")

        self.s2s_fetch_button.setEnabled(False)
        self.s2s_fetch_button.setText("Fetching...")
        self.s2s_status_label.setText("Fetching S2S data...")

        self._s2s_error_handled = False
        self.s2s_task = S2SDownloaderTask(
            aoi=aoi_feature,
            fields=fields,
            working_dir=working_directory,
            filename=f"s2s_{self.widget_key}",
            spatial_join_method="centroid",
            geometry="point",
            delete_existing=True,
        )

        self.s2s_task.progress_updated.connect(self._on_s2s_progress)
        self.s2s_task.error_occurred.connect(self._on_s2s_error)
        self.s2s_task.taskCompleted.connect(self._on_s2s_completed)
        self.s2s_task.taskTerminated.connect(self._on_s2s_terminated)
        QgsApplication.taskManager().addTask(self.s2s_task)

    def _on_s2s_progress(self, message: str) -> None:
        """Update S2S status text from task progress."""
        self.s2s_status_label.setText(message)

    def _on_s2s_error(self, message: str) -> None:
        """Handle S2S task errors."""
        self._s2s_error_handled = True
        self.s2s_status_label.setText("S2S download failed")
        self.s2s_fetch_button.setEnabled(True)
        self.s2s_fetch_button.setText("Fetch from S2S")
        friendly_message = self._humanize_s2s_error(message)
        QMessageBox.warning(self, "S2S Download Failed", friendly_message)

    def _on_s2s_terminated(self) -> None:
        """Handle cancelled/terminated S2S tasks."""
        if self._s2s_error_handled:
            return
        self.s2s_status_label.setText("S2S task terminated")
        self.s2s_fetch_button.setEnabled(True)
        self.s2s_fetch_button.setText("Fetch from S2S")

    def _on_s2s_completed(self) -> None:
        """Load output layer after successful S2S task completion."""
        self.s2s_fetch_button.setEnabled(True)
        self.s2s_fetch_button.setText("Fetch from S2S")

        if not self.s2s_output_path or not os.path.exists(self.s2s_output_path):
            self.s2s_status_label.setText("S2S output not found")
            return

        layer_name = os.path.splitext(os.path.basename(self.s2s_output_path))[0]
        output_layer = QgsVectorLayer(self.s2s_output_path, layer_name, "ogr")
        if not output_layer.isValid():
            self.s2s_status_label.setText("S2S output invalid")
            QMessageBox.warning(self, "Invalid S2S Output", "S2S output file exists but could not be loaded.")
            return

        QgsProject.instance().addMapLayer(output_layer)
        self.layer_combo.setLayer(output_layer)
        self.s2s_status_label.setText("S2S download complete")
        self.update_attributes()

    def update_attributes(self):
        """Update base layer attributes and S2S metadata attributes."""
        super().update_attributes()
        if not hasattr(self, "s2s_fields_line_edit"):
            return
        fields = self._parse_fields(self.s2s_fields_line_edit.text())
        self.attributes["s2s_fields"] = fields
        self.attributes["s2s_fields_text"] = self.s2s_fields_line_edit.text()
        self.attributes["s2s_spatial_join_method"] = "centroid"
        if self.s2s_output_path:
            self.attributes["s2s_output_path"] = self.s2s_output_path

    @staticmethod
    def _parse_fields(raw_text: str) -> List[str]:
        """Parse comma-separated field names into a de-duplicated list."""
        fields = [token.strip() for token in raw_text.split(",") if token.strip()]
        unique_fields = []
        for field in fields:
            if field not in unique_fields:
                unique_fields.append(field)
        return unique_fields

    @staticmethod
    def _build_aoi_feature(layer: QgsVectorLayer) -> dict:
        """Build a GeoJSON feature from AOI geometry in EPSG:4326."""
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

    @staticmethod
    def _humanize_s2s_error(message: str) -> str:
        """Convert low-level S2S errors into user-friendly text."""
        lowered = str(message).lower()
        if "exterior must be valid" in lowered or "coordinate" in lowered:
            return (
                "The study area geometry sent to S2S is invalid in WGS84 coordinates. "
                "Please recreate or repair the study area and try again."
            )
        if "fields are unavailable" in lowered:
            return "The selected S2S field is unavailable. Please refresh available fields and try again."
        return message
