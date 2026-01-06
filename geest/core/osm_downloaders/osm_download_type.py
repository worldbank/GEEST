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
