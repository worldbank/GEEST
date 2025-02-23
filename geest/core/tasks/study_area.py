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
    QgsVectorFileWriter,
    QgsProject,
)
from geest.utilities import log_message
from .grid_from_bbox import GridFromBbox
from .grid_chunker import GridChunker
from geest.core import setting


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
        self.write_lock = False
        # Make sure output directory exists
        self.create_study_area_directory(self.working_dir)

        # If GPKG already exists, remove it to start fresh
        if os.path.exists(self.gpkg_path):
            try:
                os.remove(self.gpkg_path)
                log_message(f"Removed existing GeoPackage: {self.gpkg_path}")
            except Exception as e:
                log_message(
                    f"Error removing existing GeoPackage: {e}", level="CRITICAL"
                )

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
            self.epsg_code = self.calculate_utm_zone(self.layer_bbox, self.src_epsg)
        else:
            auth_id = crs.authid()  # e.g. "EPSG:4326"
            if auth_id.lower().startswith("epsg:"):
                epsg_int = int(auth_id.split(":")[1])
                log_message(f"EPSG code is: {epsg_int}")
            else:
                # Handle case where it's not an EPSG-based CRS
                epsg_int = None
                raise Exception("CRS is not an EPSG-based ID.")
            self.epsg_code = epsg_int

        # Prepare OSR objects for source->target transformation
        self.target_spatial_ref = osr.SpatialReference()
        self.target_spatial_ref.ImportFromEPSG(self.epsg_code)

        if self.src_spatial_ref:
            self.coord_transform = osr.CoordinateTransformation(
                self.src_spatial_ref, self.target_spatial_ref
            )
        else:
            self.coord_transform = None

        log_message(f"Using output EPSG:{self.epsg_code}")

        # Create aligned bounding box in target CRS space
        # We interpret the layer bbox in source CRS (if it has one), transform, and align
        self.transformed_layer_bbox = self.transform_and_align_bbox(self.layer_bbox)
        log_message(
            f"Transformed layer bbox to target CRS and aligned to grid: {self.transformed_layer_bbox}"
        )
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

    def export_qgs_layer_to_shapefile(self, layer, output_dir):
        """
        Exports a QgsVectorLayer to a Shapefile in output_dir.
        Returns the full path to the .shp (main file).
        """
        shapefile_path = os.path.join(output_dir, "boundaries.shp")
        # Get the project's transform context (required for file writing)
        transform_context = QgsProject.instance().transformContext()
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "ESRI Shapefile"
        options.fileEncoding = "UTF-8"

        if layer.selectedFeatureCount() > 0:
            options.actionOnExistingFile = (
                QgsVectorFileWriter.CreateOrOverwriteFile
            )  # or OverwriteExistingFile
        else:
            options.actionOnExistingFile = (
                QgsVectorFileWriter.CreateOrOverwriteFile
            )  # or OverwriteExistingFile

        err = QgsVectorFileWriter.writeAsVectorFormatV3(
            layer, shapefile_path, transform_context, options
        )

        if err[0] != QgsVectorFileWriter.NoError:
            raise RuntimeError(f"Failed to export layer to Shapefile: {err[1]}")

        return shapefile_path

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

            # 2) Create the status tracking table
            self.create_status_tracking_table()

            # 3) Iterate over features
            self.setProgress(1)  # Trigger the UI to update with a small value
            invalid_feature_count = 0
            self.valid_feature_count = 0
            fixed_feature_count = 0
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
                    log_message(
                        f"Feature {feature.GetFID()} has invalid geometry, attempting to fix."
                    )
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

                # Singlepart vs multipart
                # OGR geometry can be geometry collection if multipart
                geom_type = ogr.GT_Flatten(geom_ref.GetGeometryType())
                if geom_type == ogr.wkbMultiPolygon:
                    log_message(f"Processing multipart geometry: {normalized_name}")
                    self.process_multipart_geometry(
                        geom_ref, normalized_name, area_name
                    )
                else:
                    log_message(f"Processing singlepart geometry: {normalized_name}")
                    self.process_singlepart_geometry(
                        geom_ref, normalized_name, area_name
                    )
            self.setProgress(100)  # Trigger the UI to update with completion value
            log_message(
                f"Processing complete. Valid: {self.valid_feature_count}, Fixed: {fixed_feature_count}, Invalid: {invalid_feature_count}"
            )
            log_message(
                f"Areas that could not be processed due to errors: {self.error_count}"
            )
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
            layer.CreateField(
                ogr.FieldDefn("clip_geom_creation_duration_secs", ogr.OFTReal)
            )
            layer.CreateField(ogr.FieldDefn("geom_total_duration_secs", ogr.OFTReal))

            log_message(f"Table '{self.status_table_name}' created in GeoPackage.")
        finally:
            ds = None

    def add_row_to_status_tracking_table(self, area_name):
        """
        Adds a new row to the tracking table for area_name.
        """
        ds = ogr.Open(self.gpkg_path, 1)
        if not ds:
            raise RuntimeError(f"Could not open {self.gpkg_path} for update.")
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

    def set_status_tracking_table_value(self, area_name, field_name, value):
        """
        Update a field value in the tracking table for the specified area_name.
        """
        ds = ogr.Open(self.gpkg_path, 1)
        if not ds:
            raise RuntimeError(f"Could not open {self.gpkg_path} for update.")
        layer = ds.GetLayerByName(self.status_table_name)
        if not layer:
            raise RuntimeError(f"Missing status table layer: {self.status_table_name}")

        layer.SetAttributeFilter(f"area_name = '{area_name}'")
        for feature in layer:
            feature.SetField(field_name, value)
            layer.SetFeature(feature)
        layer.ResetReading()
        ds = None
        log_message(
            f"Updated processing status flag for {field_name} for {area_name} to {value}."
        )

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

        self.set_status_tracking_table_value(
            normalized_name, "timestamp_start", now_str
        )

        #  Check we have a single part geom
        geom_type = ogr.GT_Flatten(geom.GetGeometryType())
        if geom_type != ogr.wkbPolygon:
            log_message(
                f"Skipping non-polygon geometry type {geom_type} for {normalized_name}."
            )
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

        # Save the geometry (in the target CRS) to "study_area_polygons"
        self.save_geometry_to_geopackage("study_area_polygons", geom, normalized_name)
        self.set_status_tracking_table_value(normalized_name, "geometry_processed", 1)

        # Create the grid
        log_message(f"Creating vector grid for {normalized_name}.")
        start_time = time.time()
        self.create_and_save_grid(normalized_name, geom, aligned_bbox)
        self.set_status_tracking_table_value(normalized_name, "grid_processed", 1)
        self.set_status_tracking_table_value(
            normalized_name, "grid_creation_duration_secs", time.time() - start_time
        )
        # Create clip polygon
        log_message(f"Creating clip polygon for {normalized_name}.")
        start_time = time.time()
        self.create_clip_polygon(geom, aligned_bbox, normalized_name)
        self.set_status_tracking_table_value(
            normalized_name, "clip_geometry_processed", 1
        )
        self.set_status_tracking_table_value(
            normalized_name,
            "clip_geom_creation_duration_secs",
            time.time() - start_time,
        )
        # (Optional) create raster mask
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
        # We use the progress object to notify of progress in the subtask
        # And the QgsTask progressChanged signal to track the main task
        self.setProgress(progress)
        log_message(f"XXXXXXXXXXXX   Progress: {progress}% XXXXXXXXXXXXXXXXXXXXXXX")

    def process_multipart_geometry(self, geom, normalized_name, area_name):
        """
        Processes each part of a multi-part geometry.
        """
        count = geom.GetGeometryCount()
        for i in range(count):
            part_geom = geom.GetGeometryRef(i)
            part_name = f"{normalized_name}_part{i}"
            try:
                self.process_singlepart_geometry(part_geom, part_name, area_name)
            except:
                self.error_count += 1

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
            return (int(value // base)) * base

        def snap_up(value, base):
            return (int(value // base) + 1) * base

        # Snap bounding values outward so we always cover the full geometry
        x_min_snap = snap_down(xmin, cell_size) - cell_size
        y_min_snap = snap_down(ymin, cell_size) - cell_size
        x_max_snap = snap_up(xmax, cell_size) + cell_size
        y_max_snap = snap_up(ymax, cell_size) + cell_size
        log_message(
            f"Aligned bbox                  : {x_min_snap}, {x_max_snap}, {y_min_snap}, {y_max_snap}"
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
    def save_geometry_to_geopackage(self, layer_name, geom, area_name):
        """
        Append a single geometry to a (possibly newly created) layer in GPKG.
        Each layer has a field 'area_name' (string) and polygon geometry.
        """
        self.create_layer_if_not_exists(layer_name)
        ds = ogr.Open(self.gpkg_path, 1)
        layer = ds.GetLayerByName(layer_name)
        if not layer:
            raise RuntimeError(
                f"Could not open target layer {layer_name} in {self.gpkg_path}"
            )

        feat_defn = layer.GetLayerDefn()
        feature = ogr.Feature(feat_defn)
        feature.SetField("area_name", area_name)
        feature.SetGeometry(geom)
        layer.CreateFeature(feature)
        feature = None
        ds = None

    def create_layer_if_not_exists(self, layer_name):
        """
        Create a GPKG layer if it does not exist. The layer has:
         - a string field 'area_name'
         - polygon geometry type
         - SRS is self.target_spatial_ref
        """
        if not os.path.exists(self.gpkg_path):
            # Create new GPKG
            driver = ogr.GetDriverByName("GPKG")
            driver.CreateDataSource(self.gpkg_path)

        ds = ogr.Open(self.gpkg_path, 1)
        layer = ds.GetLayerByName(layer_name)
        if layer is not None:
            ds = None
            return  # Already exists

        # Create it
        layer = ds.CreateLayer(
            layer_name, self.target_spatial_ref, geom_type=ogr.wkbPolygon
        )
        # area_name field
        field_defn = ogr.FieldDefn("area_name", ogr.OFTString)
        layer.CreateField(field_defn)
        ds = None

    # Helper to update time spent in a named metric block
    def track_time(self, metric_name, start_time):
        self.metrics[metric_name] += time.time() - start_time

    ##########################################################################
    # Create Vector Grid
    ##########################################################################
    def create_and_save_grid(self, normalized_name, geom, bbox):
        """
        Creates a vector grid covering bbox at self.cell_size_m spacing.
        Writes those cells that intersect 'geom' to layer 'study_area_grid'.
        (In practice, this can be quite large for big extents.)
        """
        # ----------------------------
        # Initialize metrics tracking
        # ----------------------------
        grid_layer_name = "study_area_grid"
        self.create_grid_layer_if_not_exists(grid_layer_name)

        ds = ogr.Open(self.gpkg_path, 1)  # read-write
        layer = ds.GetLayerByName(grid_layer_name)
        if not layer:
            raise RuntimeError(f"Could not open {grid_layer_name} for writing.")

        xmin, xmax, ymin, ymax = bbox
        cell_size = self.cell_size_m
        # size is squared so 5 will make a 5x5 cell chunk
        chunk_size = int(setting(key="chunk_size", default=50))

        chunker = GridChunker(
            xmin,
            xmax,
            ymin,
            ymax,
            cell_size,
            chunk_size=chunk_size,
            epsg=self.epsg_code,
            geometry=geom.ExportToWkb(),
        )
        chunker.write_chunks_to_gpkg(self.gpkg_path)

        log_message(
            f"Creating grid for extents: xmin {xmin}, xmax {xmax}, ymin {ymin}, ymax {ymax}"
        )

        # OGR geometry intersection can be slow for large grids.
        # If this area is huge, consider a more robust approach or indexing.
        # For demonstration, we do a naive approach.

        self.write_lock = False

        # worker_tasks = []
        # Get a reference to the global task manager
        # task_manager = QgsApplication.taskManager()

        # Limit concurrency to 8
        # task_manager.setMaxActiveThreadCount(8)
        feedback = QgsFeedback()

        # 1. Chunk the bounding box

        # print out all the chunk bboxes
        chunk_count = chunker.total_chunks()
        log_message(f"Chunk count: {chunk_count}")
        log_message(f"Chunk size: {chunk_size}")

        self.feedback.setProgress(0)
        counter = (
            1  # We cant use the chunk index as it includes chunks outside the geometry
        )
        for chunk in chunker.chunks():
            start_time = (
                time.time()
            )  # used for both create chunk start and total chunk start
            index = chunk["index"]
            relationship = chunk["type"]  # inside, edge or undefined
            if relationship != "undefined":
                task = GridFromBbox(
                    index,
                    (
                        chunk["x_start"],
                        chunk["x_end"],
                        chunk["y_start"],
                        chunk["y_end"],
                    ),
                    geom,
                    cell_size,
                    feedback,
                )
                self.track_time("Creating chunks", start_time)
                # Not running in thread for now, see note below
                task.run()

                self.write_chunk(layer, task, normalized_name)
                # We use the progress object to notify of progress in the subtask
                # And the QgsTask progressChanged signal to track the main task
            else:
                log_message(f"Chunk {index} is outside the geometry.")
                continue
            try:
                current_progress = int((counter / chunk_count) * 100)
                log_message(
                    f"XXXXXX Chunks Progress: {counter} / {chunk_count} : {current_progress}% XXXXXX"
                )
                self.feedback.setProgress(current_progress)
            except ZeroDivisionError:
                pass

            # This is blocking, but we're in a thread
            # Crashes QGIS, needs to be refactored to use QgsTask subtasks
            # task.taskCompleted.connect(write_grids)
            # worker_tasks.append(task)
            # log_message(f"Task {index} created for chunk {chunk}")
            # log_message(f"{len(worker_tasks)} tasks queued.")
            # task_manager.addTask(task)
            self.track_time("Complete chunk", start_time)
            counter += 1
        ds = None
        # ----------------------------
        # Print out metrics summary
        # ----------------------------
        log_message("=== Metrics Summary ===")
        for k, v in self.metrics.items():
            log_message(f"{k}: {v:.4f} seconds")
        self.total_cells += self.current_geom_actual_cell_count
        log_message(f"Grid creation completed for area {normalized_name}.")

    def write_chunk(self, layer, task, normalized_name):
        start_time = time.time()
        # Write locking is intended for a future version where we might have multiple threads
        # currently I am just using the grid_from_bbox task to generate the geometries in a
        # single thread by calling its run method directly.
        # The reason for that is that QgsTask subtasks are only called after the parent's
        # run method is completed, so I can't use them to write the geometries to the layer
        # If write_lock is true, wait for the lock to be released
        while self.write_lock:
            log_message("Waiting for write lock...")
            time.sleep(0.001)
        log_message("Write lock released.")
        log_message(f"Writing {len(task.features_out)} features to layer.")
        self.track_time("Preparing chunks", task.run_time)
        self.write_lock = True
        feat_defn = layer.GetLayerDefn()
        layer.StartTransaction()
        try:
            for geometry in task.features_out:
                feature = ogr.Feature(feat_defn)
                feature.SetField("grid_id", self.current_geom_actual_cell_count)
                feature.SetField("area_name", normalized_name)
                feature.SetGeometry(geometry)
                layer.CreateFeature(feature)
                feature = None
                self.current_geom_actual_cell_count += 1
                if self.current_geom_actual_cell_count % 20000 == 0:
                    log_message(
                        f"         Cell count: {self.current_geom_actual_cell_count}"
                    )
                    log_message(f"         Grid creation for part {normalized_name}")
                    # commit changes
                    layer.CommitTransaction()
                    layer.StartTransaction()
            layer.CommitTransaction()  # Final commit
            self.track_time("Writing chunks", start_time)
            self.write_lock = False
        except Exception as e:
            layer.RollbackTransaction()  # Rollback on error
            log_message(f"write_grids: {str(e)}")
            log_message(f"write_grids: {traceback.format_exc()}")
            self.write_lock = False

    def create_grid_layer_if_not_exists(self, layer_name):
        """
        Create a grid layer with 'grid_id' as integer field
        and a polygon geometry if it does not exist.
        """
        if not os.path.exists(self.gpkg_path):
            driver = ogr.GetDriverByName("GPKG")
            driver.CreateDataSource(self.gpkg_path)

        ds = ogr.Open(self.gpkg_path, 1)
        layer = ds.GetLayerByName(layer_name)
        if layer is None:
            layer = ds.CreateLayer(
                layer_name, self.target_spatial_ref, geom_type=ogr.wkbPolygon
            )
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

        # 2) We'll gather all grid cells that intersect *the boundary* of geom
        #    In OGR, we can do:
        boundary = geom.GetBoundary()  # line geometry for polygon boundary

        union_geom = ogr.Geometry(ogr.wkbPolygon)
        union_geom.Destroy()  # We'll handle it differently—see below.

        # For union accumulation, start with a null geometry
        dissolved_geom = None

        # For clarity, transform boundary to the same SRS if needed (already is).
        # We'll just do an Intersects check with each cell.

        grid_layer.ResetReading()
        count = 0
        for f in grid_layer:
            cell_geom = f.GetGeometryRef()
            if not cell_geom:
                continue
            if boundary.Intersects(cell_geom):
                # We'll union
                if dissolved_geom is None:
                    dissolved_geom = cell_geom.Clone()
                else:
                    dissolved_geom = dissolved_geom.Union(cell_geom)
            count += 1
        grid_layer.ResetReading()

        # Also union the original geom itself
        if dissolved_geom is None:
            # No boundary cells found, fallback
            dissolved_geom = geom.Clone()
        else:
            dissolved_geom = dissolved_geom.Union(geom)

        # dissolved_geom is now the final clip polygon
        self.save_geometry_to_geopackage(
            "study_area_clip_polygons", dissolved_geom, normalized_name
        )
        log_message(f"Created clip polygon: {normalized_name}")

    ##########################################################################
    # Split the bbox into chunks for parallel processing
    ##########################################################################
    def chunk_bbox(self, xmin, xmax, ymin, ymax, cell_size, chunk_size=1000):
        """
        Generator that yields bounding box chunks. Each chunk is a tuple:
        (x_start, x_end, y_start, y_end).

        `chunk_size` indicates how many cells in the X-direction
        (and optionally also Y-direction) you want per chunk.
        """

        x_range_count = int((xmax - xmin) / cell_size)
        y_range_count = int((ymax - ymin) / cell_size)

        x_blocks = range(0, x_range_count, chunk_size)
        y_blocks = range(0, y_range_count, chunk_size)
        for x_block_start in x_blocks:
            log_message(f"Processing chunk {x_block_start} of {x_range_count}")
            x_block_end = min(x_block_start + chunk_size, x_range_count)

            # Convert from cell index to real coords
            x_start_coord = xmin + x_block_start * cell_size
            x_end_coord = xmin + x_block_end * cell_size

            for y_block_start in y_blocks:
                log_message(f"Processing chunk {y_block_start} of {y_range_count}")
                y_block_end = min(y_block_start + chunk_size, y_range_count)

                # Convert from cell index to real coords
                y_start_coord = ymin + y_block_start * cell_size
                y_end_coord = ymin + y_block_end * cell_size

                log_message(
                    f"Created Chunk bbox: {x_start_coord}, {x_end_coord}, {ymin}, {ymax}"
                )
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
        mem_lyr = mem_ds.CreateLayer(
            "temp_mask_layer", self.target_spatial_ref, geom_type=ogr.wkbPolygon
        )

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
    # CRS / UTM calculation
    ##########################################################################
    def calculate_utm_zone(self, bbox, source_epsg=None):
        """
        Determine a UTM zone from the centroid of (xmin, xmax, ymin, ymax),
        reprojected into WGS84 if possible. Return EPSG code.
        """
        (xmin, xmax, ymin, ymax) = bbox
        cx = 0.5 * (xmin + xmax)
        cy = 0.5 * (ymin + ymax)

        # If there's no source SRS, we'll assume it's already lat/lon
        if not source_epsg:
            # fallback if no known EPSG
            log_message(
                "Source has no EPSG, defaulting to a naive assumption of WGS84 bounding box."
            )
            lon, lat = cx, cy
        else:
            # We have a known EPSG, so transform centroid to WGS84
            src_ref = osr.SpatialReference()
            src_ref.ImportFromEPSG(int(source_epsg))
            wgs84_ref = osr.SpatialReference()
            wgs84_ref.ImportFromEPSG(4326)
            ct = osr.CoordinateTransformation(src_ref, wgs84_ref)
            point = ogr.Geometry(ogr.wkbPoint)
            point.AddPoint(cx, cy)
            point.Transform(ct)
            lon = point.GetX()
            lat = point.GetY()

        # Standard formula for UTM zone
        utm_zone = int((lon + 180) / 6) + 1
        # We guess north or south
        if lat >= 0:
            return 32600 + utm_zone  # Northern Hemisphere
        else:
            return 32700 + utm_zone  # Southern Hemisphere

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
