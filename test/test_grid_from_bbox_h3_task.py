# -*- coding: utf-8 -*-
"""Unit tests for GridFromBboxH3Task's clip_to_boundary option.

Regional analyses keep the default (unclipped) behavior; local/national H3
grids opt into clipping edge hexagons to the study area boundary, matching
the square grid's own clip-to-AOI behavior (see
geest.core.grid_type_utils.get_h3_clip_to_boundary).
"""
import unittest

from osgeo import ogr, osr

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


def _wgs84_to_utm(lon, lat, target_epsg):
    """Independently-correct WGS84->UTM transform, not the function under test."""
    source_srs = osr.SpatialReference()
    source_srs.ImportFromEPSG(4326)
    source_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    target_srs = osr.SpatialReference()
    target_srs.ImportFromEPSG(target_epsg)
    target_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr.CoordinateTransformation(source_srs, target_srs)
    x, y, _ = transform.TransformPoint(lon, lat)
    return x, y


class TestGridFromBboxH3TaskReprojection(unittest.TestCase):
    """Regression test: cell geometries must land in the target (projected) CRS correctly.

    Every prior test in this file uses target_epsg=4326, which never
    exercises the WGS84->target reprojection step at all (4326-to-4326 is
    an identity transform regardless of axis order, so a lat/lon unpack
    bug there is invisible). Real GeoE3 projects always use a projected
    UTM target CRS - this guards the actual reprojection path, matching
    TestTransformWgs84ToTarget in test_h3_utils.py.
    """

    def test_cell_geometry_lands_within_the_projected_aoi(self):
        target_epsg = 32737  # UTM zone 37S - matches BBOX_CHUNK's WGS84 location
        min_x, min_y = _wgs84_to_utm(36.805, -1.295, target_epsg)
        max_x, max_y = _wgs84_to_utm(36.815, -1.285, target_epsg)
        aoi_geom = ogr.CreateGeometryFromWkt(
            f"POLYGON(({min_x} {min_y}, {min_x} {max_y}, {max_x} {max_y}, {max_x} {min_y}, {min_x} {min_y}))"
        )
        bbox_min_x, bbox_min_y = _wgs84_to_utm(36.80, -1.30, target_epsg)
        bbox_max_x, bbox_max_y = _wgs84_to_utm(36.82, -1.28, target_epsg)

        task = GridFromBboxH3Task(
            chunk_id=0,
            bbox_chunk=(bbox_min_x, bbox_max_x, bbox_min_y, bbox_max_y),
            geom=aoi_geom,
            target_epsg=target_epsg,
            h3_resolution=9,
            clip_to_boundary=True,
        )
        task.run()

        self.assertTrue(task.features_out, "test AOI must yield at least one H3 cell")
        for _h3_index, geom in task.features_out:
            env = geom.GetEnvelope()
            self.assertTrue(
                min_x - 1000 < env[0] and env[1] < max_x + 1000,
                f"cell x envelope {env[0:2]} is nowhere near the AOI x range ({min_x}, {max_x}) "
                "- geometry was not reprojected into the target CRS correctly",
            )
            self.assertTrue(
                min_y - 1000 < env[2] and env[3] < max_y + 1000,
                f"cell y envelope {env[2:4]} is nowhere near the AOI y range ({min_y}, {max_y}) "
                "- geometry was not reprojected into the target CRS correctly",
            )


if __name__ == "__main__":
    unittest.main()
