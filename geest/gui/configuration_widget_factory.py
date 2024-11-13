from qgis.core import Qgis
from geest.gui.widgets.configuration_widgets import (
    BaseConfigurationWidget,
    DontUseConfigurationWidget,
    AcledCsvConfigurationWidget,
    IndexScoreConfigurationWidget,
    MultiBufferConfigurationWidget,
    SingleBufferConfigurationWidget,
    FeaturePerCellConfigurationWidget,
    SafetyPolygonConfigurationWidget,
    StreetLightsConfigurationWidget,
    RasterReclassificationConfigurationWidget,
    SafetyRasterConfigurationWidget,
)
from geest.core import setting
from geest.utilities import log_message


class ConfigurationWidgetFactory:
    """
    Factory class for creating radio buttons based on key-value pairs.

    Unlike the combined widget factory, this factory is specifically for
    creating configuration widgets and does not include data source selection.

    The factory is used by the FactorAggregationDialog to create radio buttons
    based on the attributes dictionary.
    """

    @staticmethod
    def create_radio_button(
        key: str, value: int, attributes: dict
    ) -> BaseConfigurationWidget:
        """
        Factory method to create a radio button based on key-value pairs.
        """
        verbose_mode = int(setting(key="verbose_mode", default=0))
        if verbose_mode:

            log_message("----------------------------", tag="Geest", level=Qgis.Info)
            log_message(f"Key: {key}", tag="Geest", level=Qgis.Info)
            log_message(f"Value: {value}", tag="Geest", level=Qgis.Info)
            log_message("----------------------------", tag="Geest", level=Qgis.Info)

        try:
            if key == "indicator_required" and value == 0:
                return DontUseConfigurationWidget(
                    analysis_mode="do_not_use", attributes=attributes
                )
            if key == "use_default_index_score" and value == 1:
                return IndexScoreConfigurationWidget(
                    analysis_mode=key, attributes=attributes
                )
            if key == "use_multi_buffer_point" and value == 1:
                return MultiBufferConfigurationWidget(
                    analysis_mode=key, attributes=attributes
                )
            if key == "use_single_buffer_point" and value == 1:
                return SingleBufferConfigurationWidget(
                    analysis_mode=key, attributes=attributes
                )
            # ------------------------------------------------
            # These three all use the same configuration widgets
            # but will have different datasource widgets generated as appropriate
            if key == "use_poly_per_cell" and value == 1:  # poly = polygon
                return FeaturePerCellConfigurationWidget(
                    analysis_mode=key, attributes=attributes
                )
            if key == "use_polyline_per_cell" and value == 1:
                return FeaturePerCellConfigurationWidget(
                    analysis_mode=key, attributes=attributes
                )
            if key == "use_point_per_cell" and value == 1:
                return FeaturePerCellConfigurationWidget(
                    analysis_mode=key, attributes=attributes
                )
            if key == "use_csv_to_point_layer" and value == 1:
                return AcledCsvConfigurationWidget(
                    analysis_mode=key, attributes=attributes
                )
            # ------------------------------------------------
            if key == "use_classify_poly_into_classes" and value == 1:
                return SafetyPolygonConfigurationWidget(
                    analysis_mode=key, attributes=attributes
                )
            if key == "use_nighttime_lights" and value == 1:
                return SafetyRasterConfigurationWidget(
                    analysis_mode=key, attributes=attributes
                )
            if key == "use_environmental_hazards" and value == 1:
                return RasterReclassificationConfigurationWidget(
                    analysis_mode=key, attributes=attributes
                )
            if key == "use_street_lights" and value == 1:
                return StreetLightsConfigurationWidget(
                    analysis_mode=key, attributes=attributes
                )
            else:
                log_message(
                    f"Factory did not match any widgets for key: {key}",
                    tag="Geest",
                    level=Qgis.Critical,
                )
                return None
        except Exception as e:
            log_message(f"Error in create_radio_button: {e}", "Geest")
            import traceback

            log_message(traceback.format_exc(), "Geest")
            return None
