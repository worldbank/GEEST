# -*- coding: utf-8 -*-

"""
Scale Mappings Module.

Provides centralized, scale-specific configurations for WEE indicator analysis.
Following the ACLED pattern - simple dictionaries with scale-specific data.

Usage:
    from geest.core.workflows.mappings import WOMENS_TRAVEL_PATTERNS

    # Get thresholds for specific scale
    config = WOMENS_TRAVEL_PATTERNS.get(analysis_scale, WOMENS_TRAVEL_PATTERNS["national"])
    thresholds = config["thresholds"]  # [400, 800, 1200, 1500, 2000] for national

    # Or lookup by mapping_id
    mapping = MAPPING_REGISTRY.get("womens_travel_patterns")
    config = mapping.get(analysis_scale, mapping["national"])
"""

# Accessibility mappings
from .accessibility import (
    WOMENS_TRAVEL_PATTERNS,
    PUBLIC_TRANSPORT_ACCESS,
    HEALTH_FACILITIES_ACCESS,
    EDUCATION_FACILITIES_ACCESS,
    FINANCIAL_FACILITIES_ACCESS,
    WATER_SANITATION_ACCESS,
)

# Safety mappings
from .safety import STREETLIGHTS_SAFETY, NIGHTTIME_LIGHTS_SAFETY

# ACLED mappings
from .acled import event_scores, buffer_distances

# Active transport mappings
from .active_transport import HIGHWAY_CLASSIFICATION, CYCLEWAY_CLASSIFICATION

# Registry for lookup by mapping_id
MAPPING_REGISTRY = {
    # Accessibility factors
    "womens_travel_patterns": WOMENS_TRAVEL_PATTERNS,
    "public_transport_access": PUBLIC_TRANSPORT_ACCESS,
    "health_facilities_access": HEALTH_FACILITIES_ACCESS,
    "education_facilities_access": EDUCATION_FACILITIES_ACCESS,
    "financial_facilities_access": FINANCIAL_FACILITIES_ACCESS,
    "water_sanitation_access": WATER_SANITATION_ACCESS,
    # Safety factors
    "streetlights_safety": STREETLIGHTS_SAFETY,
    "nighttime_lights_safety": NIGHTTIME_LIGHTS_SAFETY,
    # Active transport
    "highway_classification": HIGHWAY_CLASSIFICATION,
    "cycleway_classification": CYCLEWAY_CLASSIFICATION,
}


def get_mapping(mapping_id: str):
    """
    Get mapping by ID.

    Args:
        mapping_id: The mapping identifier

    Returns:
        Mapping dictionary or None if not found
    """
    return MAPPING_REGISTRY.get(mapping_id)


__all__ = [
    # Accessibility
    "WOMENS_TRAVEL_PATTERNS",
    "PUBLIC_TRANSPORT_ACCESS",
    "HEALTH_FACILITIES_ACCESS",
    "EDUCATION_FACILITIES_ACCESS",
    "FINANCIAL_FACILITIES_ACCESS",
    "WATER_SANITATION_ACCESS",
    # Safety
    "STREETLIGHTS_SAFETY",
    "NIGHTTIME_LIGHTS_SAFETY",
    # ACLED
    "event_scores",
    "buffer_distances",
    # Active Transport
    "HIGHWAY_CLASSIFICATION",
    "CYCLEWAY_CLASSIFICATION",
    # Registry
    "MAPPING_REGISTRY",
    "get_mapping",
]
