# -*- coding: utf-8 -*-
"""Unit tests for UnifiedWriterThread's Arrow-batch write paths.

_write_grid_batch()/_write_geometry_batch() each try GDAL's bulk
Layer.WritePyArrow() first (when pyarrow is importable) and otherwise
fall back to the original per-feature CreateFeature() loop. Constructs a
bare UnifiedWriterThread instance (bypassing QThread.__init__ - these two
methods only touch self.ds/self.layers/self.gpkg_path, not the thread
queue machinery) against a real temporary GeoPackage, so both the
Arrow-batch path (when pyarrow is installed) and the fallback path are
exercised against real GDAL/OGR behaviour, not mocks.
"""
import os
import shutil
import tempfile
import unittest

from osgeo import ogr, osr

from geest.core.tasks.study_area_processing_task import GpkgOperation, UnifiedWriterThread


def _make_writer(gpkg_path):
    """A bare UnifiedWriterThread with just the state _write_*_batch() needs."""
    writer = UnifiedWriterThread.__new__(UnifiedWriterThread)
    writer.gpkg_path = gpkg_path
    writer.ds = ogr.Open(gpkg_path, 1)
    writer.layers = {}
    return writer


def _create_square_grid_layer(gpkg_path, with_h3_fields=False):
    driver = ogr.GetDriverByName("GPKG")
    ds = driver.CreateDataSource(gpkg_path)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    layer = ds.CreateLayer("study_area_grid", srs, geom_type=ogr.wkbPolygon)
    layer.CreateField(ogr.FieldDefn("grid_id", ogr.OFTInteger))
    layer.CreateField(ogr.FieldDefn("area_name", ogr.OFTString))
    if with_h3_fields:
        layer.CreateField(ogr.FieldDefn("h3_index", ogr.OFTString))
        layer.CreateField(ogr.FieldDefn("h3_resolution", ogr.OFTInteger))
    ds = None


def _square_geom(i):
    return ogr.CreateGeometryFromWkt(f"POLYGON(({i} 0,{i + 1} 0,{i + 1} 1,{i} 1,{i} 0))")


class TestWriteGridBatch(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="test_unified_writer_grid_")
        self.gpkg_path = os.path.join(self.tmp_dir, "study_area.gpkg")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_writes_square_grid_cells(self):
        _create_square_grid_layer(self.gpkg_path)
        writer = _make_writer(self.gpkg_path)
        operations = [
            GpkgOperation.write_grid_cell(geometry=_square_geom(i), area_name="area1", grid_id=i) for i in range(20)
        ]

        writer._write_grid_batch(operations)

        layer = writer.ds.GetLayerByName("study_area_grid")
        self.assertEqual(layer.GetFeatureCount(), 20)
        layer.ResetReading()
        seen_ids = sorted(f.GetField("grid_id") for f in layer)
        self.assertEqual(seen_ids, list(range(20)))

    def test_writes_h3_fields_when_present_on_the_layer(self):
        _create_square_grid_layer(self.gpkg_path, with_h3_fields=True)
        writer = _make_writer(self.gpkg_path)
        operations = [
            GpkgOperation.write_grid_cell(
                geometry=_square_geom(i), area_name="area1", grid_id=i, h3_index=f"8a{i}", h3_resolution=8
            )
            for i in range(5)
        ]

        writer._write_grid_batch(operations)

        layer = writer.ds.GetLayerByName("study_area_grid")
        layer.ResetReading()
        rows = {f.GetField("grid_id"): f.GetField("h3_index") for f in layer}
        self.assertEqual(rows, {i: f"8a{i}" for i in range(5)})

    def test_square_grid_without_h3_fields_does_not_crash(self):
        """A plain square grid has no h3_index/h3_resolution fields at all -
        the Arrow batch must not try to write columns the layer doesn't have."""
        _create_square_grid_layer(self.gpkg_path, with_h3_fields=False)
        writer = _make_writer(self.gpkg_path)
        operations = [GpkgOperation.write_grid_cell(geometry=_square_geom(0), area_name="area1", grid_id=0)]

        writer._write_grid_batch(operations)

        layer = writer.ds.GetLayerByName("study_area_grid")
        self.assertEqual(layer.GetFeatureCount(), 1)


class TestWriteGeometryBatch(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="test_unified_writer_geom_")
        self.gpkg_path = os.path.join(self.tmp_dir, "study_area.gpkg")
        driver = ogr.GetDriverByName("GPKG")
        ds = driver.CreateDataSource(self.gpkg_path)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        layer = ds.CreateLayer("study_area_bboxes", srs, geom_type=ogr.wkbPolygon)
        layer.CreateField(ogr.FieldDefn("area_name", ogr.OFTString))
        layer.CreateField(ogr.FieldDefn("intersects_ghsl", ogr.OFTInteger))
        ds = None

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_writes_geometries_with_extra_fields(self):
        writer = _make_writer(self.gpkg_path)
        operations = [
            GpkgOperation.write_geometry(
                layer_name="study_area_bboxes",
                geometry=_square_geom(i),
                area_name="area1",
                intersects_ghsl=1 if i % 2 == 0 else 0,
            )
            for i in range(10)
        ]

        writer._write_geometry_batch(operations)

        layer = writer.ds.GetLayerByName("study_area_bboxes")
        self.assertEqual(layer.GetFeatureCount(), 10)
        layer.ResetReading()
        flags = sorted(f.GetField("intersects_ghsl") for f in layer)
        self.assertEqual(flags, sorted([1 if i % 2 == 0 else 0 for i in range(10)]))

    def test_groups_by_layer_name(self):
        driver = ogr.Open(self.gpkg_path, 1)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        other_layer = driver.CreateLayer("chunks", srs, geom_type=ogr.wkbPolygon)
        other_layer.CreateField(ogr.FieldDefn("area_name", ogr.OFTString))
        driver = None

        writer = _make_writer(self.gpkg_path)
        operations = [
            GpkgOperation.write_geometry(layer_name="study_area_bboxes", geometry=_square_geom(0), area_name="a"),
            GpkgOperation.write_geometry(layer_name="chunks", geometry=_square_geom(1), area_name="a"),
        ]

        writer._write_geometry_batch(operations)

        self.assertEqual(writer.ds.GetLayerByName("study_area_bboxes").GetFeatureCount(), 1)
        self.assertEqual(writer.ds.GetLayerByName("chunks").GetFeatureCount(), 1)


if __name__ == "__main__":
    unittest.main()
