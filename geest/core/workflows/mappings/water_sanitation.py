# -*- coding: utf-8 -*-

"""
Water and Sanitation Thresholds.

Single-buffer configuration for water/sanitation access.
"""

WATER_SANITATION_ACCESS = {
    "national": {
        "buffer_distance": 3000,
        "scoring_method": "binary",
        "scores": {"intersects": 5, "no_intersection": 0},
        "description": "National scale - 3km buffer",
    },
    "local": {
        "buffer_distance": 1000,
        "scoring_method": "binary",
        "scores": {"intersects": 5, "no_intersection": 0},
        "description": "Local scale - 1km buffer",
    },
    "regional": {
        "buffer_distance": 3000,
        "scoring_method": "percentage_intersection",
        "percentage_scores": {
            0: 0,
            16: 1,
            32: 2,
            48: 3,
            64: 4,
            100: 5,
        },
        "description": "Regional scale - percentage-based scoring with 3km buffer",
    },
}
