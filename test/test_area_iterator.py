# -*- coding: utf-8 -*-
"""Regression tests for AreaIterator skipping unpopulated areas.

study_area_polygons already records intersects_ghsl for every area, and
study area creation already skips grid generation entirely for an area
with filter_study_areas_by_ghsl enabled and no GHSL settlements - but
AreaIterator never read any of that, so every indicator workflow
rediscovered the same empty area independently, on every single run,
after running its full per-area pipeline (raster subset, mask, neutral
fallback, rasterize attempt) only to find nothing to write (worldbank/
GeoE3 field report, 2026-10-23: "why are those areas still being
processed for every run?"). AreaIterator now skips any area with zero
study_area_grid cells before yielding it at all, determined directly
from the grid itself (works immediately for existing projects, not just
newly-created ones, and catches any zero-cell area regardless of why it
ended up that way, not just GHSL-filtered ones).
"""
import os
import shutil
import tempfile
import unittest

from osgeo import ogr, osr

from geest.core.algorithms.area_iterator import AreaIterator


def _square(x0, y0, size=1000.0):
    return f"POLYGON(({x0} {y0}, {x0 + size} {y0}, {x0 + size} {y0 + size}, " f"{x0} {y0 + size}, {x0} {y0}))"


class TestAreaIteratorSkipsUnpopulatedAreas(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_area_iterator_")
        self.gpkg_path = os.path.join(self.temp_dir, "study_area.gpkg")
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(32620)

        driver = ogr.GetDriverByName("GPKG")
        dataset = driver.CreateDataSource(self.gpkg_path)

        polygons = dataset.CreateLayer("study_area_polygons", srs, geom_type=ogr.wkbPolygon)
        polygons.CreateField(ogr.FieldDefn("area_name", ogr.OFTString))
        polygons.CreateField(ogr.FieldDefn("intersects_ghsl", ogr.OFTInteger))

        clip_polygons = dataset.CreateLayer("study_area_clip_polygons", srs, geom_type=ogr.wkbPolygon)
        clip_polygons.CreateField(ogr.FieldDefn("area_name", ogr.OFTString))

        bboxes = dataset.CreateLayer("study_area_bboxes", srs, geom_type=ogr.wkbPolygon)
        bboxes.CreateField(ogr.FieldDefn("area_name", ogr.OFTString))

        grid = dataset.CreateLayer("study_area_grid", srs, geom_type=ogr.wkbPolygon)
        grid.CreateField(ogr.FieldDefn("area_name", ogr.OFTString))

        # "populated_area": a real area with grid cells, intersects GHSL.
        # "ghsl_filtered_area": no GHSL settlements, so study area creation
        # never generated grid cells for it - this is the one that must now
        # be skipped entirely rather than reprocessed every run.
        for name, intersects_ghsl, x0 in [("populated_area", 1, 0.0), ("ghsl_filtered_area", 0, 2000.0)]:
            for layer in (polygons, clip_polygons, bboxes):
                feature = ogr.Feature(layer.GetLayerDefn())
                feature.SetField("area_name", name)
                if layer is polygons:
                    feature.SetField("intersects_ghsl", intersects_ghsl)
                feature.SetGeometry(ogr.CreateGeometryFromWkt(_square(x0, 0.0)))
                layer.CreateFeature(feature)

        # Only "populated_area" gets grid cells.
        for _ in range(5):
            feature = ogr.Feature(grid.GetLayerDefn())
            feature.SetField("area_name", "populated_area")
            feature.SetGeometry(ogr.CreateGeometryFromWkt(_square(0.0, 0.0, size=100.0)))
            grid.CreateFeature(feature)

        dataset = None

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_unpopulated_area_is_never_yielded(self):
        with AreaIterator(self.gpkg_path) as iterator:
            yielded_names = [area_name for _, _, _, _, area_name in iterator]

        self.assertEqual(yielded_names, ["populated_area"])

    def test_area_count_reflects_only_populated_areas(self):
        with AreaIterator(self.gpkg_path) as iterator:
            self.assertEqual(iterator.area_count(), 1)

    def test_progress_reaches_100_percent_for_the_last_populated_area(self):
        with AreaIterator(self.gpkg_path) as iterator:
            progresses = [progress for _, _, _, progress, _ in iterator]

        self.assertEqual(progresses, [100.0])


class TestAreaIteratorUnpartitionedGridIsNeverFiltered(unittest.TestCase):
    """A single, un-partitioned study area legitimately leaves every
    study_area_grid row's area_name NULL - that must never be read as
    "zero areas are populated" and silently skip everything."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_area_iterator_unpartitioned_")
        self.gpkg_path = os.path.join(self.temp_dir, "study_area.gpkg")
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(32620)

        driver = ogr.GetDriverByName("GPKG")
        dataset = driver.CreateDataSource(self.gpkg_path)

        polygons = dataset.CreateLayer("study_area_polygons", srs, geom_type=ogr.wkbPolygon)
        polygons.CreateField(ogr.FieldDefn("area_name", ogr.OFTString))
        clip_polygons = dataset.CreateLayer("study_area_clip_polygons", srs, geom_type=ogr.wkbPolygon)
        clip_polygons.CreateField(ogr.FieldDefn("area_name", ogr.OFTString))
        bboxes = dataset.CreateLayer("study_area_bboxes", srs, geom_type=ogr.wkbPolygon)
        bboxes.CreateField(ogr.FieldDefn("area_name", ogr.OFTString))
        # No area_name field at all on the grid - entirely unpartitioned.
        grid = dataset.CreateLayer("study_area_grid", srs, geom_type=ogr.wkbPolygon)

        for layer in (polygons, clip_polygons, bboxes):
            feature = ogr.Feature(layer.GetLayerDefn())
            feature.SetField("area_name", "whole_country")
            feature.SetGeometry(ogr.CreateGeometryFromWkt(_square(0.0, 0.0)))
            layer.CreateFeature(feature)

        for _ in range(5):
            feature = ogr.Feature(grid.GetLayerDefn())
            feature.SetGeometry(ogr.CreateGeometryFromWkt(_square(0.0, 0.0, size=100.0)))
            grid.CreateFeature(feature)

        dataset = None

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_area_is_still_yielded(self):
        with AreaIterator(self.gpkg_path) as iterator:
            yielded_names = [area_name for _, _, _, _, area_name in iterator]

        self.assertEqual(yielded_names, ["whole_country"])


if __name__ == "__main__":
    unittest.main()
