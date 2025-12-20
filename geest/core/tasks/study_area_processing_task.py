# -*- coding: utf-8 -*-
"""📦 Study Area Processing Task module.

This module contains functionality for study area processing task.
"""
import datetime
import glob
import os
import re
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
from threading import Thread

# GDAL / OGR / OSR imports
from osgeo import gdal, ogr, osr
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeedback,
    QgsProject,
    QgsRectangle,
    QgsTask,
    QgsVectorFileWriter,
    QgsVectorLayer,
)

from geest.core.algorithms import GHSLDownloader, GHSLProcessor
from geest.core.settings import setting
from geest.utilities import calculate_utm_zone, log_message

from .grid_chunker_task import GridChunkerTask
from .grid_from_bbox_task import GridFromBboxTask


class StudyAreaProcessingTask(QgsTask):
    """
    A QgsTask subclass for processing study area features.

    Processes study-area geometries using GDAL/OGR instead of QGIS API.
    It creates bounding boxes, grids, raster masks, a dissolved clip polygon,
    and a combined VRT of all masks.

    It works through the (multi)part geometries in the input layer, creating bounding boxes and masks.
    The masks are stored as individual tif files and then a vrt file is created to combine them.
    The grids are in two forms - the entire bounding box and the individual parts.
    The grids are aligned to cell_size_m intervals and saved as vector features in a GeoPackage.
    Any invalid geometries are discarded, and fixed geometries are processed.

    Args:
        layer (QgsVectorLayer): The input vector layer.
        field_name (str): The field name in the input layer that holds the study area name.
        cell_size_m (float): The cell size for grid spacing in meters.
        working_dir (str): The directory path where outputs will be saved.
        feedback (QgsFeedback): A feedback object to report progress.
        crs (Optional[QgsCoordinateReferenceSystem]): The target CRS. If None, a UTM zone will be computed.

    Returns:
        _type_: _description_
    """

    def __init__(
        self,
        layer: QgsVectorLayer,
        field_name,
        cell_size_m,
        working_dir,
        feedback: QgsFeedback = None,
        crs=None,
    ):
        """
        :param input_vector_path: Path to an OGR-readable vector file (e.g. .gpkg or .shp).
        :param field_name: Name of the field that holds the study area name.
        :param cell_size_m: Cell size for grid spacing (in meters).
        :param working_dir: Directory path where outputs will be saved.
        :param crs_epsg: EPSG code for target CRS. If None, a UTM zone will be computed.
        """
        super().__init__("Study Area Preparation", QgsTask.CanCancel)
        self.input_vector_path = self.export_qgs_layer_to_shapefile(layer, working_dir)
        self.field_name = field_name
        self.cell_size_m = cell_size_m
        self.working_dir = working_dir
        self.gpkg_path = os.path.join(working_dir, "study_area", "study_area.gpkg")
        self.counter = 0
        self.feedback = feedback
        self.metrics = {
            "Creating chunks": 0.0,
            "Writing chunks": 0.0,
            "Complete chunk": 0.0,
            "Preparing chunks": 0.0,
        }
        self.valid_feature_count = 0
        self.current_geom_actual_cell_count = 0
        self.current_geom_cell_count_estimate = 0
        self.error_count = 0
        self.total_cells = 0
        self.write_lock = threading.Lock()
        self.gpkg_lock = threading.Lock()
        self.grid_id_lock = threading.Lock()
        self.writer_start_lock = threading.Lock()  # Protect writer thread creation
        self.write_queue = None
        self.writer_thread = None
        self.writer_layer = None  # Track which layer the writer is using
        self.writer_ds = None  # Writer's own dataset connection
        self.writer_ref_count = 0  # Reference count for parts using the writer
        # Make sure output directory exists
        self.create_study_area_directory(self.working_dir)

        # If GPKG already exists, remove it to start fresh
        if os.path.exists(self.gpkg_path):
            try:
                os.remove(self.gpkg_path)
                log_message(f"Removed existing GeoPackage: {self.gpkg_path}")
            except Exception as e:
                log_message(f"Error removing existing GeoPackage: {e}", level="CRITICAL")

        # Open the source data using OGR
        self.source_ds = ogr.Open(self.input_vector_path, 0)  # 0 = read-only
        if not self.source_ds:
            raise RuntimeError(f"Could not open {self.input_vector_path} with OGR.")
        self.source_layer = self.source_ds.GetLayer(0)
        if not self.source_layer:
            raise RuntimeError("Could not retrieve layer from the data source.")
        self.parts_count = self.count_layer_parts()

        # Determine source EPSG (if any) by reading layer's spatial ref
        self.src_spatial_ref = self.source_layer.GetSpatialRef()
        self.src_epsg = None
        if self.src_spatial_ref:
            self.src_epsg = self.src_spatial_ref.GetAuthorityCode(None)

        # Compute bounding box from entire layer
        # (OGR Envelope: (xmin, xmax, ymin, ymax))
        layer_extent = self.source_layer.GetExtent()
        (xmin, xmax, ymin, ymax) = layer_extent
        self.layer_bbox = (xmin, xmax, ymin, ymax)

        if crs is None:
            # Attempt to pick a suitable UTM zone
            self.epsg_code = calculate_utm_zone(self.layer_bbox, self.src_epsg)
        else:
            auth_id = crs.authid()  # e.g. "EPSG:4326"
            if auth_id.lower().startswith("epsg:"):
                epsg_int = int(auth_id.split(":")[1])
                log_message(f"EPSG code is: {epsg_int}")
            else:
                # Handle case where it's not an EPSG-based CRS
                epsg_int = None
                raise Exception(f"CRS Passed to function: {crs}. CRS is not an EPSG-based ID: {auth_id}")
            self.epsg_code = epsg_int

        # Prepare OSR objects for source->target transformation
        self.target_spatial_ref = osr.SpatialReference()
        self.target_spatial_ref.ImportFromEPSG(self.epsg_code)

        if self.src_spatial_ref:
            self.coord_transform = osr.CoordinateTransformation(self.src_spatial_ref, self.target_spatial_ref)
        else:
            self.coord_transform = None

        log_message(f"Using output EPSG:{self.epsg_code}")  # noqa: E231

        # Create aligned bounding box in target CRS space
        # We interpret the layer bbox in source CRS (if it has one), transform, and align
        self.transformed_layer_bbox = self.transform_and_align_bbox(self.layer_bbox)
        log_message(f"Transformed layer bbox to target CRS and aligned to grid: {self.transformed_layer_bbox}")
        # Tracking table name
        self.status_table_name = "study_area_creation_status"

    def count_layer_parts(self):
        """
        Returns the number of parts in the layer.

        :return: The number of parts in the layer.
        """
        self.source_layer.ResetReading()
        parts_count = 0
        for feature in self.source_layer:
            geom = feature.GetGeometryRef()
            if not geom:
                continue
            geometry_type = geom.GetGeometryName()
            if geometry_type == "MULTIPOLYGON":
                parts_count += geom.GetGeometryCount()
            else:
                return self.source_layer.GetFeatureCount()
        return parts_count

    def enable_wal_mode(self):
        """Enable SQLite WAL mode for better concurrent access on Windows."""
        try:
            ds = ogr.Open(self.gpkg_path, 1)
            if ds:
                ds.ExecuteSQL("PRAGMA journal_mode=WAL")
                ds.ExecuteSQL("PRAGMA synchronous=NORMAL")
                ds = None
                log_message("Enabled WAL mode for GeoPackage")
        except Exception as e:
            log_message(f"Could not enable WAL mode: {str(e)}", level="WARNING")

    def export_qgs_layer_to_shapefile(self, layer, output_dir):
        """
        Exports a QgsVectorLayer to a Shapefile in output_dir.
        Returns the full path to the .shp (main file).
        """
        # ensure the study area directory exists
        if not os.path.exists(os.path.join(output_dir, "study_area")):
            os.makedirs(os.path.join(output_dir, "study_area"))

        shapefile_path = os.path.join(output_dir, "study_area", "boundaries.shp")
        # Get the project's transform context (required for file writing)
        transform_context = QgsProject.instance().transformContext()
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "ESRI Shapefile"
        options.fileEncoding = "UTF-8"

        if layer.selectedFeatureCount() > 0:
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile  # or OverwriteExistingFile
        else:
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile  # or OverwriteExistingFile

        err = QgsVectorFileWriter.writeAsVectorFormatV3(layer, shapefile_path, transform_context, options)

        if err[0] != QgsVectorFileWriter.NoError:
            raise RuntimeError(f"Failed to export layer to Shapefile: {err[1]}")

        return shapefile_path

    def download_and_process_ghsl(self):
        """
        Download and process GHSL data for the study area.

        Returns:
            str: Layer name in GeoPackage if successful, None otherwise
        """
        try:
            log_message("Starting GHSL download and processing...")

            # Calculate study area extent in Mollweide
            study_area_ds = ogr.Open(self.gpkg_path, 0)
            if not study_area_ds:
                log_message("Could not open study area GeoPackage for GHSL processing", level="WARNING")
                return None

            bbox_layer = study_area_ds.GetLayerByName("study_area_bbox")
            if not bbox_layer:
                log_message("Could not find study_area_bbox layer", level="WARNING")
                study_area_ds = None
                return None

            # Get extent from bbox layer
            extent = bbox_layer.GetExtent()  # (xmin, xmax, ymin, ymax)
            study_area_ds = None

            # Transform extent to Mollweide
            source_srs = self.target_spatial_ref
            mollweide_srs = osr.SpatialReference()
            mollweide_srs.ImportFromEPSG(54009)

            transform_to_mollweide = osr.CoordinateTransformation(source_srs, mollweide_srs)

            # Transform corners to get proper extent
            corners = [
                (extent[0], extent[2]),  # xmin, ymin
                (extent[1], extent[3]),  # xmax, ymax
            ]
            transformed_corners = []
            for x, y in corners:
                point = ogr.Geometry(ogr.wkbPoint)
                point.AddPoint_2D(x, y)
                point.Transform(transform_to_mollweide)
                transformed_corners.append((point.GetX(), point.GetY()))

            # Create Mollweide extent
            mollweide_xmin = min(transformed_corners[0][0], transformed_corners[1][0])
            mollweide_xmax = max(transformed_corners[0][0], transformed_corners[1][0])
            mollweide_ymin = min(transformed_corners[0][1], transformed_corners[1][1])
            mollweide_ymax = max(transformed_corners[0][1], transformed_corners[1][1])

            # Create QgsRectangle for extent_mollweide
            extent_mollweide = QgsRectangle(mollweide_xmin, mollweide_ymin, mollweide_xmax, mollweide_ymax)

            log_message(f"Study area extent in Mollweide: {extent_mollweide.toString()}")

            # Download GHSL using downloader
            log_message("Downloading GHSL tiles...")
            transform_to_4326 = QgsCoordinateTransform(
                QgsCoordinateReferenceSystem("EPSG:54009"),
                QgsCoordinateReferenceSystem("EPSG:4326"),
                QgsProject.instance(),
            )
            extent_4326 = transform_to_4326.transformBoundingBox(extent_mollweide)

            downloader = GHSLDownloader(
                extents=extent_4326,
                output_path=os.path.join(self.working_dir, "study_area"),
                filename="ghsl_temp",
                use_cache=True,
                delete_existing=True,
                feedback=self.feedback,
            )

            # Download and process tiles
            tiles = downloader.tiles_intersecting_bbox()
            if not tiles:
                log_message("No GHSL tiles intersect study area", level="WARNING")
                return None

            log_message(f"Downloading {len(tiles)} GHSL tiles...")
            tile_paths = []
            for tile_id in tiles:
                paths = downloader.download_and_unpack_tile(tile_id)
                tile_paths.extend(paths)

            if not tile_paths:
                log_message("No GHSL tiles downloaded", level="WARNING")
                return None

            # Process tiles
            log_message("Processing GHSL tiles...")
            processor = GHSLProcessor(input_raster_paths=tile_paths)

            # Reclassify
            reclassified = processor.reclassify_rasters(suffix="reclass")

            # Polygonize
            polygonized = processor.polygonize_rasters(reclassified)

            # Combine to temporary GeoParquet
            temp_parquet = os.path.join(self.working_dir, "study_area", "ghsl_temp.parquet")
            processor.combine_vectors(polygonized, temp_parquet, extent=extent_mollweide)

            # Reproject and save to GeoPackage
            log_message("Reprojecting GHSL to study area CRS and saving to GeoPackage...")

            # Read temp parquet
            temp_layer = QgsVectorLayer(temp_parquet, "ghsl_temp", "ogr")
            if not temp_layer.isValid():
                log_message("Could not load temporary GHSL layer", level="WARNING")
                return None

            # Create layer in GeoPackage
            ghsl_layer_name = "ghsl_settlements"
            self.create_ghsl_layer_if_not_exists(ghsl_layer_name)

            # Reproject and write features
            ds = ogr.Open(self.gpkg_path, 1)
            ghsl_layer = ds.GetLayerByName(ghsl_layer_name)

            if not ghsl_layer:
                log_message("Could not create GHSL layer in GeoPackage", level="WARNING")
                ds = None
                return None

            # Transform from Mollweide to target CRS
            transform_from_mollweide = osr.CoordinateTransformation(mollweide_srs, self.target_spatial_ref)

            ghsl_layer.StartTransaction()
            feature_count = 0

            for qgs_feature in temp_layer.getFeatures():
                geom_wkb = qgs_feature.geometry().asWkb()
                ogr_geom = ogr.CreateGeometryFromWkb(bytes(geom_wkb))

                # Transform geometry
                ogr_geom.Transform(transform_from_mollweide)

                # Create feature
                feat_defn = ghsl_layer.GetLayerDefn()
                feature = ogr.Feature(feat_defn)
                feature.SetField("pixel_value", qgs_feature["pixel_value"])
                feature.SetGeometry(ogr_geom)

                ghsl_layer.CreateFeature(feature)
                feature = None
                feature_count += 1

            ghsl_layer.CommitTransaction()
            ds = None

            log_message(f"Successfully added {feature_count} GHSL features to GeoPackage")

            # Clean up temporary file
            if os.path.exists(temp_parquet):
                os.remove(temp_parquet)

            return ghsl_layer_name

        except Exception as e:
            log_message(f"Error downloading/processing GHSL: {str(e)}", level="WARNING")
            log_message(traceback.format_exc(), level="WARNING")
            return None

    def create_ghsl_layer_if_not_exists(self, layer_name):
        """
        Create GHSL layer in GeoPackage if it doesn't exist.
        """
        if not os.path.exists(self.gpkg_path):
            driver = ogr.GetDriverByName("GPKG")
            driver.CreateDataSource(self.gpkg_path)

        ds = ogr.Open(self.gpkg_path, 1)
        layer = ds.GetLayerByName(layer_name)
        if layer is not None:
            ds = None
            return  # Already exists

        # Create layer
        layer = ds.CreateLayer(layer_name, self.target_spatial_ref, geom_type=ogr.wkbPolygon)
        field_defn = ogr.FieldDefn("pixel_value", ogr.OFTInteger)
        layer.CreateField(field_defn)
        ds = None

    def run(self):
        """
        Main entry point (mimics process_study_area from QGIS code).
        """
        try:
            # 1) Create the bounding box as a single polygon feature
            #    and save to GeoPackage
            self.save_bbox_polygon(
                "study_area_bbox",
                self.transformed_layer_bbox,
                "Study Area Bounding Box",
            )

            # Enable WAL mode for better concurrent access
            self.enable_wal_mode()

            # 2) Create the status tracking table
            self.create_status_tracking_table()

            # 2.5) Download and process GHSL data
            self.setProgress(1)  # Trigger UI update for GHSL download
            ghsl_layer_name = self.download_and_process_ghsl()
            if ghsl_layer_name:
                log_message(f"GHSL layer '{ghsl_layer_name}' added to GeoPackage successfully")
                self.ghsl_layer_name = ghsl_layer_name
            else:
                log_message("GHSL download failed or no data available, continuing without GHSL", level="WARNING")
                self.ghsl_layer_name = None

            # 3) Collect all valid geometries first
            self.setProgress(5)  # Reserve 0-5% for GHSL, 5-95% for features
            invalid_feature_count = 0
            self.valid_feature_count = 0
            fixed_feature_count = 0

            # Collect all geometries to process
            geometries_to_process = []
            self.source_layer.ResetReading()
            for feature in self.source_layer:
                geom_ref = feature.GetGeometryRef()
                if not geom_ref:
                    continue

                area_name = feature.GetField(self.field_name)
                if not area_name:
                    area_name = f"area_{feature.GetFID()}"

                # Clean up the name
                normalized_name = re.sub(r"\s+", "_", area_name.lower())

                # Check validity
                if not geom_ref.IsValid():
                    # Attempt a fix
                    log_message(f"Feature {feature.GetFID()} has invalid geometry, attempting to fix.")
                    # OGR >= 3.0 has MakeValid. If unavailable, Buffer(0) can fix many invalid polygons.
                    try:
                        geom_ref = geom_ref.MakeValid()
                        # geom_ref = geom_ref.Buffer(0)
                        if not geom_ref.IsValid():
                            invalid_feature_count += 1
                            log_message(
                                f"Could not fix geometry for feature {feature.GetFID()}. Skipping.",
                                level="CRITICAL",
                            )
                            continue
                        else:
                            fixed_feature_count += 1
                    except Exception as e:
                        invalid_feature_count += 1
                        log_message(f"Geometry fix error: {str(e)}", level="CRITICAL")
                        continue

                self.valid_feature_count += 1

                geom_clone = geom_ref.Clone()
                geom_type = ogr.GT_Flatten(geom_clone.GetGeometryType())

                geometries_to_process.append(
                    {
                        "geometry": geom_clone,
                        "normalized_name": normalized_name,
                        "area_name": area_name,
                        "is_multipart": geom_type == ogr.wkbMultiPolygon,
                    }
                )

            log_message(f"Collected {len(geometries_to_process)} geometries to process")
            self._process_geometries(geometries_to_process)

            self.setProgress(100)  # Trigger the UI to update with completion value
            log_message(
                f"Processing complete. Valid: {self.valid_feature_count}, Fixed: {fixed_feature_count}, Invalid: {invalid_feature_count}"
            )
            log_message(f"Areas that could not be processed due to errors: {self.error_count}")
            log_message(f"Total cells generated: {self.total_cells}")

            # 4) Create a VRT of all generated raster masks
            self.create_raster_vrt()

        except Exception as e:
            log_message(f"Error in run(): {str(e)}")
            log_message(traceback.format_exc())
            with open(os.path.join(self.working_dir, "error.txt"), "w") as f:
                f.write(f"{datetime.datetime.now()}\n")
                f.write(traceback.format_exc())
            return False

        return True

    def _process_geometries(self, geometries_to_process):
        """Process study area geometries in parallel or sequential mode.

        Args:
            geometries_to_process: List of dicts with 'geometry', 'normalized_name', 'area_name', 'is_multipart'
        """
        study_area_workers = int(setting(key="study_area_workers", default=1))
        study_area_workers = max(1, min(4, study_area_workers))

        total_areas = len(geometries_to_process)
        log_message(f"Processing {total_areas} study areas with {study_area_workers} worker(s)")

        if study_area_workers == 1 or total_areas == 1:
            log_message("Using sequential study area processing")
            self._process_geometries_sequential(geometries_to_process)
        else:
            log_message(f"Using parallel study area processing with {study_area_workers} workers")
            try:
                self._process_geometries_parallel(geometries_to_process, study_area_workers)
            except Exception as e:
                log_message(f"Parallel study area processing failed: {str(e)}", level="WARNING")
                log_message("Falling back to sequential processing", level="WARNING")
                log_message(traceback.format_exc(), level="WARNING")
                self._process_geometries_sequential(geometries_to_process)

    def _process_geometries_sequential(self, geometries_to_process):
        """Process study area geometries sequentially.

        Args:
            geometries_to_process: List of geometry dicts to process
        """
        for geom_data in geometries_to_process:
            if geom_data["is_multipart"]:
                log_message(f"Processing multipart geometry: {geom_data['normalized_name']}")
                self.process_multipart_geometry(
                    geom_data["geometry"], geom_data["normalized_name"], geom_data["area_name"]
                )
            else:
                log_message(f"Processing singlepart geometry: {geom_data['normalized_name']}")
                self.process_singlepart_geometry(
                    geom_data["geometry"], geom_data["normalized_name"], geom_data["area_name"]
                )

    def _process_geometries_parallel(self, geometries_to_process, worker_count):
        """Process study area geometries in parallel using ThreadPoolExecutor.

        Args:
            geometries_to_process: List of geometry dicts to process
            worker_count: Number of parallel workers
        """
        completed_count = 0
        failed_count = 0
        progress_lock = threading.Lock()
        total_areas = len(geometries_to_process)

        def process_single_geometry(geom_data):
            """Process a single study area geometry."""
            try:
                if geom_data["is_multipart"]:
                    log_message(f"[Parallel] Processing multipart geometry: {geom_data['normalized_name']}")
                    self.process_multipart_geometry(
                        geom_data["geometry"], geom_data["normalized_name"], geom_data["area_name"]
                    )
                else:
                    log_message(f"[Parallel] Processing singlepart geometry: {geom_data['normalized_name']}")
                    self.process_singlepart_geometry(
                        geom_data["geometry"], geom_data["normalized_name"], geom_data["area_name"]
                    )
                return (True, geom_data["normalized_name"])
            except Exception as e:
                log_message(f"Failed to process {geom_data['normalized_name']}: {str(e)}", level="ERROR")
                log_message(traceback.format_exc(), level="ERROR")
                return (False, geom_data["normalized_name"])

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_geom = {
                executor.submit(process_single_geometry, geom_data): geom_data for geom_data in geometries_to_process
            }

            for future in as_completed(future_to_geom):
                geom_data = future_to_geom[future]
                try:
                    success, name = future.result()

                    with progress_lock:
                        if success:
                            completed_count += 1
                        else:
                            failed_count += 1
                            self.error_count += 1

                        total_processed = completed_count + failed_count
                        try:
                            current_progress = 5 + int((total_processed / total_areas) * 90)
                            log_message(f"Study area progress: {total_processed}/{total_areas} ({current_progress}%)")
                            self.setProgress(current_progress)
                        except ZeroDivisionError:
                            pass

                except Exception as e:
                    with progress_lock:
                        failed_count += 1
                        self.error_count += 1
                    log_message(f"Study area {geom_data['normalized_name']} failed: {str(e)}", level="WARNING")
                    log_message(traceback.format_exc(), level="WARNING")

        if failed_count > 0:
            log_message(f"Study area processing completed with {failed_count} failures", level="WARNING")

    ##########################################################################
    # Table creation logic
    ##########################################################################
    def create_status_tracking_table(self):
        """
        Create a table in the GeoPackage to track processing status,
        similar to the QGIS version.
        """
        if not os.path.exists(self.gpkg_path):
            # Just create it if no GPKG
            driver = ogr.GetDriverByName("GPKG")
            ds = driver.CreateDataSource(self.gpkg_path)
            if not ds:
                raise RuntimeError(f"Could not create GeoPackage {self.gpkg_path}")
            ds = None  # Close

        # Check if table exists
        ds = ogr.Open(self.gpkg_path, 1)  # open in update mode
        if not ds:
            raise RuntimeError(f"Could not open or create {self.gpkg_path} for update.")
        try:
            # If a layer with status_table_name exists, do nothing
            layer = ds.GetLayerByName(self.status_table_name)
            if layer:
                log_message(f"Table '{self.status_table_name}' already exists.")
                return

            # Otherwise, create it
            srs = osr.SpatialReference()
            srs.ImportFromEPSG(4326)  # Arbitrary SRS for table with no geometry

            layer = ds.CreateLayer(self.status_table_name, srs, geom_type=ogr.wkbNone)
            layer.CreateField(ogr.FieldDefn("area_name", ogr.OFTString))
            layer.CreateField(ogr.FieldDefn("timestamp_start", ogr.OFTDateTime))
            layer.CreateField(ogr.FieldDefn("timestamp_end", ogr.OFTDateTime))
            layer.CreateField(ogr.FieldDefn("geometry_processed", ogr.OFTInteger))
            layer.CreateField(ogr.FieldDefn("clip_geometry_processed", ogr.OFTInteger))
            layer.CreateField(ogr.FieldDefn("grid_processed", ogr.OFTInteger))
            layer.CreateField(ogr.FieldDefn("mask_processed", ogr.OFTInteger))
            layer.CreateField(ogr.FieldDefn("grid_creation_duration_secs", ogr.OFTReal))
            layer.CreateField(ogr.FieldDefn("clip_geom_creation_duration_secs", ogr.OFTReal))
            layer.CreateField(ogr.FieldDefn("geom_total_duration_secs", ogr.OFTReal))

            log_message(f"Table '{self.status_table_name}' created in GeoPackage.")
        finally:
            ds = None

    def add_row_to_status_tracking_table(self, area_name):
        """Add new status tracking row with retry logic for SQLite lock handling.

        Args:
            area_name: Name of study area to track
        """
        max_retries = 5
        retry_delay = 0.5

        for attempt in range(max_retries):
            try:
                with self.gpkg_lock:
                    ds = ogr.Open(self.gpkg_path, 1)
                    if not ds:
                        raise RuntimeError(f"Could not open {self.gpkg_path} for update.")
                    ds.ExecuteSQL("PRAGMA busy_timeout = 5000")
                    layer = ds.GetLayerByName(self.status_table_name)
                    if not layer:
                        raise RuntimeError(f"Missing status table layer: {self.status_table_name}")

                    feat_defn = layer.GetLayerDefn()
                    feat = ogr.Feature(feat_defn)
                    feat.SetField("area_name", area_name)
                    feat.SetField("timestamp_start", None)
                    feat.SetField("timestamp_end", None)
                    feat.SetField("geometry_processed", 0)
                    feat.SetField("clip_geometry_processed", 0)
                    feat.SetField("grid_processed", 0)
                    feat.SetField("mask_processed", 0)
                    feat.SetField("grid_creation_duration_secs", 0.0)
                    feat.SetField("clip_geom_creation_duration_secs", 0.0)
                    feat.SetField("geom_total_duration_secs", 0.0)
                    layer.CreateFeature(feat)
                    feat = None
                    ds = None
                return
            except RuntimeError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    log_message(
                        f"Database locked, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})",
                        level="WARNING",
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise

    def set_status_tracking_table_value(self, area_name, field_name, value):
        """Update status tracking field with retry logic for SQLite lock handling.

        Args:
            area_name: Name of study area
            field_name: Field to update
            value: New value for field
        """
        max_retries = 5
        retry_delay = 0.5

        for attempt in range(max_retries):
            try:
                with self.gpkg_lock:
                    ds = ogr.Open(self.gpkg_path, 1)
                    if not ds:
                        raise RuntimeError(f"Could not open {self.gpkg_path} for update.")
                    ds.ExecuteSQL("PRAGMA busy_timeout = 5000")
                    layer = ds.GetLayerByName(self.status_table_name)
                    if not layer:
                        raise RuntimeError(f"Missing status table layer: {self.status_table_name}")

                    layer.SetAttributeFilter(f"area_name = '{area_name}'")
                    for feature in layer:
                        feature.SetField(field_name, value)
                        layer.SetFeature(feature)
                    layer.ResetReading()
                    ds = None
                log_message(f"Updated {field_name} for {area_name} to {value}")
                return
            except RuntimeError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    log_message(
                        f"Database locked, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})",
                        level="WARNING",
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise

    ##########################################################################
    # Geometry processing
    ##########################################################################
    def process_singlepart_geometry(self, geom, normalized_name, area_name):
        """
        Process a single-part geometry:
         1) Align bounding box
         2) Save bounding box as a feature
         3) Transform geometry
         4) Save geometry
         5) Create vector grid
         6) Create clip polygon
         7) Optionally create raster mask
        """
        geometry_start_time = time.time()

        now = datetime.datetime.now()  # Get current datetime
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")  # Format the datetime object

        self.set_status_tracking_table_value(normalized_name, "timestamp_start", now_str)

        #  Check we have a single part geom
        geom_type = ogr.GT_Flatten(geom.GetGeometryType())
        if geom_type != ogr.wkbPolygon:
            log_message(f"Skipping non-polygon geometry type {geom_type} for {normalized_name}.")
            return
        # check it has only one part
        if geom.GetGeometryCount() > 1:
            log_message(
                f"Skipping multi-part geometry for {normalized_name}.",
                level="WARNING",
            )
            return
        # Compute aligned bounding box in target CRS
        # (We already have a coordinate transformation if the source has a known SRS)
        geometry_bbox = geom.GetEnvelope()  # (xmin, xmax, ymin, ymax)
        aligned_bbox = self.transform_and_align_bbox(geometry_bbox)

        # Save the bounding box for this geometry
        self.save_bbox_polygon("study_area_bboxes", aligned_bbox, normalized_name)

        # Add a row to the tracking table
        self.add_row_to_status_tracking_table(normalized_name)

        # If needed, transform the geometry to target CRS
        # (Only if we have the coordinate transform)
        if self.coord_transform:
            geom.Transform(self.coord_transform)

        # Check GHSL intersection
        intersects_ghsl = self.check_ghsl_intersection(geom)
        log_message(f"{normalized_name} intersects GHSL: {intersects_ghsl}")

        # Save the geometry (in the target CRS) to "study_area_polygons"
        self.save_geometry_to_geopackage("study_area_polygons", geom, normalized_name, intersects_ghsl)
        self.set_status_tracking_table_value(normalized_name, "geometry_processed", 1)

        # Check if we should filter areas without GHSL settlements
        filter_enabled = bool(setting(key="filter_study_areas_by_ghsl", default=True))
        if filter_enabled and not intersects_ghsl:
            log_message(
                f"Skipping {normalized_name} - no GHSL settlements found (filter_study_areas_by_ghsl=True)",
                level="INFO",
            )
            # Update progress counter and return early
            self.counter += 1
            progress = int((self.counter / self.parts_count) * 100)
            self.setProgress(progress)
            log_message(f"XXXXXXXXXXXX   Progress: {progress}% XXXXXXXXXXXXXXXXXXXXXXX")
            return

        # Create the grid
        log_message(f"Creating vector grid for {normalized_name}.")
        start_time = time.time()
        self.create_and_save_grid(normalized_name, geom, aligned_bbox)
        self.set_status_tracking_table_value(normalized_name, "grid_processed", 1)
        self.set_status_tracking_table_value(normalized_name, "grid_creation_duration_secs", time.time() - start_time)

        log_message(f"Creating clip polygon for {normalized_name}.")
        start_time = time.time()
        self.create_clip_polygon(geom, aligned_bbox, normalized_name)
        self.set_status_tracking_table_value(normalized_name, "clip_geometry_processed", 1)
        self.set_status_tracking_table_value(
            normalized_name,
            "clip_geom_creation_duration_secs",
            time.time() - start_time,
        )

        log_message(f"Creating raster mask for {normalized_name}.")
        self.create_raster_mask(geom, aligned_bbox, normalized_name)
        self.set_status_tracking_table_value(normalized_name, "mask_processed", 1)
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.set_status_tracking_table_value(normalized_name, "timestamp_end", now_str)
        self.set_status_tracking_table_value(
            normalized_name,
            "geom_total_duration_secs",
            time.time() - geometry_start_time,
        )
        self.counter += 1
        progress = int((self.counter / self.parts_count) * 100)
        self.setProgress(progress)
        log_message(f"XXXXXXXXXXXX   Progress: {progress}% XXXXXXXXXXXXXXXXXXXXXXX")

    def process_multipart_geometry(self, geom, normalized_name, area_name):
        """Process each part of a multi-part geometry with parallel or sequential execution.

        Args:
            geom: OGR multi-part geometry
            normalized_name: Base name for the area
            area_name: Original area name
        """
        count = geom.GetGeometryCount()
        log_message(f"Processing {count} parts for {normalized_name}")

        parts_to_process = []
        for i in range(count):
            part_geom = geom.GetGeometryRef(i)
            part_name = f"{normalized_name}_part{i}"
            parts_to_process.append((part_geom.Clone(), part_name))

        part_workers = 1  # Sequential processing to avoid database lock contention

        if part_workers == 1 or count == 1:
            log_message(f"Processing {count} parts sequentially")
            self._process_parts_sequential(parts_to_process, area_name)
        else:
            log_message(f"Processing {count} parts with {part_workers} workers")
            try:
                self._process_parts_parallel(parts_to_process, area_name, part_workers)
            except Exception as e:
                log_message(f"Parallel part processing failed: {str(e)}", level="WARNING")
                log_message("Falling back to sequential part processing", level="WARNING")
                log_message(traceback.format_exc(), level="WARNING")
                self._process_parts_sequential(parts_to_process, area_name)

    def _process_parts_sequential(self, parts_to_process, area_name):
        """Process geometry parts sequentially.

        Args:
            parts_to_process: List of (geometry, name) tuples
            area_name: Original area name
        """
        for part_geom, part_name in parts_to_process:
            try:
                self.process_singlepart_geometry(part_geom, part_name, area_name)
            except Exception as e:
                log_message(f"Failed to process part {part_name}: {str(e)}", level="ERROR")
                self.error_count += 1

    def _process_parts_parallel(self, parts_to_process, area_name, worker_count):
        """Process geometry parts in parallel using ThreadPoolExecutor.

        Args:
            parts_to_process: List of (geometry, name) tuples
            area_name: Original area name
            worker_count: Number of parallel workers
        """
        failed_count = 0
        progress_lock = threading.Lock()

        def process_single_part(part_data):
            """Process single geometry part in worker thread."""
            part_geom, part_name = part_data
            try:
                self.process_singlepart_geometry(part_geom, part_name, area_name)
                return (True, part_name)
            except Exception as e:
                log_message(f"Failed to process part {part_name}: {str(e)}", level="ERROR")
                log_message(traceback.format_exc(), level="ERROR")
                return (False, part_name)

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_part = {
                executor.submit(process_single_part, part_data): part_data for part_data in parts_to_process
            }

            for future in as_completed(future_to_part):
                part_data = future_to_part[future]
                try:
                    success, part_name = future.result()
                    if not success:
                        with progress_lock:
                            failed_count += 1
                            self.error_count += 1
                    else:
                        log_message(f"Part {part_name} completed successfully")
                except Exception as e:
                    with progress_lock:
                        failed_count += 1
                        self.error_count += 1
                    log_message(f"Part {part_data[1]} failed: {str(e)}", level="WARNING")

        if failed_count > 0:
            log_message(f"Part processing completed with {failed_count} failures", level="WARNING")

    ##########################################################################
    # BBox handling
    ##########################################################################
    def transform_and_align_bbox(self, bbox):
        """
        BBox is (xmin, xmax, ymin, ymax). Transform to target CRS if possible,
        then align to cell_size_m grid.
        Returns new (xmin, xmax, ymin, ymax) in target CRS.
        """
        (xmin, xmax, ymin, ymax) = bbox

        # If we have a coordinate transform, we need to convert min/max
        # We'll do a polygon-based approach to ensure correctness
        if self.coord_transform:
            corner_points = [
                (xmin, ymin),
                (xmin, ymax),
                (xmax, ymax),
                (xmax, ymin),
            ]
            # Transform each corner
            transformed_corners = []
            for x, y in corner_points:
                point = ogr.Geometry(ogr.wkbPoint)
                point.AddPoint_2D(x, y)
                point.Transform(self.coord_transform)
                transformed_corners.append((point.GetX(), point.GetY()))

            # Recompute envelope from transformed corners
            xs = [pt[0] for pt in transformed_corners]
            ys = [pt[1] for pt in transformed_corners]
            xmin, xmax = min(xs), max(xs)
            ymin, ymax = min(ys), max(ys)

        log_message(f"Transformed bbox pre-alignment: {xmin}, {xmax}, {ymin}, {ymax}")
        # Now align to the cell size
        cell_size = self.cell_size_m

        def snap_down(value, base):
            """🔄 Snap down.

            Args:
                value: Value.
                base: Base.

            Returns:
                The result of the operation.
            """
            return (int(value // base)) * base

        def snap_up(value, base):
            """🔄 Snap up.

            Args:
                value: Value.
                base: Base.

            Returns:
                The result of the operation.
            """
            return (int(value // base) + 1) * base

        # Snap bounding values outward so we always cover the full geometry
        x_min_snap = snap_down(xmin, cell_size) - cell_size
        y_min_snap = snap_down(ymin, cell_size) - cell_size
        x_max_snap = snap_up(xmax, cell_size) + cell_size
        y_max_snap = snap_up(ymax, cell_size) + cell_size
        log_message(
            f"Aligned bbox                  : {x_min_snap}, {x_max_snap}, {y_min_snap}, {y_max_snap}"  # noqa: E231, E203
        )
        return (x_min_snap, x_max_snap, y_min_snap, y_max_snap)

    def save_bbox_polygon(self, layer_name, bbox, area_name):
        """
        Save a bounding-box polygon to the specified layer (creating it if needed).
        """
        # BBox is (xmin, xmax, ymin, ymax)
        (xmin, xmax, ymin, ymax) = bbox
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(xmin, ymin)
        ring.AddPoint(xmin, ymax)
        ring.AddPoint(xmax, ymax)
        ring.AddPoint(xmax, ymin)
        ring.AddPoint(xmin, ymin)
        polygon = ogr.Geometry(ogr.wkbPolygon)
        polygon.AddGeometry(ring)
        self.save_geometry_to_geopackage(layer_name, polygon, area_name)

    ##########################################################################
    # Write geometry to GPKG layers
    ##########################################################################
    def check_ghsl_intersection(self, geom):
        """
        Check if a geometry intersects with any GHSL settlement features.

        Args:
            geom: OGR geometry to check (already in target CRS)

        Returns:
            bool: True if intersects any GHSL feature, False otherwise
        """
        # Check if GHSL layer exists
        if not hasattr(self, "ghsl_layer_name") or self.ghsl_layer_name is None:
            log_message("GHSL layer not available, defaulting to True for intersection", level="INFO")
            return True

        try:
            # Open GeoPackage and get GHSL layer
            ds = ogr.Open(self.gpkg_path, 0)
            if not ds:
                log_message("Could not open GeoPackage for GHSL check", level="WARNING")
                return True

            ghsl_layer = ds.GetLayerByName(self.ghsl_layer_name)
            if not ghsl_layer:
                log_message(f"GHSL layer '{self.ghsl_layer_name}' not found", level="WARNING")
                ds = None
                return True

            # Set spatial filter using geometry
            ghsl_layer.SetSpatialFilter(geom)

            # Check if any features intersect
            intersects = False
            for ghsl_feature in ghsl_layer:
                ghsl_geom = ghsl_feature.GetGeometryRef()
                if ghsl_geom and geom.Intersects(ghsl_geom):
                    intersects = True
                    break

            # Clean up
            ghsl_layer.SetSpatialFilter(None)
            ds = None

            return intersects

        except Exception as e:
            log_message(f"Error checking GHSL intersection: {str(e)}", level="WARNING")
            return True  # Default to True on error

    def save_geometry_to_geopackage(self, layer_name, geom, area_name, intersects_ghsl=True):
        """Append a single geometry to a layer in GPKG.

        Args:
            layer_name: Name of the layer
            geom: OGR geometry
            area_name: Name of the area
            intersects_ghsl: Whether geometry intersects GHSL
        """
        self.create_layer_if_not_exists(layer_name)
        with self.gpkg_lock:
            ds = ogr.Open(self.gpkg_path, 1)
            layer = ds.GetLayerByName(layer_name)
            if not layer:
                raise RuntimeError(f"Could not open target layer {layer_name} in {self.gpkg_path}")

            feat_defn = layer.GetLayerDefn()
            feature = ogr.Feature(feat_defn)
            feature.SetField("area_name", area_name)

            # Set intersects_ghsl field if this is study_area_polygons layer
            if layer_name == "study_area_polygons":
                feature.SetField("intersects_ghsl", 1 if intersects_ghsl else 0)

            feature.SetGeometry(geom)
            layer.CreateFeature(feature)
            feature = None
            ds = None

    def create_layer_if_not_exists(self, layer_name):
        """Create a GPKG layer if it does not exist."""
        with self.gpkg_lock:
            if not os.path.exists(self.gpkg_path):
                driver = ogr.GetDriverByName("GPKG")
                driver.CreateDataSource(self.gpkg_path)

            ds = ogr.Open(self.gpkg_path, 1)
            layer = ds.GetLayerByName(layer_name)
            if layer is not None:
                ds = None
                return

            layer = ds.CreateLayer(layer_name, self.target_spatial_ref, geom_type=ogr.wkbPolygon)
            field_defn = ogr.FieldDefn("area_name", ogr.OFTString)
            layer.CreateField(field_defn)

            if layer_name == "study_area_polygons":
                intersects_field = ogr.FieldDefn("intersects_ghsl", ogr.OFTInteger)
                layer.CreateField(intersects_field)

            ds = None

    # Helper to update time spent in a named metric block
    def track_time(self, metric_name, start_time):
        """⚙️ Track time.

        Args:
            metric_name: Metric name.
            start_time: Start time.
        """
        self.metrics[metric_name] += time.time() - start_time

    ##########################################################################
    # Write Queue Management
    ##########################################################################
    def _start_writer_thread(self, layer, normalized_name):
        """Start dedicated writer thread for async writing (thread-safe singleton with ref counting)."""
        with self.writer_start_lock:
            self.writer_ref_count += 1

            if self.writer_thread is not None and self.writer_thread.is_alive():
                log_message(
                    f"Writer thread already running (ref_count={self.writer_ref_count}), reusing existing thread"
                )
                return

            log_message(f"Starting new writer thread (ref_count={self.writer_ref_count})")
            self.write_queue = Queue()

            # Open persistent connection to prevent invalidation when parts close their datasets
            writer_ds = ogr.Open(self.gpkg_path, 1)
            if not writer_ds:
                raise RuntimeError(f"Writer thread could not open {self.gpkg_path}")
            self.writer_layer = writer_ds.GetLayerByName("study_area_grid")
            if not self.writer_layer:
                raise RuntimeError("Writer thread could not open study_area_grid layer")
            self.writer_ds = writer_ds

            def writer_worker():
                """Process write queue in batches. Queue items are (geometry, area_name) tuples."""
                batch = []
                batch_size = 10000
                items_in_batch = 0

                while True:
                    item = self.write_queue.get()

                    if item is None:  # Poison pill signals shutdown
                        if batch:
                            self._write_batch(self.writer_layer, batch)
                        for _ in range(items_in_batch):
                            self.write_queue.task_done()
                        self.write_queue.task_done()
                        break

                    batch.append(item)
                    items_in_batch += 1

                    if len(batch) >= batch_size:
                        self._write_batch(self.writer_layer, batch)
                        for _ in range(items_in_batch):
                            self.write_queue.task_done()
                        batch = []
                        items_in_batch = 0

            self.writer_thread = Thread(target=writer_worker, daemon=False)
            self.writer_thread.start()
            log_message("Writer thread started")

    def _stop_writer_thread(self):
        """Stop writer thread with ref counting. Only stops when last part finishes.

        Returns:
            bool: True if writer was stopped, False if still in use by other parts
        """
        with self.writer_start_lock:
            self.writer_ref_count -= 1
            log_message(f"Writer thread ref count: {self.writer_ref_count}")

            if self.writer_ref_count > 0:
                log_message(f"Writer thread still in use by {self.writer_ref_count} part(s), not stopping")
                return False

            log_message("All parts finished, stopping writer thread")
            if self.write_queue is not None:
                self.write_queue.put(None)
                self.write_queue.join()
                if self.writer_thread is not None:
                    self.writer_thread.join()
                log_message("Writer thread stopped")

            if self.writer_ds:
                self.writer_ds.FlushCache()
                self.writer_ds = None
            self.writer_layer = None
            log_message("Writer dataset closed")
            return True

    def _write_batch(self, layer, items):
        """Write batch of (geometry, area_name) tuples in single transaction."""
        start_time = time.time()
        feat_defn = layer.GetLayerDefn()

        layer.StartTransaction()
        try:
            for geometry, area_name in items:
                feature = ogr.Feature(feat_defn)

                with self.grid_id_lock:
                    feature.SetField("grid_id", self.current_geom_actual_cell_count)
                    self.current_geom_actual_cell_count += 1
                    grid_id = self.current_geom_actual_cell_count

                feature.SetField("area_name", area_name)
                feature.SetGeometry(geometry)
                layer.CreateFeature(feature)
                feature = None

                if grid_id % 20000 == 0:
                    log_message(f"         Cell count: {grid_id}")
                    log_message(f"         Grid creation for part {area_name}")

            layer.CommitTransaction()
            self.track_time("Writing chunks", start_time)
            log_message(f"Wrote batch of {len(items)} features")
        except Exception as e:
            layer.RollbackTransaction()
            log_message(f"Batch write error: {str(e)}", level="ERROR")
            log_message(f"Batch write traceback: {traceback.format_exc()}", level="ERROR")
            raise

    def create_and_save_grid(self, normalized_name, geom, bbox):
        """Create vector grid and write intersecting cells to study_area_grid layer.

        Args:
            normalized_name: Name of study area
            geom: OGR geometry defining area boundary
            bbox: Tuple of (xmin, xmax, ymin, ymax) for grid extent
        """
        grid_layer_name = "study_area_grid"
        self.create_grid_layer_if_not_exists(grid_layer_name)

        ds = ogr.Open(self.gpkg_path, 1)  # read-write
        layer = ds.GetLayerByName(grid_layer_name)
        if not layer:
            raise RuntimeError(f"Could not open {grid_layer_name} for writing.")

        xmin, xmax, ymin, ymax = bbox
        cell_size = self.cell_size_m
        chunk_size = int(setting(key="chunk_size", default=50))

        chunker = GridChunkerTask(
            xmin,
            xmax,
            ymin,
            ymax,
            cell_size,
            chunk_size=chunk_size,
            epsg=self.epsg_code,
            geometry=geom.ExportToWkb(),
        )

        max_retries = 5
        retry_delay = 0.5
        for attempt in range(max_retries):
            try:
                with self.gpkg_lock:
                    chunker.write_chunks_to_gpkg(self.gpkg_path)
                break
            except RuntimeError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    log_message(
                        f"Chunk metadata write locked, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})",
                        level="WARNING",
                    )
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 5.0)
                else:
                    raise

        log_message(f"Creating grid for extents: xmin {xmin}, xmax {xmax}, ymin {ymin}, ymax {ymax}")

        feedback = QgsFeedback()

        chunk_count = chunker.total_chunks()
        log_message(f"Chunk count: {chunk_count}")
        log_message(f"Chunk size: {chunk_size}")

        chunks_to_process = []
        for chunk in chunker.chunks():
            if chunk["type"] != "undefined":
                chunks_to_process.append(chunk)
            else:
                log_message(f"Chunk {chunk['index']} is outside the geometry.")

        valid_chunk_count = len(chunks_to_process)
        log_message(f"Valid chunks to process: {valid_chunk_count}")

        worker_count = int(setting(key="grid_creation_workers", default=4))
        worker_count = max(1, min(8, worker_count))

        self.feedback.setProgress(0)

        # Start dedicated writer thread
        self._start_writer_thread(layer, normalized_name)

        try:
            if worker_count == 1:
                log_message("Using sequential processing (worker_count=1)")
                self._process_chunks_sequential(layer, chunks_to_process, geom, cell_size, normalized_name, feedback)
            else:
                log_message(f"Using parallel processing with {worker_count} workers")
                self._process_chunks_parallel(
                    layer, chunks_to_process, geom, cell_size, normalized_name, feedback, worker_count
                )
        except Exception as e:
            log_message(f"Parallel processing failed: {str(e)}", level="WARNING")
            log_message("Falling back to sequential processing", level="WARNING")
            log_message(traceback.format_exc(), level="WARNING")
            self._process_chunks_sequential(layer, chunks_to_process, geom, cell_size, normalized_name, feedback)
        finally:
            writer_stopped = self._stop_writer_thread()

            if writer_stopped:
                if layer:
                    layer.SyncToDisk()
                if ds:
                    ds.FlushCache()
                ds = None
                log_message("Dataset closed and flushed to disk")
        # ----------------------------
        # Print out metrics summary
        # ----------------------------
        log_message("=== Metrics Summary ===")
        for k, v in self.metrics.items():
            log_message(f"{k}: {v:.4f} seconds")  # noqa: E231
        self.total_cells += self.current_geom_actual_cell_count
        log_message(f"Grid creation completed for area {normalized_name}.")

    def _process_chunks_sequential(self, layer, chunks, geom, cell_size, normalized_name, feedback):
        """Process chunks sequentially (original implementation).

        Args:
            layer: OGR layer for writing grid cells.
            chunks: List of chunk dictionaries to process.
            geom: OGR geometry for intersection testing.
            cell_size: Cell size in meters.
            normalized_name: Name of the study area.
            feedback: QgsFeedback for progress reporting.
        """
        total_chunks = len(chunks)
        for counter, chunk in enumerate(chunks, start=1):
            start_time = time.time()
            index = chunk["index"]

            task = GridFromBboxTask(
                index,
                (chunk["x_start"], chunk["x_end"], chunk["y_start"], chunk["y_end"]),
                geom,
                cell_size,
                feedback,
            )
            self.track_time("Creating chunks", start_time)
            task.run()

            self.write_chunk(layer, task, normalized_name)

            # Update progress
            try:
                current_progress = int((counter / total_chunks) * 100)
                log_message(f"XXXXXX Chunks Progress: {counter} / {total_chunks} : {current_progress}% XXXXXX")
                self.feedback.setProgress(current_progress)
            except ZeroDivisionError:
                pass

            self.track_time("Complete chunk", start_time)

    def _process_chunks_parallel(self, layer, chunks, geom, cell_size, normalized_name, feedback, worker_count):
        """Process chunks in parallel using ThreadPoolExecutor.

        Args:
            layer: OGR layer for writing grid cells
            chunks: List of chunk dictionaries to process
            geom: OGR geometry for intersection testing
            cell_size: Cell size in meters
            normalized_name: Name of the study area
            feedback: QgsFeedback for progress reporting
            worker_count: Number of parallel workers
        """
        total_chunks = len(chunks)
        completed_count = 0
        failed_count = 0
        progress_lock = threading.Lock()

        def process_single_chunk(chunk):
            """Process single chunk in worker thread."""
            start_time = time.time()
            index = chunk["index"]

            task = GridFromBboxTask(
                index,
                (chunk["x_start"], chunk["x_end"], chunk["y_start"], chunk["y_end"]),
                geom,
                cell_size,
                feedback,
            )
            task.run()

            return (task, start_time, index)

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_chunk = {executor.submit(process_single_chunk, chunk): chunk for chunk in chunks}

            for future in as_completed(future_to_chunk):
                chunk = future_to_chunk[future]
                try:
                    task, start_time, index = future.result()
                    self.track_time("Creating chunks", start_time)

                    self.write_chunk(layer, task, normalized_name)

                    with progress_lock:
                        completed_count += 1
                        try:
                            current_progress = int((completed_count / total_chunks) * 100)
                            log_message(
                                f"XXXXXX Chunk {index} completed ({completed_count}/{total_chunks}): {current_progress}% XXXXXX"
                            )
                            self.feedback.setProgress(current_progress)
                        except ZeroDivisionError:
                            pass

                    self.track_time("Complete chunk", start_time)

                except Exception as e:
                    with progress_lock:
                        failed_count += 1
                    log_message(f"Chunk {chunk['index']} failed: {str(e)}", level="WARNING")
                    log_message(traceback.format_exc(), level="WARNING")

        if failed_count > 0:
            log_message(f"Grid creation completed with {failed_count} failed chunks", level="WARNING")

    def write_chunk(self, layer, task, normalized_name):
        """Queue features for async batched writing by dedicated writer thread.

        Args:
            layer: Unused (kept for compatibility)
            task: GridFromBboxTask with generated features
            normalized_name: Area name for this chunk
        """
        log_message(f"Queueing {len(task.features_out)} features for writing (area: {normalized_name})")
        self.track_time("Preparing chunks", task.run_time)

        for geometry in task.features_out:
            self.write_queue.put((geometry, normalized_name))

    def create_grid_layer_if_not_exists(self, layer_name):
        """
        Create a grid layer with 'grid_id' as integer field
        and a polygon geometry if it does not exist.
        """
        with self.gpkg_lock:
            if not os.path.exists(self.gpkg_path):
                driver = ogr.GetDriverByName("GPKG")
                driver.CreateDataSource(self.gpkg_path)

            ds = ogr.Open(self.gpkg_path, 1)
            layer = ds.GetLayerByName(layer_name)
            if layer is None:
                layer = ds.CreateLayer(layer_name, self.target_spatial_ref, geom_type=ogr.wkbPolygon)
                field_defn = ogr.FieldDefn("grid_id", ogr.OFTInteger)
                layer.CreateField(field_defn)
                field_defn = ogr.FieldDefn("area_name", ogr.OFTString)
                layer.CreateField(field_defn)
            ds = None

    ##########################################################################
    # Create Clip Polygon
    ##########################################################################
    def create_clip_polygon(self, geom, aligned_box, normalized_name):
        """
        Creates a polygon that includes the original geometry plus all grid cells
        that intersect the boundary of the geometry. Then dissolves them into one polygon.
        """
        # 1) We load the grid from GPKG
        grid_ds = ogr.Open(self.gpkg_path, 0)
        grid_layer = grid_ds.GetLayerByName("study_area_grid")
        if not grid_layer:
            raise RuntimeError("Missing study_area_grid layer.")

        # We'll do a bounding box filter for performance
        (xmin, ymin, xmax, ymax) = aligned_box
        grid_layer.SetSpatialFilterRect(xmin, ymin, xmax, ymax)

        boundary = geom.GetBoundary()
        log_message(f"Finding grid cells that intersect boundary for {normalized_name}")

        all_cells = []
        grid_layer.ResetReading()
        for f in grid_layer:
            cell_geom = f.GetGeometryRef()
            if cell_geom:
                all_cells.append(cell_geom.Clone())
        grid_layer.ResetReading()
        grid_layer.SetSpatialFilter(None)  # Clear filter

        total_cells = len(all_cells)
        log_message(f"Checking {total_cells} grid cells for intersection with boundary")

        def check_intersection(cell_geom):
            if boundary.Intersects(cell_geom):
                return cell_geom
            return None

        intersecting_cells = []
        worker_count = min(4, total_cells)

        if worker_count > 1 and total_cells > 100:
            log_message(f"Using parallel intersection checking with {worker_count} workers")
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                results = executor.map(check_intersection, all_cells)
                intersecting_cells = [cell for cell in results if cell is not None]
        else:
            log_message("Using sequential intersection checking")
            for cell_geom in all_cells:
                if boundary.Intersects(cell_geom):
                    intersecting_cells.append(cell_geom)

        log_message(f"Found {len(intersecting_cells)} cells intersecting boundary, performing batch union")

        intersecting_cells.append(geom.Clone())

        if len(intersecting_cells) == 0:
            dissolved_geom = geom.Clone()
        elif len(intersecting_cells) == 1:
            dissolved_geom = intersecting_cells[0]
        else:
            multi_geom = ogr.Geometry(ogr.wkbMultiPolygon)
            for cell in intersecting_cells:
                if cell.GetGeometryType() == ogr.wkbPolygon:
                    multi_geom.AddGeometry(cell)

            dissolved_geom = multi_geom.UnionCascaded()
            log_message(f"Batch union completed for {len(intersecting_cells)} geometries")

        self.save_geometry_to_geopackage("study_area_clip_polygons", dissolved_geom, normalized_name)
        log_message(f"Created clip polygon: {normalized_name}")

    def chunk_bbox(self, xmin, xmax, ymin, ymax, cell_size, chunk_size=1000):
        """Generate bounding box chunks for grid processing.

        Args:
            xmin: Minimum X coordinate
            xmax: Maximum X coordinate
            ymin: Minimum Y coordinate
            ymax: Maximum Y coordinate
            cell_size: Size of grid cells in meters
            chunk_size: Number of cells per chunk (default: 1000)

        Yields:
            Tuple of (x_start, x_end, y_start, y_end) for each chunk
        """
        x_range_count = int((xmax - xmin) / cell_size)
        y_range_count = int((ymax - ymin) / cell_size)

        x_blocks = range(0, x_range_count, chunk_size)
        y_blocks = range(0, y_range_count, chunk_size)
        for x_block_start in x_blocks:
            log_message(f"Processing chunk {x_block_start} of {x_range_count}")
            x_block_end = min(x_block_start + chunk_size, x_range_count)

            x_start_coord = xmin + x_block_start * cell_size
            x_end_coord = xmin + x_block_end * cell_size

            for y_block_start in y_blocks:
                log_message(f"Processing chunk {y_block_start} of {y_range_count}")
                y_block_end = min(y_block_start + chunk_size, y_range_count)

                y_start_coord = ymin + y_block_start * cell_size
                y_end_coord = ymin + y_block_end * cell_size

                log_message(f"Created Chunk bbox: {x_start_coord}, {x_end_coord}, {ymin}, {ymax}")
                yield (x_start_coord, x_end_coord, y_start_coord, y_end_coord)

    ##########################################################################
    # Create Raster Mask
    ##########################################################################
    def create_raster_mask(self, geom, aligned_box, mask_name):
        """
        Creates a 1-bit raster mask for a single geometry using gdal.Rasterize.
        """
        mask_filepath = os.path.join(self.working_dir, "study_area", f"{mask_name}.tif")

        driver_mem = ogr.GetDriverByName("Memory")
        mem_ds = driver_mem.CreateDataSource("temp")
        mem_lyr = mem_ds.CreateLayer("temp_mask_layer", self.target_spatial_ref, geom_type=ogr.wkbPolygon)

        # Create a field to burn
        field_def = ogr.FieldDefn("burnval", ogr.OFTInteger)
        mem_lyr.CreateField(field_def)

        # Create feature
        feat_defn = mem_lyr.GetLayerDefn()
        feat = ogr.Feature(feat_defn)
        feat.SetField("burnval", 1)
        feat.SetGeometry(geom.Clone())
        mem_lyr.CreateFeature(feat)
        feat = None

        # Now call gdal.Rasterize
        x_res = self.cell_size_m
        y_res = self.cell_size_m

        (xmin, xmax, ymin, ymax) = aligned_box

        # For pixel width/height, we can compute:
        # width in coordinate space: (xmax - xmin)
        width = int((xmax - xmin) / x_res)
        height = int((ymax - ymin) / y_res)
        if width < 1 or height < 1:
            log_message("Extent is too small for raster creation. Skipping mask.")
            return

        # Create the raster
        # NB: gdal.GetDriverByName('GTiff').Create() expects col, row order
        target_ds = gdal.GetDriverByName("GTiff").Create(
            mask_filepath,
            width,
            height,
            1,  # 1 band
            gdal.GDT_Byte,
            options=["NBITS=1"],  # 1-bit
        )
        if not target_ds:
            raise RuntimeError(f"Could not create raster {mask_filepath}")

        # Set geotransform (origin x, pixel width, rotation, origin y, rotation, pixel height)
        # Note y_res is negative if north-up. We'll use negative for correct alignment in typical north-up data
        geotransform = (xmin, x_res, 0.0, ymax, 0.0, -y_res)
        target_ds.SetGeoTransform(geotransform)
        target_ds.SetProjection(self.target_spatial_ref.ExportToWkt())

        # Rasterize
        err = gdal.RasterizeLayer(
            target_ds,
            [1],  # bands
            mem_lyr,  # layer
            burn_values=[1],  # burn value for the feature
            options=["ALL_TOUCHED=TRUE"],
        )
        if err != 0:
            log_message(f"Error in RasterizeLayer: {err}", level="CRITICAL")

        target_ds.FlushCache()
        target_ds = None
        mem_ds = None

        log_message(f"Created raster mask: {mask_filepath}")
        return mask_filepath

    ##########################################################################
    # Create VRT
    ##########################################################################
    def create_raster_vrt(self, output_vrt_name="combined_mask.vrt"):
        """
        Creates a VRT file from all .tif masks in the 'study_area' dir using
        gdal.BuildVRT (Python API) or gdalbuildvrt approach.
        """
        raster_dir = os.path.join(self.working_dir, "study_area")
        raster_files = glob.glob(os.path.join(raster_dir, "*.tif"))

        if not raster_files:
            log_message("No raster masks found to build VRT.")
            return

        vrt_filepath = os.path.join(raster_dir, output_vrt_name)
        log_message(f"Building VRT: {vrt_filepath}")

        # Use gdal.BuildVRT
        vrt = gdal.BuildVRT(vrt_filepath, raster_files, separate=False)
        if vrt is None:
            log_message("Failed to create VRT.", level="CRITICAL")
            return
        vrt.FlushCache()
        vrt = None

        log_message(f"Created VRT: {vrt_filepath}")

    ##########################################################################
    # Directory creation
    ##########################################################################
    def create_study_area_directory(self, working_dir):
        """
        Create 'study_area' subdir if not exist
        """
        study_area_dir = os.path.join(working_dir, "study_area")
        if not os.path.exists(study_area_dir):
            os.makedirs(study_area_dir)
            log_message(f"Created directory {study_area_dir}")

    ##############################################################################
