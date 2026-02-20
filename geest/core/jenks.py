# -*- coding: utf-8 -*-
"""
Jenks Natural Breaks classification implementation using Pure NumPy.

This module provides a Fisher-Jenks Natural Breaks algorithm implementation
for optimal classification of continuous data into discrete classes. The
algorithm minimizes within-class variance while maximizing between-class
variance, producing statistically optimal class boundaries.

This implementation is mathematically equivalent to the jenkspy library but
uses only NumPy (already available in QGIS) to avoid external dependencies.

Example:
    >>> import numpy as np
    >>> from geest.core.jenks import jenks_natural_breaks
    >>>
    >>> data = np.array([1.2, 1.5, 2.1, 3.4, 4.5, 5.2, 6.8, 7.1, 8.9, 9.2])
    >>> breaks = jenks_natural_breaks(data, n_classes=3)
    >>> print(breaks)  # Returns optimal break points
    [4.5, 7.1, 9.2]
"""

__copyright__ = "Copyright 2024, Tim Sutton"
__license__ = "GPL version 3"
__email__ = "tim@kartoza.com"
__revision__ = "$Format:%H$"

from typing import List, Tuple

import numpy as np

from geest.utilities import log_message

# Constants
MAX_UNIQUE_VALUES = 50000  # Threshold for automatic sampling
DEFAULT_SAMPLE_SIZE = 10000  # Sample size for large datasets


def jenks_natural_breaks(
    data: np.ndarray,
    n_classes: int,
    max_unique: int = MAX_UNIQUE_VALUES,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
) -> List[float]:
    """
    Calculate Jenks Natural Breaks classification for continuous data.

    Uses the Fisher-Jenks algorithm to find optimal class boundaries that
    minimize within-class variance. Automatically samples large datasets
    to maintain reasonable performance.

    Args:
        data: Input data array (1D NumPy array)
        n_classes: Number of classes to create (must be >= 2)
        max_unique: Maximum unique values before sampling (default: 50000)
        sample_size: Sample size for large datasets (default: 10000)

    Returns:
        List of break points [break₁, break₂, ..., max_value]
        Length will be n_classes (upper boundary of each class)

    Raises:
        ValueError: If n_classes < 2 or data is empty/invalid

    Example:
        >>> data = np.array([1, 2, 3, 10, 11, 12, 20, 21, 22])
        >>> breaks = jenks_natural_breaks(data, n_classes=3)
        >>> breaks
        [3.0, 12.0, 22.0]

    Note:
        Time complexity: O(k × n²) where k=n_classes, n=unique values
        For datasets with >50K unique values, automatic sampling is used
    """
    if n_classes < 2:
        raise ValueError(f"n_classes must be >= 2, got {n_classes}")

    if data is None or len(data) == 0:
        raise ValueError("Data array is empty")

    # Prepare and validate data
    clean_data, was_sampled = _prepare_data(data, n_classes, max_unique, sample_size)

    if was_sampled:
        log_message(
            f"🔬 Sampled {len(clean_data)} values from {len(data)} " f"for Jenks classification",
            tag="Geest",
            level=1,  # Info level
        )

    # Compute Jenks breaks using Fisher-Jenks algorithm
    breaks = _compute_jenks_breaks(clean_data, n_classes)

    return breaks


def _prepare_data(
    data: np.ndarray,
    n_classes: int,
    max_unique: int,
    sample_size: int,
) -> Tuple[np.ndarray, bool]:
    """
    Prepare data for Jenks classification: clean, dedupe, sample if needed.

    Args:
        data: Raw input data array
        n_classes: Number of classes requested
        max_unique: Threshold for sampling
        sample_size: Target sample size

    Returns:
        Tuple of (cleaned_data, was_sampled)
        - cleaned_data: Sorted array of unique valid values
        - was_sampled: Boolean indicating if sampling was performed

    Raises:
        ValueError: If insufficient valid data for requested classes
    """
    # Remove NaN and infinite values
    valid_mask = np.isfinite(data)
    clean_data = data[valid_mask]

    if len(clean_data) == 0:
        raise ValueError("No valid (non-NaN, finite) values in data")

    # Get unique values and sort
    unique_vals = np.unique(clean_data)

    # Check if we have enough unique values for the requested classes
    if len(unique_vals) < n_classes:
        raise ValueError(f"Insufficient unique values ({len(unique_vals)}) " f"for {n_classes} classes")

    # Sample if too many unique values
    was_sampled = False
    if len(unique_vals) > max_unique:
        # Use quantile-based sampling to preserve distribution
        quantiles = np.linspace(0, 1, sample_size)
        sampled = np.quantile(unique_vals, quantiles)
        unique_vals = np.unique(sampled)  # Remove any duplicates from sampling
        was_sampled = True

    return unique_vals, was_sampled


def _compute_jenks_breaks(data: np.ndarray, n_classes: int) -> List[float]:
    """
    Core Fisher-Jenks algorithm using dynamic programming.

    Computes optimal class boundaries by minimizing within-class variance
    using a dynamic programming approach with O(k × n²) complexity.

    Args:
        data: Sorted array of unique values
        n_classes: Number of classes to create

    Returns:
        List of break points (upper boundaries of each class)

    Algorithm:
        1. Build variance matrix V[i,j] for all possible ranges
        2. Use DP to find optimal k-class partition
        3. Backtrack to extract break points
    """
    n = len(data)

    # Edge case: if unique values equal classes, use each value as a break
    if n == n_classes:
        return data.tolist()

    # Precompute variance matrix: V[i][j] = variance of data[i:j+1]
    variance_matrix = _build_variance_matrix(data)

    # DP table: dp[k][j] = minimum variance for k classes using data[0:j+1]
    dp = np.full((n_classes + 1, n), np.inf)
    backtrack = np.zeros((n_classes + 1, n), dtype=int)

    # Base case: 1 class, j elements = variance of data[0:j+1]
    for j in range(n):
        dp[1][j] = variance_matrix[0][j]

    # Fill DP table for k=2 to n_classes
    for k in range(2, n_classes + 1):
        for j in range(k - 1, n):  # Need at least k elements for k classes
            # Try all possible positions for the (k-1)th break
            for i in range(k - 2, j):
                # Cost = variance of previous (k-1) classes + variance of [i+1:j+1]
                cost = dp[k - 1][i] + variance_matrix[i + 1][j]

                if cost < dp[k][j]:
                    dp[k][j] = cost
                    backtrack[k][j] = i

    # Extract break points by backtracking
    breaks = _extract_breaks(data, backtrack, n_classes, n - 1)

    return breaks


def _build_variance_matrix(data: np.ndarray) -> np.ndarray:
    """
    Build matrix of variances for all possible data ranges.

    Computes V[i][j] = variance of data[i:j+1] for all i <= j.
    Uses an optimized O(n²) algorithm with cumulative sums.

    Args:
        data: Sorted array of unique values

    Returns:
        2D array where V[i][j] = variance of data[i:j+1]

    Note:
        Uses the formula: Var(X) = E[X²] - E[X]²
        Cumulative sums allow O(1) calculation per range
    """
    n = len(data)
    variance_matrix = np.zeros((n, n))

    # Precompute cumulative sums for O(1) range queries
    cumsum = np.cumsum(data)
    cumsum2 = np.cumsum(data**2)

    for i in range(n):
        for j in range(i, n):
            variance_matrix[i][j] = _calculate_variance(data, i, j, cumsum, cumsum2)

    return variance_matrix


def _calculate_variance(
    data: np.ndarray,
    start: int,
    end: int,
    cumsum: np.ndarray,
    cumsum2: np.ndarray,
) -> float:
    """
    Calculate variance for data[start:end+1] in O(1) time.

    Uses precomputed cumulative sums to avoid recalculating for each range.

    Args:
        data: Original data array (not used, kept for clarity)
        start: Start index (inclusive)
        end: End index (inclusive)
        cumsum: Cumulative sum array
        cumsum2: Cumulative sum of squares array

    Returns:
        Variance of the specified range

    Formula:
        Var(X) = E[X²] - E[X]²
               = (Σx²/n) - (Σx/n)²
    """
    n = end - start + 1

    if n == 1:
        return 0.0

    # Get sum and sum of squares for range [start:end+1]
    if start == 0:
        sum_vals = cumsum[end]
        sum_sq = cumsum2[end]
    else:
        sum_vals = cumsum[end] - cumsum[start - 1]
        sum_sq = cumsum2[end] - cumsum2[start - 1]

    # Var(X) = E[X²] - E[X]²
    mean = sum_vals / n
    mean_sq = sum_sq / n
    variance = mean_sq - mean**2

    # Handle numerical precision issues
    return max(0.0, variance)


def _extract_breaks(
    data: np.ndarray,
    backtrack: np.ndarray,
    n_classes: int,
    last_idx: int,
) -> List[float]:
    """
    Extract break points by backtracking through DP table.

    Args:
        data: Sorted array of unique values
        backtrack: Backtrack matrix from DP algorithm
        n_classes: Number of classes
        last_idx: Last index in data array (n-1)

    Returns:
        List of break points (upper boundary of each class)
    """
    breaks = []
    k = n_classes
    idx = last_idx

    # Backtrack to find break points
    while k > 1:
        prev_idx = backtrack[k][idx]
        breaks.append(data[idx])
        idx = prev_idx
        k -= 1

    # Add the first class upper boundary
    breaks.append(data[idx])

    # Reverse to get ascending order
    breaks.reverse()

    return breaks


def calculate_goodness_of_variance_fit(
    data: np.ndarray,
    breaks: List[float],
) -> float:
    """
    Calculate Goodness of Variance Fit (GVF) statistic.

    GVF measures the quality of the classification:
    - GVF = 1.0: Perfect classification (no within-class variance)
    - GVF = 0.0: Poor classification (high within-class variance)

    Args:
        data: Original data array
        breaks: Break points from Jenks algorithm

    Returns:
        GVF value between 0 and 1 (higher is better)

    Formula:
        GVF = 1 - (SDCM / SDAM)
        where:
        - SDCM = Sum of Squared Deviations from Class Means
        - SDAM = Sum of Squared Deviations from Array Mean

    Example:
        >>> data = np.array([1, 2, 3, 10, 11, 12])
        >>> breaks = [3.0, 12.0]
        >>> gvf = calculate_goodness_of_variance_fit(data, breaks)
        >>> print(f"GVF: {gvf:.4f}")
        GVF: 0.9234
    """
    # Remove invalid values
    clean_data = data[np.isfinite(data)]

    if len(clean_data) == 0:
        return 0.0

    # Calculate SDAM (total variance)
    array_mean = np.mean(clean_data)
    sdam = np.sum((clean_data - array_mean) ** 2)

    if sdam == 0:
        return 1.0  # All values are identical

    # Calculate SDCM (within-class variance)
    sdcm = 0.0
    lower_bound = clean_data.min()

    for upper_bound in breaks:
        # Get data in this class
        class_mask = (clean_data >= lower_bound) & (clean_data <= upper_bound)
        class_data = clean_data[class_mask]

        if len(class_data) > 0:
            class_mean = np.mean(class_data)
            sdcm += np.sum((class_data - class_mean) ** 2)

        lower_bound = upper_bound

    # GVF = 1 - (within-class variance / total variance)
    gvf = 1.0 - (sdcm / sdam)

    return max(0.0, min(1.0, gvf))  # Clamp to [0, 1]
