# -*- coding: utf-8 -*-
"""Unit tests for SafetyRasterWorkflow classification table logic.

The table-building methods (_build_binary_table, _build_reclassification_table)
are pure numpy / jenks logic with no QGIS calls at runtime.  We test them by
replicating the logic as standalone helper functions (identical to the workflow
implementation) that can run without a QGIS application context.

Run with:
    pytest test/test_safety_raster_reclass_processor.py -v
"""

import unittest

import numpy as np

from geest.core.jenks import calculate_goodness_of_variance_fit, jenks_natural_breaks

# ---------------------------------------------------------------------------
# Replicate the two table-building methods as standalone functions.
# These are a direct copy of the logic in SafetyRasterWorkflow, allowing
# the tests to run without instantiating the QGIS-dependent class.
# ---------------------------------------------------------------------------


def _build_binary_table(max_val: float) -> list:
    """Mirrors SafetyRasterWorkflow._build_binary_table."""
    _ = max_val
    reclass_table = ["-inf", "0.0", "0", "0.0", "inf", "5"]
    return list(map(str, reclass_table))


def _build_reclassification_table(attributes: dict, max_val: float, median: float, valid_data) -> list:
    """Mirrors SafetyRasterWorkflow._build_reclassification_table."""
    classification_mode = attributes.get("ntl_classification_mode", "jenks")
    if classification_mode == "binary":
        return _build_binary_table(max_val)

    n_classes = 6
    breaks = jenks_natural_breaks(valid_data, n_classes=n_classes)
    gvf = calculate_goodness_of_variance_fit(valid_data, breaks)  # noqa: F841  kept for parity with workflow logging

    reclass_table: list = [0.0, breaks[0], 0]
    for i in range(len(breaks) - 1):
        reclass_table.extend([breaks[i], breaks[i + 1], i + 1])
    return list(map(str, reclass_table))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBuildBinaryTable(unittest.TestCase):
    """Tests for the binary table builder."""

    def test_length(self):
        """Binary table must have exactly 6 elements: [min, max, cls] × 2."""
        self.assertEqual(len(_build_binary_table(100.0)), 6)

    def test_class_scores(self):
        """Dark pixels → class 0; lit pixels → class 5."""
        t = _build_binary_table(50.0)
        self.assertEqual(t[2], "0")
        self.assertEqual(t[5], "5")

    def test_boundary_at_zero(self):
        """Class boundary must be exactly at 0.0."""
        t = _build_binary_table(99.0)
        self.assertEqual(t[1], "0.0")
        self.assertEqual(t[3], "0.0")

    def test_binary_table_uses_infinite_bounds(self):
        """Binary table should cover all values with -inf and inf bounds."""
        t = _build_binary_table(99.0)
        self.assertEqual(t[0], "-inf")
        self.assertEqual(t[4], "inf")

    def test_all_strings(self):
        """All entries must be strings (QGIS reclassifybytable requirement)."""
        for entry in _build_binary_table(42.0):
            self.assertIsInstance(entry, str)

    def test_max_val_not_used_for_binary(self):
        """Binary classification uses inf upper bound regardless of max_val."""
        t = _build_binary_table(77.5)
        self.assertEqual(t[4], "inf")


class TestBuildReclassificationTable(unittest.TestCase):
    """Tests for _build_reclassification_table dispatching and output."""

    # --- binary mode ---

    def test_binary_mode_returns_6_elements(self):
        attrs = {"ntl_classification_mode": "binary"}
        data = np.array([0.0, 0.0, 0.0, 5.0, 10.0, 20.0], dtype=np.float32)
        t = _build_reclassification_table(attrs, 20.0, 0.0, data)
        self.assertEqual(len(t), 6)

    def test_binary_mode_scores(self):
        attrs = {"ntl_classification_mode": "binary"}
        data = np.array([0.0, 1.0, 2.0], dtype=np.float32)
        t = _build_reclassification_table(attrs, 2.0, 1.0, data)
        self.assertEqual(t[2], "0")
        self.assertEqual(t[5], "5")

    def test_binary_mode_does_not_call_jenks(self):
        """Binary mode must not invoke jenks_natural_breaks at all."""
        import geest.core.jenks as jenks_mod

        original = jenks_mod.jenks_natural_breaks
        called = []

        def _spy(*args, **kwargs):
            called.append(1)
            return original(*args, **kwargs)

        jenks_mod.jenks_natural_breaks = _spy
        try:
            attrs = {"ntl_classification_mode": "binary"}
            data = np.linspace(0.1, 100.0, 200, dtype=np.float32)
            _build_reclassification_table(attrs, float(data.max()), float(np.median(data)), data)
            self.assertEqual(called, [], "jenks_natural_breaks must not be called in binary mode")
        finally:
            jenks_mod.jenks_natural_breaks = original

    # --- jenks mode ---

    def test_jenks_mode_returns_18_elements(self):
        """6 classes × 3 values each = 18 elements."""
        attrs = {"ntl_classification_mode": "jenks"}
        rng = np.random.default_rng(42)
        data = rng.uniform(0.1, 100.0, size=500).astype(np.float32)
        t = _build_reclassification_table(attrs, float(data.max()), float(np.median(data)), data)
        self.assertEqual(len(t), 18)

    def test_jenks_mode_all_strings(self):
        attrs = {"ntl_classification_mode": "jenks"}
        rng = np.random.default_rng(0)
        data = rng.uniform(0.1, 80.0, size=200).astype(np.float32)
        t = _build_reclassification_table(attrs, float(data.max()), float(np.median(data)), data)
        for entry in t:
            self.assertIsInstance(entry, str)

    def test_jenks_class_0_starts_at_zero(self):
        """The first class must always start at 0.0."""
        attrs = {"ntl_classification_mode": "jenks"}
        rng = np.random.default_rng(1)
        data = rng.uniform(0.1, 50.0, size=300).astype(np.float32)
        t = _build_reclassification_table(attrs, float(data.max()), float(np.median(data)), data)
        self.assertEqual(float(t[0]), 0.0)

    def test_jenks_class_numbers_ascending(self):
        """Class scores in the table must be 0, 1, 2, 3, 4, 5 in order."""
        attrs = {"ntl_classification_mode": "jenks"}
        rng = np.random.default_rng(7)
        data = rng.uniform(0.0, 100.0, size=400).astype(np.float32)
        t = _build_reclassification_table(attrs, float(data.max()), float(np.median(data)), data)
        # Every third element starting at index 2 is the class number
        scores = [int(t[i]) for i in range(2, 18, 3)]
        self.assertEqual(scores, [0, 1, 2, 3, 4, 5])

    # --- backward compat / default ---

    def test_missing_attribute_defaults_to_jenks(self):
        """No ntl_classification_mode in attributes → Jenks (18-element table)."""
        attrs = {}  # simulate old saved model without the key
        rng = np.random.default_rng(99)
        data = rng.uniform(0.1, 75.0, size=250).astype(np.float32)
        t = _build_reclassification_table(attrs, float(data.max()), float(np.median(data)), data)
        self.assertEqual(len(t), 18)


if __name__ == "__main__":
    unittest.main()
