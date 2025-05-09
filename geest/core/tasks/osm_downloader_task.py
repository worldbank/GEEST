import os
import re
import glob
import traceback
import datetime
import time

# GDAL / OGR / OSR imports
from osgeo import ogr, osr, gdal
from typing import List, Optional
from qgis.core import (
    QgsTask,
    QgsFeedback,
    QgsVectorLayer,
    QgsProject,
    QgsCoordinateTransform,
    QgsCoordinateReferenceSystem,
)
from geest.utilities import log_message
from geest.core.osm_downloaders import OSMRoadsDownloader
from geest.core import setting


class OSMDownloaderTask(QgsTask):
    """
    A QgsTask subclass for downloading OSM data.


    Args:
        layer (QgsVectorLayer): The input vector layer that determines the download extents.
        working_dir (str): The directory path where outputs will be saved.
        feedback (QgsFeedback): A feedback object to report progress.
        crs (Optional[QgsCoordinateReferenceSystem]): The target CRS. OSM Data will be reprojected to this CRS:.

    Returns:
        _type_: _description_
    """

    def __init__(
        self,
        reference_layer: QgsVectorLayer,
        working_dir,
        filename,
        use_cache=True,
        delete_gpkg=True,
        feedback: QgsFeedback = None,
        crs: QgsCoordinateReferenceSystem = None,
    ):
        """
        :param input_vector_path: Path to an OGR-readable vector file (e.g. .gpkg or .shp).
        :param working_dir: Directory path where outputs will be saved.
        :param filename: Name of the output file.
        :param use_cache: If True, use cached data if available.
        :param feedback: QgsFeedback object for reporting progress.
        :param crs_epsg: EPSG code for target CRS. If None, a UTM zone will be computed.
        """
        super().__init__("Study Area Preparation", QgsTask.CanCancel)

        self.reference_layer = reference_layer  # used to determin bbox of download
        self.working_dir = working_dir
        self.gpkg_path = os.path.join(working_dir, "study_area", f"{filename}.gpkg")
        self.filename = filename
        self.use_cache = use_cache
        self.delete_gpkg = delete_gpkg
        self.feedback = feedback
        # Make sure output directory exists
        self.create_study_area_directory(self.working_dir)

        # If GPKG already exists, remove it to start fresh
        # I think this is redundant as the downloader base class has similar logic
        if os.path.exists(self.gpkg_path):
            if self.delete_gpkg:
                try:
                    os.remove(self.gpkg_path)
                    log_message(f"Removed existing GeoPackage: {self.gpkg_path}")
                except Exception as e:
                    log_message(
                        f"Error removing existing GeoPackage: {e}", level="CRITICAL"
                    )
            else:
                log_message(
                    f"GeoPackage already exists and delete_gpkg is False: {self.gpkg_path}"
                )
        else:
            log_message(f"Writing to new GeoPackage: {self.gpkg_path}")

        # Compute bounding box from entire layer
        # (OGR Envelope: (xmin, xmax, ymin, ymax))
        self.layer_extent = self.reference_layer.extent()
        # Convert to EPSG:4326 if needed
        if self.reference_layer.crs().authid() != "EPSG:4326":
            # Transform the extent to EPSG:4326
            transform = QgsCoordinateTransform(
                self.reference_layer.crs(),
                QgsCoordinateReferenceSystem("EPSG:4326"),
                QgsProject.instance(),
            )
            self.layer_extent = transform.transformBoundingBox(self.layer_extent)
        self.output_crs = crs

    def run(self):
        """
        Main entry point (mimics process_study_area from QGIS code).
        """
        try:
            self.setProgress(1)  # Trigger the UI to update with a small value
            log_message(f"Downloading roads starting....")
            log_message(f"Using CRS: {self.output_crs.authid()} for OSM download")

            downloader = OSMRoadsDownloader(
                extents=self.layer_extent,
                output_path=self.gpkg_path,
                output_crs=self.output_crs,
                filename=self.filename,  # will also set the layer name in the gpkg
                use_cache=self.use_cache,
                delete_gpkg=self.delete_gpkg,
                feedback=self.feedback,
            )
            self.setProgress(100)  # Trigger the UI to update with completion value
            downloader.process_response()
            log_message(f"OSM Downloaded to {self.gpkg_path}.")

        except Exception as e:
            log_message(f"Error in run(): {str(e)}")
            log_message(traceback.format_exc())
            with open(os.path.join(self.working_dir, "error.txt"), "w") as f:
                f.write(f"{datetime.datetime.now()}\n")
                f.write(traceback.format_exc())
            return False

        return True

    def create_study_area_directory(self, working_dir):
        """
        Create 'study_area' subdir if not exist
        """
        study_area_dir = os.path.join(working_dir, "study_area")
        if not os.path.exists(study_area_dir):
            os.makedirs(study_area_dir)
            log_message(f"Created directory {study_area_dir}")
