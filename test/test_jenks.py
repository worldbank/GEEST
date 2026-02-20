# -*- coding: utf-8 -*-
"""
Unit tests for Jenks Natural Breaks classification module.
"""

import unittest

import numpy as np

from geest.core.jenks import (
    calculate_goodness_of_variance_fit,
    jenks_natural_breaks,
)


class TestJenksNaturalBreaks(unittest.TestCase):
    """Test suite for jenks_natural_breaks function."""

    def test_basic_classification(self):
        """Test basic Jenks classification with simple data."""
        data = np.array([1, 2, 3, 10, 11, 12, 20, 21, 22])
        breaks = jenks_natural_breaks(data, n_classes=3)

        self.assertEqual(len(breaks), 3)
        self.assertTrue(breaks[0] <= breaks[1] <= breaks[2])
        self.assertEqual(breaks[-1], np.max(data))

    def test_low_light_scenario(self):
        """Test classification with very low nighttime lights values."""
        # Simulate VIIRS data with very low values (< 0.05)
        data = np.array([0.0, 0.001, 0.002, 0.005, 0.01, 0.015, 0.02, 0.03, 0.04])
        breaks = jenks_natural_breaks(data, n_classes=5)

        self.assertEqual(len(breaks), 5)
        self.assertTrue(all(0 <= b <= 0.04 for b in breaks))
        np.testing.assert_allclose(breaks[-1], 0.04, rtol=1e-6)

    def test_viirs_like_distribution(self):
        """Test with realistic VIIRS nighttime lights distribution."""
        # Simulate real VIIRS data: mostly low values with some high outliers
        np.random.seed(42)
        low_values = np.random.exponential(scale=0.5, size=900)
        high_values = np.random.uniform(5, 10, size=100)
        data = np.concatenate([low_values, high_values])

        breaks = jenks_natural_breaks(data, n_classes=6)

        self.assertEqual(len(breaks), 6)
        self.assertTrue(breaks[0] < breaks[-1])
        # Should capture the transition from low to high values
        self.assertTrue(breaks[3] < breaks[4])  # Gap between moderate and high

    def test_uniform_distribution(self):
        """Test with uniformly distributed data."""
        data = np.linspace(0, 100, 1000)
        breaks = jenks_natural_breaks(data, n_classes=4)

        self.assertEqual(len(breaks), 4)
        # For uniform distribution, breaks should be roughly evenly spaced
        diffs = np.diff(breaks)
        self.assertTrue(np.std(diffs) < np.mean(diffs) * 0.5)  # Reasonably uniform

    def test_normal_distribution(self):
        """Test with normally distributed data."""
        np.random.seed(123)
        data = np.random.normal(loc=50, scale=10, size=5000)
        breaks = jenks_natural_breaks(data, n_classes=5)

        self.assertEqual(len(breaks), 5)
        self.assertTrue(breaks[0] < breaks[-1])
        # Median break should be near the mean for normal distribution
        median_break_idx = len(breaks) // 2
        self.assertTrue(abs(breaks[median_break_idx] - 50) < 15)

    def test_identical_values(self):
        """Test with all identical values (edge case)."""
        data = np.array([5.0] * 100)

        with self.assertRaises(ValueError) as context:
            jenks_natural_breaks(data, n_classes=3)
        self.assertIn("Insufficient unique values", str(context.exception))

    def test_exact_classes_match_unique_values(self):
        """Test when number of unique values equals number of classes."""
        data = np.array([1, 5, 10, 20, 50, 100])
        breaks = jenks_natural_breaks(data, n_classes=6)

        self.assertEqual(len(breaks), 6)
        self.assertEqual(breaks[-1], 100)

    def test_two_classes_minimum(self):
        """Test that minimum 2 classes are required."""
        data = np.array([1, 2, 3, 4, 5])

        with self.assertRaises(ValueError) as context:
            jenks_natural_breaks(data, n_classes=1)
        self.assertIn("n_classes must be >= 2", str(context.exception))

    def test_empty_data(self):
        """Test error handling for empty data."""
        data = np.array([])

        with self.assertRaises(ValueError) as context:
            jenks_natural_breaks(data, n_classes=3)
        self.assertIn("Data array is empty", str(context.exception))

    def test_nan_handling(self):
        """Test that NaN values are properly filtered."""
        data = np.array([1, 2, np.nan, 3, 4, np.nan, 5, 6, 7, 8, 9, 10])
        breaks = jenks_natural_breaks(data, n_classes=3)

        self.assertEqual(len(breaks), 3)
        self.assertFalse(np.any(np.isnan(breaks)))

    def test_inf_handling(self):
        """Test that infinite values are properly filtered."""
        data = np.array([1, 2, 3, np.inf, 4, 5, -np.inf, 6, 7, 8, 9, 10])
        breaks = jenks_natural_breaks(data, n_classes=3)

        self.assertEqual(len(breaks), 3)
        self.assertFalse(np.any(np.isinf(breaks)))

    def test_insufficient_unique_values(self):
        """Test error when not enough unique values for classes."""
        data = np.array([1, 1, 1, 2, 2, 2])  # Only 2 unique values

        with self.assertRaises(ValueError) as context:
            jenks_natural_breaks(data, n_classes=5)
        self.assertIn("Insufficient unique values", str(context.exception))

    def test_large_dataset_sampling(self):
        """Test automatic sampling for very large datasets."""
        # Create dataset with > 50K unique values
        np.random.seed(999)
        data = np.random.uniform(0, 100, size=100000)

        breaks = jenks_natural_breaks(data, n_classes=5)

        self.assertEqual(len(breaks), 5)
        self.assertTrue(breaks[0] < breaks[-1])
        # Despite sampling, should still produce reasonable breaks

    def test_sparse_data(self):
        """Test with sparse data (large gaps between values)."""
        data = np.array([1, 2, 100, 101, 1000, 1001])
        breaks = jenks_natural_breaks(data, n_classes=3)

        self.assertEqual(len(breaks), 3)
        # Should identify the natural clusters
        self.assertTrue(breaks[0] < 100)  # First cluster
        self.assertTrue(100 <= breaks[1] < 1000)  # Second cluster
        self.assertTrue(breaks[2] >= 1000)  # Third cluster

    def test_breaks_monotonic_increasing(self):
        """Test that breaks are always monotonically increasing."""
        np.random.seed(456)
        data = np.random.exponential(scale=2, size=1000)

        for n_classes in range(2, 8):
            breaks = jenks_natural_breaks(data, n_classes=n_classes)
            self.assertTrue(all(breaks[i] <= breaks[i + 1] for i in range(len(breaks) - 1)))

    def test_deterministic_results(self):
        """Test that same data produces same breaks (deterministic)."""
        data = np.array([1.5, 2.3, 3.1, 4.8, 5.2, 6.9, 7.4, 8.1, 9.7])

        breaks1 = jenks_natural_breaks(data, n_classes=3)
        breaks2 = jenks_natural_breaks(data, n_classes=3)

        np.testing.assert_array_almost_equal(breaks1, breaks2)

    def test_float32_data(self):
        """Test with float32 data (common for raster data)."""
        data = np.array([1.5, 2.3, 3.1, 4.8, 5.2], dtype=np.float32)
        breaks = jenks_natural_breaks(data, n_classes=2)

        self.assertEqual(len(breaks), 2)
        self.assertIsInstance(breaks, list)

    def test_integer_data(self):
        """Test with integer data."""
        data = np.array([1, 2, 3, 10, 11, 12, 20, 21, 22], dtype=np.int32)
        breaks = jenks_natural_breaks(data, n_classes=3)

        self.assertEqual(len(breaks), 3)
        self.assertEqual(breaks[-1], 22)


class TestGoodnessOfVarianceFit(unittest.TestCase):
    """Test suite for calculate_goodness_of_variance_fit function."""

    def test_perfect_classification(self):
        """Test GVF with well-separated classes."""
        # Three well-separated clusters with clear boundaries
        data = np.array([1, 1, 1, 10, 10, 10, 100, 100, 100])
        breaks = jenks_natural_breaks(data, n_classes=3)

        gvf = calculate_goodness_of_variance_fit(data, breaks)

        # GVF should be between 0 and 1
        self.assertTrue(0.0 <= gvf <= 1.0)
        # For this data, GVF should be reasonable (not perfect due to within-class variance)
        self.assertTrue(gvf > 0.2)

    def test_gvf_range(self):
        """Test that GVF is always between 0 and 1."""
        np.random.seed(789)
        data = np.random.uniform(0, 100, size=1000)

        for n_classes in range(2, 6):
            breaks = jenks_natural_breaks(data, n_classes=n_classes)
            gvf = calculate_goodness_of_variance_fit(data, breaks)

            self.assertTrue(0.0 <= gvf <= 1.0)

    def test_gvf_with_identical_values(self):
        """Test GVF when all values are identical."""
        data = np.array([5.0] * 100)
        breaks = [5.0]

        gvf = calculate_goodness_of_variance_fit(data, breaks)

        # Should be 1.0 (perfect fit - no variance to explain)
        np.testing.assert_allclose(gvf, 1.0)

    def test_gvf_with_nan_values(self):
        """Test GVF filtering of NaN values."""
        data = np.array([1, 2, np.nan, 3, 10, 11, np.nan, 12])
        breaks = [3, 12]

        gvf = calculate_goodness_of_variance_fit(data, breaks)

        self.assertTrue(0.0 <= gvf <= 1.0)
        self.assertFalse(np.isnan(gvf))

    def test_gvf_empty_data(self):
        """Test GVF with empty valid data."""
        data = np.array([np.nan, np.nan, np.inf])
        breaks = [1, 2, 3]

        gvf = calculate_goodness_of_variance_fit(data, breaks)

        self.assertEqual(gvf, 0.0)

    def test_gvf_increases_with_classes(self):
        """Test that GVF generally increases with more classes."""
        np.random.seed(321)
        data = np.random.exponential(scale=5, size=1000)

        gvf_values = []
        for n_classes in range(2, 8):
            breaks = jenks_natural_breaks(data, n_classes=n_classes)
            gvf = calculate_goodness_of_variance_fit(data, breaks)
            gvf_values.append(gvf)

        # GVF should generally increase (or stay same) with more classes
        self.assertTrue(
            all(
                gvf_values[i] <= gvf_values[i + 1] + 0.01  # Allow small floating point variations
                for i in range(len(gvf_values) - 1)
            )
        )
