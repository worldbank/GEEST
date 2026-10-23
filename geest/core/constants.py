# coding=utf-8
"""This module contains constants."""

__copyright__ = "Copyright 2022, Tim Sutton"
__license__ = "GPL version 3"
__email__ = "tim@kartoza.com"
__revision__ = "$Format:%H$"

# -----------------------------------------------------------
# Copyright (C) 2022 Tim Sutton
# -----------------------------------------------------------
# Licensed under the terms of GNU GPL 3
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# ---------------------------------------------------------------------

# Scope in QSettings
APPLICATION_NAME = "GeoE3"
GDAL_OUTPUT_DATA_TYPE = 6  # Float32

# The five discrete score classes every result map/raster uses (see
# resources/qml/indicator.qml, resources/qml/factor.qml), 0-1 Very Low
# Enablement through 4-5 Highly Enabling. The QML's DISCRETE classifier
# buckets by upper bound, so a raw score of 0 falls in the same "<=1"
# bucket - and colour - as 1.
SCORE_LEGEND_COLORS = {
    0: "#d7191c",
    1: "#d7191c",
    2: "#fdae61",
    3: "#ffffbf",
    4: "#bce1b8",
    5: "#2c7bb6",
}

# GeoE3 x Population bivariate score (1-15): enablement level x relative
# population density. Matches resources/qml/geoe3_by_population_score.qml's
# PalettedRasterRenderer exactly - each value is an EXACT class, not a
# range (unlike SCORE_LEGEND_COLORS's 0-5 DISCRETE scheme).
GEOE3_BY_POPULATION_COLORS = {
    1: "#b11419",
    2: "#d7191c",
    3: "#f14247",
    4: "#d68f47",
    5: "#fdae61",
    6: "#ffc688",
    7: "#e0e09f",
    8: "#ffffb4",
    9: "#ffffee",
    10: "#93bd9b",
    11: "#bce1b8",
    12: "#dbfbd5",
    13: "#1d5c8d",
    14: "#2c7bb6",
    15: "#4ab8e0",
}

# Space2Stats defaults
DEFAULT_S2S_NTL_FIELD = "sum_viirs_ntl_2024"
DEFAULT_S2S_POPULATION_FIELD = "sum_pop_2024"
DEFAULT_S2S_ENV_HAZARD_FIELDS = {
    "fire": "fires_density_mean",
    "flood": "pop_flood_pct",
    "landslide": "landslide_susceptibility_mean_2023",
    "cyclone": "cy_frequency_mean",
    "drought": "drought_spei_1_5_rp100_mean",
}

# World Bank Data Catalog (DDH) source URLs for environmental hazard layers.
ENV_HAZARD_SOURCE_URLS = {
    "fire": "https://datacatalog.worldbank.org/int/search/dataset/0067117/active_fires_density_20032022",
    "flood": "https://datacatalog.worldbank.org/int/search/dataset/0067118/flood_hazard_100_year_return_period",
    "landslide": "https://datacatalog.worldbank.org/int/search/dataset/0067119/landslide_susceptibility",
    "cyclone": "https://datacatalog.worldbank.org/int/search/dataset/0067120/tropical_cyclone_frequency",
    "drought": "https://datacatalog.worldbank.org/int/search/dataset/0067121/global_drought_hazard_based_on_spei",
}

# Human-readable dataset names for environmental hazard source links.
ENV_HAZARD_SOURCE_LABELS = {
    "fire": "Active Fires Density (2003-2022)",
    "flood": "Flood Hazard (100-Year Return Period)",
    "landslide": "Landslide Susceptibility",
    "cyclone": "Tropical Cyclone Frequency",
    "drought": "Global Drought Hazard (based on SPEI)",
}

# Direct, no-login World Bank Data Catalog (DDH) file URLs for each hazard,
# verified reachable via plain HTTPS GET (no auth, no Range-request
# dependency). Downloaded in full via QgsNetworkAccessManager, same pattern
# as NTL_VNL_SOURCE_URL_TEMPLATE, then cropped locally to the study area.
# The literal "(" / ")" in the landslide filename are percent-encoded since
# QUrl's tolerant parsing is not guaranteed across Qt versions.
ENV_HAZARD_DOWNLOAD_URLS = {
    "fire": "https://datacatalogfiles.worldbank.org/ddh-published/0067117/DR0096159/fires_density_total.tif",
    "flood": "https://datacatalogfiles.worldbank.org/ddh-published/0067118/DR0096180/fl_hazard_100_yrp.tif",
    "landslide": (
        "https://datacatalogfiles.worldbank.org/ddh-published/0067119/DR0096160/"
        "global-landslide-susceptibility-map-2-27-23_%281%29.tif"
    ),
    "cyclone": "https://datacatalogfiles.worldbank.org/ddh-published/0067120/DR0096161/cy_frequency.tif",
    "drought": (
        "https://datacatalogfiles.worldbank.org/ddh-published/0067121/DR0096162/"
        "global-drought-spei-1.5-return-period-100-years.tif"
    ),
}

# Approximate source file sizes in MB, shown to the user before downloading.
# Drought is a ~1 GB global raster (much larger than the others) so the
# button warns about it up front rather than surprising the user mid-download.
ENV_HAZARD_DOWNLOAD_SIZE_MB = {
    "fire": 4,
    "flood": 50,
    "landslide": 32,
    "cyclone": 3,
    "drought": 1000,
}

# Annual VIIRS nighttime lights composite (OpenGeoHub / Hengl, CC-BY 4.0),
# a public no-login mirror of the EOG VNL V2 "average_masked" radiance
# product on Zenodo. One global GeoTIFF per year (~60 MB), downloaded in
# full via QgsNetworkAccessManager's blocking GET (same pattern as
# S2SClient) rather than GDAL's /vsicurl/ driver - some network/proxy
# environments block the HTTP Range requests /vsicurl/ needs to read a
# Cloud-Optimized GeoTIFF remotely, so a plain synchronous download is more
# portable even though it means fetching the whole file.
# Verified empirically (gdallocationinfo) that pixel values are already in
# the original EOG radiance-like units - no rescale needed before feeding
# the fixed NOAA threshold table in safety_raster_workflow.py.
NTL_VNL_DATASET_PAGE_URL = "https://zenodo.org/records/17294744"
NTL_VNL_SOURCE_LABEL = "Annual VIIRS Nighttime Lights (OpenGeoHub, 2000-2024)"
NTL_VNL_SOURCE_URL_TEMPLATE = (
    "https://zenodo.org/records/17294744/files/"
    "nightlights.average_viirs.v21_m_500m_s_{year}0101_{year}1231_go_epsg4326_v20250904.tif"
)
NTL_VNL_LATEST_YEAR = 2024
NTL_VNL_EARLIEST_YEAR = 2000

# Education proxy fields from S2S urbanization_ghssmod dataset.
# NOTE: ghs_21_pop (suburban) is intentionally excluded by design.
DEFAULT_S2S_EDUCATION_URBANIZATION_FIELDS = [
    "ghs_11_pop",
    "ghs_12_pop",
    "ghs_13_pop",
    "ghs_22_pop",
    "ghs_23_pop",
    "ghs_30_pop",
    "ghs_total_pop",
]

# Urban/rural population-share measures selectable for the Education indicator.
# The urban/rural breakdown is carried by the S2S population layer, not a
# separate education dataset.
DEFAULT_S2S_URBAN_RURAL_MEASURES = {
    "urban": "Urban population share",
    "rural": "Rural population share",
}

MAX_FEATURES_FOR_VECTOR = 100000
