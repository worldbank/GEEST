# -*- coding: utf-8 -*-
"""Unit tests for geest.core.arrow_batch_writer.

Covers both branches the fallback design depends on: pyarrow genuinely
missing (ImportError -> graceful False, never raised) and pyarrow present
and used for a real write (the common case once a QGIS install has
python3-pyarrow, e.g. the default Windows OSGeo4W install). The
"available" tests are skipped, not failed, when pyarrow is not importable
in the environment actually running this suite - the nix dev shell/CI
image used for this plugin does not currently carry it.
"""
import os
import tempfile
import unittest
from unittest.mock import patch

from osgeo import ogr, osr

from geest.core.arrow_batch_writer import log_arrow_batch_fallback, write_features_arrow_batch

try:
    import pyarrow  # noqa: F401

    HAS_PYARROW = True
except ImportError:
    HAS_PYARROW = False


def _make_square_layer(ds, name="cells"):
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    layer = ds.CreateLayer(name, srs, geom_type=ogr.wkbPolygon)
    layer.CreateField(ogr.FieldDefn("cell_id", ogr.OFTInteger64))
    layer.CreateField(ogr.FieldDefn("score", ogr.OFTReal))
    return layer


def _square_geom(i):
    return ogr.CreateGeometryFromWkt(f"POLYGON(({i} 0,{i + 1} 0,{i + 1} 1,{i} 1,{i} 0))")


class TestWriteFeaturesArrowBatchWithoutPyarrow(unittest.TestCase):
    """When pyarrow is not importable, the function must return False, never raise."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="test_arrow_batch_writer_")
        self.gpkg_path = os.path.join(self.tmp_dir, "cells.gpkg")
        self.ds = ogr.GetDriverByName("GPKG").CreateDataSource(self.gpkg_path)
        self.layer = _make_square_layer(self.ds)

    def tearDown(self):
        self.ds = None
        import shutil

        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_returns_false_when_pyarrow_missing(self):
        real_import = __import__

        def fake_import(name, *args, **kwargs):
            if name == "pyarrow":
                raise ImportError("simulated: pyarrow not installed")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            result = write_features_arrow_batch(
                self.layer,
                {"cell_id": [1, 2], "score": [0.1, 0.2]},
                [_square_geom(0), _square_geom(1)],
            )

        self.assertFalse(result)
        self.assertEqual(self.layer.GetFeatureCount(), 0)


@unittest.skipUnless(HAS_PYARROW, "pyarrow is not installed in this environment")
class TestWriteFeaturesArrowBatchWithPyarrow(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="test_arrow_batch_writer_")
        self.gpkg_path = os.path.join(self.tmp_dir, "cells.gpkg")
        self.ds = ogr.GetDriverByName("GPKG").CreateDataSource(self.gpkg_path)
        self.layer = _make_square_layer(self.ds)

    def tearDown(self):
        self.ds = None
        import shutil

        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_writes_features_via_arrow_batch(self):
        n = 50
        result = write_features_arrow_batch(
            self.layer,
            {"cell_id": list(range(n)), "score": [i / 10.0 for i in range(n)]},
            [_square_geom(i) for i in range(n)],
        )

        self.assertTrue(result)
        self.assertEqual(self.layer.GetFeatureCount(), n)
        self.layer.ResetReading()
        seen_ids = sorted(f.GetField("cell_id") for f in self.layer)
        self.assertEqual(seen_ids, list(range(n)))

    def test_null_geometry_is_written_as_null(self):
        result = write_features_arrow_batch(
            self.layer,
            {"cell_id": [1], "score": [0.5]},
            [None],
        )

        self.assertTrue(result)
        self.layer.ResetReading()
        feature = next(iter(self.layer))
        self.assertIsNone(feature.GetGeometryRef())

    def test_mismatched_lengths_raise_value_error(self):
        with self.assertRaises(ValueError):
            write_features_arrow_batch(
                self.layer,
                {"cell_id": [1, 2], "score": [0.5]},
                [_square_geom(0), _square_geom(1)],
            )

    def test_respects_layers_own_geometry_column_name(self):
        """GPKG's geometry column is fixed at creation ("geom") - a column
        named anything else must still land correctly, exercising the
        GetGeometryColumn() lookup rather than a hardcoded "wkb_geometry"."""
        self.assertEqual(self.layer.GetGeometryColumn(), "geom")

        result = write_features_arrow_batch(
            self.layer,
            {"cell_id": [1], "score": [0.5]},
            [_square_geom(0)],
        )

        self.assertTrue(result)
        self.assertEqual(self.layer.GetFeatureCount(), 1)


class TestLogArrowBatchFallback(unittest.TestCase):
    def test_does_not_raise(self):
        # Just needs to not blow up - the actual log sink is exercised by
        # geest.utilities.log_message's own tests.
        log_arrow_batch_fallback("some_context", RuntimeError("boom"))


if __name__ == "__main__":
    unittest.main()
