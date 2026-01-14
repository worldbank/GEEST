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
# Same for all scales
NIGHTTIME_LIGHTS_SAFETY = {
    "data_source": "VIIRS annual composites",
    "scoring_method": "raster_value_classification",
    "classes": [
        {"min_value": 0, "max_value": 15, "score": 0},
        {"min_value": 16, "max_value": 50, "score": 1},
        {"min_value": 51, "max_value": 85, "score": 2},
        {"min_value": 86, "max_value": 120, "score": 3},
        {"min_value": 121, "max_value": 155, "score": 4},
        {"min_value": 156, "max_value": None, "score": 5},
    ],
}
