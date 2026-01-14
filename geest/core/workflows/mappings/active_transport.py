# -*- coding: utf-8 -*-

"""
Active Transport OSM Classifications.

Highway and cycleway scoring for walkability/cycling infrastructure.

Following the ACLED pattern - simple dictionaries with scale-specific data.
"""

# OSM Highway Type Suitability for Walking/Cycling
# Same for all analysis scales
HIGHWAY_CLASSIFICATION = {
    # Low suitability - high-speed roads
    "motorway": 1,
    "trunk": 1,
    "motorway_link": 1,
    "trunk_link": 1,
    # Medium-low - major roads
    "primary": 2,
    "primary_link": 2,
    # Medium - secondary roads
    "secondary": 3,
    "secondary_link": 3,
    "unclassified": 3,
    "road": 3,
    "service": 3,
    "bridleway": 3,
    # High - minor roads and paths
    "tertiary": 4,
    "tertiary_link": 4,
    "cycleway": 4,
    "path": 4,
    # Very high - pedestrian/residential
    "residential": 5,
    "living_street": 5,
    "pedestrian": 5,
    "footway": 5,
    "steps": 5,
    # Low - tracks and specialized
    "track": 2,
    # Zero - unusable
    "bus_guideway": 0,
    "escape": 0,
    "raceway": 0,
    "construction": 0,
    "proposed": 0,
}

# OSM Cycleway Infrastructure Scoring
# National: All score 4 (uniform)
# Local: Dedicated infrastructure scores 5 (emphasis on quality)
CYCLEWAY_CLASSIFICATION = {
    "national": {
        "lane": 4,
        "shared_lane": 4,
        "share_busway": 4,
        "track": 4,
        "separate": 4,
        "crossing": 4,
        "shoulder": 4,
        "link": 4,
    },
    "local": {
        "lane": 5,  # Dedicated lane - higher in local
        "track": 5,  # Dedicated track - higher in local
        "separate": 5,  # Physically separated - higher in local
        "crossing": 5,  # Safe crossing - higher in local
        "shared_lane": 4,  # Shared - same as national
        "share_busway": 2,  # Shared with buses - lower in local
        "shoulder": 2,  # Just shoulder - lower in local
        "link": 3,  # Link/connection - slightly lower
    },
}
