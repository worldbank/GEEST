# -*- coding: utf-8 -*-
"""Unit tests for GridFromBboxH3Task's clip_to_boundary option.

Regional analyses keep the default (unclipped) behavior; local/national H3
grids opt into clipping edge hexagons to the study area boundary, matching
the square grid's own clip-to-AOI behavior (see
geest.core.grid_type_utils.get_h3_clip_to_boundary).
"""
import unittest

from osgeo import ogr

from geest.core.tasks.grid_from_bbox_h3_task import GridFromBboxH3Task

# A small AOI, smaller than a resolution-9 hexagon, so every intersecting
# cell is necessarily an edge cell.
AOI_WKT = "POLYGON((36.805 -1.295, 36.805 -1.285, 36.815 -1.285, 36.815 -1.295, 36.805 -1.295))"
BBOX_CHUNK = (36.80, 36.82, -1.30, -1.28)  # x_start, x_end, y_start, y_end


def _run_task(clip_to_boundary):
    aoi_geom = ogr.CreateGeometryFromWkt(AOI_WKT)
    task = GridFromBboxH3Task(
        chunk_id=0,
        bbox_chunk=BBOX_CHUNK,
        geom=aoi_geom,
        target_epsg=4326,
        h3_resolution=9,
        clip_to_boundary=clip_to_boundary,
    )
    task.run()
    return aoi_geom, task.features_out


class TestGridFromBboxH3TaskClipping(unittest.TestCase):
    """Tests for GridFromBboxH3Task's clip_to_boundary option."""

    def test_unclipped_keeps_full_hexagons_extending_beyond_aoi(self):
        aoi_geom, features = _run_task(clip_to_boundary=False)
        self.assertTrue(features, "test AOI must yield at least one H3 cell")
        self.assertTrue(
            any(not aoi_geom.Contains(geom) for _h3_index, geom in features),
            "the default (regional) behavior must keep at least one full, unclipped edge hexagon extending beyond the AOI",
        )

    def test_clipped_confines_every_cell_to_the_aoi(self):
        aoi_geom, features = _run_task(clip_to_boundary=True)
        self.assertTrue(features, "test AOI must yield at least one H3 cell")
        self.assertTrue(
            all(aoi_geom.Contains(geom) for _h3_index, geom in features),
            "every cell must be clipped to within the AOI boundary when clip_to_boundary is True",
        )

    def test_clipping_does_not_change_which_cells_are_returned(self):
        _, unclipped = _run_task(clip_to_boundary=False)
        _, clipped = _run_task(clip_to_boundary=True)
        self.assertEqual(
            {h3_index for h3_index, _geom in unclipped},
            {h3_index for h3_index, _geom in clipped},
            "clipping must only affect geometry, not which H3 cells intersect the AOI",
        )


if __name__ == "__main__":
    unittest.main()
