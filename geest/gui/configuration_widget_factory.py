from qgis.core import QgsMessageLog, Qgis
from geest.gui.widgets.configuration_widgets import (
    BaseConfigurationWidget,
    DontUseConfigurationWidget,
    AcledCsvConfigurationWidget,
    IndexScoreConfigurationWidget,
    MultiBufferConfigurationWidget,
    SingleBufferConfigurationWidget,
    FeaturePerCellConfigurationWidget,
)
from geest.core import setting


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
        QgsMessageLog.logMessage(
            "Configuration widget factory called", tag="Geest", level=Qgis.Info
        )
        verbose_mode = int(setting(key="verbose_mode", default=0))
        if verbose_mode:

            QgsMessageLog.logMessage(
                "----------------------------", tag="Geest", level=Qgis.Info
            )
            QgsMessageLog.logMessage(f"Key: {key}", tag="Geest", level=Qgis.Info)
            QgsMessageLog.logMessage(f"Value: {value}", tag="Geest", level=Qgis.Info)
            QgsMessageLog.logMessage(
                "----------------------------", tag="Geest", level=Qgis.Info
            )

        try:
            if key == "indicator_required" and value == 0:
                return DontUseConfigurationWidget(
                    label_text="do_not_use", attributes=attributes
                )
            if key == "use_default_index_score" and value == 1:
                return IndexScoreConfigurationWidget(
                    label_text=key, attributes=attributes
                )
            if key == "use_multi_buffer_point" and value == 1:
                return MultiBufferConfigurationWidget(
                    label_text=key, attributes=attributes
                )
            if key == "use_single_buffer_point" and value == 1:
                return SingleBufferConfigurationWidget(
                    label_text=key, attributes=attributes
                )
            # ------------------------------------------------
            # These three all use the same configuration widgets
            # but will have different datasource widgets generated as appropriate
            if key == "use_poly_per_cell" and value == 1:  # poly = polygon
                return FeaturePerCellConfigurationWidget(
                    label_text=key, attributes=attributes
                )
            if key == "use_polyline_per_cell" and value == 1:
                return FeaturePerCellConfigurationWidget(
                    label_text=key, attributes=attributes
                )
            if key == "use_point_per_cell" and value == 1:
                return FeaturePerCellConfigurationWidget(
                    label_text=key, attributes=attributes
                )
            if key == "use_csv_to_point_layer" and value == 1:
                return AcledCsvConfigurationWidget(
                    label_text=key, attributes=attributes
                )
            # ------------------------------------------------
            # if key == "use_classify_poly_into_classes" and value == 1:
            #     return SafetyPolygonWidget(label_text=key, attributes=attributes)
            # if key == "use_nighttime_lights" and value == 1:
            #     return SafetyRasterWidget(label_text=key, attributes=attributes)
            # if key == "use_environmental_hazards" and value == 1:
            #     return RasterReclassificationWidget(
            #         label_text=key, attributes=attributes
            #     )
            # if key == "use_street_lights" and value == 1:
            #     return StreetLightsWidget(label_text=key, attributes=attributes)
            else:
                QgsMessageLog.logMessage(
                    f"Factory did not match any widgets",
                    tag="Geest",
                    level=Qgis.Critical,
                )
                return None
        except Exception as e:
            QgsMessageLog.logMessage(f"Error in create_radio_button: {e}", "Geest")
            return None
