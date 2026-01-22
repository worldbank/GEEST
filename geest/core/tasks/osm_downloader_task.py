# -*- coding: utf-8 -*-
"""📦 Osm Downloader Task module.

This module contains functionality for osm downloader task.
"""

import datetime
import os
import traceback
from typing import Optional

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeedback,
    QgsProject,
    QgsRectangle,
    QgsTask,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import pyqtSignal

from geest.core.osm_downloaders import OSMDownloaderFactory, OSMDownloadType
from geest.utilities import log_message


class OSMDownloaderTask(QgsTask):
    """
    A QgsTask subclass for downloading OSM data.

    This task properly integrates with the QGIS task manager and follows the
    established workflow architecture pattern. It supports two usage modes:

    1. Layer-based: Provide reference_layer to extract extent
    2. Extent-based: Provide extents directly (must be in EPSG:4326)

    Args:
        osm_download_type: Type of OSM data to download.
        reference_layer: QgsVectorLayer to determine extent (optional if extents provided).
        extents: Direct extent in EPSG:4326 (optional if reference_layer provided).
        working_dir: Directory for outputs (optional if output_path provided).
        filename: Output filename (optional if output_path provided).
        output_path: Direct output path (optional if working_dir + filename provided).
        crs: Target CRS for reprojection.
        use_cache: Whether to use cached data.
        delete_gpkg: Whether to delete existing gpkg before download.
        feedback: QgsFeedback object for progress reporting.
    """

    error_occurred = pyqtSignal(str)  # for propogating error messages out of the thread
    progress_updated = pyqtSignal(str)  # for progress messages

    def __init__(
        self,
        osm_download_type: OSMDownloadType,
        reference_layer: Optional[QgsVectorLayer] = None,
        extents: Optional[QgsRectangle] = None,
        working_dir: Optional[str] = None,
        filename: Optional[str] = None,
        output_path: Optional[str] = None,
        crs: Optional[QgsCoordinateReferenceSystem] = None,
        use_cache: bool = True,
        delete_gpkg: bool = True,
        feedback: Optional[QgsFeedback] = None,
    ):
        """
        Initialize the OSM downloader task.

        Either reference_layer OR extents must be provided.
        Either output_path OR (working_dir + filename) must be provided.

        :param osm_download_type: Type of OSM data to download.
        :param reference_layer: QgsVectorLayer used to determine the bounding box.
        :param extents: Direct extent rectangle (must be in EPSG:4326).
        :param working_dir: Directory path where outputs will be saved.
        :param filename: Name of the output file.
        :param output_path: Direct path to output GeoPackage file.
        :param crs: Target CRS for output data.
        :param use_cache: If True, use cached data if available.
        :param delete_gpkg: If True, delete existing gpkg before download.
        :param feedback: QgsFeedback object for reporting progress.
        """
        super().__init__("OSM Downloader Task", QgsTask.CanCancel)

        self.osm_download_type = osm_download_type
        self.reference_layer = reference_layer
        self.use_cache = use_cache
        self.delete_gpkg = delete_gpkg
        self.feedback = feedback if feedback else QgsFeedback()
        self.output_crs = crs

        # Validate inputs - must provide either layer or extent
        if reference_layer is None and extents is None:
            raise ValueError("Either reference_layer or extents must be provided")

        if output_path is None and (working_dir is None or filename is None):
            raise ValueError("Either output_path or (working_dir + filename) must be provided")

        # Determine output path
        if output_path:
            self.gpkg_path = output_path
            # Extract working_dir from output_path (go up from study_area dir if it exists)
            parent_dir = os.path.dirname(output_path)
            if os.path.basename(parent_dir) == "study_area":
                self.working_dir = os.path.dirname(parent_dir)
            else:
                self.working_dir = parent_dir
        else:
            if working_dir is None or working_dir == "":
                raise ValueError("Working directory cannot be None or empty")
            self.working_dir = working_dir
            self.gpkg_path = os.path.join(working_dir, "study_area", f"{filename}.gpkg")

        self.filename = filename if filename else os.path.splitext(os.path.basename(self.gpkg_path))[0]

        log_message(f"OSMDownloaderTask: GeoPackage path: {self.gpkg_path}", tag="Geest", level=Qgis.Info)

        # Make sure output directory exists
        self._create_output_directory()

        # Handle existing GPKG
        if os.path.exists(self.gpkg_path):
            if self.delete_gpkg:
                try:
                    os.remove(self.gpkg_path)
                    log_message(
                        f"Removed existing GeoPackage: {self.gpkg_path}",
                        tag="Geest",
                        level=Qgis.Info,
                    )
                except Exception as e:
                    log_message(
                        f"Error removing existing GeoPackage: {e}",
                        tag="Geest",
                        level=Qgis.Critical,
                    )
            else:
                log_message(
                    f"GeoPackage already exists and delete_gpkg is False: {self.gpkg_path}",
                    tag="Geest",
                    level=Qgis.Warning,
                )
        else:
            log_message(f"Writing to new GeoPackage: {self.gpkg_path}", tag="Geest", level=Qgis.Info)

        # Determine extent
        if extents:
            # Use provided extent (assumed to be in EPSG:4326)
            self.layer_extent = extents
            log_message(
                f"Using provided extent: {extents.toString()}",
                tag="Geest",
                level=Qgis.Info,
            )
        else:
            # Compute bounding box from reference layer
            if not isinstance(reference_layer, QgsVectorLayer):
                raise ValueError("Reference layer must be a QgsVectorLayer")

            self.layer_extent = self.reference_layer.extent()
            # Convert to EPSG:4326 if needed
            if self.reference_layer.crs().authid() != "EPSG:4326":
                transform = QgsCoordinateTransform(
                    self.reference_layer.crs(),
                    QgsCoordinateReferenceSystem("EPSG:4326"),
                    QgsProject.instance(),
                )
                self.layer_extent = transform.transformBoundingBox(self.layer_extent)
                log_message(
                    f"Transformed extent to EPSG:4326: {self.layer_extent.toString()}",
                    tag="Geest",
                    level=Qgis.Info,
                )

    def run(self) -> bool:
        """
        Main entry point - executes in worker thread.

        Returns:
            True if successful, False otherwise.
        """
        try:
            self.setProgress(1)  # Trigger the UI to update with a small value
            self.progress_updated.emit("Starting OSM download...")
            log_message(
                f"Downloading OSM {self.osm_download_type.value} data...",
                tag="Geest",
                level=Qgis.Info,
            )
            if self.output_crs:
                log_message(f"Using CRS: {self.output_crs.authid()} for OSM download", tag="Geest", level=Qgis.Info)

            self.progress_updated.emit("Creating downloader...")
            downloader = OSMDownloaderFactory.get_osm_downloader(
                extents=self.layer_extent,
                download_type=self.osm_download_type,
                output_path=self.gpkg_path,
                output_crs=self.output_crs,
                filename=self.filename,  # will also set the layer name in the gpkg
                use_cache=self.use_cache,
                delete_gpkg=self.delete_gpkg,
                feedback=self.feedback,
            )

            self.progress_updated.emit("Processing OSM data...")
            downloader.process_response()

            self.setProgress(100)  # Trigger the UI to update with completion value
            self.progress_updated.emit("Download complete!")
            log_message(f"OSM Downloaded to {self.gpkg_path}.", tag="Geest", level=Qgis.Info)

        except Exception as e:
            log_message(f"Error in OSMDownloaderTask: {str(e)}", tag="Geest", level=Qgis.Critical)
            log_message(traceback.format_exc(), tag="Geest", level=Qgis.Critical)

            # Write error to file for debugging
            try:
                error_file = os.path.join(self.working_dir, "osm_download_error.txt")
                with open(error_file, "w") as f:
                    f.write(f"{datetime.datetime.now()}\n")
                    f.write(f"Download Type: {self.osm_download_type.value}\n")
                    f.write(f"Output Path: {self.gpkg_path}\n")
                    f.write(traceback.format_exc())
            except Exception:
                pass  # Don't fail on error logging

            # Emit user-friendly error message
            if "probably too busy" in str(e).lower():
                self.error_occurred.emit("Overpass API is probably too busy right now. Please try again later.")
            else:
                self.error_occurred.emit(f"Error downloading OSM data: {str(e)}")

            # Clean up any partial/malformed GeoPackage on failure
            if os.path.exists(self.gpkg_path):
                try:
                    os.remove(self.gpkg_path)
                    log_message(
                        f"Removed malformed GeoPackage after download failure: {self.gpkg_path}",
                        tag="Geest",
                        level=Qgis.Warning,
                    )
                except Exception as cleanup_error:
                    log_message(
                        f"Could not remove malformed GeoPackage: {cleanup_error}",
                        tag="Geest",
                        level=Qgis.Warning,
                    )

            return False  # Return False on failure so callbacks know the task failed

        return True

    def _create_output_directory(self) -> None:
        """Create output directory if it doesn't exist."""
        output_dir = os.path.dirname(self.gpkg_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            log_message(f"Created directory: {output_dir}", tag="Geest", level=Qgis.Info)
