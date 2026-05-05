# -*- coding: utf-8 -*-
"""Space2Stats downloader task."""

import datetime
import json
import os
import traceback
import uuid
from typing import Any, Dict, List, Optional

from osgeo import ogr, osr
from qgis.core import QgsFeedback, QgsTask
from qgis.PyQt.QtCore import pyqtSignal

from geest.core.s2s_client import S2SClient
from geest.utilities import log_message


class S2SDownloaderTask(QgsTask):
    """A QgsTask for downloading and persisting Space2Stats summary data."""

    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(str)

    def __init__(
        self,
        aoi: Dict[str, Any],
        fields: List[str],
        working_dir: str,
        filename: str = "s2s_summary",
        spatial_join_method: str = "centroid",
        geometry: Optional[str] = "point",
        base_url: Optional[str] = None,
        delete_existing: bool = True,
        feedback: Optional[QgsFeedback] = None,
    ):
        """Initialize S2S downloader task.

        Args:
            aoi: GeoJSON feature polygon/multipolygon.
            fields: S2S fields to fetch.
            working_dir: Project working directory.
            filename: Output file basename (without extension).
            spatial_join_method: touches, centroid, or within.
            geometry: Optional geometry mode (point/polygon) for S2S response.
            base_url: Optional S2S API base URL override.
            delete_existing: Remove existing output file before writing.
            feedback: Optional feedback object.
        """
        super().__init__("S2S Downloader Task", QgsTask.CanCancel)

        if not working_dir:
            raise ValueError("Working directory cannot be empty")
        if not isinstance(fields, list) or not fields:
            raise ValueError("Fields must be a non-empty list")
        if not isinstance(aoi, dict) or not aoi:
            raise ValueError("AOI must be a non-empty GeoJSON feature")

        self.aoi = aoi
        self.fields = fields
        self.working_dir = working_dir
        self.filename = filename
        self.spatial_join_method = spatial_join_method
        self.geometry = geometry
        self.base_url = base_url
        self.delete_existing = delete_existing
        self.feedback = feedback if feedback else QgsFeedback()

        self.study_area_dir = os.path.join(self.working_dir, "study_area")
        self.output_path = os.path.join(self.study_area_dir, f"{self.filename}.gpkg")
        self.layer_name = self.filename
        self._temp_output_path = ""

        self._create_output_directory()

    def run(self) -> bool:
        """Execute task in worker thread."""
        try:
            self.setProgress(1)
            self.progress_updated.emit("Checking S2S API health...")
            client = S2SClient(base_url=self.base_url)
            client.health()

            if self.isCanceled():
                return False

            self.setProgress(10)
            self.progress_updated.emit("Validating requested S2S fields...")
            available_fields = set(client.fields())
            missing_fields = [field for field in self.fields if field not in available_fields]
            if missing_fields:
                raise ValueError(f"Requested S2S fields are unavailable: {', '.join(missing_fields)}")

            if self.isCanceled():
                return False

            self.setProgress(25)
            self.progress_updated.emit("Fetching S2S summary data...")
            rows = client.summary(
                aoi=self.aoi,
                fields=self.fields,
                spatial_join_method=self.spatial_join_method,
                geometry=self.geometry,
            )

            if not rows:
                raise ValueError("S2S returned no rows for the provided AOI and fields.")

            if self.isCanceled():
                return False

            self.setProgress(70)
            self.progress_updated.emit("Writing S2S output to GeoPackage...")
            self._write_rows_to_gpkg(rows)

            self.setProgress(100)
            self.progress_updated.emit("S2S download complete.")
            log_message(f"S2S output written to {self.output_path}")
            return True

        except Exception as error:
            message = f"Error in S2SDownloaderTask: {error}"
            log_message(message)
            log_message(traceback.format_exc())
            self.error_occurred.emit(message)
            self._cleanup_partial_output()
            self._write_error_file(traceback.format_exc())
            return False

    def _create_output_directory(self) -> None:
        """Create study area directory if needed."""
        os.makedirs(self.study_area_dir, exist_ok=True)

    def _cleanup_partial_output(self) -> None:
        """Remove partial output file on failure."""
        if self._temp_output_path and os.path.exists(self._temp_output_path):
            try:
                os.remove(self._temp_output_path)
            except Exception as cleanup_error:
                log_message(f"Could not remove temporary S2S output: {cleanup_error}")
        self._temp_output_path = ""

    def _write_error_file(self, stack_trace: str) -> None:
        """Write a task error trace in the working directory."""
        try:
            error_file = os.path.join(self.working_dir, "s2s_download_error.txt")
            with open(error_file, "w", encoding="utf-8") as handle:
                handle.write(f"{datetime.datetime.now()}\n")
                handle.write(f"Output Path: {self.output_path}\n")
                handle.write(stack_trace)
        except Exception:
            pass

    def _write_rows_to_gpkg(self, rows: List[Dict[str, Any]]) -> None:
        """Persist S2S rows to a GeoPackage layer."""
        driver = ogr.GetDriverByName("GPKG")
        if driver is None:
            raise RuntimeError("GeoPackage driver is not available.")

        if os.path.exists(self.output_path) and not self.delete_existing:
            raise RuntimeError(f"Output already exists and delete_existing is False: {self.output_path}")

        temp_filename = f"{self.filename}.{uuid.uuid4().hex}.tmp.gpkg"
        self._temp_output_path = os.path.join(self.study_area_dir, temp_filename)

        dataset = driver.CreateDataSource(self._temp_output_path)
        if dataset is None:
            raise RuntimeError(f"Could not create output GeoPackage: {self._temp_output_path}")

        try:
            geometry_type = self._infer_geometry_type(rows)
            spatial_ref = None
            if geometry_type != ogr.wkbNone:
                spatial_ref = osr.SpatialReference()
                spatial_ref.ImportFromEPSG(4326)

            layer = dataset.CreateLayer(self.layer_name, srs=spatial_ref, geom_type=geometry_type)
            if layer is None:
                raise RuntimeError("Could not create S2S output layer.")

            output_fields = ["hex_id"] + [field for field in self.fields if field != "hex_id"]
            output_field_types = self._infer_field_types(rows, output_fields)

            for field_name in output_fields:
                field_defn = ogr.FieldDefn(field_name, output_field_types[field_name])
                if output_field_types[field_name] == ogr.OFTReal:
                    field_defn.SetWidth(32)
                    field_defn.SetPrecision(12)
                layer.CreateField(field_defn)

            layer_defn = layer.GetLayerDefn()
            total = len(rows)
            for index, row in enumerate(rows):
                if self.isCanceled():
                    raise RuntimeError("S2S task was cancelled during output write.")

                feature = ogr.Feature(layer_defn)
                for field_name in output_fields:
                    value = row.get(field_name)
                    if value is None:
                        continue
                    if isinstance(value, bool):
                        feature.SetField(field_name, int(value))
                    elif isinstance(value, (int, float, str)):
                        feature.SetField(field_name, value)
                    else:
                        feature.SetField(field_name, json.dumps(value))

                geometry_value = row.get("geometry")
                if geometry_value is not None and geometry_type != ogr.wkbNone:
                    normalized_geometry = self._normalize_geometry(geometry_value)
                    geometry = None
                    if normalized_geometry is not None:
                        geometry = ogr.CreateGeometryFromJson(json.dumps(normalized_geometry))
                    if geometry is not None:
                        feature.SetGeometry(geometry)

                if layer.CreateFeature(feature) != 0:
                    raise RuntimeError("Failed to create feature in S2S output layer.")

                progress = 70 + int(((index + 1) / total) * 30)
                self.setProgress(progress)
                feature = None

        finally:
            dataset = None

        os.replace(self._temp_output_path, self.output_path)
        self._temp_output_path = ""

    @staticmethod
    def _infer_geometry_type(rows: List[Dict[str, Any]]) -> int:
        """Infer OGR geometry type from S2S rows."""
        for row in rows:
            geometry = S2SDownloaderTask._normalize_geometry(row.get("geometry"))
            if not geometry:
                continue

            geom_type = str(geometry.get("type", "")).lower()
            if geom_type == "point":
                return ogr.wkbPoint
            if geom_type == "polygon":
                return ogr.wkbPolygon
            if geom_type == "multipolygon":
                return ogr.wkbMultiPolygon
            return ogr.wkbUnknown

        return ogr.wkbNone

    @staticmethod
    def _normalize_geometry(geometry_value: Any) -> Optional[Dict[str, Any]]:
        """Normalize geometry values from S2S rows to GeoJSON dicts."""
        if geometry_value is None:
            return None

        if isinstance(geometry_value, dict):
            return geometry_value

        if isinstance(geometry_value, str):
            try:
                parsed = json.loads(geometry_value)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return None

        return None

    @staticmethod
    def _infer_field_types(rows: List[Dict[str, Any]], output_fields: List[str]) -> Dict[str, int]:
        """Infer OGR field types from returned rows."""
        inferred = {field: ogr.OFTString for field in output_fields}

        for field_name in output_fields:
            for row in rows:
                value = row.get(field_name)
                if value is None:
                    continue

                if field_name == "hex_id":
                    inferred[field_name] = ogr.OFTString
                elif isinstance(value, bool):
                    inferred[field_name] = ogr.OFTInteger
                elif isinstance(value, int):
                    inferred[field_name] = ogr.OFTInteger64
                elif isinstance(value, float):
                    inferred[field_name] = ogr.OFTReal
                else:
                    inferred[field_name] = ogr.OFTString
                break

        return inferred
