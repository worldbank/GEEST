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
    "regional": {
        "buffer_distance": 1500,
        "scoring_method": "percentage_intersection",
        "percentage_scores": {
            0: 0,  # 0% (no intersection)
            6: 1,  # 0.01-6%
            12: 2,  # 6.01-12%
            18: 3,  # 12.01-18%
            24: 4,  # 18.01-24%
            100: 5,  # 24.01-100%
        },
        "description": "Regional scale - percentage-based scoring with 1.5km buffer",
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
    "regional": {
        "buffer_distance": 1000,
        "scoring_method": "percentage_intersection",
        "percentage_scores": {
            0: 0,  # 0% (no intersection)
            6: 1,  # 0.01-6%
            12: 2,  # 6.01-12%
            18: 3,  # 12.01-18%
            24: 4,  # 18.01-24%
            100: 5,  # 24.01-100%
        },
        "description": "Regional scale - percentage-based scoring with 1km buffer",
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
    "regional": {
        "buffer_distance": 6000,
        "scoring_method": "percentage_intersection",
        "percentage_scores": {
            0: 0,  # 0% (no intersection)
            20: 1,  # 0.01-20%
            40: 2,  # 20.01-40%
            60: 3,  # 40.01-60%
            80: 4,  # 60.01-80%
            100: 5,  # 80.01-100%
        },
        "description": "Regional scale - percentage-based scoring with 6km buffer",
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
    "regional": {
        "buffer_distance": 3000,
        "scoring_method": "percentage_intersection",
        "percentage_scores": {
            0: 0,  # 0% (no intersection)
            16: 1,  # 0.01-16%
            32: 2,  # 16.01-32%
            48: 3,  # 32.01-48%
            64: 4,  # 48.01-64%
            100: 5,  # 64.01-100%
        },
        "description": "Regional scale - percentage-based scoring with 3km buffer",
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
    "regional": {
        "buffer_distance": 2500,
        "scoring_method": "percentage_intersection",
        "percentage_scores": {
            0: 0,  # 0% (no intersection)
            10: 1,  # 0.01-10%
            20: 2,  # 10.01-20%
            30: 3,  # 20.01-30%
            40: 4,  # 30.01-40%
            100: 5,  # 40.01-100%
        },
        "description": "Regional scale - percentage-based scoring with 2.5km buffer",
    },
}
