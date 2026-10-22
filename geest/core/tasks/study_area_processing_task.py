# -*- coding: utf-8 -*-
"""📦 Study Area Processing Task module.

This module contains functionality for study area processing task.
"""

import datetime
import glob
import os
import re
import time
import traceback

# GDAL / OGR / OSR imports
from osgeo import gdal, ogr, osr
from qgis.core import (
    Qgis,
    QgsFeedback,
    QgsProject,
    QgsRectangle,
    QgsTask,
    QgsVectorFileWriter,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import (
    QMutex,
    QRunnable,
    QThread,
    QThreadPool,
    QWaitCondition,
    pyqtSignal,
)

from geest.core.algorithms import GHSLDownloader, GHSLProcessor
from geest.core.arrow_batch_writer import log_arrow_batch_fallback, write_features_arrow_batch
from geest.core.grid_column_utils import add_model_columns_to_grid
from geest.core.h3_utils import estimate_h3_cells_for_area, get_h3_resolution_for_scale, h3_cell_area_km2
from geest.core.settings import setting
from geest.utilities import (
    apply_sqlite_write_safety_options,
    calculate_utm_zone,
    log_message,
    restore_sqlite_write_safety_options,
)

from .grid_chunker_task import GridChunkerTask
from .grid_from_bbox_h3_task import GridFromBboxH3Task
from .grid_from_bbox_task import GridFromBboxTask


class QtQueue:
    """Thread-safe queue using Qt primitives.

    A simple bounded queue implementation using QMutex and QWaitCondition
    to replace Python's queue.Queue for better QGIS compatibility.

    Attributes:
        maxsize: Maximum number of items in the queue (0 = unbounded).
    """

    def __init__(self, maxsize=0):
        """Initialize the queue.

        Args:
            maxsize: Maximum queue size. 0 means unbounded.
        """
        self._queue = []
        self._maxsize = maxsize
        self._mutex = QMutex()
        self._not_empty = QWaitCondition()
        self._not_full = QWaitCondition()
        self._unfinished_tasks = 0
        self._all_tasks_done = QWaitCondition()

    def put(self, item, timeout=None):
        """Add item to queue, blocking if full.

        Args:
            item: Item to add to queue.
            timeout: Maximum time to wait in seconds (None = wait forever).

        Returns:
            True if item was added, False if timeout expired.
        """
        self._mutex.lock()
        try:
            if self._maxsize > 0:
                while len(self._queue) >= self._maxsize:
                    if timeout is not None:
                        if not self._not_full.wait(self._mutex, int(timeout * 1000)):
                            return False
                    else:
                        self._not_full.wait(self._mutex)
            self._queue.append(item)
            self._unfinished_tasks += 1
            self._not_empty.wakeOne()
            return True
        finally:
            self._mutex.unlock()

    def get(self, timeout=None):
        """Remove and return item from queue, blocking if empty.

        Args:
            timeout: Maximum time to wait in seconds (None = wait forever).

        Returns:
            Item from queue.

        Raises:
            TimeoutError: If timeout expires before item available.
        """
        self._mutex.lock()
        try:
            while len(self._queue) == 0:
                if timeout is not None:
                    if not self._not_empty.wait(self._mutex, int(timeout * 1000)):
                        raise TimeoutError("Queue get timeout")
                else:
                    self._not_empty.wait(self._mutex)
            item = self._queue.pop(0)
            self._not_full.wakeOne()
            return item
        finally:
            self._mutex.unlock()

    def task_done(self):
        """Indicate that a formerly enqueued task is complete.

        Should be called by consumer after processing each item from get().
        """
        self._mutex.lock()
        try:
            if self._unfinished_tasks <= 0:
                log_message("task_done() called too many times", level="WARNING")
                return
            self._unfinished_tasks -= 1
            if self._unfinished_tasks == 0:
                self._all_tasks_done.wakeAll()
        finally:
            self._mutex.unlock()

    def empty(self):
        """Check if queue is empty.

        Returns:
            True if queue is empty.
        """
        self._mutex.lock()
        try:
            return len(self._queue) == 0
        finally:
            self._mutex.unlock()

    def qsize(self):
        """Return approximate queue size.

        Returns:
            Number of items in queue.
        """
        self._mutex.lock()
        try:
            return len(self._queue)
        finally:
            self._mutex.unlock()

    def join(self):
        """Block until all items in the queue have been processed.

        The count of unfinished tasks goes up when items are put() and
        goes down when task_done() is called. When it reaches zero,
        join() unblocks.
        """
        self._mutex.lock()
        try:
            while self._unfinished_tasks > 0:
                self._all_tasks_done.wait(self._mutex)
        finally:
            self._mutex.unlock()


class GpkgOperation:
    """Represents a queued GeoPackage operation for unified writer thread.

    This class encapsulates different types of database operations that can be
    queued and processed asynchronously by the UnifiedWriterThread. All operations
    are serialized through a single queue to prevent concurrent write conflicts.

    Operation Types:
        WRITE_GRID_CELL: Write a grid cell geometry to study_area_grid layer
        WRITE_GEOMETRY: Write a geometry to any layer (bbox, polygon, clip, etc.)
        UPDATE_STATUS: Update a field in the status tracking table
        INSERT_STATUS: Insert a new row in the status tracking table
        CREATE_LAYER: Create a new layer in the GeoPackage

    Attributes:
        op_type (str): Type of operation (one of the constants above)
        data (dict): Operation-specific data
    """

    # Operation type constants
    WRITE_GRID_CELL = "write_grid"
    WRITE_GEOMETRY = "write_geom"
    UPDATE_STATUS = "update_status"
    INSERT_STATUS = "insert_status"
    CREATE_LAYER = "create_layer"

    def __init__(self, op_type, **kwargs):
        """Initialize a GeoPackage operation.

        Args:
            op_type: Type of operation (use class constants)
            **kwargs: Operation-specific data
        """
        self.op_type = op_type
        self.data = kwargs

    @classmethod
    def write_grid_cell(cls, geometry, area_name, grid_id, h3_index=None, h3_resolution=None):
        """Factory method for grid cell write operation.

        Args:
            geometry: OGR geometry for the grid cell
            area_name: Name of the area this cell belongs to
            grid_id: Unique grid cell ID
            h3_index: Optional H3 cell index for hexagonal grids (regional scale)
            h3_resolution: Optional H3 resolution level

        Returns:
            GpkgOperation instance
        """
        return cls(
            cls.WRITE_GRID_CELL,
            geometry=geometry,
            area_name=area_name,
            grid_id=grid_id,
            h3_index=h3_index,
            h3_resolution=h3_resolution,
        )

    @classmethod
    def write_geometry(cls, layer_name, geometry, area_name, **extra_fields):
        """Factory method for general geometry write operation.

        Args:
            layer_name: Target layer name (e.g., 'study_area_bboxes')
            geometry: OGR geometry to write
            area_name: Name of the area
            **extra_fields: Additional fields to set (e.g., intersects_ghsl=True)

        Returns:
            GpkgOperation instance
        """
        return cls(
            cls.WRITE_GEOMETRY, layer_name=layer_name, geometry=geometry, area_name=area_name, extra_fields=extra_fields
        )

    @classmethod
    def update_status(cls, area_name, field_name, value):
        """Factory method for status update operation.

        Args:
            area_name: Name of the area to update
            field_name: Field name to update
            value: New value for the field

        Returns:
            GpkgOperation instance
        """
        return cls(cls.UPDATE_STATUS, area_name=area_name, field_name=field_name, value=value)

    @classmethod
    def insert_status(cls, area_name):
        """Factory method for status insert operation.

        Args:
            area_name: Name of the area to create status row for

        Returns:
            GpkgOperation instance
        """
        return cls(cls.INSERT_STATUS, area_name=area_name)

    @classmethod
    def create_layer(cls, layer_name, geom_type, extra_fields=None):
        """Factory method for layer creation operation.

        Args:
            layer_name: Name of layer to create
            geom_type: OGR geometry type (e.g., ogr.wkbPolygon)
            extra_fields: List of (field_name, field_type) tuples for extra fields

        Returns:
            GpkgOperation instance
        """
        return cls(cls.CREATE_LAYER, layer_name=layer_name, geom_type=geom_type, extra_fields=extra_fields or [])

    def __repr__(self):
        """String representation for debugging.

        Returns:
            str: Human-readable representation of the operation.
        """
        return f"GpkgOperation({self.op_type}, {self.data})"


class UnifiedWriterThread(QThread):
    """Unified writer thread handling ALL GeoPackage write operations.

    This thread processes all database operations through a single queue,
    preventing concurrent write conflicts and database corruption. It maintains
    a single persistent database connection and handles multiple operation types.

    Operation types handled:
        - Grid cell writes (study_area_grid)
        - Geometry writes (study_area_bboxes, study_area_polygons, etc.)
        - Status tracking updates and inserts
        - Layer creation

    Attributes:
        queue: QtQueue containing GpkgOperation instances
        gpkg_path: Path to the GeoPackage file
        target_srs: Target spatial reference system
        flush_token: Special token that triggers immediate batch flush
        parent_task: Reference to parent StudyAreaProcessingTask for shared state
        batch_size: Maximum number of operations per batch
        ds: Persistent OGR dataset connection
        layers: Cache of opened layer references
    """

    def __init__(self, queue, gpkg_path, target_srs, flush_token, parent_task, parent=None):
        """Initialize the unified writer thread.

        Args:
            queue: QtQueue to read GpkgOperation instances from
            gpkg_path: Path to GeoPackage file
            target_srs: Target spatial reference system (osr.SpatialReference)
            flush_token: Token that triggers batch flush when received
            parent_task: Reference to StudyAreaProcessingTask instance
            parent: Parent QObject
        """
        super().__init__(parent)
        self.queue = queue
        self.gpkg_path = gpkg_path
        self.target_srs = target_srs
        self.flush_token = flush_token
        self.parent_task = parent_task
        self.batch_size = 10000
        self._stop_requested = False

        # Persistent database connection (single writer)
        self.ds = None
        self.layers = {}  # Cache layer references

    def run(self):
        """Process all operations from queue with single database connection."""
        try:
            # Open persistent connection once
            self.ds = ogr.Open(self.gpkg_path, 1)
            if not self.ds:
                log_message(f"UnifiedWriter: Could not open {self.gpkg_path}", level="CRITICAL")
                return

            log_message("UnifiedWriter: Started with persistent connection")

            batch = []

            while not self._stop_requested:
                try:
                    item = self.queue.get(timeout=60)
                except TimeoutError:
                    continue

                if item is None:  # Shutdown signal
                    log_message("UnifiedWriter: Received shutdown signal")
                    self._flush_batch(batch)
                    self.queue.task_done()
                    break

                if item is self.flush_token:  # Force flush
                    self._flush_batch(batch)
                    batch = []
                    self.queue.task_done()
                    continue

                # Accumulate operations
                batch.append(item)

                if len(batch) >= self.batch_size:
                    self._flush_batch(batch)
                    batch = []

        except Exception as e:
            log_message(f"UnifiedWriter: Fatal error: {e}", level="CRITICAL")
            log_message(traceback.format_exc(), level="CRITICAL")
        finally:
            # Cleanup
            if self.ds:
                try:
                    self.ds.FlushCache()
                    # Serialised process-wide via gpkg_doctor's checkpoint lock.
                    from geest.core.gpkg_doctor import checkpoint_dataset

                    checkpoint_dataset(self.ds)
                except Exception as e:
                    log_message(f"UnifiedWriter: Error flushing on cleanup: {e}", level="WARNING")
                self.ds = None
            self.layers = {}
            log_message("UnifiedWriter: Stopped and cleaned up")

    def _flush_batch(self, batch):
        """Process batch of operations grouped by type.

        Args:
            batch: List of GpkgOperation instances

        Raises:
            Exception: If any batch operation fails.
        """
        if not batch:
            return

        try:
            # Group operations by type for efficient processing
            grouped = self._group_operations(batch)

            # Process each operation type
            if GpkgOperation.WRITE_GRID_CELL in grouped:
                self._write_grid_batch(grouped[GpkgOperation.WRITE_GRID_CELL])

            if GpkgOperation.WRITE_GEOMETRY in grouped:
                self._write_geometry_batch(grouped[GpkgOperation.WRITE_GEOMETRY])

            if GpkgOperation.INSERT_STATUS in grouped:
                self._insert_status_batch(grouped[GpkgOperation.INSERT_STATUS])

            if GpkgOperation.UPDATE_STATUS in grouped:
                self._update_status_batch(grouped[GpkgOperation.UPDATE_STATUS])

            if GpkgOperation.CREATE_LAYER in grouped:
                self._create_layer_batch(grouped[GpkgOperation.CREATE_LAYER])

            # Mark all operations as done
            for _ in batch:
                self.queue.task_done()

        except Exception as e:
            log_message(f"UnifiedWriter: Batch processing error: {e}", level="ERROR")
            log_message(traceback.format_exc(), level="ERROR")
            # Still mark as done to prevent queue hanging
            for _ in batch:
                self.queue.task_done()
            raise

    def _group_operations(self, batch):
        """Group operations by type for efficient batched processing.

        Args:
            batch: List of GpkgOperation instances

        Returns:
            Dict mapping operation type to list of operations
        """
        grouped = {}
        for op in batch:
            if op.op_type not in grouped:
                grouped[op.op_type] = []
            grouped[op.op_type].append(op)
        return grouped

    def _get_layer(self, layer_name):
        """Get or cache a layer reference from the dataset.

        If layer is not found, closes and reopens dataset to pick up newly created layers.

        Args:
            layer_name: Name of layer to get

        Returns:
            OGR layer object

        Raises:
            RuntimeError: If layer cannot be opened after retry
        """
        if layer_name not in self.layers:
            layer = self.ds.GetLayerByName(layer_name)
            if not layer:
                # Layer doesn't exist - might have been created after we opened dataset
                # Close and reopen to pick up new layers
                log_message(f"UnifiedWriter: Layer {layer_name} not found, reloading dataset")
                self.ds = None
                self.ds = ogr.Open(self.gpkg_path, 1)
                if not self.ds:
                    raise RuntimeError("UnifiedWriter: Could not reopen GeoPackage")

                # Clear cache since we have a new dataset connection
                self.layers = {}

                # Try again
                layer = self.ds.GetLayerByName(layer_name)
                if not layer:
                    raise RuntimeError(f"UnifiedWriter: Could not open layer {layer_name} even after reload")

            self.layers[layer_name] = layer
        return self.layers[layer_name]

    def _write_grid_batch(self, operations):
        """Write batch of grid cell geometries in single transaction.

        Args:
            operations: List of GpkgOperation instances with WRITE_GRID_CELL type

        Raises:
            Exception: If the transaction fails.
        """
        layer = self._get_layer("study_area_grid")
        feat_defn = layer.GetLayerDefn()
        has_h3_fields = feat_defn.GetFieldIndex("h3_index") >= 0

        wrote_via_arrow = False
        try:
            field_values = {
                "grid_id": [op.data["grid_id"] for op in operations],
                "area_name": [op.data["area_name"] for op in operations],
            }
            if has_h3_fields:
                field_values["h3_index"] = [op.data.get("h3_index") or None for op in operations]
                field_values["h3_resolution"] = [op.data.get("h3_resolution") or None for op in operations]
            geometries = [op.data["geometry"] for op in operations]
            wrote_via_arrow = write_features_arrow_batch(layer, field_values, geometries)
        except Exception as error:
            log_arrow_batch_fallback("UnifiedWriter._write_grid_batch", error)

        if wrote_via_arrow:
            log_message(f"UnifiedWriter: Wrote {len(operations)} grid cells (Arrow batch)")
            return

        layer.StartTransaction()
        try:
            for op in operations:
                feature = ogr.Feature(feat_defn)
                feature.SetField("grid_id", op.data["grid_id"])
                feature.SetField("area_name", op.data["area_name"])

                # Add H3 fields if present (regional scale)
                if "h3_index" in op.data and op.data["h3_index"]:
                    feature.SetField("h3_index", op.data["h3_index"])
                if "h3_resolution" in op.data and op.data["h3_resolution"]:
                    feature.SetField("h3_resolution", op.data["h3_resolution"])

                feature.SetGeometry(op.data["geometry"])
                layer.CreateFeature(feature)
                feature = None

            layer.CommitTransaction()
            log_message(f"UnifiedWriter: Wrote {len(operations)} grid cells")

        except Exception as e:
            layer.RollbackTransaction()
            log_message(f"UnifiedWriter: Grid batch write failed: {e}", level="ERROR")
            raise

    def _write_geometry_batch(self, operations):
        """Write batch of geometries to various layers in transactions.

        Groups by layer name for efficient batch writes.

        Args:
            operations: List of GpkgOperation instances with WRITE_GEOMETRY type

        Raises:
            Exception: If any layer transaction fails.
        """
        # Group by layer name
        by_layer = {}
        for op in operations:
            layer_name = op.data["layer_name"]
            if layer_name not in by_layer:
                by_layer[layer_name] = []
            by_layer[layer_name].append(op)

        # Write each layer's operations in a transaction
        for layer_name, layer_ops in by_layer.items():
            layer = self._get_layer(layer_name)
            feat_defn = layer.GetLayerDefn()

            wrote_via_arrow = False
            try:
                extra_keys = set()
                for op in layer_ops:
                    extra_keys.update(op.data.get("extra_fields", {}).keys())
                # Only fields that actually exist on this layer's schema can
                # be written via Arrow - unlike SetField(), which silently
                # no-ops on an unknown field name.
                extra_keys = {key for key in extra_keys if feat_defn.GetFieldIndex(key) >= 0}

                field_values = {}
                if feat_defn.GetFieldIndex("area_name") >= 0:
                    field_values["area_name"] = [op.data["area_name"] for op in layer_ops]
                for key in extra_keys:
                    field_values[key] = [op.data.get("extra_fields", {}).get(key) for op in layer_ops]
                geometries = [op.data["geometry"] for op in layer_ops]
                wrote_via_arrow = write_features_arrow_batch(layer, field_values, geometries)
            except Exception as error:
                log_arrow_batch_fallback(f"UnifiedWriter._write_geometry_batch[{layer_name}]", error)

            if wrote_via_arrow:
                log_message(f"UnifiedWriter: Wrote {len(layer_ops)} geometries to {layer_name} (Arrow batch)")
                continue

            layer.StartTransaction()
            try:
                for op in layer_ops:
                    feature = ogr.Feature(feat_defn)
                    # Legacy layers (e.g. chunks created by pre-2.1 plugin
                    # versions) may lack the standard area_name field.
                    if feat_defn.GetFieldIndex("area_name") >= 0:
                        feature.SetField("area_name", op.data["area_name"])

                    # Set extra fields (e.g., intersects_ghsl, geom_area)
                    for field_name, field_value in op.data.get("extra_fields", {}).items():
                        feature.SetField(field_name, field_value)

                    feature.SetGeometry(op.data["geometry"])
                    layer.CreateFeature(feature)
                    feature = None

                layer.CommitTransaction()
                log_message(f"UnifiedWriter: Wrote {len(layer_ops)} geometries to {layer_name}")

            except Exception as e:
                layer.RollbackTransaction()
                log_message(f"UnifiedWriter: Geometry batch write to {layer_name} failed: {e}", level="ERROR")
                raise

    def _insert_status_batch(self, operations):
        """Insert batch of status tracking rows.

        Args:
            operations: List of GpkgOperation instances with INSERT_STATUS type

        Raises:
            Exception: If the transaction fails.
        """
        layer = self._get_layer("study_area_creation_status")
        feat_defn = layer.GetLayerDefn()

        layer.StartTransaction()
        try:
            for op in operations:
                feature = ogr.Feature(feat_defn)
                feature.SetField("area_name", op.data["area_name"])
                feature.SetField("geometry_processed", 0)
                feature.SetField("clip_geometry_processed", 0)
                feature.SetField("grid_processed", 0)
                feature.SetField("mask_processed", 0)
                feature.SetField("grid_creation_duration_secs", 0.0)
                feature.SetField("clip_geom_creation_duration_secs", 0.0)
                feature.SetField("geom_total_duration_secs", 0.0)
                layer.CreateFeature(feature)
                feature = None

            layer.CommitTransaction()
            log_message(f"UnifiedWriter: Inserted {len(operations)} status rows")

        except Exception as e:
            layer.RollbackTransaction()
            log_message(f"UnifiedWriter: Status insert batch failed: {e}", level="ERROR")
            raise

    def _update_status_batch(self, operations):
        """Update batch of status tracking fields.

        Groups by area_name for efficient updates.

        Args:
            operations: List of GpkgOperation instances with UPDATE_STATUS type

        Raises:
            Exception: If the transaction fails.
        """
        layer = self._get_layer("study_area_creation_status")

        # Group updates by area_name
        updates_by_area = {}
        for op in operations:
            area_name = op.data["area_name"]
            if area_name not in updates_by_area:
                updates_by_area[area_name] = {}
            updates_by_area[area_name][op.data["field_name"]] = op.data["value"]

        layer.StartTransaction()
        try:
            for area_name, fields in updates_by_area.items():
                layer.SetAttributeFilter(f"area_name = '{area_name}'")
                for feature in layer:
                    for field_name, value in fields.items():
                        feature.SetField(field_name, value)
                    layer.SetFeature(feature)
                layer.ResetReading()

            layer.SetAttributeFilter(None)
            layer.CommitTransaction()
            log_message(f"UnifiedWriter: Updated {len(operations)} status fields")

        except Exception as e:
            layer.RollbackTransaction()
            log_message(f"UnifiedWriter: Status update batch failed: {e}", level="ERROR")
            raise

    def _create_layer_batch(self, operations):
        """Create layers (executed immediately, not batched).

        Args:
            operations: List of GpkgOperation instances with CREATE_LAYER type

        Raises:
            Exception: If layer creation fails.
        """
        for op in operations:
            layer_name = op.data["layer_name"]

            # Check if already exists
            if self.ds.GetLayerByName(layer_name):
                continue

            try:
                layer = self.ds.CreateLayer(layer_name, self.target_srs, geom_type=op.data["geom_type"])

                # Add area_name field (standard for all layers)
                field_defn = ogr.FieldDefn("area_name", ogr.OFTString)
                layer.CreateField(field_defn)

                # Add extra fields
                for field_name, field_type in op.data.get("extra_fields", []):
                    field_defn = ogr.FieldDefn(field_name, field_type)
                    layer.CreateField(field_defn)

                # Cache the layer
                self.layers[layer_name] = layer
                log_message(f"UnifiedWriter: Created layer {layer_name}")

            except Exception as e:
                log_message(f"UnifiedWriter: Failed to create layer {layer_name}: {e}", level="ERROR")
                raise

    def request_stop(self):
        """Request the thread to stop."""
        self._stop_requested = True


class ChunkRunnable(QRunnable):
    """QRunnable for processing a single grid chunk.

    When a write_callback is provided, the runnable writes and frees
    cell geometries immediately upon chunk completion, keeping memory
    bounded. Without a callback it falls back to storing results for
    the caller to consume (legacy behaviour).

    Attributes:
        chunk: Chunk parameters dictionary.
        geom: OGR geometry for intersection testing.
        cell_size: Cell size in meters.
        feedback: QgsFeedback for progress reporting.
        result: Tuple of (task, start_time, index) after run completes.
        error: Exception if processing failed.
    """

    def __init__(
        self,
        chunk,
        geom,
        cell_size,
        feedback,
        write_callback=None,
        analysis_scale="national",
        epsg_code=None,
        h3_resolution=6,
    ):
        """Initialize the chunk runnable.

        Args:
            chunk: Dictionary with chunk parameters.
            geom: OGR geometry for intersection testing.
            cell_size: Cell size in meters.
            feedback: QgsFeedback for progress reporting.
            write_callback: Optional callable(task, start_time) that queues
                the chunk's geometries to the write queue and frees them.
            analysis_scale: Analysis scale ("regional", "national", or "local")
            epsg_code: EPSG code for coordinate transformation
            h3_resolution: H3 resolution override for regional scale.
        """
        super().__init__()
        self.chunk = chunk
        self.geom = geom
        self.cell_size = cell_size
        self.feedback = feedback
        self.write_callback = write_callback
        self.analysis_scale = analysis_scale
        self.epsg_code = epsg_code
        self.h3_resolution = h3_resolution
        self.result = None
        self.error = None
        self.setAutoDelete(False)  # We manage lifecycle manually

    def run(self):
        """Process the chunk and write results immediately if callback set."""
        try:
            start_time = time.time()
            index = self.chunk["index"]

            # Use H3 task for regional scale, regular grid task otherwise
            if self.analysis_scale == "regional":
                h3_res = self.h3_resolution
                task = GridFromBboxH3Task(
                    index,
                    (
                        self.chunk["x_start"],
                        self.chunk["x_end"],
                        self.chunk["y_start"],
                        self.chunk["y_end"],
                    ),
                    self.geom,
                    int(self.epsg_code) if self.epsg_code else 4326,
                    h3_res,
                    self.feedback,
                )
            else:
                task = GridFromBboxTask(
                    index,
                    (
                        self.chunk["x_start"],
                        self.chunk["x_end"],
                        self.chunk["y_start"],
                        self.chunk["y_end"],
                    ),
                    self.geom,
                    self.cell_size,
                    self.feedback,
                )
            task.run()

            if self.write_callback:
                self.write_callback(task, start_time)
                # Free geometries immediately after queuing to write thread
                task.features_out = []
                self.result = (None, start_time, index)
            else:
                self.result = (task, start_time, index)
        except Exception as e:
            self.error = e


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

    Signals:
        ghsl_download_failed: Emitted when GHSL download fails. Contains error message string.
    """

    # Signal emitted when GHSL download fails - allows UI to prompt user to continue or abort
    ghsl_download_failed = pyqtSignal(str)

    MIN_H3_ESTIMATED_CELLS = 3
    MAX_H3_ESTIMATED_CELLS = 200000

    # Signal emitted when waiting for user response about GHSL failure
    ghsl_user_response_ready = pyqtSignal()

    def __init__(
        self,
        layer: QgsVectorLayer,
        field_name,
        cell_size_m,
        working_dir,
        feedback: "QgsFeedback | None" = None,
        crs=None,
        analysis_scale: str = "national",
        h3_resolution: int = None,
    ):
        """Initialize the study area processing task.

        Args:
            layer: The input vector layer containing study area polygons.
            field_name: Name of the field that holds the study area name.
            cell_size_m: Cell size for grid spacing (in meters).
            working_dir: Directory path where outputs will be saved.
            feedback: QgsFeedback object for progress reporting.
            crs: Target CRS. If None, a UTM zone will be computed.
            analysis_scale: Analysis scale ("regional", "national", or "local").
                Regional uses H3 hexagonal grids, others use square grids.
            h3_resolution: Optional H3 resolution override for regional analysis.

        Raises:
            RuntimeError: If the input layer cannot be opened with OGR.
            Exception: If the CRS is not EPSG-based.
        """
        """Initialize the study area processing task.

        Args:
            layer: The input vector layer containing study area polygons.
            field_name: Name of the field that holds the study area name.
            cell_size_m: Cell size for grid spacing (in meters).
            working_dir: Directory path where outputs will be saved.
            feedback: QgsFeedback object for progress reporting.
            crs: Target CRS. If None, a UTM zone will be computed.

        Raises:
            RuntimeError: If the input layer cannot be opened with OGR.
            Exception: If the CRS is not EPSG-based.
        """
        super().__init__("Study Area Preparation", QgsTask.CanCancel)
        self._previous_gdal_sqlite_options = {}

        self.field_name = field_name
        self.input_vector_path = self.export_qgs_layer_to_shapefile(layer, working_dir)
        self.input_vector_path = self.dissolve_input_layer_by_field(
            self.input_vector_path, self.field_name, working_dir
        )
        self.cell_size_m = cell_size_m
        self.analysis_scale = analysis_scale
        self.h3_resolution = (
            h3_resolution if h3_resolution is not None else (get_h3_resolution_for_scale("regional") or 6)
        )
        if self.analysis_scale == "regional":
            log_message(f"Using H3 resolution: {self.h3_resolution}")
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
        # GHSL download synchronization - allows UI to prompt user on failure
        self._ghsl_mutex = QMutex()
        self._ghsl_wait_condition = QWaitCondition()
        self._ghsl_response_received = False
        self._ghsl_continue_without = False  # Set by UI when user responds
        self.termination_reason = ""
        self.termination_detail = ""
        self.write_lock = QMutex()
        self.gpkg_lock = QMutex()
        self.grid_id_lock = QMutex()
        self.writer_start_lock = QMutex()
        self.write_queue = None
        self.writer_thread = None
        self.writer_ref_count = 0
        self._writer_flush_token = object()
        self.create_study_area_directory(self.working_dir)

        if os.path.exists(self.gpkg_path):
            try:
                os.remove(self.gpkg_path)
                log_message(f"Removed existing GeoPackage: {self.gpkg_path}")
            except Exception as e:
                log_message(f"Error removing existing GeoPackage: {e}", level="CRITICAL")

        self.source_ds = ogr.Open(self.input_vector_path, 0)
        if not self.source_ds:
            raise RuntimeError(f"Could not open {self.input_vector_path} with OGR.")
        self.source_layer = self.source_ds.GetLayer(0)
        if not self.source_layer:
            raise RuntimeError("Could not retrieve layer from the data source.")
        self.parts_count = self.count_layer_parts()

        self.src_spatial_ref = self.source_layer.GetSpatialRef()
        self.src_epsg = None
        if self.src_spatial_ref:
            self.src_epsg = self.src_spatial_ref.GetAuthorityCode(None)
        log_message(
            f"DIAG: dissolved/source layer '{self.input_vector_path}' spatial ref: "
            f"{self.src_spatial_ref.ExportToWkt() if self.src_spatial_ref else 'MISSING (GetSpatialRef() returned None)'}"
        )

        layer_extent = self.source_layer.GetExtent()
        xmin, xmax, ymin, ymax = layer_extent
        self.layer_bbox = (xmin, xmax, ymin, ymax)

        if crs is None:
            self.epsg_code = calculate_utm_zone(self.layer_bbox, self.src_epsg)
        else:
            auth_id = crs.authid()
            if auth_id.lower().startswith("epsg:"):
                epsg_int = int(auth_id.split(":")[1])
                log_message(f"EPSG code is: {epsg_int}")
            else:
                epsg_int = None
                raise Exception(f"CRS Passed to function: {crs}. CRS is not an EPSG-based ID: {auth_id}")
            self.epsg_code = epsg_int

        self.target_spatial_ref = osr.SpatialReference()
        self.target_spatial_ref.ImportFromEPSG(self.epsg_code)

        if self.src_spatial_ref:
            self.coord_transform = osr.CoordinateTransformation(self.src_spatial_ref, self.target_spatial_ref)
        else:
            self.coord_transform = None

        log_message(f"Using output EPSG:{self.epsg_code}")  # noqa: E231

        self.transformed_layer_bbox = self.transform_and_align_bbox(self.layer_bbox)
        log_message(f"Transformed layer bbox to target CRS and aligned to grid: {self.transformed_layer_bbox}")
        self.status_table_name = "study_area_creation_status"

    def count_layer_parts(self):
        """Return the number of parts in the layer.

        Returns:
            The number of parts in the layer.
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

    def set_ghsl_user_response(self, continue_without: bool):
        """Set user response for GHSL download failure.

        Called from UI thread when user responds to the GHSL failure prompt.

        Args:
            continue_without: True if user wants to continue without GHSL,
                            False if user wants to abort the task.
        """
        self._ghsl_mutex.lock()
        self._ghsl_continue_without = continue_without
        self._ghsl_response_received = True
        self._ghsl_wait_condition.wakeAll()
        self._ghsl_mutex.unlock()

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
        """Export a QgsVectorLayer to a Shapefile in output_dir.

        Args:
            layer: The QgsVectorLayer to export.
            output_dir: Directory where the shapefile will be saved.

        Returns:
            Full path to the .shp (main file).

        Raises:
            RuntimeError: If the export fails.
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

    def dissolve_input_layer_by_field(self, input_vector_path, field_name, output_dir):
        """Dissolve input polygons by selected area-name field.

        Args:
            input_vector_path: Path to source vector layer exported from QGIS.
            field_name: Field used to group/dissolve AOI geometries.
            output_dir: Working directory for writing dissolved output.

        Returns:
            Path to dissolved output, or original input if dissolve is unavailable.

        Notes:
            This is a best-effort preprocessing step. If dissolve fails because of
            environment/driver/path issues, processing falls back to the original
            exported layer instead of aborting task initialization.
        """
        log_message(f"Dissolving input AOI by '{field_name}' before grid generation")

        source_ds = ogr.Open(input_vector_path, 0)
        if not source_ds:
            log_message(
                f"Could not open input layer for dissolve, using original AOI: {input_vector_path}",
                level="WARNING",
            )
            return input_vector_path

        source_layer = source_ds.GetLayer(0)
        if not source_layer:
            source_ds = None
            log_message("Could not read source layer for dissolve, using original AOI", level="WARNING")
            return input_vector_path

        source_defn = source_layer.GetLayerDefn()
        if source_defn.GetFieldIndex(field_name) < 0:
            source_ds = None
            log_message(
                f"Field '{field_name}' not found for dissolve, using original AOI",
                level="WARNING",
            )
            return input_vector_path

        dissolved_geometries = {}
        source_layer.ResetReading()
        for feature in source_layer:
            geom = feature.GetGeometryRef()
            if geom is None or geom.IsEmpty():
                continue

            geom_clone = geom.Clone()
            try:
                if not geom_clone.IsValid():
                    geom_clone = geom_clone.MakeValid()
            except Exception:  # nosec B110
                pass

            area_name = feature.GetField(field_name)
            if area_name is None or str(area_name).strip() == "":
                area_name = f"area_{feature.GetFID()}"
            area_name = str(area_name)

            if area_name in dissolved_geometries:
                dissolved_geometries[area_name] = dissolved_geometries[area_name].Union(geom_clone)
            else:
                dissolved_geometries[area_name] = geom_clone

        source_srs = source_layer.GetSpatialRef()
        source_ds = None

        if not dissolved_geometries:
            log_message("No valid geometries found to dissolve, using original AOI", level="WARNING")
            return input_vector_path

        dissolved_dir = os.path.join(output_dir, "study_area")
        os.makedirs(dissolved_dir, exist_ok=True)
        dissolved_path = os.path.join(dissolved_dir, "boundaries_dissolved.gpkg")
        if os.path.exists(dissolved_path):
            try:
                os.remove(dissolved_path)
            except OSError as error:
                log_message(f"Could not replace dissolved AOI file: {error}. Using original AOI.", level="WARNING")
                return input_vector_path

        driver = ogr.GetDriverByName("GPKG")
        if driver is None:
            log_message("GPKG driver unavailable for dissolve output, using original AOI", level="WARNING")
            return input_vector_path
        dissolved_ds = driver.CreateDataSource(dissolved_path)
        if not dissolved_ds:
            log_message(
                f"Could not create dissolved AOI dataset: {dissolved_path}. Using original AOI.",
                level="WARNING",
            )
            return input_vector_path

        dissolved_layer = dissolved_ds.CreateLayer("boundaries_dissolved", source_srs, geom_type=ogr.wkbUnknown)
        if dissolved_layer is None:
            dissolved_ds = None
            log_message("Could not create dissolved AOI layer, using original AOI", level="WARNING")
            return input_vector_path
        dissolved_layer.CreateField(ogr.FieldDefn(field_name, ogr.OFTString))

        for area_name, dissolved_geom in dissolved_geometries.items():
            if dissolved_geom is None or dissolved_geom.IsEmpty():
                continue
            if dissolved_geom.GetCoordinateDimension() == 3:
                dissolved_geom.FlattenTo2D()

            feature = ogr.Feature(dissolved_layer.GetLayerDefn())
            feature.SetField(field_name, area_name)
            feature.SetGeometry(dissolved_geom)
            dissolved_layer.CreateFeature(feature)
            feature = None

        dissolved_ds = None
        log_message(f"Dissolved AOI created with {len(dissolved_geometries)} grouped feature(s)")
        return dissolved_path

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

            # Transform extent to Mollweide (ESRI:54009, not EPSG)
            source_srs = self.target_spatial_ref
            mollweide_srs = osr.SpatialReference()
            mollweide_srs.SetFromUserInput("ESRI:54009")

            transform_to_mollweide = osr.CoordinateTransformation(source_srs, mollweide_srs)

            bbox_ring = ogr.Geometry(ogr.wkbLinearRing)
            bbox_ring.AddPoint(extent[0], extent[2])
            bbox_ring.AddPoint(extent[1], extent[2])
            bbox_ring.AddPoint(extent[1], extent[3])
            bbox_ring.AddPoint(extent[0], extent[3])
            bbox_ring.AddPoint(extent[0], extent[2])

            bbox_polygon = ogr.Geometry(ogr.wkbPolygon)
            bbox_polygon.AddGeometry(bbox_ring)
            bbox_polygon.AssignSpatialReference(source_srs)
            bbox_polygon.Transform(transform_to_mollweide)

            mollweide_envelope = bbox_polygon.GetEnvelope()
            mollweide_xmin = mollweide_envelope[0]
            mollweide_xmax = mollweide_envelope[1]
            mollweide_ymin = mollweide_envelope[2]
            mollweide_ymax = mollweide_envelope[3]

            # Create QgsRectangle for extent_mollweide
            extent_mollweide = QgsRectangle(mollweide_xmin, mollweide_ymin, mollweide_xmax, mollweide_ymax)

            log_message(f"Study area extent in Mollweide: {extent_mollweide.toString()}")

            # Download GHSL using downloader
            # Note: GHSLDownloader expects extents in Mollweide (ESRI:54009) projection
            # because the tile index layer is in Mollweide
            log_message("Downloading GHSL tiles...")

            downloader = GHSLDownloader(
                extents=extent_mollweide,  # Must be in Mollweide projection
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

            # Reproject and save to GeoPackage using GDAL VectorTranslate
            # This is much faster than feature-by-feature reprojection
            log_message("Reprojecting GHSL to study area CRS using GDAL VectorTranslate...")

            ghsl_layer_name = "ghsl_settlements"

            try:
                # Use GDAL VectorTranslate for efficient batch reprojection
                # This handles the entire operation in one optimized call
                translate_options = gdal.VectorTranslateOptions(
                    format="GPKG",
                    accessMode="append",  # Append to existing GPKG
                    srcSRS="ESRI:54009",  # Mollweide
                    dstSRS=f"EPSG:{self.epsg_code}",
                    layerName=ghsl_layer_name,
                    geometryType="PROMOTE_TO_MULTI",  # Handle mixed geometry types
                )

                # Ensure GPKG exists
                if not os.path.exists(self.gpkg_path):
                    driver = ogr.GetDriverByName("GPKG")
                    ds = driver.CreateDataSource(self.gpkg_path)
                    ds = None

                result = gdal.VectorTranslate(
                    self.gpkg_path,
                    temp_parquet,
                    options=translate_options,
                )

                if result is None:
                    log_message("GDAL VectorTranslate failed", level="WARNING")
                    return None

                # Close result to flush writes
                result = None

                # Get feature count for logging
                ds = ogr.Open(self.gpkg_path, 0)
                if ds:
                    layer = ds.GetLayerByName(ghsl_layer_name)
                    if layer:
                        feature_count = layer.GetFeatureCount()
                        log_message(f"Successfully added {feature_count} GHSL features to GeoPackage")
                    ds = None

                return ghsl_layer_name

            finally:
                # Clean up temporary parquet file
                try:
                    if os.path.exists(temp_parquet):
                        os.remove(temp_parquet)
                except OSError as cleanup_error:
                    # Don't fail if we can't delete - GHSL data is already in GeoPackage
                    log_message(f"Could not remove temp parquet file: {cleanup_error}", level="INFO")

        except Exception as e:
            log_message(f"Error downloading/processing GHSL: {str(e)}", level="WARNING")
            log_message(traceback.format_exc(), level="WARNING")
            return None

    def create_ghsl_layer_if_not_exists(self, layer_name):
        """Create GHSL layer in GeoPackage if it doesn't exist.

        Args:
            layer_name: Name of the layer to create.
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
        """Main entry point (mimics process_study_area from QGIS code).

        Returns:
            True if processing completed successfully, False otherwise.
        """
        self.termination_reason = ""
        self.termination_detail = ""
        self._set_sqlite_write_safety_options()

        # Regional scale grids are generated with H3 — without the library
        # every chunk task quietly returns no cells and the study area ends
        # up with an empty grid. Fail fast with a clear message instead.
        if self.analysis_scale == "regional":
            try:
                import h3  # noqa: F401
            except ImportError:
                self._set_termination_reason(
                    reason="The H3 library is not available.",
                    detail="Regional scale analysis grids are built with H3 hexagons, but the "
                    "H3 python library is not installed in this QGIS environment. Install it "
                    "(e.g. pip install h3) and re-create the study area.",
                )
                return False

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
                log_message("GHSL download failed or no data available", level="WARNING")
                # Emit signal to UI to prompt user - pass error message
                error_msg = (
                    "GHSL (Global Human Settlement Layer) data could not be downloaded.\n\n"
                    "This data is used to filter study areas by population settlements. "
                    "Without it, all study areas will be processed regardless of settlement status.\n\n"
                    "Do you want to continue without GHSL data?"
                )
                self.ghsl_download_failed.emit(error_msg)

                # Wait for user response (with timeout to prevent deadlock)
                log_message("Waiting for user response about GHSL download failure...")
                self._ghsl_mutex.lock()
                # Wait up to 5 minutes for user response
                self._ghsl_wait_condition.wait(self._ghsl_mutex, 300000)  # 5 min in ms
                continue_without = self._ghsl_continue_without
                response_received = self._ghsl_response_received
                self._ghsl_mutex.unlock()

                if not response_received:
                    log_message("No user response received within timeout, aborting task", level="WARNING")
                    self._set_termination_reason(
                        reason="GHSL confirmation timed out.",
                        detail="GHSL download failed and confirmation timed out. "
                        "Check connectivity/settings and try again.",
                    )
                    return False

                if not continue_without:
                    log_message("User chose to abort task due to GHSL download failure")
                    self._set_termination_reason(
                        reason="GHSL download failed.",
                        detail="GHSL data could not be downloaded and processing was stopped.",
                    )
                    return False

                log_message("User chose to continue without GHSL data")
                self.ghsl_layer_name = None

            # 2.6) Pre-create all study area layers before worker threads start.
            # This avoids Windows-specific GeoPackage trigger/schema races when
            # layer creation happens while UnifiedWriter holds a persistent connection.
            self._prepare_study_area_layers()

            # 3) Process geometries one at a time (memory efficient)
            self.setProgress(5)  # Reserve 0-5% for GHSL, 5-95% for features
            invalid_feature_count = 0
            self.valid_feature_count = 0
            fixed_feature_count = 0

            # First pass: count total features for progress calculation
            self.source_layer.ResetReading()
            total_feature_count = self.source_layer.GetFeatureCount()
            log_message(f"Total features to process: {total_feature_count}")

            # Second pass: process geometries one at a time (memory efficient)
            self.source_layer.ResetReading()
            processed_count = 0
            for feature in self.source_layer:
                geom_ref = feature.GetGeometryRef()
                if not geom_ref:
                    processed_count += 1
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
                            processed_count += 1
                            continue
                        else:
                            fixed_feature_count += 1
                    except Exception as e:
                        invalid_feature_count += 1
                        log_message(f"Geometry fix error: {str(e)}", level="CRITICAL")
                        processed_count += 1
                        continue

                self.valid_feature_count += 1

                # Clone geometry for processing, then release after processing
                geom_clone = geom_ref.Clone()
                geom_type = ogr.GT_Flatten(geom_clone.GetGeometryType())
                is_multipart = geom_type == ogr.wkbMultiPolygon

                # Process this geometry immediately (memory efficient - one at a time)
                try:
                    if is_multipart:
                        log_message(f"Processing multipart geometry: {normalized_name}")
                        self.process_multipart_geometry(geom_clone, normalized_name, area_name)
                    else:
                        log_message(f"Processing singlepart geometry: {normalized_name}")
                        self.process_singlepart_geometry(geom_clone, normalized_name, area_name)
                finally:
                    # Explicitly release geometry reference after processing
                    geom_clone = None

                processed_count += 1
                # Update progress (5-95% range for geometry processing)
                if total_feature_count > 0:
                    progress = 5 + int((processed_count / total_feature_count) * 90)
                    self.setProgress(min(95, progress))

            log_message(f"Processed {self.valid_feature_count} geometries")

            self.setProgress(100)  # Trigger the UI to update with completion value
            log_message(
                f"Processing complete. Valid: {self.valid_feature_count}, Fixed: {fixed_feature_count}, Invalid: {invalid_feature_count}"
            )
            log_message(f"Areas that could not be processed due to errors: {self.error_count}")
            log_message(f"Total cells generated: {self.total_cells}")

            # 4) Add model columns to the grid layer
            model_path = os.path.join(self.working_dir, "model.json")
            if os.path.exists(model_path):
                log_message("Adding model columns to study_area_grid layer...")
                if add_model_columns_to_grid(self.gpkg_path, model_path):
                    log_message("Model columns added successfully")
                else:
                    log_message("Failed to add model columns, retrying after delay...", level="WARNING")
                    import time as _time

                    _time.sleep(2)
                    if not add_model_columns_to_grid(self.gpkg_path, model_path):
                        raise RuntimeError(
                            "Failed to add model columns to study_area_grid. "
                            "This may be a Windows GeoPackage locking issue. "
                            "Try reopening the project and re-running the analysis."
                        )
            else:
                log_message(f"Model file not found at {model_path}, skipping column addition", level="WARNING")

            # 5) Create a VRT of all generated raster masks
            self.create_raster_vrt()

            # 6) Verify the GeoPackage survived all concurrent writes intact,
            #    self-healing it in place if anything is amiss.
            self._verify_gpkg_health()

        except Exception as e:
            reason, detail = self._friendly_error_message(e)
            self._set_termination_reason(reason=reason, detail=detail)
            log_message(f"Error in run(): {str(e)}")
            log_message(traceback.format_exc())
            with open(os.path.join(self.working_dir, "error.txt"), "w") as f:
                f.write(f"{datetime.datetime.now()}\n")
                f.write(traceback.format_exc())
            return False

        finally:
            self._restore_sqlite_write_safety_options()
            # Explicit cleanup of GDAL resources to prevent memory leaks
            self._cleanup_gdal_resources()

        return True

    def _verify_gpkg_health(self) -> None:
        """Check the study area GeoPackage after processing, healing in place.

        Raises:
            RuntimeError: If the GeoPackage is corrupt and could not be
                healed, or if the analysis grid ended up empty (a study area
                without grid cells silently breaks every later analysis).
        """
        from geest.core.gpkg_doctor import heal_geopackage
        from geest.core.grid_column_utils import grid_cell_count

        report = heal_geopackage(self.gpkg_path, log=lambda message: log_message(message, tag="GeoE3"))
        if report.was_corrupt:
            log_message(
                f"Study area GeoPackage required self-healing: {report.summary()}",
                tag="GeoE3",
                level=Qgis.Warning,
            )
        if not report.healthy:
            raise RuntimeError(f"Study area GeoPackage is corrupt and could not be self-healed: {report.summary()}")

        cell_count = grid_cell_count(self.gpkg_path)
        log_message(f"Analysis grid contains {cell_count} cells", tag="GeoE3")
        if cell_count == 0:
            raise RuntimeError(
                "Study area creation produced an EMPTY analysis grid — no grid cells were "
                "written, so analyses would silently produce empty results. For Regional "
                "scale this can happen when the H3 library is unavailable in the QGIS "
                "python environment. Check the logs from the grid creation step."
            )

    def _set_termination_reason(self, reason: str, detail: str = "") -> None:
        """Store safe, user-facing termination text for the UI."""
        safe_reason = (reason or "Could not prepare study area.").strip()
        safe_detail = (detail or safe_reason).strip()
        self.termination_reason = safe_reason
        self.termination_detail = safe_detail

    def _friendly_error_message(self, error: Exception) -> tuple[str, str]:
        """Convert technical exceptions to user-friendly summary text."""
        error_message = str(error).strip()
        lowered = error_message.lower()

        if isinstance(error, PermissionError):
            return (
                "Cannot write output files.",
                "Cannot write output files. Check folder permissions and try again.",
            )

        if "failed to export layer to shapefile" in lowered:
            return (
                "Failed to export boundary layer.",
                "Failed to export the boundary layer. Check input layer validity and output path.",
            )

        if "could not open" in lowered and "ogr" in lowered:
            return (
                "Could not open study area layer.",
                "Could not read the study area layer. Check data source availability and try again.",
            )

        if "crs" in lowered and "epsg" in lowered:
            return (
                "Invalid CRS selection.",
                "The selected CRS is not EPSG-based. Choose a valid EPSG CRS and try again.",
            )

        if "database" in lowered and ("locked" in lowered or "readonly" in lowered):
            return (
                "Study area database is busy.",
                "The study area database is locked or read-only. Close other apps and retry.",
            )

        if "ghsl" in lowered:
            return (
                "GHSL data processing failed.",
                "GHSL data could not be processed. Check connectivity/settings and try again.",
            )

        if error_message:
            return (
                "Could not prepare study area.",
                f"Could not prepare study area: {error_message}",
            )

        return (
            "Could not prepare study area.",
            "An unexpected error occurred while preparing the study area.",
        )

    def _writer_is_active(self) -> bool:
        """Return True when unified writer thread is currently running."""
        return self.writer_thread is not None and self.writer_thread.isRunning()

    def _prepare_study_area_layers(self) -> None:
        """Create required study area layers before background writes begin.

        Every layer that will be written during processing is created here,
        up front, so no schema DDL (and its rtree trigger creation) ever runs
        while the unified writer holds its persistent connection.
        """
        self.create_layer_if_not_exists("study_area_bboxes")
        self.create_layer_if_not_exists("study_area_polygons")
        self.create_layer_if_not_exists("study_area_clip_polygons")
        self.create_layer_if_not_exists("chunks")
        self.create_grid_layer_if_not_exists("study_area_grid")

    def _set_sqlite_write_safety_options(self) -> None:
        """Configure safer SQLite options for GeoPackage writes.

        Delegates to the shared geest.utilities helper - see that module for
        why SQLITE_USE_OGR_VFS must stay off. These options are process-wide
        in GDAL, so the caller snapshots and restores them per task
        execution; note the same hardening is also applied around workflow
        (analysis) execution in WorkflowQueueManager, since AreaIterator
        reads and grid_column_utils writes against the same GeoPackage there
        are exactly the kind of concurrent access this guards against.
        """
        self._previous_gdal_sqlite_options = apply_sqlite_write_safety_options()
        log_message("Configured safer GeoPackage write settings (WAL/NORMAL, OGR VFS off)")

    def _restore_sqlite_write_safety_options(self) -> None:
        """Restore GDAL SQLite options captured before task execution."""
        restore_sqlite_write_safety_options(self._previous_gdal_sqlite_options)

    def _cleanup_gdal_resources(self):
        """Clean up GDAL/OGR resources to prevent memory leaks and file handle issues."""
        try:
            if hasattr(self, "source_layer") and self.source_layer:
                self.source_layer = None
            if hasattr(self, "source_ds") and self.source_ds:
                self.source_ds = None

            if hasattr(self, "write_queue") and self.write_queue:
                try:
                    while not self.write_queue.empty():
                        try:
                            self.write_queue.get_nowait()
                        except Exception:
                            break
                except Exception:  # nosec B110
                    pass  # Best-effort drain during cleanup
                self.write_queue = None

            log_message("GDAL resources cleaned up successfully")
        except Exception as e:
            log_message(f"Error during GDAL cleanup: {e}", level="WARNING")

    ##########################################################################
    # Table creation logic
    ##########################################################################
    def create_status_tracking_table(self):
        """Create a table in the GeoPackage to track processing status.

        Raises:
            RuntimeError: If the GeoPackage cannot be created or opened.
        """
        if not os.path.exists(self.gpkg_path):
            # Just create it if no GPKG
            driver = ogr.GetDriverByName("GPKG")
            ds = driver.CreateDataSource(self.gpkg_path)
            if not ds:
                raise RuntimeError(f"Could not create GeoPackage {self.gpkg_path}")
            ds = None

        ds = ogr.Open(self.gpkg_path, 1)
        if not ds:
            raise RuntimeError(f"Could not open or create {self.gpkg_path} for update.")
        try:
            layer = ds.GetLayerByName(self.status_table_name)
            if layer:
                log_message(f"Table '{self.status_table_name}' already exists.")
                return

            srs = osr.SpatialReference()
            srs.ImportFromEPSG(4326)

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
        """Add a new status tracking row - queues if writer running, else writes directly.

        Args:
            area_name: Name of study area to track
        """
        if self.write_queue is not None:
            op = GpkgOperation.insert_status(area_name=area_name)
            self.write_queue.put(op)
        else:
            self._insert_status_directly(area_name)

    def set_status_tracking_table_value(self, area_name, field_name, value):
        """Update status tracking field - queues if writer running, else writes directly.

        Args:
            area_name: Name of study area
            field_name: Field to update
            value: New value for field
        """
        if self.write_queue is not None:
            op = GpkgOperation.update_status(area_name=area_name, field_name=field_name, value=value)
            self.write_queue.put(op)
        else:
            self._update_status_directly(area_name, field_name, value)

    def _insert_status_directly(self, area_name):
        """Insert a status tracking row directly (synchronous).

        Args:
            area_name: Name of study area

        Raises:
            RuntimeError: If the GeoPackage or status table cannot be opened.
        """
        self.gpkg_lock.lock()
        try:
            ds = ogr.Open(self.gpkg_path, 1)
            if not ds:
                raise RuntimeError(f"Could not open {self.gpkg_path}")

            layer = ds.GetLayerByName(self.status_table_name)
            if not layer:
                raise RuntimeError(f"Status table {self.status_table_name} not found")

            feat_defn = layer.GetLayerDefn()
            feat = ogr.Feature(feat_defn)
            feat.SetField("area_name", area_name)
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
        finally:
            self.gpkg_lock.unlock()

    def _update_status_directly(self, area_name, field_name, value):
        """Update a status tracking field directly (synchronous).

        Args:
            area_name: Name of study area
            field_name: Field to update
            value: New value

        Raises:
            RuntimeError: If the GeoPackage or status table cannot be opened.
        """
        self.gpkg_lock.lock()
        try:
            ds = ogr.Open(self.gpkg_path, 1)
            if not ds:
                raise RuntimeError(f"Could not open {self.gpkg_path}")

            layer = ds.GetLayerByName(self.status_table_name)
            if not layer:
                raise RuntimeError(f"Status table {self.status_table_name} not found")

            layer.SetAttributeFilter(f"area_name = '{area_name}'")
            for feature in layer:
                feature.SetField(field_name, value)
                layer.SetFeature(feature)
            layer.SetAttributeFilter(None)
            layer.ResetReading()
            ds = None
        finally:
            self.gpkg_lock.unlock()

    # NOTE: _flush_status_updates methods removed - status updates now queued via UnifiedWriterThread

    ##########################################################################
    # Geometry processing
    ##########################################################################
    def process_singlepart_geometry(self, geom, normalized_name, area_name, shared_layer=None):
        """
        Process a single-part geometry:
         1) Align bounding box
         2) Save bounding box as a feature
         3) Transform geometry
         4) Save geometry
         5) Create vector grid
         6) Create clip polygon
         7) Optionally create raster mask

        Args:
            geom: OGR geometry to process
            normalized_name: Normalized name for this geometry
            area_name: Original area name
            shared_layer: Optional pre-opened layer for grid writing (when called from multipart context).
                         If provided, uses shared writer thread instead of managing its own.
        """
        geometry_start_time = time.time()

        now = datetime.datetime.now()  # Get current datetime
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")  # Format the datetime object

        self.set_status_tracking_table_value(normalized_name, "timestamp_start", now_str)

        #  Check we have a single part geom
        geom_type = ogr.GT_Flatten(geom.GetGeometryType())
        if geom_type != ogr.wkbPolygon:
            log_message(f"Skipping non-polygon geometry type {geom_type} for {normalized_name}.")
            # Increment counter even for skipped parts to maintain progress accuracy
            self.counter += 1
            progress = int((self.counter / self.parts_count) * 100)
            self.setProgress(progress)
            return
        # For Polygon type, GetGeometryCount() returns number of rings (exterior + holes)
        # This is valid - polygons with holes are single-part geometries
        # Only check for actual nested multipolygons
        if geom_type == ogr.wkbMultiPolygon:
            log_message(
                f"Skipping nested multi-part geometry for {normalized_name}.",
                level="WARNING",
            )
            # Increment counter even for skipped parts to maintain progress accuracy
            self.counter += 1
            progress = int((self.counter / self.parts_count) * 100)
            self.setProgress(progress)
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
        log_message(
            f"DIAG: {normalized_name} geom envelope BEFORE transform: {geom.GetEnvelope()}, "
            f"coord_transform is {'SET' if self.coord_transform else 'NONE (transform will be SKIPPED)'}"
        )
        if self.coord_transform:
            geom.Transform(self.coord_transform)
        log_message(f"DIAG: {normalized_name} geom envelope AFTER transform: {geom.GetEnvelope()}")

        # Check GHSL intersection
        intersects_ghsl = self.check_ghsl_intersection(geom)
        log_message(f"{normalized_name} intersects GHSL: {intersects_ghsl}")

        if self.analysis_scale == "regional" and not self._validate_regional_h3_runtime_guard(geom, normalized_name):
            self.error_count += 1
            self.counter += 1
            progress = int((self.counter / self.parts_count) * 100)
            self.setProgress(progress)
            return

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
        if shared_layer is not None:
            # Use shared writer thread (multipart geometry context)
            log_message(f"Using shared writer thread for {normalized_name}")
            self._process_grid_chunks_for_geometry(shared_layer, normalized_name, geom, aligned_bbox)
        else:
            # Standalone singlepart geometry - manage own writer thread
            self.create_and_save_grid(normalized_name, geom, aligned_bbox)
        if shared_layer is not None:
            self._wait_for_writer_queue()
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
        """Process each part of a multi-part geometry with unified writer thread.

        This method starts ONE UnifiedWriterThread for ALL parts and ALL database operations,
        preventing database corruption from concurrent access while maintaining high performance.

        Args:
            geom: OGR multi-part geometry
            normalized_name: Base name for the area
            area_name: Original area name
        """
        count = geom.GetGeometryCount()
        log_message(f"Processing {count} parts for {normalized_name} with unified writer thread")

        parts_to_process = []
        for i in range(count):
            part_geom = geom.GetGeometryRef(i)
            part_name = f"{normalized_name}_part{i}"
            parts_to_process.append((part_geom.Clone(), part_name))

        # Ensure grid layer exists (created synchronously before starting writer)
        grid_layer_name = "study_area_grid"
        self.create_grid_layer_if_not_exists(grid_layer_name)

        log_message(f"Starting unified writer thread for {count} parts")
        self._start_unified_writer(normalized_name)

        try:
            # Process all parts - all database operations automatically queued
            self._process_parts_sequential(parts_to_process, area_name, shared_layer=None)
        finally:
            # Stop writer thread ONCE after all parts complete
            log_message(f"Stopping unified writer thread after {count} parts")
            writer_stopped = self._stop_writer_thread()

            if writer_stopped:
                log_message("Unified writer stopped and database flushed")

            # Print metrics summary for multipart geometry
            log_message("=== Multipart Geometry Metrics Summary ===")
            for k, v in self.metrics.items():
                log_message(f"{k}: {v:.4f} seconds")
            self.total_cells += self.current_geom_actual_cell_count

    def _process_parts_sequential(self, parts_to_process, area_name, shared_layer=None):
        """Process geometry parts sequentially.

        Args:
            parts_to_process: List of (geometry, name) tuples
            area_name: Original area name
            shared_layer: Optional pre-opened layer for grid writing (for multipart geometries)
        """
        for part_geom, part_name in parts_to_process:
            try:
                self.process_singlepart_geometry(part_geom, part_name, area_name, shared_layer=shared_layer)
            except Exception as e:
                log_message(f"Failed to process part {part_name}: {str(e)}", level="ERROR")
                log_message(f"Traceback: {traceback.format_exc()}", level="ERROR")
                self.error_count += 1
                # Increment counter for failed parts to maintain progress accuracy
                self.counter += 1
                progress = int((self.counter / self.parts_count) * 100)
                self.setProgress(progress)

    ##########################################################################
    # BBox handling
    ##########################################################################
    def transform_and_align_bbox(self, bbox):
        """Transform and align a bounding box to the target CRS and grid.

        Args:
            bbox: Bounding box tuple (xmin, xmax, ymin, ymax) in source CRS.

        Returns:
            New bounding box (xmin, xmax, ymin, ymax) aligned to grid in target CRS.
        """
        xmin, xmax, ymin, ymax = bbox

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
        """Save a bounding-box polygon to the specified layer (creating it if needed).

        Args:
            layer_name: Name of the layer to save to.
            bbox: Bounding box tuple (xmin, xmax, ymin, ymax).
            area_name: Name of the area for the feature.
        """
        # BBox is (xmin, xmax, ymin, ymax)
        xmin, xmax, ymin, ymax = bbox
        ring = ogr.Geometry(ogr.wkbLinearRing)
        # Use AddPoint_2D to create 2D geometry (not 2.5D with Z=0)
        ring.AddPoint_2D(xmin, ymin)
        ring.AddPoint_2D(xmin, ymax)
        ring.AddPoint_2D(xmax, ymax)
        ring.AddPoint_2D(xmax, ymin)
        ring.AddPoint_2D(xmin, ymin)
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
        if not hasattr(self, "ghsl_layer_name") or self.ghsl_layer_name is None:
            log_message("GHSL layer not available, defaulting to True for intersection", level="INFO")
            return True

        try:
            ds = ogr.Open(self.gpkg_path, 0)
            if not ds:
                log_message("Could not open GeoPackage for GHSL check", level="WARNING")
                return True

            ghsl_layer = ds.GetLayerByName(self.ghsl_layer_name)
            if not ghsl_layer:
                log_message(f"GHSL layer '{self.ghsl_layer_name}' not found", level="WARNING")
                ds = None
                return True

            total_ghsl_features = ghsl_layer.GetFeatureCount()
            log_message(f"GHSL layer has {total_ghsl_features} total features")

            ghsl_layer.SetSpatialFilter(geom)
            filtered_count = ghsl_layer.GetFeatureCount()
            log_message(f"GHSL spatial filter found {filtered_count} candidate features")

            intersects = False
            checked_count = 0
            for ghsl_feature in ghsl_layer:
                checked_count += 1
                ghsl_geom = ghsl_feature.GetGeometryRef()
                if ghsl_geom and geom.Intersects(ghsl_geom):
                    log_message(f"Found intersection with GHSL feature {checked_count}")
                    intersects = True
                    break

            log_message(f"Checked {checked_count} GHSL features, intersects: {intersects}")

            ghsl_layer.SetSpatialFilter(None)
            ds = None

            return intersects

        except Exception as e:
            log_message(f"Error checking GHSL intersection: {str(e)}", level="WARNING")
            return True

    def save_geometry_to_geopackage(self, layer_name, geom, area_name, intersects_ghsl=True):
        """Save geometry to GeoPackage - queues if writer thread running, else writes directly.

        Args:
            layer_name: Name of the layer
            geom: OGR geometry
            area_name: Name of the area
            intersects_ghsl: Whether geometry intersects GHSL
        """
        # Ensure layer exists only when writer is not active.
        # When UnifiedWriter is active, creating layers from a second connection
        # can trigger Windows-specific GeoPackage schema races.
        if not self._writer_is_active():
            self.create_layer_if_not_exists(layer_name)

        # Prepare extra fields
        extra_fields = {}
        if layer_name == "study_area_polygons":
            extra_fields["intersects_ghsl"] = 1 if intersects_ghsl else 0
            extra_fields["geom_area"] = geom.GetArea()

        if self.write_queue is not None:
            op = GpkgOperation.write_geometry(
                layer_name=layer_name, geometry=geom.Clone(), area_name=area_name, **extra_fields
            )
            self.write_queue.put(op)
        else:
            log_message(f"Writing {layer_name} directly (writer not started yet)")
            self._write_geometry_directly(layer_name, geom, area_name, **extra_fields)

    def _write_geometry_directly(self, layer_name, geom, area_name, **extra_fields):
        """Write a single geometry directly to the GeoPackage (synchronous).

        Used when UnifiedWriterThread is not running yet (e.g., early bbox writes).

        Args:
            layer_name: Name of the layer
            geom: OGR geometry
            area_name: Name of the area
            **extra_fields: Additional fields to set

        Raises:
            RuntimeError: If the GeoPackage or target layer cannot be opened.
        """
        self.gpkg_lock.lock()
        try:
            ds = ogr.Open(self.gpkg_path, 1)
            if not ds:
                raise RuntimeError(f"Could not open {self.gpkg_path} for writing")

            layer = ds.GetLayerByName(layer_name)
            if not layer:
                raise RuntimeError(f"Layer {layer_name} not found")

            feat_defn = layer.GetLayerDefn()
            feature = ogr.Feature(feat_defn)
            feature.SetField("area_name", area_name)

            # Set any extra fields
            for field_name, value in extra_fields.items():
                feature.SetField(field_name, value)

            feature.SetGeometry(geom)
            layer.CreateFeature(feature)
            feature = None
            ds = None

            log_message(f"Wrote geometry to {layer_name} directly")
        finally:
            self.gpkg_lock.unlock()

    def create_layer_if_not_exists(self, layer_name):
        """Create a GPKG layer if it does not exist.

        Args:
            layer_name: Name of the layer to create.
        """
        self.gpkg_lock.lock()
        try:
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
                # Store computed area to avoid recalculation during iteration
                area_field = ogr.FieldDefn("geom_area", ogr.OFTReal)
                layer.CreateField(area_field)

            if layer_name == "chunks":
                layer.CreateField(ogr.FieldDefn("index", ogr.OFTInteger))
                layer.CreateField(ogr.FieldDefn("type", ogr.OFTString))

            # Flush to ensure writer thread can see this layer
            ds.FlushCache()
            ds = None
            log_message(f"Created layer: {layer_name}")
        finally:
            self.gpkg_lock.unlock()

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
    # Maximum queue size to limit memory (~100k items * ~1KB = ~100MB max)
    WRITE_QUEUE_MAX_SIZE = 100000

    def _start_unified_writer(self, normalized_name):
        """Start unified writer thread for all database operations (thread-safe singleton with ref counting).

        Uses bounded queue to limit memory usage and routes ALL GeoPackage operations
        through a single thread to prevent database corruption from concurrent access.

        Args:
            normalized_name: Name of the area being processed.
        """
        self.writer_start_lock.lock()
        try:
            self.writer_ref_count += 1

            if self.writer_thread is not None and self.writer_thread.isRunning():
                log_message(
                    f"UnifiedWriter already running (ref_count={self.writer_ref_count}), reusing existing thread"
                )
                return

            log_message(f"Starting new UnifiedWriter thread (ref_count={self.writer_ref_count})")
            # Use bounded queue to limit memory usage
            self.write_queue = QtQueue(maxsize=self.WRITE_QUEUE_MAX_SIZE)

            # Create and start the unified writer thread
            # It will open its own persistent connection to the GeoPackage
            self.writer_thread = UnifiedWriterThread(
                queue=self.write_queue,
                gpkg_path=self.gpkg_path,
                target_srs=self.target_spatial_ref,
                flush_token=self._writer_flush_token,
                parent_task=self,  # Pass reference for shared state access
            )
            self.writer_thread.start()
            log_message("UnifiedWriter thread started")
        finally:
            self.writer_start_lock.unlock()

    def _stop_writer_thread(self):
        """Stop unified writer thread with ref counting. Only stops when last part finishes.

        Uses timeouts to prevent deadlocks.

        Returns:
            bool: True if writer was stopped, False if still in use by other parts
        """
        QUEUE_TIMEOUT = 60  # seconds
        THREAD_TIMEOUT_MS = 30000  # milliseconds

        self.writer_start_lock.lock()
        try:
            self.writer_ref_count -= 1
            log_message(f"UnifiedWriter thread ref count: {self.writer_ref_count}")

            if self.writer_ref_count > 0:
                log_message(f"UnifiedWriter still in use by {self.writer_ref_count} part(s), not stopping")
                return False

            log_message("All parts finished, stopping UnifiedWriter thread")
            if self.write_queue is not None:
                try:
                    # Send poison pill with timeout
                    if not self.write_queue.put(None, timeout=QUEUE_TIMEOUT):
                        log_message("Warning: timeout putting poison pill in queue", level="WARNING")
                except Exception as e:
                    log_message(f"Warning: error putting poison pill in queue: {e}", level="WARNING")

                # Wait for queue to drain with timeout
                try:
                    start = time.time()
                    while not self.write_queue.empty():
                        if time.time() - start > QUEUE_TIMEOUT:
                            log_message("Warning: timeout waiting for queue to drain", level="WARNING")
                            break
                        time.sleep(0.1)
                except Exception as e:
                    log_message(f"Warning: error waiting for queue: {e}", level="WARNING")

                if self.writer_thread is not None:
                    self.writer_thread.request_stop()
                    if not self.writer_thread.wait(THREAD_TIMEOUT_MS):
                        log_message("Warning: UnifiedWriter thread did not terminate within timeout", level="WARNING")
                    else:
                        log_message("UnifiedWriter thread stopped")

            # UnifiedWriterThread manages its own dataset connection - no need to close here
            self.write_queue = None
            self.writer_thread = None
            log_message("UnifiedWriter cleaned up")
            return True
        finally:
            self.writer_start_lock.unlock()

    def _wait_for_writer_queue(self):
        """Block until the writer queue is flushed."""
        if self.write_queue is None:
            return
        log_message("Waiting for grid writer queue to flush before continuing.")
        self.write_queue.put(self._writer_flush_token)
        self.write_queue.join()
        log_message("Grid writer queue flushed.")

    # NOTE: _write_batch() removed - UnifiedWriterThread handles batch writing internally

    def _process_grid_chunks_for_geometry(self, layer, normalized_name, geom, bbox):
        """Process grid chunks for a single geometry (core chunk processing logic).

        This method assumes:
        - Layer is already open
        - Writer thread is already started
        - Does NOT manage writer lifecycle or dataset connections

        Args:
            layer: Already-open OGR layer for writing grid cells
            normalized_name: Name of study area
            geom: OGR geometry defining area boundary
            bbox: Tuple of (xmin, xmax, ymin, ymax) for grid extent

        Raises:
            RuntimeError: If there is an error processing the grid chunks.
        """
        xmin, xmax, ymin, ymax = bbox
        cell_size = self.cell_size_m
        chunk_size = int(setting(key="chunk_size", default=100))

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

        # Chunk tiles are queued through the unified writer below (single
        # writer connection — no second write connection racing it, so no
        # lock/retry dance). The layer itself is pre-created before any
        # worker starts (_prepare_study_area_layers).
        log_message(f"Creating grid for extents: xmin {xmin}, xmax {xmax}, ymin {ymin}, ymax {ymax}")

        feedback = QgsFeedback()

        chunk_count = chunker.total_chunks()
        log_message(f"Chunk count: {chunk_count}")
        log_message(f"Chunk size: {chunk_size}")

        chunks_to_process = []
        for counter, chunk in enumerate(chunker.chunks(), start=1):
            # Queue the chunk tile via the unified writer (cloned so the
            # writer thread never shares a live geometry with the chunk
            # processing workers).
            self.write_queue.put(
                GpkgOperation.write_geometry(
                    "chunks",
                    chunk["geometry"].Clone(),
                    normalized_name,
                    index=chunk["index"],
                    type=chunk["type"],
                )
            )
            if chunk["type"] != "undefined":
                chunks_to_process.append(chunk)
            else:
                log_message(f"Chunk {chunk['index']} is outside the geometry.")
            try:
                current_progress = min(100, int((counter / chunk_count) * 100))
                log_message(f"XXXXXX Chunks Progress: {counter} / {chunk_count} : {current_progress}% XXXXXX")
                self.feedback.setProgress(current_progress)
            except ZeroDivisionError:
                pass

        valid_chunk_count = len(chunks_to_process)
        log_message(f"Valid chunks to process: {valid_chunk_count}")

        worker_count = int(setting(key="grid_creation_workers", default=4))
        worker_count = max(1, min(8, worker_count))

        self.feedback.setProgress(0)

        # Process chunks (writer thread must already be started by caller)
        if worker_count == 1:
            log_message("Using sequential processing (worker_count=1)")
            self._process_chunks_sequential(layer, chunks_to_process, geom, cell_size, normalized_name, feedback)
        else:
            log_message(f"Using parallel processing with {worker_count} workers")
            try:
                self._process_chunks_parallel(
                    layer, chunks_to_process, geom, cell_size, normalized_name, feedback, worker_count
                )
            except Exception as e:
                log_message(f"Parallel processing failed: {str(e)}", level="WARNING")
                log_message("Falling back to sequential processing", level="WARNING")
                log_message(traceback.format_exc(), level="WARNING")
                self._process_chunks_sequential(layer, chunks_to_process, geom, cell_size, normalized_name, feedback)
        log_message(f"Grid creation completed for area {normalized_name}.")

    def create_and_save_grid(self, normalized_name, geom, bbox):
        """Create vector grid and write intersecting cells to study_area_grid layer.

        This is the main entry point for grid creation, managing unified writer thread lifecycle.
        For singlepart geometries or when called standalone.

        Args:
            normalized_name: Name of study area
            geom: OGR geometry defining area boundary
            bbox: Tuple of (xmin, xmax, ymin, ymax) for grid extent
        """
        grid_layer_name = "study_area_grid"
        if not self._writer_is_active():
            self.create_grid_layer_if_not_exists(grid_layer_name)

        # Start unified writer thread for this geometry
        self._start_unified_writer(normalized_name)

        try:
            # Process grid chunks - writes are automatically queued
            self._process_grid_chunks_for_geometry(None, normalized_name, geom, bbox)

            # Flush to ensure all grid cells written before continuing
            if self.write_queue:
                log_message("Flushing write queue after grid creation")
                self.write_queue.put(self._writer_flush_token)
                self.write_queue.join()
                log_message("Write queue flushed")
        finally:
            # Stop writer thread and cleanup
            writer_stopped = self._stop_writer_thread()

            if writer_stopped:
                log_message("Unified writer stopped and database flushed")

        # Print out metrics summary
        log_message("=== Metrics Summary ===")
        for k, v in self.metrics.items():
            log_message(f"{k}: {v:.4f} seconds")  # noqa: E231
        self.total_cells += self.current_geom_actual_cell_count

    def _create_grid_task(self, index, bbox_chunk, geom, cell_size, feedback):
        """Create the appropriate grid task based on analysis scale.

        Args:
            index: Chunk index.
            bbox_chunk: Tuple of (x_start, x_end, y_start, y_end).
            geom: OGR geometry for intersection testing.
            cell_size: Cell size in meters.
            feedback: QgsFeedback for progress reporting.

        Returns:
            Grid task (GridFromBboxTask or GridFromBboxH3Task)
        """
        if self.analysis_scale == "regional":
            h3_res = self.h3_resolution
            log_message(f"Creating H3 grid task (resolution {h3_res}) for chunk {index}")
            task = GridFromBboxH3Task(
                index,
                bbox_chunk,
                geom,
                int(self.epsg_code),
                h3_res,
                feedback,
            )
        else:
            task = GridFromBboxTask(
                index,
                bbox_chunk,
                geom,
                cell_size,
                feedback,
            )
        return task

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

            task = self._create_grid_task(
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
        """Process chunks in parallel using QThreadPool.

        Each worker writes its results to the unified write queue as soon as
        it finishes a chunk, then frees the geometries. This keeps peak memory
        proportional to (worker_count * chunk_size^2) rather than
        (total_chunks * chunk_size^2).

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
        progress_lock = QMutex()

        # Get global thread pool and set max thread count
        pool = QThreadPool.globalInstance()
        pool.setMaxThreadCount(worker_count)

        def _write_callback(task, start_time):
            """Called from worker threads to queue results immediately.

            Args:
                task: The completed GridFromBboxTask with features_out.
                start_time: When the chunk started processing.
            """
            nonlocal completed_count
            self.track_time("Creating chunks", start_time)
            self.write_chunk(layer, task, normalized_name)
            self.track_time("Complete chunk", start_time)

            progress_lock.lock()
            try:
                completed_count += 1
                count = completed_count
            finally:
                progress_lock.unlock()

            try:
                current_progress = int((count / total_chunks) * 100)
                if count % 10 == 0 or count == total_chunks:
                    log_message(f"Chunk progress: {count}/{total_chunks} ({current_progress}%)")
                self.feedback.setProgress(current_progress)
            except ZeroDivisionError:
                pass

        # Submit all chunks but each writes+frees immediately on completion
        runnables = []
        for chunk in chunks:
            runnable = ChunkRunnable(
                chunk,
                geom,
                cell_size,
                feedback,
                write_callback=_write_callback,
                analysis_scale=self.analysis_scale,
                epsg_code=self.epsg_code,
                h3_resolution=self.h3_resolution,
            )
            runnables.append(runnable)
            pool.start(runnable)

        pool.waitForDone()

        # Check for errors (results already written)
        for runnable in runnables:
            if runnable.error is not None:
                failed_count += 1
                log_message(f"Chunk {runnable.chunk['index']} failed: {str(runnable.error)}", level="WARNING")

        if failed_count > 0:
            log_message(f"Grid creation completed with {failed_count} failed chunks", level="WARNING")

    def write_chunk(self, layer, task, normalized_name):
        """Queue features for async batched writing by unified writer thread.

        Args:
            layer: Unused (kept for compatibility)
            task: GridFromBboxTask or GridFromBboxH3Task with generated features
            normalized_name: Area name for this chunk
        """
        self.metrics["Preparing chunks"] += task.run_time

        # Check if this is an H3 task (features are tuples of (h3_index, geometry))
        is_h3_task = isinstance(task.features_out[0], tuple) if task.features_out else False

        if is_h3_task:
            h3_resolution = self.h3_resolution

        for feature in task.features_out:
            # Get unique grid_id with lock
            self.grid_id_lock.lock()
            try:
                grid_id = self.current_geom_actual_cell_count
                self.current_geom_actual_cell_count += 1
            finally:
                self.grid_id_lock.unlock()

            # Handle H3 features (tuples) vs square grid features (just geometry)
            if is_h3_task:
                h3_index, geometry = feature
                op = GpkgOperation.write_grid_cell(
                    geometry=geometry,
                    area_name=normalized_name,
                    grid_id=grid_id,
                    h3_index=h3_index,
                    h3_resolution=h3_resolution,
                )
            else:
                op = GpkgOperation.write_grid_cell(
                    geometry=feature,
                    area_name=normalized_name,
                    grid_id=grid_id,
                )
            self.write_queue.put(op)

        # Free geometries after queuing to release memory
        task.features_out = []

    def create_grid_layer_if_not_exists(self, layer_name):
        """Create a GeoPackage grid layer.

        Args:
            layer_name: Name of the layer to create.
        """
        self.gpkg_lock.lock()
        try:
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

                # Add H3 fields for regional scale
                if self.analysis_scale == "regional":

                    h3_res = self.h3_resolution
                    field_defn = ogr.FieldDefn("h3_index", ogr.OFTString)
                    layer.CreateField(field_defn)
                    field_defn = ogr.FieldDefn("h3_resolution", ogr.OFTInteger)
                    layer.CreateField(field_defn)
                    log_message(f"Created grid layer with H3 fields (resolution {h3_res})")

            ds = None
        finally:
            self.gpkg_lock.unlock()

    ##########################################################################
    # Create Clip Polygon
    ##########################################################################
    def create_clip_polygon(self, geom, aligned_box, normalized_name):
        """Create a polygon that includes geometry plus all grid cells that intersect boundary.

        Uses optimized spatial filtering with buffered boundary to reduce intersection checks.
        Memory-efficient batched processing limits memory usage to ~500MB max.

        Performance optimizations:
        - Buffered boundary spatial filter reduces candidate cells by ~90%
        - Two-phase check: fast Contains() then precise Intersects()
        - Batched UnionCascaded for efficient geometry merging

        Args:
            geom: OGR geometry to create clip polygon for.
            aligned_box: Aligned bounding box (unused, kept for API compatibility).
            normalized_name: Name of the area.

        Raises:
            RuntimeError: If the grid layer is missing.
        """
        # Memory-efficient batch size - roughly 50k geometries at ~10KB each = ~500MB
        BATCH_SIZE = 50000

        # CRITICAL: Flush all pending writes before reading grid
        # This prevents "database disk image is malformed" errors from concurrent access
        if self.write_queue:
            log_message(f"Flushing write queue before reading grid for {normalized_name}")
            self.write_queue.put(self._writer_flush_token)
            self.write_queue.join()  # Wait for flush to complete
            log_message("Write queue flushed successfully")

        grid_ds = None
        try:
            # Load the grid from GeoPackage (read-only)
            grid_ds = ogr.Open(self.gpkg_path, 0)
            grid_layer = grid_ds.GetLayerByName("study_area_grid")

            if not grid_layer:
                raise RuntimeError("Missing study_area_grid layer.")

            grid_layer.SetAttributeFilter(f"area_name = '{normalized_name}'")
            # Get boundary for intersection testing
            boundary = geom.GetBoundary()

            # OPTIMIZATION: Buffer the boundary by cell_size to create a narrow band
            # that we use as a spatial filter. This dramatically reduces the number
            # of cells we need to check for intersection.
            buffer_distance = self.cell_size_m * 1.5  # Slightly larger than cell diagonal
            buffered_boundary = boundary.Buffer(buffer_distance)

            # Use buffered boundary as spatial filter instead of full bbox
            # This can reduce cells to check by 90%+ for large study areas
            grid_layer.SetSpatialFilter(buffered_boundary)

            # Count features for progress updates
            total_features = grid_layer.GetFeatureCount()
            log_message(
                f"Processing {total_features} candidate cells for clip polygon "
                f"(filtered from bbox using {buffer_distance}m buffer)"
            )

            # Process in batches to limit memory usage
            # We accumulate intersecting cells and periodically union them
            dissolved_geom = None
            intersecting_count = 0
            skipped_inside = 0
            count = 0
            current_batch = []

            # Log interval for progress - reduce logging frequency for performance
            log_interval = max(1, total_features // 10)  # Log ~10 times

            grid_layer.ResetReading()
            for f in grid_layer:
                cell_geom = f.GetGeometryRef()
                if cell_geom:
                    # OPTIMIZATION: Two-phase check
                    # Phase 1: If cell is fully inside geometry, skip it (not on boundary)
                    if geom.Contains(cell_geom):
                        skipped_inside += 1
                    # Phase 2: Check if cell intersects the boundary
                    elif boundary.Intersects(cell_geom):
                        # Only clone cells that actually intersect boundary
                        current_batch.append(cell_geom.Clone())
                        intersecting_count += 1

                count += 1
                if count % log_interval == 0:
                    if total_features > 0:
                        progress = min(100, int((count / total_features) * 100))
                        self.feedback.setProgress(progress)

                # When batch is full, union and release memory
                if len(current_batch) >= BATCH_SIZE:
                    log_message(f"Processing batch of {len(current_batch)} intersecting cells...")
                    batch_union = self._union_geometries(current_batch)
                    if dissolved_geom is None:
                        dissolved_geom = batch_union
                    else:
                        dissolved_geom = dissolved_geom.Union(batch_union)
                        batch_union = None  # Release reference
                    # Clear batch to free memory
                    current_batch = []

            # Process remaining cells in final batch
            if current_batch:
                log_message(f"Processing final batch of {len(current_batch)} intersecting cells...")
                batch_union = self._union_geometries(current_batch)
                if dissolved_geom is None:
                    dissolved_geom = batch_union
                else:
                    dissolved_geom = dissolved_geom.Union(batch_union)
                    batch_union = None
                current_batch = []  # Clear for GC

            grid_layer.SetSpatialFilter(None)  # Clear filter

            log_message(
                f"Found {intersecting_count} boundary cells, skipped {skipped_inside} interior cells "
                f"(from {count} candidates)"
            )

            # Add the original geometry to the dissolved result
            if dissolved_geom is None:
                dissolved_geom = geom.Clone()
            else:
                dissolved_geom = dissolved_geom.Union(geom)

            if dissolved_geom is None or dissolved_geom.IsEmpty():
                log_message(
                    "Clip polygon result empty; falling back to original geometry.",
                    level="WARNING",
                )
                dissolved_geom = geom.Clone()

            self.save_geometry_to_geopackage("study_area_clip_polygons", dissolved_geom, normalized_name)
            log_message(f"Created clip polygon: {normalized_name}")
            grid_layer.SetSpatialFilter(None)
            grid_layer.SetAttributeFilter(None)

        finally:
            # Explicit cleanup
            if grid_ds:
                grid_ds = None

    def _union_geometries(self, geometries):
        """
        Union a list of geometries efficiently using UnionCascaded.

        Args:
            geometries: List of OGR geometry objects

        Returns:
            Union of all geometries, or None if empty
        """
        if not geometries:
            return None

        if len(geometries) == 1:
            return geometries[0]

        multi_geom = ogr.Geometry(ogr.wkbMultiPolygon)
        for cell in geometries:
            geom_type = cell.GetGeometryType()
            if geom_type in (ogr.wkbPolygon, ogr.wkbPolygon25D):
                multi_geom.AddGeometry(cell)
            elif geom_type in (ogr.wkbMultiPolygon, ogr.wkbMultiPolygon25D):
                for i in range(cell.GetGeometryCount()):
                    part = cell.GetGeometryRef(i)
                    if part and part.GetGeometryType() in (
                        ogr.wkbPolygon,
                        ogr.wkbPolygon25D,
                    ):
                        multi_geom.AddGeometry(part)

        if multi_geom.GetGeometryCount() == 0:
            return None

        return multi_geom.UnionCascaded()

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

    def _estimate_geom_area_km2(self, geom):
        """Estimate geometry area in square kilometers using Mollweide projection."""
        if geom is None or geom.IsEmpty():
            return 0.0

        geom_clone = geom.Clone()
        geom_clone.AssignSpatialReference(self.target_spatial_ref)

        mollweide_srs = osr.SpatialReference()
        mollweide_srs.SetFromUserInput("ESRI:54009")

        transform_to_mollweide = osr.CoordinateTransformation(self.target_spatial_ref, mollweide_srs)
        geom_clone.Transform(transform_to_mollweide)

        area_m2 = abs(geom_clone.GetArea())
        return area_m2 / 1000000.0

    def _validate_regional_h3_runtime_guard(self, geom, normalized_name):
        """Fail fast at runtime for unsafe H3 density choices."""
        try:
            area_km2 = self._estimate_geom_area_km2(geom)
            estimated_cells = estimate_h3_cells_for_area(area_km2, self.h3_resolution)
            cell_area_km2 = h3_cell_area_km2(self.h3_resolution)

            if estimated_cells > self.MAX_H3_ESTIMATED_CELLS:
                log_message(
                    (
                        f"Skipping {normalized_name}: H3 resolution {self.h3_resolution} is too fine "
                        f"for runtime safeguards (estimated {estimated_cells:,} cells from {area_km2:,.2f} km2, "
                        f"cell area {cell_area_km2:,.6f} km2, max {self.MAX_H3_ESTIMATED_CELLS:,})."
                    ),
                    level="WARNING",
                )
                return False

            if estimated_cells < self.MIN_H3_ESTIMATED_CELLS:
                log_message(
                    (
                        f"Skipping {normalized_name}: H3 resolution {self.h3_resolution} is too coarse "
                        f"for runtime safeguards (estimated {estimated_cells} cells from {area_km2:,.2f} km2, "
                        f"minimum {self.MIN_H3_ESTIMATED_CELLS})."
                    ),
                    level="WARNING",
                )
                return False

            return True
        except Exception as e:
            log_message(f"Runtime H3 safeguard check failed for {normalized_name}: {e}", level="WARNING")
            return False

    ##########################################################################
    # Create Raster Mask
    ##########################################################################
    def create_raster_mask(self, geom, aligned_box, mask_name):
        """Create a 1-bit raster mask for a single geometry using gdal.Rasterize.

        Uses optimized TIFF creation options for better I/O performance:
        DEFLATE compression, tiled output, NBITS=1.

        Args:
            geom: OGR geometry to rasterize.
            aligned_box: Aligned bounding box (xmin, xmax, ymin, ymax).
            mask_name: Name for the output mask file.

        Returns:
            Path to the created mask file, or None if mask is too small.

        Raises:
            RuntimeError: If rasterization fails.
        """
        mask_filepath = os.path.join(self.working_dir, "study_area", f"{mask_name}.tif")

        mem_ds = None
        target_ds = None
        try:
            driver_mem = ogr.GetDriverByName("MEM")
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

            xmin, xmax, ymin, ymax = aligned_box

            # For pixel width/height, we can compute:
            # width in coordinate space: (xmax - xmin)
            width = int((xmax - xmin) / x_res)
            height = int((ymax - ymin) / y_res)
            if width < 1 or height < 1:
                log_message("Extent is too small for raster creation. Skipping mask.")
                return None

            # Create the raster with optimized options
            # - DEFLATE compression for smaller files
            # - Tiled output for better VRT performance
            # - NBITS=1 for minimal storage
            creation_options = [
                "NBITS=1",
                "COMPRESS=DEFLATE",
                "TILED=YES",
                "BLOCKXSIZE=256",
                "BLOCKYSIZE=256",
            ]

            target_ds = gdal.GetDriverByName("GTiff").Create(
                mask_filepath,
                width,
                height,
                1,  # 1 band
                gdal.GDT_Byte,
                options=creation_options,
            )
            if not target_ds:
                raise RuntimeError(f"Could not create raster {mask_filepath}")

            # Set geotransform (origin x, pixel width, rotation, origin y, rotation, pixel height)
            # Note y_res is negative if north-up
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
            log_message(f"Created raster mask: {mask_filepath}")
            return mask_filepath

        finally:
            # Explicit cleanup
            if target_ds:
                target_ds = None
            if mem_ds:
                mem_ds = None

    ##########################################################################
    # Create VRT
    ##########################################################################
    def create_raster_vrt(self, output_vrt_name="combined_mask.vrt"):
        """Create a VRT file from all .tif masks in the study_area directory.

        Args:
            output_vrt_name: Name for the output VRT file.
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
        """Create 'study_area' subdirectory if it doesn't exist.

        Args:
            working_dir: Parent directory for the study_area subdirectory.
        """
        study_area_dir = os.path.join(working_dir, "study_area")
        if not os.path.exists(study_area_dir):
            os.makedirs(study_area_dir)
            log_message(f"Created directory {study_area_dir}")

    ##############################################################################
