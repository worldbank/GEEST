# coding=utf-8
"""H3 Grid From Bbox Task module.

This module contains functionality for generating H3 hexagonal grid cells
for Regional scale analysis.

The task transforms bounding boxes from target CRS to WGS84,
generates H3 hexagonal cells using h3.h3shape_to_cells() (h3-py v4 API),
and returns the cell indexes along with geometries in the target CRS.
"""

__copyright__ = "Copyright 2024, Tim Sutton"
__license__ = "GPL version 3"
__email__ = "tim@kartoza.com"
__revision__ = "$Format:%H$"

import time
from typing import List, Tuple

from osgeo import ogr
from qgis.core import Qgis, QgsFeedback, QgsTask

from geest.core.h3_utils import (
    bbox_to_wgs84,
    generate_h3_indexes,
    transform_wgs84_to_target,
)
from geest.utilities import log_message


class GridFromBboxH3Task(QgsTask):
    """A QGIS task to generate H3 hexagonal cells in a bounding box chunk.

    This task:
    1. Takes a bounding box chunk in target CRS
    2. Transforms to WGS84 for H3 operations
    3. Uses h3.h3shape_to_cells() to generate hexagonal cell indexes (h3-py v4)
    4. Converts H3 boundaries to polygon geometries in target CRS
    5. Returns list of (h3_index, geometry) tuples

    Used specifically for Regional scale analysis (H3 Resolution 6).
    """

    def __init__(
        self,
        chunk_id: int,
        bbox_chunk: Tuple[float, float, float, float],
        geom: ogr.Geometry,
        target_epsg: int,
        h3_resolution: int,
        feedback: "QgsFeedback | None" = None,
    ):
        """Initialize the instance.

        Args:
            chunk_id: Chunk id.
            bbox_chunk: Bbox chunk (x_start, x_end, y_start, y_end) in target CRS.
            geom: OGR Geometry for intersection testing (in target CRS).
            target_epsg: EPSG code of target CRS.
            h3_resolution: H3 resolution level (6 for Regional).
            feedback: OptionalQgsFeedback for progress reporting.
        """
        super().__init__(f"CreateH3GridChunkTask-{chunk_id}", QgsTask.CanCancel)
        self.chunk_id = chunk_id
        self.bbox_chunk = bbox_chunk  # (x_start, x_end, y_start, y_end)
        self.geom = geom
        self.target_epsg = target_epsg
        self.h3_resolution = h3_resolution
        self.feedback = feedback

        # Ensure geometry is 2D (not 2.5D or 3D)
        if self.geom.GetCoordinateDimension() == 3:
            self.geom.FlattenTo2D()

        self.run_time = 0.0
        # List of (h3_index, geometry) tuples
        self.features_out: List[Tuple[str, ogr.Geometry]] = []

    def run(self) -> bool:
        """Generate H3 hexagonal cells for this chunk.

        Returns:
            bool: True if successful.
        """
        start_time = time.time()

        # Check for cancellation
        if self.feedback and self.feedback.isCanceled():
            return True

        x_start, x_end, y_start, y_end = self.bbox_chunk

        # Transform bbox to WGS84 for H3 operations
        wgs84_bbox = bbox_to_wgs84(x_start, x_end, y_start, y_end, self.target_epsg)

        # Generate H3 indexes using polyfill
        h3_indexes = generate_h3_indexes(wgs84_bbox, self.h3_resolution)

        if not h3_indexes:
            log_message(
                f"Chunk {self.chunk_id}: No H3 cells generated for bbox",
                level=Qgis.Warning,
            )
            return True

        # Get total count for progress reporting
        total_cells = len(h3_indexes)
        processed = 0

        # Get study area geometry envelope for quick filtering
        geom_env = self.geom.GetEnvelope()
        geom_min_x, geom_max_x, geom_min_y, geom_max_y = geom_env

        try:
            import h3
        except ImportError:
            log_message(
                "H3 library not available. Install with: pip install h3",
                level=Qgis.Critical,
            )
            return False

        # Process each H3 index
        for h3_index in h3_indexes:
            # Check for cancellation
            if self.feedback and self.feedback.isCanceled():
                break

            # Get H3 boundary in WGS84
            boundary = h3.cell_to_boundary(h3_index)

            # Transform boundary coordinates to target CRS
            transformed_coords = []
            for lon, lat in boundary:
                tx, ty = transform_wgs84_to_target(lon, lat, self.target_epsg)
                transformed_coords.append((tx, ty))

            # Create OGR polygon
            ring = ogr.Geometry(ogr.wkbLinearRing)
            for x, y in transformed_coords:
                ring.AddPoint(x, y)
            ring.CloseRings()

            polygon = ogr.Geometry(ogr.wkbPolygon)
            polygon.AddGeometry(ring)

            # Quick bounding box filter before expensive intersection check
            poly_env = polygon.GetEnvelope()
            poly_min_x, poly_max_x, poly_min_y, poly_max_y = poly_env

            # Skip if clearly outside geometry envelope
            if poly_max_x < geom_min_x or poly_min_x > geom_max_x or poly_max_y < geom_min_y or poly_min_y > geom_max_y:
                processed += 1
                if self.feedback:
                    self.feedback.setProgress(int(processed / total_cells * 100))
                continue

            # Check precise intersection with study area geometry
            if self.geom.Intersects(polygon):
                self.features_out.append((h3_index, polygon))

            processed += 1

            # Update progress
            if self.feedback:
                self.feedback.setProgress(int(processed / total_cells * 100))

        end_time = time.time()
        self.run_time = end_time - start_time
        log_message(
            f"Chunk {self.chunk_id}: {len(self.features_out)} H3 cells "
            f"from {total_cells} indexes in {self.run_time:.2f}s"
        )

        return True

    def finished(self, result: bool) -> None:
        """Called in the main thread after run() completes.

        Args:
            result: Result from run().
        """
        # We do *not* write to the data source here to avoid concurrency issues.
        # Results are passed back to the caller for processing.
        pass

    def cancel(self) -> None:
        """Cancel the task."""
        super().cancel()
        if self.feedback:
            self.feedback.cancel()
        self.features_out = []
