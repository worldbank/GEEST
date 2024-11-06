from qgis.core import QgsMessageLog, Qgis
from geest.gui.widgets.datasource_widgets import (
    BaseDataSourceWidget,
    AcledCsvLayerWidget,
    RasterDataSourceWidget,
    FixedValueDataSourceWidget,
    VectorDataSourceWidget,
    VectorAndFieldDataSourceWidget,
)

from geest.core import setting


class DataSourceWidgetFactory:
    """
    Factory class for creating data source widgets based on key-value pairs.
    """

    @staticmethod
    def create_widget(
        widget_key: str, value: int, attributes: dict
    ) -> BaseDataSourceWidget:
        """
        Factory method to create a datasource widget based on key-value pairs.
        """
        verbose_mode = int(setting(key="verbose_mode", default=0))
        if verbose_mode:
            QgsMessageLog.logMessage(
                "Datasource widget factory called", tag="Geest", level=Qgis.Info
            )
            QgsMessageLog.logMessage(
                "----------------------------", tag="Geest", level=Qgis.Info
            )
            QgsMessageLog.logMessage(f"Key: {key}", tag="Geest", level=Qgis.Info)
            QgsMessageLog.logMessage(f"Value: {value}", tag="Geest", level=Qgis.Info)
            QgsMessageLog.logMessage(
                "----------------------------", tag="Geest", level=Qgis.Info
            )

        try:
            # if widget_key == "indicator_required" and value == 0:
            #     return DontUseRadioButton(
            #         label_text="do_not_use", attributes=attributes
            #     )            self.distance_radio.setEnabled(enabled)
            if widget_key == "use_default_index_score" and value == 1:
                return FixedValueDataSourceWidget(
                    widget_key=widget_key, attributes=attributes
                )
            if widget_key == "use_multi_buffer_point" and value == 1:
                return VectorDataSourceWidget(
                    widget_key=widget_key, attributes=attributes
                )
            # if widget_key == "use_single_buffer_point" and value == 1:
            #     return SingleBufferDistanceWidget(label_text=key, attributes=attributes)
            # if widget_key == "use_poly_per_cell" and value == 1:
            #     return PolygonWidget(label_text=key, attributes=attributes)
            # if widget_key == "use_polyline_per_cell" and value == 1:
            #     return PolylineWidget(label_text=key, attributes=attributes)
            # if widget_key == "use_point_per_cell" and value == 1:
            #     return PointLayerWidget(label_text=key, attributes=attributes)
            if widget_key == "use_csv_to_point_layer" and value == 1:
                return AcledCsvLayerWidget(widget_key=widget_key, attributes=attributes)
            if widget_key == "use_classify_poly_into_classes" and value == 1:
                return VectorAndFieldDataSourceWidget(
                    widget_key=widget_key, attributes=attributes
                )
            # if widget_key == "use_nighttime_lights" and value == 1:
            #     return SafetyRasterWidget(label_text=key, attributes=attributes)
            if widget_key == "use_environmental_hazards" and value == 1:
                return RasterDataSourceWidget(
                    widget_key=widget_key, attributes=attributes
                )
            # if widget_key == "use_street_lights" and value == 1:
            #     return StreetLightsWidget(label_text=key, attributes=attributes)
            else:
                QgsMessageLog.logMessage(
                    f"Datasource Factory did not match any widgets",
                    tag="Geest",
                    level=Qgis.Critical,
                )
                return None
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error in datasource widget: {e}", tag="Geest", level=Qgis.Critical
            )
            return None
