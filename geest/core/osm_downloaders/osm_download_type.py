# *- coding: utf-8 -*-

"""📦 Osm Download Type module.

This module contains functionality for osm download type.
"""
from enum import Enum


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
