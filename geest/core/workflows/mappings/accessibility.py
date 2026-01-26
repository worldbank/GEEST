# -*- coding: utf-8 -*-

"""
Accessibility Dimension Thresholds.

Provides distance thresholds for accessibility factors based on
GeoE3 Technical Specifications.

Following the ACLED pattern - simple dictionaries with scale-specific data.
"""

# Women's Travel Patterns
# Access to childcare, primary schools, grocery stores, pharmacies, green spaces
WOMENS_TRAVEL_PATTERNS = {
    "national": {
        "thresholds": [400, 800, 1200, 1500, 2000],
        "scores": [5, 4, 3, 2, 1, 0],
        "max_distance": 2000,
        "description": "National scale - broader catchment areas",
    },
    "local": {
        "thresholds": [300, 800, 1000, 1300, 1500],
        "scores": [5, 4, 3, 2, 1, 0],
        "max_distance": 1500,
        "description": "Local scale - tighter urban distances",
    },
}

# Public Transportation Stops
PUBLIC_TRANSPORT_ACCESS = {
    "national": {
        "thresholds": [250, 500, 750, 1000, 1500],
        "scores": [5, 4, 3, 2, 1, 0],
        "max_distance": 1500,
        "description": "National scale",
    },
    "local": {
        "thresholds": [250, 500, 750, 1000, 1250],
        "scores": [5, 4, 3, 2, 1, 0],
        "max_distance": 1250,
        "description": "Local scale - slightly tighter",
    },
}

# Healthcare Facilities
HEALTH_FACILITIES_ACCESS = {
    "national": {
        "thresholds": [2000, 4000, 6000, 8000, 10000],
        "scores": [5, 4, 3, 2, 1, 0],
        "max_distance": 10000,
        "description": "National scale - up to 10km",
    },
    "local": {
        "thresholds": [400, 800, 1250, 1650, 2500],
        "scores": [5, 4, 3, 2, 1, 0],
        "max_distance": 2500,
        "description": "Local scale - up to 2.5km (4x tighter)",
    },
}

# Higher Education and Training Centers
EDUCATION_FACILITIES_ACCESS = {
    "national": {
        "thresholds": [2000, 4000, 6000, 8000, 10000],
        "scores": [5, 4, 3, 2, 1, 0],
        "max_distance": 10000,
        "description": "National scale",
    },
    "local": {
        "thresholds": [350, 700, 1100, 1500, 2100],
        "scores": [5, 4, 3, 2, 1, 0],
        "max_distance": 2100,
        "description": "Local scale - ~5x tighter than national",
    },
}

# Banks and Financial Institutions
FINANCIAL_FACILITIES_ACCESS = {
    "national": {
        "thresholds": [500, 1000, 1500, 2000, 3000],
        "scores": [5, 4, 3, 2, 1, 0],
        "max_distance": 3000,
        "description": "National scale",
    },
    "local": {
        "thresholds": [400, 800, 1200, 2000, 2500],
        "scores": [5, 4, 3, 2, 1, 0],
        "max_distance": 2500,
        "description": "Local scale",
    },
}
