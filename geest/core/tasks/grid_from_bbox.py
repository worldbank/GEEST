import time
from osgeo import ogr
from qgis.core import QgsTask
from geest.utilities import log_message


class GridFromBbox(QgsTask):
    """
    A QGIS task to generate grid cells in a bounding box chunk, check intersections,
    and store them in memory for later writing.
    """

    def __init__(self, chunk_id, bbox_chunk, geom, cell_size, feedback):
        super().__init__(f"CreateGridChunkTask-{chunk_id}", QgsTask.CanCancel)
        self.chunk_id = chunk_id
        self.bbox_chunk = bbox_chunk  # (x_start, x_end, y_start, y_end)
        self.geom = geom
        self.cell_size = cell_size
        self.feedback = feedback
        self.run_time = 0.0
        self.features_out = []  # store geometries here

    def run(self):
        log_message(f"##################################")
        log_message(f"Processing chunk {self.chunk_id}...")
        log_message(f"Chunk bbox: {self.bbox_chunk}")
        log_message(f"##################################")
        start_time = time.time()
        x_start, x_end, y_start, y_end = self.bbox_chunk

        # Convert geom to OGR if needed
        # If self.geom is an ogr.Geometry, skip this step
        # If it's a PyQGIS geometry, convert to WKB or so, e.g.:
        #  ogr_geom = ogr.CreateGeometryFromWkb(self.geom.asWkb())

        # We'll assume self.geom is already an ogr.Geometry
        skip_intersection_check = False

        chunk_bounds = ogr.CreateGeometryFromWkt(
            f"POLYGON(({x_start} {y_start}, {x_end} {y_start}, "
            f"{x_end} {y_end}, {x_start} {y_end}, {x_start} {y_start}))"
        )

        # If chunk bounding box is fully outside of the geometry, skip chunk
        if not self.geom.Intersects(chunk_bounds):
            log_message(
                f"Chunk {self.chunk_id} is completely outside geometry, skipping."
            )
            return True

        # If the whole chunk is within the geometry, skip intersection check
        if self.geom.Contains(chunk_bounds):
            log_message(
                f"Whole chunk is within the geometry, we will skip check intersection for each feature..."
            )
            skip_intersection_check = True
        else:
            log_message(
                f"Whole chunk is NOT within the geometry, we will check intersection for each feature..."
            )

        x = x_start
        while x < x_end:
            x2 = x + self.cell_size
            if x2 <= x:
                break
            y = y_start
            while y < y_end:
                y2 = y + self.cell_size
                if y2 <= y:
                    break
                # Create cell polygon in memory
                ring = ogr.Geometry(ogr.wkbLinearRing)
                ring.AddPoint(x, y)
                ring.AddPoint(x, y2)
                ring.AddPoint(x2, y2)
                ring.AddPoint(x2, y)
                ring.AddPoint(x, y)

                cell_polygon = ogr.Geometry(ogr.wkbPolygon)
                cell_polygon.AddGeometry(ring)

                # Check intersection
                if not skip_intersection_check:
                    if self.geom.Intersects(cell_polygon):
                        self.features_out.append(cell_polygon)
                else:
                    self.features_out.append(cell_polygon)

                y = y2
            x = x2

        end_time = time.time()
        self.run_time = end_time - start_time
        # self.feedback.pushInfo(
        log_message(
            f"Chunk {self.chunk_id} processed in {end_time - start_time:.2f} s; created {len(self.features_out)} features."
        )

        return True

    def finished(self, result):
        # This is called in the main thread after `run` completes
        # We do *not* write to the data source here if we want to avoid concurrency issues.
        pass

    def cancel(self):
        super().cancel()
        # clean up if needed
