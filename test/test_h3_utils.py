# -*- coding: utf-8 -*-
"""Unit tests for H3 resolution-picking utilities in geest.core.h3_utils.

Covers the "local"/"national" resolution-selection additions:
get_h3_resolution_for_cell_size() and the cell_size_m-aware branch of
get_h3_resolution_for_scale(). Regional's fixed resolution-6 behaviour is
also covered here as a pure regression guard - it must never change.
"""

import unittest

from osgeo import osr

from geest.core.h3_utils import (
    _get_cached_transform,
    bbox_to_wgs84,
    get_h3_resolution_for_cell_size,
    get_h3_resolution_for_scale,
    h3_cell_area_km2,
    transform_wgs84_to_target,
)


def _closest_resolution_by_area(target_area_km2):
    """Independently recompute which of resolutions 0-15 best matches an area.

    Deliberately re-derives the "closest" answer from h3_cell_area_km2()
    (the same area table the module under test reads from) rather than
    hardcoding an expected resolution number, which could silently drift
    if the underlying h3 library's area table changes.
    """
    return min(range(16), key=lambda r: abs(h3_cell_area_km2(r) - target_area_km2))


class TestGetH3ResolutionForCellSize(unittest.TestCase):
    """Tests for get_h3_resolution_for_cell_size()."""

    def test_matches_independently_computed_closest_resolution_100m(self):
        cell_size_m = 100.0
        expected = _closest_resolution_by_area((cell_size_m / 1000.0) ** 2)
        self.assertEqual(get_h3_resolution_for_cell_size(cell_size_m), expected)

    def test_matches_independently_computed_closest_resolution_500m(self):
        cell_size_m = 500.0
        expected = _closest_resolution_by_area((cell_size_m / 1000.0) ** 2)
        self.assertEqual(get_h3_resolution_for_cell_size(cell_size_m), expected)

    def test_matches_independently_computed_closest_resolution_1000m(self):
        cell_size_m = 1000.0
        expected = _closest_resolution_by_area((cell_size_m / 1000.0) ** 2)
        self.assertEqual(get_h3_resolution_for_cell_size(cell_size_m), expected)

    def test_result_is_within_valid_resolution_range(self):
        for cell_size_m in (10.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 5000.0, 25000.0):
            resolution = get_h3_resolution_for_cell_size(cell_size_m)
            self.assertGreaterEqual(resolution, 0)
            self.assertLessEqual(resolution, 15)


class TestGetH3ResolutionForScale(unittest.TestCase):
    """Tests for get_h3_resolution_for_scale()."""

    def test_regional_always_returns_six(self):
        # Regional analyses must keep using a fixed H3 resolution 6,
        # completely unchanged by the local/national cell_size_m addition.
        self.assertEqual(get_h3_resolution_for_scale("regional"), 6)

    def test_regional_ignores_cell_size_m(self):
        # Even if a caller mistakenly passes cell_size_m for a regional
        # analysis, regional must still resolve to resolution 6.
        self.assertEqual(get_h3_resolution_for_scale("regional", cell_size_m=100.0), 6)

    def test_local_with_cell_size_matches_direct_lookup(self):
        self.assertEqual(
            get_h3_resolution_for_scale("local", cell_size_m=100.0),
            get_h3_resolution_for_cell_size(100.0),
        )

    def test_national_with_cell_size_matches_direct_lookup(self):
        self.assertEqual(
            get_h3_resolution_for_scale("national", cell_size_m=500.0),
            get_h3_resolution_for_cell_size(500.0),
        )

    def test_local_without_cell_size_returns_none(self):
        self.assertIsNone(get_h3_resolution_for_scale("local"))

    def test_unknown_scale_returns_none(self):
        self.assertIsNone(get_h3_resolution_for_scale("unknown", cell_size_m=100.0))


class TestTransformWgs84ToTarget(unittest.TestCase):
    """Regression guard for the GDAL axis-order bug.

    Without SetAxisMappingStrategy(OAMS_TRADITIONAL_GIS_ORDER) on the
    source EPSG:4326 spatial reference, GDAL's default authority-compliant
    axis order silently treats TransformPoint(x, y) as (lat, lon) instead
    of (lon, lat) - swapping every coordinate and producing wildly wrong,
    out-of-zone results for a projected target CRS. This directly caused
    the H3 pyramid level tables (study_area_grid_h3_res<N>) to be written
    with corrupted geometry while the base study_area_grid table happened
    to look fine, because its writer had an independent, compensating
    lat/lon-unpack bug of its own (see grid_from_bbox_h3_task.py).
    """

    def _independent_reference(self, lon, lat, target_epsg):
        """Recompute the expected answer with its own, explicitly-correct transform."""
        source_srs = osr.SpatialReference()
        source_srs.ImportFromEPSG(4326)
        source_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        target_srs = osr.SpatialReference()
        target_srs.ImportFromEPSG(target_epsg)
        target_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        transform = osr.CoordinateTransformation(source_srs, target_srs)
        x, y, _ = transform.TransformPoint(lon, lat)
        return x, y

    def test_matches_independently_computed_utm_coordinates(self):
        lon, lat = -23.5, 15.5  # a point within Cabo Verde
        target_epsg = 32626  # UTM zone 26N
        expected_x, expected_y = self._independent_reference(lon, lat, target_epsg)

        x, y = transform_wgs84_to_target(lon, lat, target_epsg)

        self.assertAlmostEqual(x, expected_x, places=3)
        self.assertAlmostEqual(y, expected_y, places=3)

    def test_result_is_a_sane_utm_easting_northing_not_an_axis_swapped_value(self):
        # A buggy (axis-swapped) transform for this point lands around
        # x=5,122,042 / y=-3,383,379 - nowhere near a valid UTM26N
        # easting/northing. The correct answer is a normal easting in the
        # low hundreds-of-thousands and a northing in the low millions.
        x, y = transform_wgs84_to_target(-23.5, 15.5, 32626)

        self.assertTrue(100000 < x < 900000, f"x={x} is not a plausible UTM easting")
        self.assertTrue(1000000 < y < 2500000, f"y={y} is not a plausible UTM northing")


class TestCachedTransform(unittest.TestCase):
    """_get_cached_transform() backs both bbox_to_wgs84() and
    transform_wgs84_to_target() - building a fresh osr.CoordinateTransformation
    per call measured ~20x slower than reusing one, which matters since
    both are called once per grid cell during generation."""

    def test_same_epsg_pair_returns_the_identical_cached_object(self):
        first = _get_cached_transform(4326, 32626)
        second = _get_cached_transform(4326, 32626)

        self.assertIs(first, second)

    def test_different_epsg_pairs_get_independent_transforms(self):
        to_utm26 = _get_cached_transform(4326, 32626)
        to_utm27 = _get_cached_transform(4326, 32627)

        self.assertIsNot(to_utm26, to_utm27)

    def test_reused_transform_still_produces_correct_coordinates(self):
        # Call twice (hitting the cache the second time) and confirm the
        # cached transform wasn't left in some consumed/invalid state.
        first_x, first_y = transform_wgs84_to_target(-23.5, 15.5, 32626)
        second_x, second_y = transform_wgs84_to_target(-23.5, 15.5, 32626)

        self.assertEqual(first_x, second_x)
        self.assertEqual(first_y, second_y)

    def test_bbox_to_wgs84_round_trips_through_transform_wgs84_to_target(self):
        target_epsg = 32626
        lon, lat = -23.5, 15.5
        x, y = transform_wgs84_to_target(lon, lat, target_epsg)

        wgs84_xmin, wgs84_xmax, wgs84_ymin, wgs84_ymax = bbox_to_wgs84(x - 1, x + 1, y - 1, y + 1, target_epsg)

        self.assertTrue(wgs84_xmin < lon < wgs84_xmax)
        self.assertTrue(wgs84_ymin < lat < wgs84_ymax)


if __name__ == "__main__":
    unittest.main()
