# -*- coding: utf-8 -*-
"""Unit tests for H3 resolution-picking utilities in geest.core.h3_utils.

Covers the "local"/"national" resolution-selection additions:
get_h3_resolution_for_cell_size() and the cell_size_m-aware branch of
get_h3_resolution_for_scale(). Regional's fixed resolution-6 behaviour is
also covered here as a pure regression guard - it must never change.
"""

import unittest

from geest.core.h3_utils import (
    get_h3_resolution_for_cell_size,
    get_h3_resolution_for_scale,
    h3_cell_area_km2,
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


if __name__ == "__main__":
    unittest.main()
