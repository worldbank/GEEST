# -*- coding: utf-8 -*-
"""Nighttime lights raster downloader task."""

import datetime
import os
import traceback
import uuid
from typing import Optional

from qgis.core import QgsRectangle, QgsTask
from qgis.PyQt.QtCore import pyqtSignal

from geest.core.constants import NTL_VNL_LATEST_YEAR, NTL_VNL_SOURCE_URL_TEMPLATE
from geest.core.tasks.raster_download_utils import crop_raster_to_extent, download_file_with_retry
from geest.utilities import log_message


class NTLDownloaderTask(QgsTask):
    """A QgsTask that downloads the annual VIIRS nighttime lights composite and crops it.

    The global composite (~60 MB) is downloaded synchronously via
    QgsNetworkAccessManager (the same pattern S2SClient uses), then cropped
    to the study area with a purely local gdal.Translate call.
    """

    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(str)

    def __init__(
        self,
        extent: QgsRectangle,
        extent_crs_authid: str,
        working_dir: str,
        filename: str = "nighttime_lights_annual",
        year: Optional[int] = None,
        delete_existing: bool = True,
    ):
        """Initialize the nighttime lights downloader task.

        Args:
            extent: Bounding box of the study area to crop to.
            extent_crs_authid: CRS authid (e.g. "EPSG:32626") that ``extent`` is in.
            working_dir: Project working directory.
            filename: Output file basename (without extension).
            year: Composite year to fetch. Defaults to the latest available year.
            delete_existing: Remove an existing output file before writing.
        """
        super().__init__("Nighttime Lights Downloader Task", QgsTask.CanCancel)

        if not working_dir:
            raise ValueError("Working directory cannot be empty")
        if extent is None or extent.isEmpty():
            raise ValueError("Extent must be a non-empty rectangle")
        if not extent_crs_authid:
            raise ValueError("Extent CRS authid cannot be empty")

        self.extent = extent
        self.extent_crs_authid = extent_crs_authid
        self.working_dir = working_dir
        self.filename = filename
        self.year = int(year) if year else NTL_VNL_LATEST_YEAR
        self.delete_existing = delete_existing

        self.study_area_dir = os.path.join(self.working_dir, "study_area")
        self.output_path = os.path.join(self.study_area_dir, f"{self.filename}.tif")
        self._temp_global_path = ""
        self._temp_output_path = ""

        os.makedirs(self.study_area_dir, exist_ok=True)

    def run(self) -> bool:
        """Execute task in worker thread."""
        try:
            self.setProgress(5)
            source_url = NTL_VNL_SOURCE_URL_TEMPLATE.format(year=self.year)
            description = f"{self.year} nighttime lights composite"
            self.progress_updated.emit(f"Downloading {description} (~60 MB)...")

            if self.isCanceled():
                return False

            self._temp_global_path = os.path.join(
                self.study_area_dir, f".ntl_global_{self.year}_{uuid.uuid4().hex}.tif"
            )
            downloaded = download_file_with_retry(
                url=source_url,
                destination=self._temp_global_path,
                is_canceled=self.isCanceled,
                on_progress=self.progress_updated.emit,
                description=description,
            )
            if not downloaded:
                return False

            self.setProgress(70)
            self.progress_updated.emit("Cropping nighttime lights to study area...")

            temp_filename = f"{self.filename}.{uuid.uuid4().hex}.tmp.tif"
            self._temp_output_path = os.path.join(self.study_area_dir, temp_filename)

            crop_raster_to_extent(
                source_path=self._temp_global_path,
                destination_path=self._temp_output_path,
                extent=self.extent,
                extent_crs_authid=self.extent_crs_authid,
                description=description,
            )

            if self.isCanceled():
                return False

            self.setProgress(90)
            if self.delete_existing and os.path.exists(self.output_path):
                os.remove(self.output_path)
            os.replace(self._temp_output_path, self.output_path)
            self._temp_output_path = ""

            self.setProgress(100)
            self.progress_updated.emit("Nighttime lights download complete.")
            log_message(f"Nighttime lights output written to {self.output_path}")
            return True

        except Exception as error:
            message = f"Error in NTLDownloaderTask: {error}"
            log_message(message)
            log_message(traceback.format_exc())
            self.error_occurred.emit(message)
            self._write_error_file(traceback.format_exc())
            return False

        finally:
            self._cleanup_temp_files()

    def _cleanup_temp_files(self) -> None:
        """Remove temporary global and partial output files."""
        for path_attr in ("_temp_global_path", "_temp_output_path"):
            path = getattr(self, path_attr, "")
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as cleanup_error:
                    log_message(f"Could not remove temporary nighttime lights file {path}: {cleanup_error}")
            setattr(self, path_attr, "")

    def _write_error_file(self, stack_trace: str) -> None:
        """Write a task error trace in the working directory."""
        try:
            error_file = os.path.join(self.working_dir, "ntl_download_error.txt")
            with open(error_file, "w", encoding="utf-8") as handle:
                handle.write(f"{datetime.datetime.now()}\n")
                handle.write(f"Output Path: {self.output_path}\n")
                handle.write(stack_trace)
        except Exception as e:
            log_message(f"Could not write nighttime lights error file: {e}")
