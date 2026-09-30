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
