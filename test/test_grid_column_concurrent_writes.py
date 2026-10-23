# -*- coding: utf-8 -*-
"""Reproduction of concurrent grid-column writes silently losing data.

Real-world evidence (CaboVerdeWomen, 2026-10-22, concurrent_tasks > 1): three
ContextualIndexScoreWorkflow instances (Workplace_Index/Pay_Parenthood_Index/
Entrepreneurship_Index) started within 6ms of each other and all reported
"Workflow Completed" with no error - but a fresh read of study_area_grid
afterward showed only one of the three columns actually held its value; the
other two were NULL. Each write is a single whole-table SQL UPDATE wrapped in
StartTransaction()/CommitTransaction() (checked, raises on failure) via its
own independent ogr.Open(gpkg_path, 1) connection - this test drives that
exact pattern with real threads against a real GeoPackage to see whether
concurrent writers to DIFFERENT columns of the SAME table can lose data
despite every write reporting success.
"""
import os
import shutil
import tempfile
import threading
import unittest

from osgeo import ogr

from geest.core.grid_column_utils import write_uniform_value_to_grid

ogr.UseExceptions()


class TestConcurrentGridColumnWrites(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_grid_concurrent_")
        self.gpkg_path = os.path.join(self.temp_dir, "study_area.gpkg")
        driver = ogr.GetDriverByName("GPKG")
        dataset = driver.CreateDataSource(self.gpkg_path)
        layer = dataset.CreateLayer("study_area_grid", geom_type=ogr.wkbPolygon)
        self.columns = [f"col_{i}" for i in range(6)]
        for column in self.columns:
            layer.CreateField(ogr.FieldDefn(column, ogr.OFTReal))
        layer_defn = layer.GetLayerDefn()
        for _ in range(50):
            layer.CreateFeature(ogr.Feature(layer_defn))
        dataset = None

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _read_column(self, column_name):
        dataset = ogr.Open(self.gpkg_path, 0)
        layer = dataset.GetLayerByName("study_area_grid")
        values = [feature.GetField(column_name) for feature in layer]
        dataset = None
        return values

    def test_concurrent_writes_to_different_columns_all_persist(self):
        """Every column's write must survive, even when started together."""
        errors = {}
        barrier = threading.Barrier(len(self.columns))

        def _write(column_name, value):
            try:
                barrier.wait(timeout=5)  # maximise overlap between writers
                result = write_uniform_value_to_grid(
                    gpkg_path=self.gpkg_path,
                    column_name=column_name,
                    value=value,
                )
                if result < 0:
                    errors[column_name] = "write_uniform_value_to_grid returned an error code"
            except Exception as error:  # noqa: BLE001 - want to see every failure, not just the first
                errors[column_name] = repr(error)

        threads = [
            threading.Thread(target=_write, args=(column, float(index))) for index, column in enumerate(self.columns)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        self.assertFalse(errors, f"write(s) raised/failed: {errors}")

        lost = {}
        for index, column in enumerate(self.columns):
            values = self._read_column(column)
            expected = float(index)
            if not all(v == expected for v in values):
                lost[column] = set(values)
        self.assertFalse(
            lost,
            f"column(s) did not persist their concurrent write despite reporting success: {lost}",
        )


if __name__ == "__main__":
    unittest.main()
