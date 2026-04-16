# -*- coding: utf-8 -*-
"""S2S-backed Nighttime Lights raster datasource widget."""

import os
from urllib.parse import quote

from qgis.core import (
    QgsApplication,
    QgsMapLayerProxyModel,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QFileDialog, QLabel, QMessageBox, QSizePolicy

from geest.core.constants import DEFAULT_S2S_NTL_FIELD
from geest.core.tasks import S2SDownloaderTask

from .download_task_controls import DownloadTaskControls
from .raster_datasource_widget import RasterDataSourceWidget
from .s2s_datasource_widget import S2SDataSourceWidget


class S2SNTLRasterDataSourceWidget(RasterDataSourceWidget):
    """Datasource widget that fetches NTL from S2S for regional grid scoring."""

    VECTOR_EXTENSIONS = {".gpkg", ".shp", ".geojson", ".json", ".sqlite", ".fgb", ".parquet"}

    def add_internal_widgets(self) -> None:
        """Build raster controls and append S2S fetch controls."""
        super().add_internal_widgets()

        self.raster_layer_combo.setFilters(QgsMapLayerProxyModel.RasterLayer | QgsMapLayerProxyModel.VectorLayer)
        self.raster_layer_combo.setToolTip("Select raster or vector layer from the map")
        self.raster_layer_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.s2s_ntl_field = self.attributes.get("s2s_ntl_field") or DEFAULT_S2S_NTL_FIELD
        self.s2s_controls = DownloadTaskControls(
            button_text="Download from S2S",
            tooltip="Download data from Space2Stats",
            click_handler=self.fetch_from_s2s,
        )
        self.s2s_fetch_button = self.s2s_controls.button
        self.layout.addWidget(self.s2s_controls.container)

        self.s2s_status_label = QLabel("S2S idle")
        self.s2s_status_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.s2s_status_label.setMinimumWidth(90)
        self.s2s_status_label.setMaximumWidth(170)
        self.layout.addWidget(self.s2s_status_label)

        self.raster_line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.layout.setStretchFactor(self.raster_layer_combo, 5)
        self.layout.setStretchFactor(self.raster_line_edit, 5)

        self.s2s_task = None
        self.s2s_vector_output_path = self.attributes.get("s2s_output_path", "")
        self.s2s_raster_output_path = ""
        self._s2s_error_handled = False

        if not self.s2s_vector_output_path:
            settings = QSettings()
            working_directory = settings.value("last_working_directory", "")
            candidate_path = os.path.join(working_directory, "study_area", "s2s_nighttime_lights.gpkg")
            if working_directory and os.path.exists(candidate_path):
                self.s2s_vector_output_path = candidate_path
        if self.s2s_vector_output_path and os.path.exists(self.s2s_vector_output_path):
            self._set_status("Existing S2S nighttime lights found")

    def fetch_from_s2s(self) -> None:
        """Fetch S2S summary rows for downstream grid-based regional scoring."""
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

        ntl_field = self.s2s_ntl_field
        if not ntl_field:
            QMessageBox.warning(self, "S2S Field Required", "No S2S nighttime lights field is configured.")
            return

        aoi_layer = QgsVectorLayer(f"{study_area_gpkg}|layername=study_area_bboxes", "study_area_bboxes", "ogr")
        if not aoi_layer.isValid() or aoi_layer.featureCount() == 0:
            QMessageBox.warning(
                self,
                "Invalid Study Area",
                "Could not load study_area_bboxes from study_area.gpkg.",
            )
            return

        aoi_feature = S2SDataSourceWidget._build_aoi_feature(aoi_layer)
        if not aoi_feature:
            QMessageBox.warning(self, "Invalid AOI", "Failed to build AOI feature from study area geometry.")
            return

        filename = "s2s_nighttime_lights"
        self.s2s_vector_output_path = os.path.join(working_directory, "study_area", f"{filename}.gpkg")
        self.s2s_raster_output_path = ""

        self.s2s_controls.set_running()
        self._set_status("Fetching S2S data...")
        self._s2s_error_handled = False

        self.s2s_task = S2SDownloaderTask(
            aoi=aoi_feature,
            fields=[ntl_field],
            working_dir=working_directory,
            filename=filename,
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
        self._set_status(message)
        self.s2s_controls.update_progress(message)

    def _on_s2s_error(self, message: str) -> None:
        """Handle S2S task errors."""
        self._s2s_error_handled = True
        self._set_status("S2S download failed")
        self.s2s_controls.set_download_failed(message)
        friendly_message = S2SDataSourceWidget._humanize_s2s_error(message)
        QMessageBox.warning(self, "S2S Download Failed", friendly_message)

    def _on_s2s_terminated(self) -> None:
        """Handle cancelled/terminated S2S tasks."""
        if self._s2s_error_handled:
            return
        self._set_status("S2S task terminated")
        self.s2s_controls.set_cancelled()

    def _on_s2s_completed(self) -> None:
        """Record S2S vector output and update attributes for grid-based workflows."""
        self.s2s_controls.reset()

        if not os.path.exists(self.s2s_vector_output_path):
            self._set_status("S2S output not found")
            self.s2s_controls.set_not_found(self.s2s_vector_output_path)
            return

        layer_name = os.path.splitext(os.path.basename(self.s2s_vector_output_path))[0]
        s2s_layer = QgsVectorLayer(f"{self.s2s_vector_output_path}|layername={layer_name}", layer_name, "ogr")
        if s2s_layer.isValid():
            QgsProject.instance().addMapLayer(s2s_layer)
        else:
            self.s2s_controls.set_load_failed(self.s2s_vector_output_path)
            self._set_status("S2S output invalid")
            QMessageBox.warning(self, "Invalid S2S Output", "S2S output file exists but could not be loaded.")
            return

        self.raster_line_edit.clear()
        self.raster_line_edit.setVisible(False)
        self.raster_layer_combo.setVisible(True)
        self.raster_layer_combo.setLayer(s2s_layer if s2s_layer.isValid() else None)

        self._set_status("S2S nighttime lights downloaded")
        self.s2s_controls.set_downloaded()
        self.update_attributes()

    def _set_status(self, message: str) -> None:
        """Set status label text when available."""
        if hasattr(self, "s2s_status_label") and self.s2s_status_label is not None:
            self.s2s_status_label.setText(message)

    def select_raster(self) -> None:
        """Select raster or vector file for nighttime lights input."""
        last_dir = self.settings.value("GeoE3/lastRasterDir", "")
        if not last_dir:
            last_dir = self.settings.value("GeoE3/lastShapefileDir", "")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Nighttime Lights Layer",
            last_dir,
            "Supported (*.vrt *.tif *.asc *.gpkg *.shp *.geojson *.json *.sqlite *.fgb *.parquet);;"
            "Raster (*.vrt *.tif *.asc);;"
            "Vector (*.gpkg *.shp *.geojson *.json *.sqlite *.fgb *.parquet);;"
            "All files (*)",
        )
        if not file_path:
            return

        self.raster_layer_combo.setVisible(False)
        self.raster_line_edit.setVisible(True)
        self.raster_line_edit.setText(file_path)
        parent_directory = os.path.dirname(file_path)
        self.settings.setValue("GeoE3/lastRasterDir", parent_directory)
        self.settings.setValue("GeoE3/lastShapefileDir", parent_directory)
        self.resizeEvent(None)

    def clear_raster(self):
        """Clear selected file and reset widget state."""
        super().clear_raster()

    @classmethod
    def _is_vector_path(cls, file_path: str) -> bool:
        """Return True when file extension represents a known vector format."""
        if not file_path:
            return False
        extension = os.path.splitext(file_path)[1].lower()
        return extension in cls.VECTOR_EXTENSIONS

    def update_attributes(self):
        """Update raster attributes and S2S metadata."""
        super().update_attributes()
        selected_layer = self.raster_layer_combo.currentLayer()
        selected_path = self.raster_line_edit.text().strip()
        is_vector_file = self._is_vector_path(selected_path)
        is_vector_layer = bool(selected_layer and selected_layer.type() == QgsMapLayerType.VectorLayer)

        self.attributes[f"{self.widget_key}_input_type"] = "none"

        if is_vector_file:
            self.attributes[f"{self.widget_key}_vector"] = quote(selected_path)
            self.attributes[f"{self.widget_key}_raster"] = ""
            self.attributes[f"{self.widget_key}_selected_field"] = ""
            self.attributes[f"{self.widget_key}_input_type"] = "vector"
        elif is_vector_layer and self._is_vector_path(selected_layer.source()):
            self.attributes[f"{self.widget_key}_vector"] = quote(selected_layer.source())
            self.attributes[f"{self.widget_key}_selected_field"] = ""
            self.attributes[f"{self.widget_key}_input_type"] = "vector"
        elif selected_path:
            self.attributes[f"{self.widget_key}_input_type"] = "raster"
        else:
            self.attributes[f"{self.widget_key}_vector"] = ""
            self.attributes[f"{self.widget_key}_selected_field"] = ""
            if selected_layer:
                self.attributes[f"{self.widget_key}_input_type"] = "raster"

        if not hasattr(self, "s2s_ntl_field"):
            return
        self.attributes["s2s_ntl_field"] = self.s2s_ntl_field
        self.attributes["s2s_spatial_join_method"] = "centroid"
        if self.s2s_vector_output_path:
            self.attributes["s2s_output_path"] = self.s2s_vector_output_path
