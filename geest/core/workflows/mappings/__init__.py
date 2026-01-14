# -*- coding: utf-8 -*-

"""
Scale Mappings Module.

Provides centralized, scale-specific configurations for WEE indicator analysis.

Usage:
    from geest.core.workflows.mappings import WOMENS_TRAVEL_PATTERNS, MAPPING_REGISTRY

    # Direct import (for single-purpose workflows like safety/acled):
    config = WOMENS_TRAVEL_PATTERNS.get(analysis_scale, WOMENS_TRAVEL_PATTERNS["national"])
    thresholds = config["thresholds"]  # [400, 800, 1200, 1500, 2000] for national

    # Lookup by factor ID (for multi-buffer workflows handling multiple factors):
    factor_id = item.attributes.get("id")  # "women_s_travel_patterns"
    mapping = MAPPING_REGISTRY.get(factor_id)
    config = mapping.get(analysis_scale, mapping["national"])
    thresholds = config["thresholds"]
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

# Registry for lookup by factor ID (matches model.json factor IDs)
MAPPING_REGISTRY = {
    # Accessibility factors (multi-buffer workflows use factor ID for lookup)
    "women_s_travel_patterns": WOMENS_TRAVEL_PATTERNS,
    "access_to_public_transport": PUBLIC_TRANSPORT_ACCESS,
    "access_to_health_facilities": HEALTH_FACILITIES_ACCESS,
    "access_to_education_and_training_facilities": EDUCATION_FACILITIES_ACCESS,
    "access_to_financial_facilities": FINANCIAL_FACILITIES_ACCESS,
    "water_sanitation": WATER_SANITATION_ACCESS,
    # Note: Active transport workflows import CYCLEWAY_CLASSIFICATION/HIGHWAY_CLASSIFICATION directly
    # Note: Safety workflows import STREETLIGHTS_SAFETY/NIGHTTIME_LIGHTS_SAFETY directly
    # Note: ACLED uses event_scores/buffer_distances directly
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
