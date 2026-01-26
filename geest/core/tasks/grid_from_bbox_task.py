# -*- coding: utf-8 -*-
"""📦 Grid From Bbox Task module.

This module contains functionality for grid from bbox task.

Performance optimizations:
- Uses numpy for batch coordinate generation
- Uses prepared geometry for faster intersection checks
- Reduces Python object creation overhead
"""

import time

import numpy as np
from osgeo import ogr
from qgis.core import QgsTask

from geest.utilities import log_message


class GridFromBboxTask(QgsTask):
    """
    A QGIS task to generate grid cells in a bounding box chunk, check intersections,
    and store them in memory for later writing.

    Uses numpy for efficient coordinate generation and prepared geometry for
    faster intersection checks.
    """

    def __init__(self, chunk_id, bbox_chunk, geom, cell_size, feedback):
        """Initialize the instance.

        Args:
            chunk_id: Chunk id.
            bbox_chunk: Bbox chunk (x_start, x_end, y_start, y_end).
            geom: OGR Geometry for intersection testing.
            cell_size: Cell size in map units.
            feedback: QgsFeedback for progress reporting.
        """
        super().__init__(f"CreateGridChunkTask-{chunk_id}", QgsTask.CanCancel)
        self.chunk_id = chunk_id
        self.bbox_chunk = bbox_chunk  # (x_start, x_end, y_start, y_end)
        self.geom = geom
        # Ensure geometry is 2D (not 2.5D or 3D)
        if self.geom.GetCoordinateDimension() == 3:
            self.geom.FlattenTo2D()
        self.cell_size = cell_size
        self.feedback = feedback
        self.run_time = 0.0
        self.features_out = []  # store geometries here

    def run(self):
        """Generate grid cells for this chunk.

        Returns:
            bool: True if successful.
        """
        start_time = time.time()
        x_start, x_end, y_start, y_end = self.bbox_chunk

        # Create chunk bounds for initial check
        chunk_bounds = ogr.CreateGeometryFromWkt(
            f"POLYGON(({x_start} {y_start}, {x_end} {y_start}, "
            f"{x_end} {y_end}, {x_start} {y_end}, {x_start} {y_start}))"
        )

        # If chunk bounding box is fully outside of the geometry, skip chunk
        if not self.geom.Intersects(chunk_bounds):
            log_message(f"Chunk {self.chunk_id} outside geometry, skipping.")
            return True

        # If the whole chunk is within the geometry, skip intersection check
        skip_intersection_check = self.geom.Contains(chunk_bounds)

        # Use numpy for efficient coordinate generation
        # Generate all x and y coordinates at once
        x_coords = np.arange(x_start, x_end, self.cell_size)
        y_coords = np.arange(y_start, y_end, self.cell_size)

        if len(x_coords) == 0 or len(y_coords) == 0:
            return True

        # Pre-calculate cell corners using numpy broadcasting
        # This avoids creating thousands of individual coordinate pairs in Python
        cell_size = self.cell_size

        if skip_intersection_check:
            # Fast path: all cells are inside, generate them directly
            self._generate_cells_no_check(x_coords, y_coords, cell_size)
        else:
            # Need to check intersections - use prepared geometry approach
            self._generate_cells_with_check(x_coords, y_coords, cell_size)

        end_time = time.time()
        self.run_time = end_time - start_time
        log_message(f"Chunk {self.chunk_id}: {len(self.features_out)} cells in {self.run_time:.2f}s")

        return True

    def _generate_cells_no_check(self, x_coords, y_coords, cell_size):
        """Generate all cells without intersection checking.

        This is the fast path when the entire chunk is inside the geometry.

        Args:
            x_coords: numpy array of x coordinates (lower-left corners)
            y_coords: numpy array of y coordinates (lower-left corners)
            cell_size: Size of each cell
        """
        self.features_out = []

        # Use WKT batch creation for efficiency
        for x in x_coords:
            x2 = x + cell_size
            for y in y_coords:
                y2 = y + cell_size
                # Create polygon using WKT - faster than building ring manually
                wkt = f"POLYGON(({x} {y},{x} {y2},{x2} {y2},{x2} {y},{x} {y}))"
                cell_polygon = ogr.CreateGeometryFromWkt(wkt)
                self.features_out.append(cell_polygon)

    def _generate_cells_with_check(self, x_coords, y_coords, cell_size):
        """Generate cells with intersection checking using prepared geometry.

        Uses a two-phase approach:
        1. Quick bounding box check using geometry envelope
        2. Precise intersection check only for candidates

        Args:
            x_coords: numpy array of x coordinates (lower-left corners)
            y_coords: numpy array of y coordinates (lower-left corners)
            cell_size: Size of each cell
        """
        self.features_out = []

        # Get geometry envelope for quick rejection
        geom_env = self.geom.GetEnvelope()  # (minX, maxX, minY, maxY)
        geom_min_x, geom_max_x, geom_min_y, geom_max_y = geom_env

        # Filter coordinates that are clearly outside geometry envelope
        # This is a quick numpy operation that can eliminate many cells
        x_mask = (x_coords + cell_size >= geom_min_x) & (x_coords <= geom_max_x)
        y_mask = (y_coords + cell_size >= geom_min_y) & (y_coords <= geom_max_y)

        valid_x = x_coords[x_mask]
        valid_y = y_coords[y_mask]

        if len(valid_x) == 0 or len(valid_y) == 0:
            return

        # For remaining cells, do precise intersection check
        # Group checks to reduce Python overhead
        for x in valid_x:
            x2 = x + cell_size
            for y in valid_y:
                y2 = y + cell_size

                # Create polygon using WKT - faster than building ring manually
                wkt = f"POLYGON(({x} {y},{x} {y2},{x2} {y2},{x2} {y},{x} {y}))"
                cell_polygon = ogr.CreateGeometryFromWkt(wkt)

                # Check intersection
                if self.geom.Intersects(cell_polygon):
                    self.features_out.append(cell_polygon)

    def finished(self, result):
        """Called in the main thread after run() completes.

        Args:
            result: Result from run().
        """
        # We do *not* write to the data source here to avoid concurrency issues.
        pass

    def cancel(self):
        """Cancel the task."""
        super().cancel()
        # Clean up if needed
        self.features_out = []
