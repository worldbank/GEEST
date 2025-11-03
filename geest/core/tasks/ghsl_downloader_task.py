# -*- coding: utf-8 -*-
import datetime
import os
import traceback

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeedback,
    QgsProject,
    QgsRectangle,
    QgsTask,
)
from qgis.PyQt.QtCore import pyqtSignal

from geest.core.algorithms import GHSLDownloader, GHSLProcessor
from geest.utilities import log_message


class GHSLDownloaderTask(QgsTask):
    """
    A QgsTask subclass for downloading Global Human Settlements data.


    Args:
        layer (QgsVectorLayer): The input vector layer that determines the download extents.
        working_dir (str): The directory path where outputs will be saved.
        feedback (QgsFeedback): A feedback object to report progress.

    Returns:
        _type_: _description_
    """

    error_occurred = pyqtSignal(str)  # for propogating error messages out of the thread

    def __init__(
        self,
        working_dir,
        filename,
        use_cache=True,
        delete_existing=True,
        feedback: QgsFeedback = None,
        extent_mollweide: QgsRectangle = None,
    ):
        """
        :param input_vector_path: Path to an OGR-readable vector file (e.g. .gpkg or .shp).
        :param working_dir: Directory path where outputs will be saved.
        :param filename: Name of the output file.
        :param use_cache: If True, use cached data if available.
        :param delete_existing: If True, delete existing output files before downloading.
        :param feedback: QgsFeedback object for reporting progress.
        :param extent_mollweide: QgsRectangle defining the area to download (in Mollweide ESRI:54009).
        """
        super().__init__("GHSL Downloader", QgsTask.CanCancel)

        if working_dir is None or working_dir == "":
            raise ValueError("Working directory cannot be None")
        self.working_dir = working_dir
        self.ghsl_result_path = os.path.join(working_dir, "study_area", f"ghsl_{filename}.parquet")
        self.vrt_path = os.path.join(working_dir, "study_area", f"ghsl_{filename}.vrt")
        log_message(f"GHSL output path: {self.ghsl_result_path}")
        self.filename = filename
        self.use_cache = use_cache
        self.delete_existing = delete_existing
        self.feedback = feedback
        # Make sure output directory exists
        self.create_study_area_directory(self.working_dir)

        # If GPKG already exists, remove it to start fresh
        # I think this is redundant as the downloader base class has similar logic
        if os.path.exists(self.ghsl_result_path):
            if self.delete_existing:
                try:
                    os.remove(self.ghsl_result_path)
                    log_message(f"Removed existing GHSL dataset: {self.ghsl_result_path}")
                except Exception as e:
                    log_message(f"Error removing existing GHSL dataset: {e}", level="CRITICAL")
            else:
                log_message(f"GHSL dataset already exists and delete_existing is False: {self.ghsl_result_path}")
        else:
            log_message(f"Writing to new GeoPackage: {self.ghsl_result_path}")

        self.extent_mollweide = extent_mollweide
        # Compute bounding box in EPSG:4326
        transform = QgsCoordinateTransform(
            QgsCoordinateReferenceSystem("EPSG:54009"),  # Mollweide
            QgsCoordinateReferenceSystem("EPSG:4326"),
            QgsProject.instance(),
        )
        self.extent_4326 = transform.transformBoundingBox(self.extent_mollweide)

    def run(self):
        """
        Main entry point (mimics process_study_area from QGIS code).
        """
        try:
            self.setProgress(1)  # Trigger the UI to update with a small value
            log_message("Downloading GHSL starting....")

            downloader = GHSLDownloader(
                extents=self.extent_4326,
                output_path=self.ghsl_result_path,
                filename=self.filename,  # will also set the layer name in the gpkg
                use_cache=self.use_cache,
                delete_existing=self.delete_existing,
                feedback=self.feedback,
            )
            log_message("Getting GHSL Tile List")
            tiles = downloader.tiles_intersecting_bbox()
            log_message(f"Tiles intersecting area: {tiles}")
            tile_paths = []
            for tile in tiles:
                self.setProgress(int(tiles.index(tile) / len(tiles)))
                log_message(f"Downloading tile {tile}...")
                tile_paths.extend(downloader.download_and_unpack_tile(tile))
            log_message("All tiles downloaded, finalizing...")
            log_message(f"Merging {len(tile_paths)} tiles into {self.ghsl_result_path}...")

            for path in tile_paths:
                log_message(f"Tile path: {path}")

            tifs = self.filter_tif_files(tile_paths)
            log_message(f"Filtered to {len(tifs)} .tif files.")
            if len(tifs) == 0:
                raise ValueError("No .tif files found to merge.")
            processor = GHSLProcessor(input_raster_paths=tifs)

            reclassified_layers = processor.reclassify_rasters(suffix="reclass")
            for path in reclassified_layers:
                log_message(f"Reclassified layer: {path}")

            polygonized_paths = processor.polygonize_rasters(reclassified_layers)
            for path in polygonized_paths:
                log_message(f"Polygonized layer: {path}")

            # Combine all polygonized layers into a single GeoParquet layer
            processor.combine_vectors(
                polygonized_paths, output_vector_path=self.ghsl_result_path, extent=self.extent_mollweide
            )
            self.setProgress(100)  # Trigger the UI to update with completion value
            # downloader.process_response()
            log_message(f"GHSL Downloaded to {self.ghsl_result_path}.")

        except Exception as e:
            log_message(f"Error in run(): {str(e)}")
            log_message(traceback.format_exc())
            with open(os.path.join(self.working_dir, "error.txt"), "w") as f:
                f.write(f"{datetime.datetime.now()}\n")
                f.write(traceback.format_exc())
            self.error_occurred.emit(f"Error in GHSLDownloaderTask: {str(e)}")
        return True

    def create_study_area_directory(self, working_dir):
        """
        Create 'study_area' subdir if not exist
        """
        study_area_dir = os.path.join(working_dir, "study_area")
        if not os.path.exists(study_area_dir):
            os.makedirs(study_area_dir)
            log_message(f"Created directory {study_area_dir}")

    def filter_tif_files(self, file_list):
        """
        Filter a list of files to only include .tif files.

        Args:
            file_list (list): List of file paths.

        Returns:
            list: Filtered list containing only .tif files.
        """
        return [f for f in file_list if f.lower().endswith(".tif")]
