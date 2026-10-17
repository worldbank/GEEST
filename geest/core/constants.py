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

MAX_FEATURES_FOR_VECTOR = 100000
