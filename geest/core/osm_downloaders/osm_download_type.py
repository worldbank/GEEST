# *- coding: utf-8 -*-

"""📦 Osm Download Type module.

This module contains functionality for osm download type.
"""

from enum import Enum
from typing import Optional


class OSMDownloadType(Enum):
    """🎯 O S M Download Type."""

    ACTIVE_TRANSPORT = "active_transport"
    PUBLIC_TRANSPORT = "public_transport"
    EDUCATION = "education"
    FINANCIAL = "financial"
    KINDERGARTEN = "kindergarten"
    PRIMARY_SCHOOL = "primary_school"
    PHARMACY = "pharmacy"
    GROCERY = "grocery"
    GREEN_SPACE = "green_space"
    HEALTH_FACILITY = "health_facility"
    WATER_POINT = "water_point"


# Shared with geest.core.download_all_resources, which uses these same
# labels when it downloads a type on an indicator's behalf.
OSM_DOWNLOAD_TOOLTIPS = {
    OSMDownloadType.PUBLIC_TRANSPORT: "Download public transport data from OpenStreetMap",
    OSMDownloadType.EDUCATION: "Download education facilities from OpenStreetMap",
    OSMDownloadType.FINANCIAL: "Download financial services from OpenStreetMap",
    OSMDownloadType.KINDERGARTEN: "Download kindergarten and childcare facilities from OpenStreetMap",
    OSMDownloadType.PRIMARY_SCHOOL: "Download primary schools from OpenStreetMap",
    OSMDownloadType.PHARMACY: "Download pharmacies from OpenStreetMap",
    OSMDownloadType.GROCERY: "Download grocery stores and markets from OpenStreetMap",
    OSMDownloadType.GREEN_SPACE: "Download green spaces and parks from OpenStreetMap",
    OSMDownloadType.HEALTH_FACILITY: "Download hospitals and clinics from OpenStreetMap",
    OSMDownloadType.WATER_POINT: "Download water points and water infrastructure from OpenStreetMap",
}


def resolve_point_osm_download_type(item_id: str, item_name: str, indicator_text: str) -> Optional[OSMDownloadType]:
    """Decide which OSM dataset (if any) a buffer-point indicator should auto-download.

    Single source of truth for the keyword-matching eligibility rule used
    by both VectorDataSourceWidget's in-dialog "Download from OSM" button
    and geest.core.download_all_resources' bulk download - previously
    duplicated inline in the widget, which risked the two drifting apart.
    Only meaningful for indicators using use_multi_buffer_point or
    use_single_buffer_point; callers are responsible for checking that
    first, since plenty of other indicator ids/names use these same words
    in an unrelated sense (e.g. a non-OSM "education" indicator).

    Order matters: the first matching category wins, exactly as the
    original if/elif chain did (e.g. "primary school" matches EDUCATION
    before PRIMARY_SCHOOL ever gets a chance, since "school" alone already
    satisfies the EDUCATION check).

    Args:
        item_id: The indicator's lowercased id.
        item_name: The indicator's lowercased name.
        indicator_text: The indicator's lowercased display/indicator text.

    Returns:
        The matching OSMDownloadType, or None if nothing matches.
    """
    haystacks = (item_id, item_name, indicator_text)

    def any_contains(*keywords: str) -> bool:
        return any(keyword in text for text in haystacks for keyword in keywords)

    if any_contains("public", "transport"):
        return OSMDownloadType.PUBLIC_TRANSPORT
    if any_contains("education", "school", "training"):
        return OSMDownloadType.EDUCATION
    if any_contains("financial", "bank", "finance"):
        return OSMDownloadType.FINANCIAL
    if any_contains("kindergarten", "childcare"):
        return OSMDownloadType.KINDERGARTEN
    if any_contains("primary", "school"):
        return OSMDownloadType.PRIMARY_SCHOOL
    if any_contains("pharmacy", "pharmacies"):
        return OSMDownloadType.PHARMACY
    if any_contains("grocery", "groceries", "market"):
        return OSMDownloadType.GROCERY
    if any_contains("green", "park", "garden"):
        return OSMDownloadType.GREEN_SPACE
    if any_contains("hospital", "clinic", "health"):
        return OSMDownloadType.HEALTH_FACILITY
    if any_contains("water"):
        return OSMDownloadType.WATER_POINT
    return None
