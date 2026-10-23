# -*- coding: utf-8 -*-
"""Tests for the analysis report's score-distribution sparkline.

AnalysisReport/BaseReport are heavy classes (full QgsLayout/template
construction), so these call the unbound methods directly against a
lightweight MagicMock stand-in or against None where self is unused,
matching the pattern in test_tree_panel_download_all_resources.py.
"""
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

import numpy
from osgeo import gdal, osr
from qgis.core import QgsRasterLayer

from geest.core.reports.analysis_report import AnalysisReport
from geest.core.reports.base_report import BaseReport


class TestRasterScoreHistogram(unittest.TestCase):
    """Score 0 must never leak into the 1-5 distribution the sparkline shows."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_score_histogram_")
        self.raster_path = os.path.join(self.temp_dir, "score.tif")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_raster(self, pixel_values, nodata=None):
        driver = gdal.GetDriverByName("GTiff")
        dataset = driver.Create(self.raster_path, len(pixel_values), 1, 1, gdal.GDT_Float32)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        dataset.SetProjection(srs.ExportToWkt())
        dataset.SetGeoTransform([0, 1, 0, 0, 0, -1])
        band = dataset.GetRasterBand(1)
        if nodata is not None:
            band.SetNoDataValue(nodata)
        band.WriteArray(numpy.array([pixel_values], dtype=numpy.float32))
        band.FlushCache()
        dataset = None

    def test_excludes_score_zero_from_the_returned_counts(self):
        self._make_raster([0, 0, 0, 1, 2, 2, 3, 4, 5, 5])
        layer = QgsRasterLayer(self.raster_path, "test")

        counts = AnalysisReport._raster_score_histogram(None, layer)

        self.assertEqual(counts, [1, 2, 1, 1, 2])

    def test_nodata_cells_are_not_counted_as_score_zero(self):
        self._make_raster([-9999, -9999, 1, 1, 1], nodata=-9999)
        layer = QgsRasterLayer(self.raster_path, "test")

        counts = AnalysisReport._raster_score_histogram(None, layer)

        self.assertEqual(counts, [3, 0, 0, 0, 0])

    def test_fractional_values_match_the_qml_discrete_boundaries(self):
        """Regression: a prior scheme centred bins on each integer (e.g.
        [2.5, 3.5) for score "3"), disagreeing with the map's own
        right-inclusive QML boundaries (0,1],(1,2],(2,3],(3,4],(4,5] - a
        raster of mostly 3.3-3.99 values painted entirely green on the
        map but showed up as a yellow "3" bar on the sparkline.
        """
        self._make_raster([3.3, 3.5, 3.8, 3.99])
        layer = QgsRasterLayer(self.raster_path, "test")

        counts = AnalysisReport._raster_score_histogram(None, layer)

        self.assertEqual(counts, [0, 0, 0, 4, 0])

    def test_value_exactly_at_a_boundary_belongs_to_the_lower_class(self):
        """QGIS's DISCRETE shader is right-inclusive: value == 3.0 belongs
        to the (2,3] "yellow" class, not (3,4] "green"."""
        self._make_raster([3.0])
        layer = QgsRasterLayer(self.raster_path, "test")

        counts = AnalysisReport._raster_score_histogram(None, layer)

        self.assertEqual(counts, [0, 0, 1, 0, 0])

    def test_unreadable_layer_returns_five_zero_counts(self):
        layer = MagicMock()
        layer.source.return_value = os.path.join(self.temp_dir, "does_not_exist.tif")

        counts = AnalysisReport._raster_score_histogram(None, layer)

        self.assertEqual(counts, [0, 0, 0, 0, 0])


class TestDrawSparkline(unittest.TestCase):
    """_draw_sparkline() scales bar heights relative to the tallest bar."""

    def setUp(self):
        self.report = MagicMock()
        self.report._rect = MagicMock()

    def test_bar_heights_are_proportional_to_the_peak_value(self):
        BaseReport._draw_sparkline(
            self.report,
            values=[1, 2, 4],
            colors=["red", "orange", "blue"],
            x=0.0,
            y=0.0,
            w=10.0,
            h=8.0,
            page=1,
        )

        self.assertEqual(self.report._rect.call_count, 3)
        heights = [call_args.args[3] for call_args in self.report._rect.call_args_list]
        self.assertAlmostEqual(heights[0], 2.0)  # 1/4 of peak * h=8
        self.assertAlmostEqual(heights[1], 4.0)  # 2/4 of peak * h=8
        self.assertAlmostEqual(heights[2], 8.0)  # 4/4 of peak * h=8

    def test_zero_value_bars_are_skipped(self):
        BaseReport._draw_sparkline(
            self.report,
            values=[0, 3],
            colors=["red", "blue"],
            x=0.0,
            y=0.0,
            w=10.0,
            h=8.0,
            page=1,
        )

        self.assertEqual(self.report._rect.call_count, 1)
        self.assertEqual(self.report._rect.call_args.args[-1], 1)

    def test_all_zero_values_draws_nothing(self):
        BaseReport._draw_sparkline(
            self.report,
            values=[0, 0, 0],
            colors=["red", "orange", "blue"],
            x=0.0,
            y=0.0,
            w=10.0,
            h=8.0,
            page=1,
        )

        self.report._rect.assert_not_called()

    def test_empty_values_draws_nothing(self):
        BaseReport._draw_sparkline(
            self.report,
            values=[],
            colors=[],
            x=0.0,
            y=0.0,
            w=10.0,
            h=8.0,
            page=1,
        )

        self.report._rect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
