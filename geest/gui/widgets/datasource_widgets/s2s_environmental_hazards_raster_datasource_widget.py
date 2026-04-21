# -*- coding: utf-8 -*-
"""S2S-backed Environmental Hazards raster datasource widget."""

import os

from qgis.core import QgsApplication, QgsVectorLayer
from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox

from geest.core.constants import DEFAULT_S2S_ENV_HAZARD_FIELDS
from geest.core.tasks import S2SDownloaderTask

from .s2s_datasource_widget import S2SDataSourceWidget
from .s2s_ntl_raster_datasource_widget import S2SNTLRasterDataSourceWidget


class S2SEnvironmentalHazardsRasterDataSourceWidget(S2SNTLRasterDataSourceWidget):
    """Regional datasource widget that fetches hazard values from S2S."""

    def add_internal_widgets(self) -> None:
        """Build controls and configure hazard-specific S2S defaults."""
        super().add_internal_widgets()
        self.s2s_vector_field_combo.setLayer(None)
        self.s2s_vector_field_combo.setCurrentIndex(-1)
        self.s2s_vector_field_combo.setEnabled(False)
        self.s2s_vector_field_combo.setVisible(False)
        self.s2s_ntl_field = self._hazard_field_from_attributes()
        self.s2s_status_label.setToolTip(f"S2S field: {self.s2s_ntl_field}")
        self._select_existing_hazard_output_layer()

    def _update_vector_field_combo(self) -> None:
        """Disable manual field selection for S2S-specific hazards workflow."""
        if hasattr(self, "s2s_vector_field_combo"):
            self.s2s_vector_field_combo.setLayer(None)
            self.s2s_vector_field_combo.setCurrentIndex(-1)
            self.s2s_vector_field_combo.setEnabled(False)
            self.s2s_vector_field_combo.setVisible(False)

    def fetch_from_s2s(self) -> None:
        """Fetch S2S summary rows for environmental hazards grid scoring."""
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

        hazard_field = self._hazard_field_from_attributes()
        if not hazard_field:
            QMessageBox.warning(self, "S2S Field Required", "No S2S environmental hazards field is configured.")
            return

        aoi_layer = self._build_aoi_layer(study_area_gpkg)
        if not aoi_layer:
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

        filename = f"s2s_environmental_hazards_{self.attributes.get('id', '').lower()}"
        self.s2s_vector_output_path = os.path.join(working_directory, "study_area", f"{filename}.gpkg")
        self.s2s_raster_output_path = ""
        self.s2s_ntl_field = hazard_field

        self.s2s_controls.set_running()
        self._set_status("Fetching S2S data...")
        self._s2s_error_handled = False

        self.s2s_task = S2SDownloaderTask(
            aoi=aoi_feature,
            fields=[hazard_field],
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

    def _hazard_field_from_attributes(self) -> str:
        """Resolve S2S hazard field from indicator id or existing attribute."""
        existing = self.attributes.get("s2s_hazard_field", "")
        if existing:
            return str(existing)
        indicator_id = str(self.attributes.get("id", "")).lower()
        return DEFAULT_S2S_ENV_HAZARD_FIELDS.get(indicator_id, "")

    @staticmethod
    def _build_aoi_layer(study_area_gpkg: str):
        """Build and validate AOI layer from study area geopackage."""
        aoi_layer = QgsVectorLayer(f"{study_area_gpkg}|layername=study_area_bboxes", "study_area_bboxes", "ogr")
        if not aoi_layer.isValid() or aoi_layer.featureCount() == 0:
            return None
        return aoi_layer

    def select_raster(self) -> None:
        """Select raster or vector file for environmental hazards input."""
        last_dir = self.settings.value("GeoE3/lastRasterDir", "")
        if not last_dir:
            last_dir = self.settings.value("GeoE3/lastShapefileDir", "")
        indicator_name = self.attributes.get("name") or "Environmental Hazards"
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Select {indicator_name} Layer",
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
        self._update_vector_field_combo()

    def update_attributes(self):
        """Update attributes with hazard-specific S2S metadata."""
        super().update_attributes()
        self.attributes["s2s_hazard_field"] = self.s2s_ntl_field
        self.attributes["s2s_ntl_field"] = ""

    def _select_existing_hazard_output_layer(self) -> None:
        """Auto-select existing S2S hazard output when available."""
        if not self.s2s_vector_output_path:
            self.s2s_vector_output_path = self.attributes.get("s2s_output_path", "")
        if not self.s2s_vector_output_path or not os.path.exists(self.s2s_vector_output_path):
            return

        layer_name = os.path.splitext(os.path.basename(self.s2s_vector_output_path))[0]
        output_layer = S2SDataSourceWidget._load_or_reuse_vector_layer(self.s2s_vector_output_path, layer_name)
        if output_layer is None:
            self._set_status("S2S output invalid")
            return

        self.raster_line_edit.clear()
        self.raster_line_edit.setVisible(False)
        self.raster_layer_combo.setVisible(True)
        self.raster_layer_combo.setLayer(output_layer)
        self.s2s_controls.set_downloaded()
        self.update_attributes()
