# -*- coding: utf-8 -*-

"""
Safety Factor Configurations.

Streetlights and nighttime lights scoring methodologies.

Following the ACLED pattern - simple dictionaries with scale-specific data.
"""

# Streetlights Safety
# National: Large buffer (1km) with binary scoring
# Local: Small buffer (20m) with percentage-based intersection scoring
STREETLIGHTS_SAFETY = {
    "national": {
        "buffer_distance": 1000,
        "buffer_type": "meters",
        "scoring_method": "binary",
        "scores": {"intersects_buffer": 5, "no_intersection": 0},
        "description": "1km buffer with binary scoring",
    },
    "local": {
        "buffer_distance": 20,
        "buffer_type": "meters",
        "scoring_method": "percentage_intersection",
        "percentage_scores": {
            0: 0,  # 0% intersection
            1: 1,  # 1-19% intersection
            20: 2,  # 20-39% intersection
            40: 3,  # 40-59% intersection
            60: 4,  # 60-79% intersection
            80: 5,  # 80-100% intersection
        },
        "description": "20m buffer with percentage-based scoring",
    },
}

# Nighttime Lights Safety (VIIRS annual composites)
# Uses Jenks Natural Breaks algorithm for optimal data-driven classification
NIGHTTIME_LIGHTS_SAFETY = {
    "data_source": "VIIRS annual composites",
    "scoring_method": "jenks_natural_breaks",
    "classes": [
        {"score": 0, "label": "No Access", "range": "0 - Break₁", "example": "0 - 0.5"},
        {"score": 1, "label": "Very Low", "range": "> Break₁ - Break₂", "example": "0.5 - 2.0"},
        {"score": 2, "label": "Low", "range": "> Break₂ - Break₃", "example": "2.0 - 8.0"},
        {"score": 3, "label": "Moderate", "range": "> Break₃ - Break₄", "example": "8.0 - 25.0"},
        {"score": 4, "label": "High", "range": "> Break₄ - Break₅", "example": "25.0 - 75.0"},
        {"score": 5, "label": "Very High", "range": "> Break₅", "example": "> 75.0"},
    ],
    "example_note": ("Example values shown are for a typical urban area with VIIRS nighttime lights data."),
    "note": (
        "Actual break points are computed dynamically using Jenks Natural Breaks algorithm "
        "for optimal classification based on your study area's data distribution. "
        "For areas with very low maximum values (≤0.05) or low variance, "
        "a percentile-based classification is used instead."
    ),
}
