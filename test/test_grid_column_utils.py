# -*- coding: utf-8 -*-
"""Tests for key-based grid column write utilities."""

import os
import shutil
import tempfile
import unittest

from osgeo import ogr

from geest.core.grid_column_utils import (
    rasterize_grid_column,
    write_aggregation_to_grid,
    write_joined_values_to_grid,
    write_percentage_scores_to_grid,
    write_spatial_join_to_grid,
)


class TestWriteJoinedValuesToGrid(unittest.TestCase):
    """Validate direct key join writes from external GPKG into study_area_grid."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_grid_join_")
        self.main_gpkg = os.path.join(self.temp_dir, "study_area.gpkg")
        self.source_gpkg = os.path.join(self.temp_dir, "s2s.gpkg")

        self._create_study_area_grid()
        self._create_source_layer()

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _create_study_area_grid(self):
        driver = ogr.GetDriverByName("GPKG")
        dataset = driver.CreateDataSource(self.main_gpkg)
        layer = dataset.CreateLayer("study_area_grid", geom_type=ogr.wkbPolygon)
        layer.CreateField(ogr.FieldDefn("h3_index", ogr.OFTString))
        layer.CreateField(ogr.FieldDefn("area_name", ogr.OFTString))

        layer_defn = layer.GetLayerDefn()
        for hex_id, area_name in [
            ("h3_a", "Area 1"),
            ("h3_b", "Area 1"),
            ("h3_c", "Area 2"),
        ]:
            feature = ogr.Feature(layer_defn)
            feature.SetField("h3_index", hex_id)
            feature.SetField("area_name", area_name)
            layer.CreateFeature(feature)

        dataset = None

    def _create_source_layer(self):
        driver = ogr.GetDriverByName("GPKG")
        dataset = driver.CreateDataSource(self.source_gpkg)
        layer = dataset.CreateLayer("s2s_nighttime_lights", geom_type=ogr.wkbPoint)
        layer.CreateField(ogr.FieldDefn("hex_id", ogr.OFTString))
        layer.CreateField(ogr.FieldDefn("sum_viirs_ntl_2024", ogr.OFTReal))

        layer_defn = layer.GetLayerDefn()
        for hex_id, value in [
            ("h3_a", 10.5),
            ("h3_b", 20.5),
            ("h3_extra", 999.0),
        ]:
            feature = ogr.Feature(layer_defn)
            feature.SetField("hex_id", hex_id)
            feature.SetField("sum_viirs_ntl_2024", value)
            layer.CreateFeature(feature)

        dataset = None

    def _read_grid_values(self, column_name):
        dataset = ogr.Open(self.main_gpkg, 0)
        layer = dataset.GetLayerByName("study_area_grid")
        values = {}
        for feature in layer:
            values[feature.GetField("h3_index")] = feature.GetField(column_name)
        dataset = None
        return values

    def test_write_joined_values_to_grid_updates_matching_rows(self):
        updated_count = write_joined_values_to_grid(
            gpkg_path=self.main_gpkg,
            column_name="nighttime_lights",
            source_gpkg=self.source_gpkg,
            source_layer="s2s_nighttime_lights",
            source_key_field="hex_id",
            target_key_field="h3_index",
            source_value_field="sum_viirs_ntl_2024",
        )

        self.assertEqual(updated_count, 2)
        values = self._read_grid_values("nighttime_lights")
        self.assertAlmostEqual(values["h3_a"], 10.5)
        self.assertAlmostEqual(values["h3_b"], 20.5)
        self.assertIsNone(values["h3_c"])

    def test_write_joined_values_to_grid_respects_area_filter(self):
        updated_count = write_joined_values_to_grid(
            gpkg_path=self.main_gpkg,
            column_name="nighttime_lights",
            source_gpkg=self.source_gpkg,
            source_layer="s2s_nighttime_lights",
            source_key_field="hex_id",
            target_key_field="h3_index",
            source_value_field="sum_viirs_ntl_2024",
            area_name="Area 1",
        )

        self.assertEqual(updated_count, 2)
        values = self._read_grid_values("nighttime_lights")
        self.assertAlmostEqual(values["h3_a"], 10.5)
        self.assertAlmostEqual(values["h3_b"], 20.5)
        self.assertIsNone(values["h3_c"])


if __name__ == "__main__":
    unittest.main()


class TestWriteBufferValuesToGrid(unittest.TestCase):
    """Buffer-to-grid scoring must survive invalid geometries and CRS drift.

    Field regression: scored isochrone hulls (frequently self-intersecting)
    produced 'Found 0 grid cells with intersecting buffers' on strict GEOS
    builds, writing 0 into every cell while the run reported success.
    """

    ORIGIN_X = 700000.0
    ORIGIN_Y = 1516000.0
    CELL = 1000.0

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_grid_buffer_")
        self.main_gpkg = os.path.join(self.temp_dir, "study_area.gpkg")
        driver = ogr.GetDriverByName("GPKG")
        dataset = driver.CreateDataSource(self.main_gpkg)
        from osgeo import osr

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(32620)
        layer = dataset.CreateLayer("study_area_grid", srs, geom_type=ogr.wkbPolygon)
        layer.CreateField(ogr.FieldDefn("area_name", ogr.OFTString))
        layer_defn = layer.GetLayerDefn()
        for row in range(2):
            for col in range(2):
                x0 = self.ORIGIN_X + col * self.CELL
                y0 = self.ORIGIN_Y + row * self.CELL
                ring = ogr.Geometry(ogr.wkbLinearRing)
                for px, py in [
                    (x0, y0),
                    (x0 + self.CELL, y0),
                    (x0 + self.CELL, y0 + self.CELL),
                    (x0, y0 + self.CELL),
                    (x0, y0),
                ]:
                    ring.AddPoint(px, py)
                polygon = ogr.Geometry(ogr.wkbPolygon)
                polygon.AddGeometry(ring)
                feature = ogr.Feature(layer_defn)
                feature.SetField("area_name", "test_area")
                feature.SetGeometry(polygon)
                layer.CreateFeature(feature)
        dataset = None

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _scored_cells(self, column):
        dataset = ogr.Open(self.main_gpkg, 0)
        layer = dataset.GetLayerByName("study_area_grid")
        values = [feature.GetField(column) for feature in layer]
        dataset = None
        return values

    def _buffer_layer(self, wkt, crs="EPSG:32620"):
        from qgis.core import QgsFeature, QgsGeometry, QgsVectorLayer

        layer = QgsVectorLayer(f"Polygon?crs={crs}&field=value:integer", "buffers", "memory")
        feature = QgsFeature(layer.fields())
        feature.setAttribute("value", 5)
        feature.setGeometry(QgsGeometry.fromWkt(wkt))
        layer.dataProvider().addFeature(feature)
        layer.updateExtents()
        return layer

    def test_invalid_bowtie_buffer_is_repaired_and_scores_cells(self):
        from geest.core.grid_column_utils import write_buffer_values_to_grid

        x0, y0 = self.ORIGIN_X, self.ORIGIN_Y
        x1, y1 = x0 + 2 * self.CELL, y0 + 2 * self.CELL
        # Self-intersecting hourglass spanning the whole grid
        bowtie = f"POLYGON(({x0} {y0}, {x1} {y1}, {x1} {y0}, {x0} {y1}, {x0} {y0}))"
        layer = self._buffer_layer(bowtie)
        self.assertFalse(next(layer.getFeatures()).geometry().isGeosValid(), "fixture must be invalid")

        updated = write_buffer_values_to_grid(self.main_gpkg, "bowtie_col", layer)
        self.assertGreater(updated, 0, "invalid buffer geometry must be repaired, not silently score nothing")
        self.assertIn(5.0, self._scored_cells("bowtie_col"))

    def test_mismatched_crs_buffer_is_reprojected(self):
        from qgis.core import (
            QgsCoordinateReferenceSystem,
            QgsCoordinateTransform,
            QgsGeometry,
            QgsProject,
            QgsRectangle,
        )

        from geest.core.grid_column_utils import write_buffer_values_to_grid

        rect = QgsRectangle(self.ORIGIN_X, self.ORIGIN_Y, self.ORIGIN_X + 2 * self.CELL, self.ORIGIN_Y + 2 * self.CELL)
        transform = QgsCoordinateTransform(
            QgsCoordinateReferenceSystem("EPSG:32620"),
            QgsCoordinateReferenceSystem("EPSG:4326"),
            QgsProject.instance(),
        )
        rect4326 = transform.transformBoundingBox(rect)
        wkt = QgsGeometry.fromRect(rect4326).asWkt()
        layer = self._buffer_layer(wkt, crs="EPSG:4326")

        updated = write_buffer_values_to_grid(self.main_gpkg, "crs_col", layer)
        self.assertGreater(updated, 0, "a 4326 buffer over a 32620 grid must be reprojected, not score nothing")
        self.assertIn(5.0, self._scored_cells("crs_col"))


class TestRasterizeGridColumn(unittest.TestCase):
    """A sliver area with no matching study_area_grid rows must be skipped.

    Field regression: a tiny island fragment had no grid cells assigned to
    it, but rasterize_grid_column still "succeeded" by falling back to the
    full (unfiltered) grid extent - burning nothing and producing a
    country-sized, all-nodata raster that later broke VRT generation
    downstream. It must now refuse to rasterize and return False instead.
    """

    ORIGIN_X = 700000.0
    ORIGIN_Y = 1516000.0
    CELL = 1000.0

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_grid_rasterize_")
        self.main_gpkg = os.path.join(self.temp_dir, "study_area.gpkg")
        driver = ogr.GetDriverByName("GPKG")
        dataset = driver.CreateDataSource(self.main_gpkg)
        from osgeo import osr

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(32620)
        layer = dataset.CreateLayer("study_area_grid", srs, geom_type=ogr.wkbPolygon)
        layer.CreateField(ogr.FieldDefn("area_name", ogr.OFTString))
        layer.CreateField(ogr.FieldDefn("score_col", ogr.OFTReal))
        layer_defn = layer.GetLayerDefn()
        x0, y0 = self.ORIGIN_X, self.ORIGIN_Y
        ring = ogr.Geometry(ogr.wkbLinearRing)
        for px, py in [
            (x0, y0),
            (x0 + self.CELL, y0),
            (x0 + self.CELL, y0 + self.CELL),
            (x0, y0 + self.CELL),
            (x0, y0),
        ]:
            ring.AddPoint(px, py)
        polygon = ogr.Geometry(ogr.wkbPolygon)
        polygon.AddGeometry(ring)
        feature = ogr.Feature(layer_defn)
        feature.SetField("area_name", "normal_area")
        feature.SetField("score_col", 2.0)
        feature.SetGeometry(polygon)
        layer.CreateFeature(feature)
        dataset = None

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_area_with_no_grid_cells_is_skipped_not_rasterized(self):
        output_path = os.path.join(self.temp_dir, "sliver.tif")
        ok = rasterize_grid_column(
            gpkg_path=self.main_gpkg,
            column_name="score_col",
            output_raster_path=output_path,
            cell_size=100.0,
            extent=(self.ORIGIN_X, self.ORIGIN_Y, self.ORIGIN_X + 100.0, self.ORIGIN_Y + 100.0),
            area_name="sliver_with_no_grid_cells",
        )
        self.assertFalse(ok, "rasterizing an area with zero matching grid cells must fail, not fall back silently")
        self.assertFalse(os.path.exists(output_path))

    def test_area_with_grid_cells_still_rasterizes(self):
        output_path = os.path.join(self.temp_dir, "normal.tif")
        ok = rasterize_grid_column(
            gpkg_path=self.main_gpkg,
            column_name="score_col",
            output_raster_path=output_path,
            cell_size=100.0,
            extent=(self.ORIGIN_X, self.ORIGIN_Y, self.ORIGIN_X + self.CELL, self.ORIGIN_Y + self.CELL),
            area_name="normal_area",
        )
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(output_path))

    def test_area_name_unused_in_grid_still_rasterizes(self):
        """A single, un-partitioned study area may leave area_name NULL on
        every grid row while still naming the area itself (e.g. "none_part0").

        Field regression: that legitimate case was indistinguishable from a
        sliver with no grid cells, since both filter to zero matching rows -
        it must rasterize from the whole (unfiltered) grid, not be skipped.
        """
        gpkg = os.path.join(self.temp_dir, "unpartitioned.gpkg")
        driver = ogr.GetDriverByName("GPKG")
        dataset = driver.CreateDataSource(gpkg)
        from osgeo import osr

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(32620)
        layer = dataset.CreateLayer("study_area_grid", srs, geom_type=ogr.wkbPolygon)
        layer.CreateField(ogr.FieldDefn("area_name", ogr.OFTString))
        layer.CreateField(ogr.FieldDefn("score_col", ogr.OFTReal))
        layer_defn = layer.GetLayerDefn()
        x0, y0 = self.ORIGIN_X, self.ORIGIN_Y
        ring = ogr.Geometry(ogr.wkbLinearRing)
        for px, py in [
            (x0, y0),
            (x0 + self.CELL, y0),
            (x0 + self.CELL, y0 + self.CELL),
            (x0, y0 + self.CELL),
            (x0, y0),
        ]:
            ring.AddPoint(px, py)
        polygon = ogr.Geometry(ogr.wkbPolygon)
        polygon.AddGeometry(ring)
        feature = ogr.Feature(layer_defn)
        feature.SetField("score_col", 3.0)  # area_name left NULL
        feature.SetGeometry(polygon)
        layer.CreateFeature(feature)
        dataset = None

        output_path = os.path.join(self.temp_dir, "unpartitioned.tif")
        ok = rasterize_grid_column(
            gpkg_path=gpkg,
            column_name="score_col",
            output_raster_path=output_path,
            cell_size=100.0,
            extent=(self.ORIGIN_X, self.ORIGIN_Y, self.ORIGIN_X + self.CELL, self.ORIGIN_Y + self.CELL),
            area_name="none_part0",
        )
        self.assertTrue(ok, "area_name being unused in the grid must not be treated as a missing sliver")
        self.assertTrue(os.path.exists(output_path))


class TestWriteSpatialJoinToGrid(unittest.TestCase):
    """write_spatial_join_to_grid was rewritten to build a QgsSpatialIndex

    once over the (typically small) features layer instead of re-querying
    it with SetSpatialFilter for every grid cell - the old per-cell
    re-query was the dominant cost scaling with grid cell count
    (worldbank/GeoE3#445: a 100x finer grid turned a 7-minute run into a
    7.5-hour stall). These tests pin the observable behaviour so the
    rewrite can't silently change results.
    """

    ORIGIN_X = 700000.0
    ORIGIN_Y = 1516000.0
    CELL = 1000.0

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_grid_spatial_join_")
        self.main_gpkg = os.path.join(self.temp_dir, "study_area.gpkg")
        self.features_gpkg = os.path.join(self.temp_dir, "features.gpkg")
        self._create_grid()

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _create_grid(self):
        from osgeo import osr

        driver = ogr.GetDriverByName("GPKG")
        dataset = driver.CreateDataSource(self.main_gpkg)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(32620)
        layer = dataset.CreateLayer("study_area_grid", srs, geom_type=ogr.wkbPolygon)
        layer.CreateField(ogr.FieldDefn("area_name", ogr.OFTString))
        layer.CreateField(ogr.FieldDefn("score_col", ogr.OFTReal))
        layer_defn = layer.GetLayerDefn()
        for row in range(2):
            for col in range(2):
                x0 = self.ORIGIN_X + col * self.CELL
                y0 = self.ORIGIN_Y + row * self.CELL
                ring = ogr.Geometry(ogr.wkbLinearRing)
                for px, py in [
                    (x0, y0),
                    (x0 + self.CELL, y0),
                    (x0 + self.CELL, y0 + self.CELL),
                    (x0, y0 + self.CELL),
                    (x0, y0),
                ]:
                    ring.AddPoint(px, py)
                polygon = ogr.Geometry(ogr.wkbPolygon)
                polygon.AddGeometry(ring)
                feature = ogr.Feature(layer_defn)
                feature.SetField("area_name", "test_area")
                feature.SetGeometry(polygon)
                layer.CreateFeature(feature)
        dataset = None

    def _create_features(self, scored_points, epsg=32620):
        """Create a point features GPKG with a 'score' field.

        Args:
            scored_points: list of (x, y, score) tuples. Each point is
                placed inside cell (0, 0) when x/y fall in its range.
        """
        from osgeo import osr

        driver = ogr.GetDriverByName("GPKG")
        dataset = driver.CreateDataSource(self.features_gpkg)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(epsg)
        layer = dataset.CreateLayer("features", srs, geom_type=ogr.wkbPoint)
        layer.CreateField(ogr.FieldDefn("score", ogr.OFTReal))
        layer_defn = layer.GetLayerDefn()
        for x, y, score in scored_points:
            point = ogr.Geometry(ogr.wkbPoint)
            point.AddPoint(x, y)
            feature = ogr.Feature(layer_defn)
            feature.SetField("score", score)
            feature.SetGeometry(point)
            layer.CreateFeature(feature)
        dataset = None

    def test_aggregation_methods(self):
        # Two points inside cell (0,0): origin+100 and origin+200.
        self._create_features(
            [
                (self.ORIGIN_X + 100, self.ORIGIN_Y + 100, 2.0),
                (self.ORIGIN_X + 200, self.ORIGIN_Y + 200, 8.0),
            ]
        )
        for method, expected in [
            ("MAX", 8.0),
            ("MIN", 2.0),
            ("AVG", 5.0),
            ("SUM", 10.0),
            ("COUNT", 2.0),
        ]:
            updated = write_spatial_join_to_grid(
                gpkg_path=self.main_gpkg,
                column_name=f"score_{method.lower()}",
                features_gpkg=self.features_gpkg,
                features_layer="features",
                score_expression="score",
                aggregation_method=method,
                save_buffers=False,
            )
            self.assertEqual(updated, 1, f"aggregation method {method} should update exactly 1 cell")
            values = self._read_scores(f"score_{method.lower()}")
            self.assertEqual(values.get((0, 0)), expected, f"{method} aggregation mismatch")
            self.assertIsNone(values.get((1, 1)), f"{method}: untouched cell must stay NULL")

    def test_callable_score_expression(self):
        self._create_features([(self.ORIGIN_X + 100, self.ORIGIN_Y + 100, 1.0)])
        constant = 4.5
        updated = write_spatial_join_to_grid(
            gpkg_path=self.main_gpkg,
            column_name="score_col",
            features_gpkg=self.features_gpkg,
            features_layer="features",
            score_expression=lambda feat: constant,
            aggregation_method="MAX",
            save_buffers=False,
        )
        self.assertEqual(updated, 1)
        self.assertEqual(self._read_scores("score_col").get((0, 0)), constant)

    def test_area_name_filter_restricts_to_one_area(self):
        # Points inside both grid cells, but area_name filter should only
        # touch cell (0,0) since that's the only one tagged 'test_area' in
        # this fixture — exercising the same filter used per-area in production.
        self._create_features(
            [
                (self.ORIGIN_X + 100, self.ORIGIN_Y + 100, 3.0),
                (self.ORIGIN_X + 1100, self.ORIGIN_Y + 1100, 3.0),
            ]
        )
        updated = write_spatial_join_to_grid(
            gpkg_path=self.main_gpkg,
            column_name="score_col",
            features_gpkg=self.features_gpkg,
            features_layer="features",
            score_expression="score",
            area_name="test_area",
            aggregation_method="MAX",
            save_buffers=False,
        )
        self.assertEqual(updated, 2, "both cells share area_name='test_area' in this fixture")

    def test_no_intersecting_features_updates_nothing(self):
        self._create_features([(self.ORIGIN_X - 10000, self.ORIGIN_Y - 10000, 9.0)])
        updated = write_spatial_join_to_grid(
            gpkg_path=self.main_gpkg,
            column_name="score_col",
            features_gpkg=self.features_gpkg,
            features_layer="features",
            score_expression="score",
            aggregation_method="MAX",
            save_buffers=False,
        )
        self.assertEqual(updated, 0)

    def _read_scores(self, column):
        dataset = ogr.Open(self.main_gpkg, 0)
        layer = dataset.GetLayerByName("study_area_grid")
        result = {}
        for feature in layer:
            geom = feature.GetGeometryRef()
            x0, _x1, y0, _y1 = geom.GetEnvelope()
            col = round((x0 - self.ORIGIN_X) / self.CELL)
            row = round((y0 - self.ORIGIN_Y) / self.CELL)
            result[(row, col)] = feature.GetField(column)
        dataset = None
        return result


class TestWritePercentageScoresToGrid(unittest.TestCase):
    """write_percentage_scores_to_grid gained a bbox pre-filter before the

    expensive exact GEOS intersection (worldbank/GeoE3#445/#448) - these
    tests confirm cells far from any buffer still correctly score 0 and
    cells overlapping a buffer still score correctly, i.e. the fast-reject
    path doesn't change results.
    """

    ORIGIN_X = 700000.0
    ORIGIN_Y = 1516000.0
    CELL = 1000.0

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_grid_pct_")
        self.main_gpkg = os.path.join(self.temp_dir, "study_area.gpkg")
        driver = ogr.GetDriverByName("GPKG")
        dataset = driver.CreateDataSource(self.main_gpkg)
        from osgeo import osr

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(32620)
        layer = dataset.CreateLayer("study_area_grid", srs, geom_type=ogr.wkbPolygon)
        layer.CreateField(ogr.FieldDefn("area_name", ogr.OFTString))
        layer_defn = layer.GetLayerDefn()
        # Two cells side by side: (0,0) will overlap the buffer, (0,1) (far
        # to the east) will not.
        for col, x0 in [(0, self.ORIGIN_X), (1, self.ORIGIN_X + 100 * self.CELL)]:
            ring = ogr.Geometry(ogr.wkbLinearRing)
            for px, py in [
                (x0, self.ORIGIN_Y),
                (x0 + self.CELL, self.ORIGIN_Y),
                (x0 + self.CELL, self.ORIGIN_Y + self.CELL),
                (x0, self.ORIGIN_Y + self.CELL),
                (x0, self.ORIGIN_Y),
            ]:
                ring.AddPoint(px, py)
            polygon = ogr.Geometry(ogr.wkbPolygon)
            polygon.AddGeometry(ring)
            feature = ogr.Feature(layer_defn)
            feature.SetField("area_name", "test_area")
            feature.SetGeometry(polygon)
            layer.CreateFeature(feature)
        dataset = None

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _buffer_layer_covering_cell_0(self):
        from qgis.core import QgsFeature, QgsGeometry, QgsVectorLayer

        layer = QgsVectorLayer("Polygon?crs=EPSG:32620", "buffers", "memory")
        feature = QgsFeature(layer.fields())
        # Fully covers cell (0,0): 100% intersection.
        wkt = (
            f"POLYGON(({self.ORIGIN_X} {self.ORIGIN_Y}, "
            f"{self.ORIGIN_X + self.CELL} {self.ORIGIN_Y}, "
            f"{self.ORIGIN_X + self.CELL} {self.ORIGIN_Y + self.CELL}, "
            f"{self.ORIGIN_X} {self.ORIGIN_Y + self.CELL}, "
            f"{self.ORIGIN_X} {self.ORIGIN_Y}))"
        )
        feature.setGeometry(QgsGeometry.fromWkt(wkt))
        layer.dataProvider().addFeature(feature)
        layer.updateExtents()
        return layer

    def _read_scores(self, column):
        dataset = ogr.Open(self.main_gpkg, 0)
        layer = dataset.GetLayerByName("study_area_grid")
        result = {}
        for feature in layer:
            geom = feature.GetGeometryRef()
            x0 = geom.GetEnvelope()[0]
            col = round((x0 - self.ORIGIN_X) / self.CELL) if x0 < self.ORIGIN_X + 50 * self.CELL else 1
            result[col] = feature.GetField(column)
        dataset = None
        return result

    def test_overlapping_cell_scores_full_coverage_far_cell_scores_zero(self):
        buffer_layer = self._buffer_layer_covering_cell_0()
        updated = write_percentage_scores_to_grid(
            gpkg_path=self.main_gpkg,
            column_name="pct_col",
            buffer_layer=buffer_layer,
            percentage_scores={0: 0, 50: 3, 100: 5},
        )
        self.assertGreaterEqual(updated, 1)
        scores = self._read_scores("pct_col")
        self.assertEqual(scores.get(0), 5, "cell fully inside the buffer must score the top class")
        self.assertEqual(scores.get(1), 0, "cell far from the buffer (rejected by the bbox pre-filter) must score 0")


class TestWriteAggregationToGrid(unittest.TestCase):
    """Regression test: an aggregated column must be visible to a FRESH connection.

    write_aggregation_to_grid() used to close its dataset with plain
    `ds = None` - no WAL checkpoint/FlushCache beforehand, unlike every
    other grid-write function in this module. Under WAL mode, the UPDATE
    itself commits fine, but a later reader opening its own connection
    (QGIS reopening the project, this test's _read_grid_values helper, a
    real run's downstream rasterization step) can still see the pre-update
    NULL values if the WAL was never merged into the main .gpkg file.
    Reading back through the SAME ogr.Dataset that did the write would not
    catch this - it has to be a separate connection, like a real caller.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_grid_aggregation_")
        self.main_gpkg = os.path.join(self.temp_dir, "study_area.gpkg")

        driver = ogr.GetDriverByName("GPKG")
        dataset = driver.CreateDataSource(self.main_gpkg)
        layer = dataset.CreateLayer("study_area_grid", geom_type=ogr.wkbPolygon)
        layer.CreateField(ogr.FieldDefn("indicator_a", ogr.OFTReal))
        layer.CreateField(ogr.FieldDefn("indicator_b", ogr.OFTReal))
        layer.CreateField(ogr.FieldDefn("fac_example", ogr.OFTReal))

        layer_defn = layer.GetLayerDefn()
        for value_a, value_b in [(2.0, 4.0), (3.0, None), (None, None)]:
            feature = ogr.Feature(layer_defn)
            if value_a is not None:
                feature.SetField("indicator_a", value_a)
            if value_b is not None:
                feature.SetField("indicator_b", value_b)
            layer.CreateFeature(feature)
        dataset = None

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _read_grid_values(self, column_name):
        dataset = ogr.Open(self.main_gpkg, 0)
        layer = dataset.GetLayerByName("study_area_grid")
        values = [feature.GetField(column_name) for feature in layer]
        dataset = None
        return values

    def test_aggregated_column_is_visible_from_a_fresh_connection(self):
        result = write_aggregation_to_grid(
            gpkg_path=self.main_gpkg,
            target_column="fac_example",
            source_columns_weights={"indicator_a": 0.5, "indicator_b": 0.5},
        )

        self.assertEqual(result, 0)
        values = self._read_grid_values("fac_example")
        self.assertEqual(len(values), 3)
        self.assertTrue(all(v is not None for v in values), f"expected no NULLs, got {values}")
        self.assertAlmostEqual(values[0], 0.5 * 2.0 + 0.5 * 4.0)
        self.assertAlmostEqual(values[1], 0.5 * 3.0 + 0.5 * 0.0)
        self.assertAlmostEqual(values[2], 0.0)


if __name__ == "__main__":
    unittest.main()
