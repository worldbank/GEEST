# -*- coding: utf-8 -*-
# flake8: noqa
# isort: skip_file
# black: skip-file
"""📦 Configuration Widgets module.

This module contains functionality for configuration widgets.
"""
from .acled_csv_configuration_widget import AcledCsvConfigurationWidget
from .base_configuration_widget import BaseConfigurationWidget
from .classified_polygon_configuration_widget import (
    ClassifiedPolygonConfigurationWidget,
)
from .contextual_index_score_configuration_widget import (
    ContextualIndexScoreConfigurationWidget,
)
from .dont_use_configuration_widget import DontUseConfigurationWidget
from .feature_per_cell_configuration_widget import FeaturePerCellConfigurationWidget
from .osm_transport_configuration_widget import OsmTransportConfigurationWidget
from .index_score_configuration_widget import IndexScoreConfigurationWidget
from .index_score_with_ghsl_configuration_widget import IndexScoreWithGHSLConfigurationWidget
from .index_score_with_ookla_configuration_widget import IndexScoreWithOOKLAConfigurationWidget
from .multi_buffer_configuration_widget import MultiBufferConfigurationWidget
from .osm_transport_configuration_widget import OsmTransportConfigurationWidget
from .raster_reclassification_configuration_widget import (
    RasterReclassificationConfigurationWidget,
)
from .safety_polygon_configuration_widget import SafetyPolygonConfigurationWidget
from .safety_raster_configuration_widget import SafetyRasterConfigurationWidget
from .single_buffer_configuration_widget import SingleBufferConfigurationWidget
from .street_lights_configuration_widget import StreetLightsConfigurationWidget
