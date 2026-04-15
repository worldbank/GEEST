# -*- coding: utf-8 -*-
"""S2S-backed Nighttime Lights raster datasource widget."""

import os

from qgis import processing
from qgis.core import (
    QgsFeature,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QLabel, QMessageBox, QPushButton

from geest.core.constants import DEFAULT_S2S_NTL_FIELD
from geest.core.tasks import S2SDownloaderTask

from .raster_datasource_widget import RasterDataSourceWidget
from .s2s_datasource_widget import S2SDataSourceWidget


class S2SNTLRasterDataSourceWidget(RasterDataSourceWidget):
    """Datasource widget that fetches NTL from S2S and creates a raster."""

    def add_internal_widgets(self) -> None:
        """Build base raster controls and append S2S controls."""
        super().add_internal_widgets()

        self.s2s_ntl_field = self.attributes.get("s2s_ntl_field") or DEFAULT_S2S_NTL_FIELD
        self.s2s_fetch_button = QPushButton("Fetch from S2S")
        self.s2s_fetch_button.clicked.connect(self.fetch_from_s2s)
        self.layout.addWidget(self.s2s_fetch_button)

        self.s2s_status_label = QLabel("S2S idle")
        self.layout.addWidget(self.s2s_status_label)

        self.s2s_task = None
        self.s2s_vector_output_path = ""
        self.s2s_raster_output_path = ""
        self._s2s_error_handled = False

    def fetch_from_s2s(self) -> None:
        """Fetch S2S summary rows and convert them into a raster."""
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
        self.s2s_raster_output_path = os.path.join(working_directory, "study_area", "s2s_nighttime_lights.tif")

        self.s2s_fetch_button.setEnabled(False)
        self.s2s_fetch_button.setText("Fetching...")
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

    def _on_s2s_error(self, message: str) -> None:
        """Handle S2S task errors."""
        self._s2s_error_handled = True
        self._set_status("S2S download failed")
        self.s2s_fetch_button.setEnabled(True)
        self.s2s_fetch_button.setText("Fetch from S2S")
        friendly_message = S2SDataSourceWidget._humanize_s2s_error(message)
        QMessageBox.warning(self, "S2S Download Failed", friendly_message)

    def _on_s2s_terminated(self) -> None:
        """Handle cancelled/terminated S2S tasks."""
        if self._s2s_error_handled:
            return
        self._set_status("S2S task terminated")
        self.s2s_fetch_button.setEnabled(True)
        self.s2s_fetch_button.setText("Fetch from S2S")

    def _on_s2s_completed(self) -> None:
        """Convert S2S vector output into NTL raster and update attributes."""
        self.s2s_fetch_button.setEnabled(True)
        self.s2s_fetch_button.setText("Fetch from S2S")

        if not os.path.exists(self.s2s_vector_output_path):
            self._set_status("S2S output not found")
            return

        ntl_field = self.s2s_ntl_field
        try:
            self._rasterize_s2s_output(self.s2s_vector_output_path, self.s2s_raster_output_path, ntl_field)
        except Exception as error:
            self._set_status("Rasterization failed")
            QMessageBox.warning(self, "S2S Rasterization Failed", str(error))
            return

        raster_layer = QgsRasterLayer(self.s2s_raster_output_path, "S2S Nighttime Lights", "gdal")
        if not raster_layer.isValid():
            self._set_status("Raster output invalid")
            QMessageBox.warning(self, "Invalid Raster", "Raster file was created but could not be loaded.")
            return

        QgsProject.instance().addMapLayer(raster_layer)
        self.raster_layer_combo.setLayer(raster_layer)
        self.raster_line_edit.setVisible(True)
        self.raster_layer_combo.setVisible(False)
        self.raster_line_edit.setText(self.s2s_raster_output_path)
        self._set_status("S2S nighttime lights ready")
        self.update_attributes()

    def _set_status(self, message: str) -> None:
        """Set status label text when available."""
        if hasattr(self, "s2s_status_label") and self.s2s_status_label is not None:
            self.s2s_status_label.setText(message)

    def update_attributes(self):
        """Update raster attributes and S2S metadata."""
        super().update_attributes()
        if not hasattr(self, "s2s_ntl_field"):
            return
        self.attributes["s2s_ntl_field"] = self.s2s_ntl_field
        self.attributes["s2s_spatial_join_method"] = "centroid"
        if self.s2s_vector_output_path:
            self.attributes["s2s_output_path"] = self.s2s_vector_output_path

    def _rasterize_s2s_output(self, input_vector: str, output_raster: str, value_field: str) -> None:
        """Rasterize the S2S vector output using the selected value field."""
        study_area_layer = self._load_study_area_layer()
        if not study_area_layer:
            raise RuntimeError("Could not load study area extent for rasterization.")

        extent_layer = study_area_layer
        if study_area_layer.crs().authid() != "EPSG:4326":
            extent_layer = self._reproject_to_epsg4326(study_area_layer)
            if not extent_layer or not extent_layer.isValid():
                raise RuntimeError("Could not transform study area extent to EPSG:4326.")

        extent = extent_layer.extent()
        extent_string = f"{extent.xMinimum()},{extent.xMaximum()},{extent.yMinimum()},{extent.yMaximum()} [EPSG:4326]"

        if os.path.exists(output_raster):
            os.remove(output_raster)

        params = {
            "INPUT": input_vector,
            "FIELD": value_field,
            "BURN": 0,
            "USE_Z": False,
            "UNITS": 1,
            "WIDTH": 500,
            "HEIGHT": 500,
            "EXTENT": extent_string,
            "NODATA": 0,
            "OPTIONS": "",
            "DATA_TYPE": 5,
            "INIT": 0,
            "INVERT": False,
            "EXTRA": "-a_srs EPSG:4326 -at",
            "OUTPUT": output_raster,
        }
        processing.run("gdal:rasterize", params)

    @staticmethod
    def _load_study_area_layer() -> QgsVectorLayer:
        """Load the study area bbox layer from working directory."""
        settings = QSettings()
        working_directory = settings.value("last_working_directory", "")
        if not working_directory:
            return None
        gpkg_path = os.path.join(working_directory, "study_area", "study_area.gpkg")
        if not os.path.exists(gpkg_path):
            return None
        layer = QgsVectorLayer(f"{gpkg_path}|layername=study_area_bboxes", "study_area_bboxes", "ogr")
        return layer if layer.isValid() else None

    @staticmethod
    def _reproject_to_epsg4326(layer: QgsVectorLayer) -> QgsVectorLayer:
        """Create an in-memory copy of a layer in EPSG:4326."""
        target_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = QgsCoordinateTransform(layer.crs(), target_crs, QgsProject.instance())

        memory_layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "study_area_4326", "memory")
        provider = memory_layer.dataProvider()
        provider.addAttributes(layer.fields())
        memory_layer.updateFields()

        features = []
        for feature in layer.getFeatures():
            new_feature = QgsFeature(feature)
            geom = feature.geometry()
            geom.transform(transform)
            new_feature.setGeometry(geom)
            features.append(new_feature)

        provider.addFeatures(features)
        memory_layer.updateExtents()
        return memory_layer
