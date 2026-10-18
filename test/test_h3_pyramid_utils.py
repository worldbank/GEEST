# -*- coding: utf-8 -*-
"""Unit tests for geest.core.h3_pyramid_utils.

Exercises the real H3 pyramid engine end to end (unlike
test_tree_panel_pyramid_migration.py's `_fake_h3_pyramid_utils`, which
stands in for this module to test TreePanel's own wiring in isolation).
Mirrors test_grid_pyramid_utils.py's structure/coverage for the
square-grid pyramid, but against real H3 hexagons generated with h3-py.
"""
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from osgeo import ogr, osr

from geest.core.grid_pyramid_utils import invalidate_pyramid, is_pyramid_fresh
from geest.core.h3_pyramid_utils import (
    build_h3_pyramid_scaffold,
    compute_h3_level_resolutions,
    get_exposed_h3_levels,
    h3_effective_cell_size_m,
    h3_pyramid_steps,
    has_h3_pyramid_structure,
    refresh_h3_pyramid_column,
)


def _build_h3_grid(gpkg_path, h3_resolution=9, score_fields=(), bbox_wgs84=(36.80, -1.30, 36.82, -1.28)):
    """Create a minimal H3-indexed study_area_grid with the given REAL (scored) fields.

    Cells are real H3 hexagons (h3-py v4's h3shape_to_cells) covering a
    small WGS84 bounding box, with an "h3_index" text column matching the
    field study_area_processing_task.py writes for H3-grid projects.

    Args:
        gpkg_path: Destination path for the study_area.gpkg fixture.
        h3_resolution: H3 resolution to generate cells at.
        score_fields: REAL (scored) column names to add and populate, each
            cell getting a distinct value (its 0-based index) so MIN
            aggregation across a coarser cell's children is distinguishable.
        bbox_wgs84: (min_lon, min_lat, max_lon, max_lat), kept small so the
            generated cell count stays low and tests run fast.

    Returns:
        The number of base cells created.
    """
    import h3

    driver = ogr.GetDriverByName("GPKG")
    ds = driver.CreateDataSource(gpkg_path)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    layer = ds.CreateLayer("study_area_grid", srs, geom_type=ogr.wkbPolygon)
    layer.CreateField(ogr.FieldDefn("grid_id", ogr.OFTInteger))
    h3_field = ogr.FieldDefn("h3_index", ogr.OFTString)
    h3_field.SetWidth(16)
    layer.CreateField(h3_field)
    for field in score_fields:
        layer.CreateField(ogr.FieldDefn(field, ogr.OFTReal))

    min_lon, min_lat, max_lon, max_lat = bbox_wgs84
    shape = h3.LatLngPoly([(min_lat, min_lon), (min_lat, max_lon), (max_lat, max_lon), (max_lat, min_lon)])
    cells = list(h3.h3shape_to_cells(shape, h3_resolution))
    if not cells:
        raise RuntimeError("No H3 cells generated for the test bbox - widen bbox_wgs84.")

    for grid_id, cell in enumerate(cells):
        boundary = h3.cell_to_boundary(cell)  # [(lat, lon), ...]
        ring = ogr.Geometry(ogr.wkbLinearRing)
        for lat, lon in boundary:
            ring.AddPoint(lon, lat)
        ring.CloseRings()
        polygon = ogr.Geometry(ogr.wkbPolygon)
        polygon.AddGeometry(ring)

        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField("grid_id", grid_id)
        feature.SetField("h3_index", cell)
        for field in score_fields:
            feature.SetField(field, float(grid_id))
        feature.SetGeometry(polygon)
        layer.CreateFeature(feature)
        feature = None
    ds = None
    return len(cells)


def _build_h3_grid_projected(gpkg_path, h3_resolution, score_fields, bbox_wgs84, target_epsg):
    """Like _build_h3_grid but writes the base grid reprojected to target_epsg.

    Real GeoE3 projects always store study_area_grid in a projected CRS
    (a UTM zone, picked per study area), never raw WGS84 - _build_h3_grid's
    EPSG:4326 fixture never exercises the WGS84->target reprojection branch
    of _ensure_h3_level_table_scaffold() at all, which is exactly why the
    axis-order bug (see test_h3_utils.TestTransformWgs84ToTarget) slipped
    through undetected. This fixture closes that gap.

    Deliberately uses its own explicitly axis-ordered transform (not
    geest.core.h3_utils.transform_wgs84_to_target) so the fixture's
    correctness never depends on the function under test.
    """
    import h3

    source_srs = osr.SpatialReference()
    source_srs.ImportFromEPSG(4326)
    source_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    target_srs = osr.SpatialReference()
    target_srs.ImportFromEPSG(target_epsg)
    target_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr.CoordinateTransformation(source_srs, target_srs)

    driver = ogr.GetDriverByName("GPKG")
    ds = driver.CreateDataSource(gpkg_path)
    layer = ds.CreateLayer("study_area_grid", target_srs, geom_type=ogr.wkbPolygon)
    layer.CreateField(ogr.FieldDefn("grid_id", ogr.OFTInteger))
    h3_field = ogr.FieldDefn("h3_index", ogr.OFTString)
    h3_field.SetWidth(16)
    layer.CreateField(h3_field)
    for field in score_fields:
        layer.CreateField(ogr.FieldDefn(field, ogr.OFTReal))

    min_lon, min_lat, max_lon, max_lat = bbox_wgs84
    shape = h3.LatLngPoly([(min_lat, min_lon), (min_lat, max_lon), (max_lat, max_lon), (max_lat, min_lon)])
    cells = list(h3.h3shape_to_cells(shape, h3_resolution))
    if not cells:
        raise RuntimeError("No H3 cells generated for the test bbox - widen bbox_wgs84.")

    for grid_id, cell in enumerate(cells):
        boundary = h3.cell_to_boundary(cell)  # [(lat, lon), ...]
        ring = ogr.Geometry(ogr.wkbLinearRing)
        for lat, lon in boundary:
            tx, ty, _ = transform.TransformPoint(lon, lat)
            ring.AddPoint(tx, ty)
        ring.CloseRings()
        polygon = ogr.Geometry(ogr.wkbPolygon)
        polygon.AddGeometry(ring)

        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField("grid_id", grid_id)
        feature.SetField("h3_index", cell)
        for field in score_fields:
            feature.SetField(field, float(grid_id))
        feature.SetGeometry(polygon)
        layer.CreateFeature(feature)
        feature = None
    ds = None
    return len(cells)


class TestH3PyramidReprojection(unittest.TestCase):
    """Regression test: pyramid level geometry must land in the same place as the base grid.

    See TestTransformWgs84ToTarget in test_h3_utils.py for the underlying
    axis-order bug this guards against.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_h3_pyramid_reproj_")
        self.gpkg_path = os.path.join(self.temp_dir, "study_area.gpkg")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_level_table_geometry_overlaps_base_grid_extent(self):
        target_epsg = 32626  # UTM zone 26N - matches real Cabo Verde projects
        _build_h3_grid_projected(
            self.gpkg_path,
            h3_resolution=9,
            score_fields=("jobs",),
            bbox_wgs84=(-23.52, 15.08, -23.48, 15.12),
            target_epsg=target_epsg,
        )

        ds = ogr.Open(self.gpkg_path)
        base_extent = ds.GetLayerByName("study_area_grid").GetExtent()
        ds = None

        self.assertTrue(refresh_h3_pyramid_column(self.gpkg_path, "jobs", 9))

        ds = ogr.Open(self.gpkg_path)
        level_layer = ds.GetLayerByName("study_area_grid_h3_res8")
        self.assertIsNotNone(level_layer)
        self.assertGreater(level_layer.GetFeatureCount(), 0)
        level_extent = level_layer.GetExtent()
        ds = None

        # A coarser level's cells are the same hexagons' parents, so its
        # extent must overlap the base grid's (allowing a generous margin
        # since coarser hexes are a bit larger) - not land millions of
        # metres away in the wrong hemisphere/UTM zone, as it did when
        # WGS84->target reprojection silently swapped lat/lon.
        margin = 50000
        self.assertGreater(level_extent[1], base_extent[0] - margin)
        self.assertLess(level_extent[0], base_extent[1] + margin)
        self.assertGreater(level_extent[3], base_extent[2] - margin)
        self.assertLess(level_extent[2], base_extent[3] + margin)


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


def _add_clip_boundary_layer(gpkg_path, wkt, target_epsg):
    """Add a study_area_clip_polygons layer (one feature) to an existing gpkg."""
    target_srs = osr.SpatialReference()
    target_srs.ImportFromEPSG(target_epsg)
    target_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    ds = ogr.Open(gpkg_path, 1)
    layer = ds.CreateLayer("study_area_clip_polygons", target_srs, geom_type=ogr.wkbPolygon)
    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetGeometry(ogr.CreateGeometryFromWkt(wkt))
    layer.CreateFeature(feature)
    feature = None
    ds = None


class TestH3PyramidEdgeClipping(unittest.TestCase):
    """Regression test: clip_to_boundary=True must also clip coarser pyramid levels.

    Previously only the base grid (GridFromBboxH3Task) honored
    clip_to_boundary - the coarser level tables built by
    _ensure_h3_level_table_scaffold() always wrote full, unclipped parent
    hexagons regardless of the project's setting.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_h3_pyramid_clip_")
        self.gpkg_path = os.path.join(self.temp_dir, "study_area.gpkg")
        self.target_epsg = 32737  # UTM zone 37S
        self.bbox_wgs84 = (36.78, -1.32, 36.84, -1.26)
        _build_h3_grid_projected(
            self.gpkg_path,
            h3_resolution=9,
            score_fields=("jobs",),
            bbox_wgs84=self.bbox_wgs84,
            target_epsg=self.target_epsg,
        )
        # A boundary smaller than the full grid extent, so some level-8
        # parent hexagons are necessarily edge cells.
        min_x, min_y = _wgs84_to_utm(36.795, -1.305, self.target_epsg)
        max_x, max_y = _wgs84_to_utm(36.825, -1.275, self.target_epsg)
        self.boundary_wkt = (
            f"POLYGON(({min_x} {min_y}, {min_x} {max_y}, {max_x} {max_y}, {max_x} {min_y}, {min_x} {min_y}))"
        )
        self.boundary_geom = ogr.CreateGeometryFromWkt(self.boundary_wkt)
        _add_clip_boundary_layer(self.gpkg_path, self.boundary_wkt, self.target_epsg)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_without_clip_some_level_cells_extend_beyond_the_boundary(self):
        self.assertTrue(refresh_h3_pyramid_column(self.gpkg_path, "jobs", 9, clip_to_boundary=False))

        ds = ogr.Open(self.gpkg_path)
        level_layer = ds.GetLayerByName("study_area_grid_h3_res8")
        cells = [feature.GetGeometryRef().Clone() for feature in level_layer]
        ds = None

        self.assertTrue(cells)
        self.assertTrue(
            any(not self.boundary_geom.Contains(geom) for geom in cells),
            "with clipping off, at least one level-8 cell must extend beyond the boundary",
        )

    def test_with_clip_every_level_cell_is_confined_to_the_boundary(self):
        self.assertTrue(refresh_h3_pyramid_column(self.gpkg_path, "jobs", 9, clip_to_boundary=True))

        ds = ogr.Open(self.gpkg_path)
        for table_name in ("study_area_grid_h3_res8", "study_area_grid_h3_res7"):
            level_layer = ds.GetLayerByName(table_name)
            cells = [feature.GetGeometryRef().Clone() for feature in level_layer]
            self.assertTrue(cells, f"{table_name} must have at least one cell")
            for geom in cells:
                self.assertTrue(
                    self.boundary_geom.Contains(geom) or self.boundary_geom.Equals(geom),
                    f"{table_name} cell {geom.ExportToWkt()[:80]} extends beyond the clip boundary",
                )
        ds = None


class TestH3PyramidStepsSetting(unittest.TestCase):
    """Tests for h3_pyramid_steps() and its effect on get_exposed_h3_levels().

    National and local are tuned independently - a scale of anything other
    than "local" (including "national") reads the national key.
    """

    def test_defaults_to_three_when_unset(self):
        with patch("geest.core.h3_pyramid_utils.setting", side_effect=lambda key, default=None: default):
            self.assertEqual(h3_pyramid_steps("national"), 3)
            self.assertEqual(h3_pyramid_steps("local"), 3)

    def test_reads_the_national_key_for_national_scale(self):
        def fake_setting(key, default=None):
            return {"h3_pyramid_steps_national": 5, "h3_pyramid_steps_local": 2}.get(key, default)

        with patch("geest.core.h3_pyramid_utils.setting", side_effect=fake_setting):
            self.assertEqual(h3_pyramid_steps("national"), 5)

    def test_reads_the_local_key_for_local_scale(self):
        def fake_setting(key, default=None):
            return {"h3_pyramid_steps_national": 5, "h3_pyramid_steps_local": 2}.get(key, default)

        with patch("geest.core.h3_pyramid_utils.setting", side_effect=fake_setting):
            self.assertEqual(h3_pyramid_steps("local"), 2)

    def test_unrecognised_scale_falls_back_to_national(self):
        def fake_setting(key, default=None):
            return {"h3_pyramid_steps_national": 5, "h3_pyramid_steps_local": 2}.get(key, default)

        with patch("geest.core.h3_pyramid_utils.setting", side_effect=fake_setting):
            self.assertEqual(h3_pyramid_steps("something_else"), 5)

    def test_get_exposed_h3_levels_honours_the_scale_specific_step_count(self):
        def fake_setting(key, default=None):
            return {"h3_pyramid_steps_national": 1, "h3_pyramid_steps_local": 3}.get(key, default)

        with patch("geest.core.h3_pyramid_utils.setting", side_effect=fake_setting):
            national_levels = get_exposed_h3_levels("unused.gpkg", "jobs", 9, analysis_scale="national")
            local_levels = get_exposed_h3_levels("unused.gpkg", "jobs", 9, analysis_scale="local")
        self.assertEqual([res for res, _table in national_levels], [9, 8])
        self.assertEqual([res for res, _table in local_levels], [9, 8, 7, 6])


class TestComputeH3LevelResolutions(unittest.TestCase):
    """Tests for compute_h3_level_resolutions()."""

    def test_steps_down_by_one_each_level(self):
        self.assertEqual(compute_h3_level_resolutions(9), [9, 8, 7, 6])

    def test_clamps_at_zero(self):
        self.assertEqual(compute_h3_level_resolutions(2), [2, 1, 0, 0])

    def test_custom_step_count(self):
        self.assertEqual(compute_h3_level_resolutions(9, steps=2), [9, 8, 7])


class TestH3EffectiveCellSizeM(unittest.TestCase):
    """Tests for h3_effective_cell_size_m()."""

    def test_coarser_resolution_is_larger(self):
        self.assertGreater(h3_effective_cell_size_m(5), h3_effective_cell_size_m(9))

    def test_positive_for_every_valid_resolution(self):
        for resolution in range(16):
            self.assertGreater(h3_effective_cell_size_m(resolution), 0)


class TestBuildH3PyramidScaffold(unittest.TestCase):
    """Tests for build_h3_pyramid_scaffold() - the geometry-only, column-agnostic build.

    This is what StudyAreaProcessingTask calls right after writing the base
    H3 grid, so every level table already exists before any indicator has
    ever run - see the matching call site in study_area_processing_task.py.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_h3_pyramid_scaffold_")
        self.gpkg_path = os.path.join(self.temp_dir, "study_area.gpkg")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_builds_every_level_table_with_no_score_columns(self):
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=())

        self.assertTrue(build_h3_pyramid_scaffold(self.gpkg_path, 9))

        for table_name in (
            "study_area_grid_h3_res8",
            "study_area_grid_h3_res7",
            "study_area_grid_h3_res6",
        ):
            ds = ogr.Open(self.gpkg_path, 0)
            level_layer = ds.GetLayerByName(table_name)
            self.assertIsNotNone(level_layer, f"expected {table_name} to exist")
            self.assertGreater(level_layer.GetFeatureCount(), 0)
            layer_defn = level_layer.GetLayerDefn()
            field_names = {layer_defn.GetFieldDefn(i).GetName().lower() for i in range(layer_defn.GetFieldCount())}
            self.assertEqual(field_names, {"h3_index"})
            ds = None

    def test_a_later_refresh_for_a_real_column_does_not_duplicate_rows(self):
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=("jobs",))
        self.assertTrue(build_h3_pyramid_scaffold(self.gpkg_path, 9))

        ds = ogr.Open(self.gpkg_path, 0)
        scaffold_count = ds.GetLayerByName("study_area_grid_h3_res8").GetFeatureCount()
        ds = None

        self.assertTrue(refresh_h3_pyramid_column(self.gpkg_path, "jobs", 9))

        ds = ogr.Open(self.gpkg_path, 0)
        after_refresh_count = ds.GetLayerByName("study_area_grid_h3_res8").GetFeatureCount()
        ds = None
        self.assertEqual(scaffold_count, after_refresh_count)

    def test_none_resolution_fails_cleanly(self):
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=())
        self.assertFalse(build_h3_pyramid_scaffold(self.gpkg_path, None))


class TestH3PyramidEndToEnd(unittest.TestCase):
    """End-to-end tests against a real H3 grid GeoPackage."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_h3_pyramid_")
        self.gpkg_path = os.path.join(self.temp_dir, "study_area.gpkg")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_has_structure_false_before_build(self):
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=("jobs",))
        self.assertFalse(has_h3_pyramid_structure(self.gpkg_path, "jobs", 9))

    def test_has_structure_none_resolution_returns_false(self):
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=("jobs",))
        self.assertFalse(has_h3_pyramid_structure(self.gpkg_path, "jobs", None))

    def test_refresh_builds_structure_and_marks_fresh(self):
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=("jobs",))

        self.assertTrue(refresh_h3_pyramid_column(self.gpkg_path, "jobs", 9))
        self.assertTrue(has_h3_pyramid_structure(self.gpkg_path, "jobs", 9))
        self.assertTrue(is_pyramid_fresh(self.gpkg_path, "jobs"))

    def test_level_tables_mirror_every_base_column_even_if_never_refreshed(self):
        # Each H3 level must be a complete, scaled mirror of the base
        # grid's current column set - not a sparse table that only grows
        # the columns someone happened to explicitly
        # refresh_h3_pyramid_column() for. A column whose indicator hasn't
        # run yet is NULL on both the base grid and every level.
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=("jobs",))
        ds = ogr.Open(self.gpkg_path, 1)
        ds.ExecuteSQL("ALTER TABLE study_area_grid ADD COLUMN never_refreshed REAL")
        ds = None

        self.assertTrue(refresh_h3_pyramid_column(self.gpkg_path, "jobs", 9))

        ds = ogr.Open(self.gpkg_path, 0)
        for table_name in ("study_area_grid_h3_res8", "study_area_grid_h3_res7", "study_area_grid_h3_res6"):
            layer = ds.GetLayer(table_name)
            self.assertIsNotNone(layer, f"expected level table {table_name} to exist")
            layer_defn = layer.GetLayerDefn()
            field_names = {layer_defn.GetFieldDefn(i).GetName() for i in range(layer_defn.GetFieldCount())}
            self.assertIn(
                "never_refreshed",
                field_names,
                f"{table_name} must mirror every base-grid score column, including ones never explicitly refreshed",
            )
        ds = None

    def test_refresh_missing_column_fails_cleanly(self):
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=())
        self.assertFalse(refresh_h3_pyramid_column(self.gpkg_path, "nonexistent", 9))

    def test_refresh_none_resolution_fails_cleanly(self):
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=("jobs",))
        self.assertFalse(refresh_h3_pyramid_column(self.gpkg_path, "jobs", None))

    def test_refresh_missing_gpkg_fails_cleanly(self):
        self.assertFalse(refresh_h3_pyramid_column(os.path.join(self.temp_dir, "nope.gpkg"), "jobs", 9))

    def test_aggregated_value_is_min_of_children(self):
        import h3

        n_cells = _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=("jobs",))
        self.assertGreater(n_cells, 1, "Test bbox must yield more than one base H3 cell to exercise aggregation.")

        self.assertTrue(refresh_h3_pyramid_column(self.gpkg_path, "jobs", 9))

        # Independently recompute the expected MIN-per-parent at resolution 8
        # straight from the base grid, then compare against what got built -
        # a coarse cell shows its worst (most conservative) child score.
        ds = ogr.Open(self.gpkg_path, 0)
        base_layer = ds.GetLayerByName("study_area_grid")
        expected = {}
        for feature in base_layer:
            parent = h3.cell_to_parent(feature.GetField("h3_index"), 8)
            value = feature.GetField("jobs")
            if value is None:
                continue
            expected[parent] = min(expected.get(parent, value), value)

        level_layer = ds.GetLayerByName("study_area_grid_h3_res8")
        self.assertIsNotNone(level_layer, "Expected level table study_area_grid_h3_res8 to exist.")
        actual = {}
        for feature in level_layer:
            actual[feature.GetField("h3_index")] = feature.GetField("jobs")
        ds = None

        self.assertEqual(actual, expected)

    def test_refresh_is_idempotent(self):
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=("jobs",))
        self.assertTrue(refresh_h3_pyramid_column(self.gpkg_path, "jobs", 9))
        self.assertTrue(refresh_h3_pyramid_column(self.gpkg_path, "jobs", 9))
        self.assertTrue(has_h3_pyramid_structure(self.gpkg_path, "jobs", 9))

    def test_refresh_reverts_to_null_when_children_become_null(self):
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=("jobs",))
        self.assertTrue(refresh_h3_pyramid_column(self.gpkg_path, "jobs", 9))

        ds = ogr.Open(self.gpkg_path, 1)
        base_layer = ds.GetLayerByName("study_area_grid")
        for feature in base_layer:
            feature.SetFieldNull("jobs")
            base_layer.SetFeature(feature)
        ds = None

        self.assertTrue(refresh_h3_pyramid_column(self.gpkg_path, "jobs", 9))

        ds = ogr.Open(self.gpkg_path, 0)
        level_layer = ds.GetLayerByName("study_area_grid_h3_res8")
        values = [feature.GetField("jobs") for feature in level_layer]
        ds = None
        self.assertTrue(all(value is None for value in values))

    def test_invalidate_pyramid_clears_freshness_not_structure(self):
        # Shared bookkeeping (grid_pyramid_utils.invalidate_pyramid()) must
        # work for the H3 path too - see the matching TreePanel regression
        # test in test_tree_panel_pyramid_migration.py.
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=("jobs",))
        self.assertTrue(refresh_h3_pyramid_column(self.gpkg_path, "jobs", 9))

        invalidate_pyramid(self.gpkg_path, "jobs")

        self.assertFalse(is_pyramid_fresh(self.gpkg_path, "jobs"))
        self.assertTrue(has_h3_pyramid_structure(self.gpkg_path, "jobs", 9))


class TestGetExposedH3Levels(unittest.TestCase):
    """Tests for get_exposed_h3_levels()."""

    def test_base_level_has_no_table(self):
        levels = get_exposed_h3_levels("unused.gpkg", "jobs", 9)
        self.assertEqual(levels[0], (9, None))

    def test_returns_every_built_level_not_a_curated_subset(self):
        # Every level refresh_h3_pyramid_column() builds is exposed - no
        # point building optimized scale-dependent levels and hiding most
        # of them from the actual scale-dependent visualization.
        levels = get_exposed_h3_levels("unused.gpkg", "jobs", 9)
        self.assertEqual([res for res, _table in levels], [9, 8, 7, 6])
        self.assertEqual(
            [table for _res, table in levels][1:],
            [
                "study_area_grid_h3_res8",
                "study_area_grid_h3_res7",
                "study_area_grid_h3_res6",
            ],
        )

    def test_deduplicates_once_resolution_clamps_to_zero(self):
        levels = get_exposed_h3_levels("unused.gpkg", "jobs", 2)
        # resolution 2 -> steps of 1 give [2, 1, 0, max(0,-1)=0, max(0,-2)=0];
        # the three clamped-to-0 levels must collapse into a single entry.
        self.assertEqual(
            levels,
            [(2, None), (1, "study_area_grid_h3_res1"), (0, "study_area_grid_h3_res0")],
        )

    def test_none_resolution_returns_empty_list(self):
        self.assertEqual(get_exposed_h3_levels("unused.gpkg", "jobs", None), [])


if __name__ == "__main__":
    unittest.main()
