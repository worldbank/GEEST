# -*- coding: utf-8 -*-
"""Tests for the analysis report's score-distribution sparkline.

AnalysisReport/BaseReport are heavy classes (full QgsLayout/template
construction), so these call the unbound methods directly against a
lightweight MagicMock stand-in, matching the pattern in
test_tree_panel_download_all_resources.py.
"""
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

from osgeo import ogr

from geest.core.reports.analysis_report import AnalysisReport
from geest.core.reports.base_report import BaseReport


class TestGridColumnScoreHistogram(unittest.TestCase):
    """Reads the study_area_grid column directly - the same values every
    result raster was rasterised from - rather than re-deriving the
    distribution from the rasterised output, which (a) is a resampled
    render of those same values, and (b) for some products (e.g. the
    1-15 bivariate "by population" score) uses an entirely different
    colour scheme than the plain 0-5 scale this sparkline shows.

    Score 0 must never leak into the 1-5 distribution the sparkline shows.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_score_histogram_")
        self.gpkg_path = os.path.join(self.temp_dir, "study_area.gpkg")
        self.report = MagicMock()
        self.report.grid_gpkg_path = self.gpkg_path
        # self.report is a MagicMock, so without this the histogram methods'
        # internal call to self._read_grid_column_values(...) would hit an
        # auto-mocked attribute instead of the real method under test.
        self.report._read_grid_column_values.side_effect = lambda column_name: (
            AnalysisReport._read_grid_column_values(self.report, column_name)
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_grid(self, column_name, values):
        driver = ogr.GetDriverByName("GPKG")
        dataset = driver.CreateDataSource(self.gpkg_path)
        layer = dataset.CreateLayer("study_area_grid", geom_type=ogr.wkbPolygon)
        layer.CreateField(ogr.FieldDefn(column_name, ogr.OFTReal))
        layer_defn = layer.GetLayerDefn()
        for value in values:
            feature = ogr.Feature(layer_defn)
            if value is not None:
                feature.SetField(column_name, value)
            layer.CreateFeature(feature)
        dataset = None

    def test_excludes_score_zero_from_the_returned_counts(self):
        self._make_grid("geoe3", [0, 0, 0, 1, 2, 2, 3, 4, 5, 5])

        counts = AnalysisReport._grid_column_score_histogram(self.report, "geoe3")

        self.assertEqual(counts, [1, 2, 1, 1, 2])

    def test_null_cells_are_not_counted_as_score_zero(self):
        self._make_grid("geoe3", [None, None, 1, 1, 1])

        counts = AnalysisReport._grid_column_score_histogram(self.report, "geoe3")

        self.assertEqual(counts, [3, 0, 0, 0, 0])

    def test_fractional_values_match_the_qml_discrete_boundaries(self):
        """Regression: a prior raster-based scheme centred bins on each
        integer (e.g. [2.5, 3.5) for score "3"), disagreeing with the
        map's own right-inclusive QML boundaries (0,1],(1,2],(2,3],(3,4],
        (4,5] - a column of mostly 3.3-3.99 values painted entirely green
        on the map but showed up as a yellow "3" bar on the sparkline.
        """
        self._make_grid("geoe3", [3.3, 3.5, 3.8, 3.99])

        counts = AnalysisReport._grid_column_score_histogram(self.report, "geoe3")

        self.assertEqual(counts, [0, 0, 0, 4, 0])

    def test_value_exactly_at_a_boundary_belongs_to_the_lower_class(self):
        """QGIS's DISCRETE shader is right-inclusive: value == 3.0 belongs
        to the (2,3] "yellow" class, not (3,4] "green"."""
        self._make_grid("geoe3", [3.0])

        counts = AnalysisReport._grid_column_score_histogram(self.report, "geoe3")

        self.assertEqual(counts, [0, 0, 1, 0, 0])

    def test_missing_gpkg_returns_five_zero_counts(self):
        self.report.grid_gpkg_path = os.path.join(self.temp_dir, "does_not_exist.gpkg")

        counts = AnalysisReport._grid_column_score_histogram(self.report, "geoe3")

        self.assertEqual(counts, [0, 0, 0, 0, 0])

    def test_unsafe_column_name_is_refused(self):
        self._make_grid("geoe3", [1, 2, 3])

        counts = AnalysisReport._grid_column_score_histogram(self.report, "geoe3; DROP TABLE study_area_grid")

        self.assertEqual(counts, [0, 0, 0, 0, 0])


class TestGridColumnPaletteHistogram(unittest.TestCase):
    """The "by population" bivariate product (1-15, PalettedRasterRenderer
    in geoe3_by_population_score.qml) needs EXACT-value counting, not the
    (lower, upper] range bucketing _grid_column_score_histogram() uses.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_palette_histogram_")
        self.gpkg_path = os.path.join(self.temp_dir, "study_area.gpkg")
        self.report = MagicMock()
        self.report.grid_gpkg_path = self.gpkg_path
        self.report._read_grid_column_values.side_effect = lambda column_name: (
            AnalysisReport._read_grid_column_values(self.report, column_name)
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_grid(self, column_name, values):
        driver = ogr.GetDriverByName("GPKG")
        dataset = driver.CreateDataSource(self.gpkg_path)
        layer = dataset.CreateLayer("study_area_grid", geom_type=ogr.wkbPolygon)
        layer.CreateField(ogr.FieldDefn(column_name, ogr.OFTReal))
        layer_defn = layer.GetLayerDefn()
        for value in values:
            feature = ogr.Feature(layer_defn)
            if value is not None:
                feature.SetField(column_name, value)
            layer.CreateFeature(feature)
        dataset = None

    def test_counts_each_exact_value_separately(self):
        self._make_grid("geoe3_by_population", [1, 1, 7, 15, 15, 15])

        counts = AnalysisReport._grid_column_palette_histogram(self.report, "geoe3_by_population", 15)

        expected = [0] * 15
        expected[0] = 2  # value 1
        expected[6] = 1  # value 7
        expected[14] = 3  # value 15
        self.assertEqual(counts, expected)

    def test_excludes_score_zero_from_the_returned_counts(self):
        self._make_grid("geoe3_by_population", [0, 0, 5])

        counts = AnalysisReport._grid_column_palette_histogram(self.report, "geoe3_by_population", 15)

        self.assertEqual(counts[4], 1)  # value 5
        self.assertEqual(sum(counts), 1)


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


class TestGridColumnName(unittest.TestCase):
    """Mirrors JsonTreeItem.gridColumnName()'s sanitisation exactly, since
    report code only has the model dict (not a JsonTreeItem) to work from.
    """

    def test_dimension_gets_dim_prefix(self):
        self.assertEqual(AnalysisReport._grid_column_name("dimension", "Contextual"), "dim_contextual")

    def test_factor_gets_fac_prefix(self):
        self.assertEqual(AnalysisReport._grid_column_name("factor", "EPLEX"), "fac_eplex")

    def test_indicator_has_no_prefix(self):
        self.assertEqual(
            AnalysisReport._grid_column_name("indicator", "eplex_score_indicator"), "eplex_score_indicator"
        )

    def test_spaces_and_hyphens_become_underscores(self):
        self.assertEqual(
            AnalysisReport._grid_column_name("factor", "Travel Patterns-2"),
            "fac_travel_patterns_2",
        )


class TestAddMinimapGridSparklineEligibility(unittest.TestCase):
    """Only minimaps with a grid_column on the plain 0-5 scale get a
    sparkline - e.g. the "by population" bivariate product must not, since
    it uses a completely different 1-15 colour scheme.
    """

    def setUp(self):
        self.report = MagicMock()
        self.report._map_layers.side_effect = lambda layer: [layer]

    def test_sparkline_drawn_only_for_entries_with_a_grid_column(self):
        layer_a = MagicMock()
        layer_b = MagicMock()
        minimaps = [
            ("Dimension A", layer_a, "dim_a", "likert"),
            ("By population", layer_b, None, None),
        ]

        AnalysisReport._add_minimap_grid(self.report, minimaps, current_page=1, top=50.0)

        self.assertEqual(self.report.make_minimap.call_count, 2)
        self.report._draw_sparkline_for_column.assert_called_once()
        called_kwargs = self.report._draw_sparkline_for_column.call_args.kwargs
        self.assertEqual(called_kwargs["column_name"], "dim_a")
        self.assertEqual(called_kwargs["palette"], "likert")


if __name__ == "__main__":
    unittest.main()
