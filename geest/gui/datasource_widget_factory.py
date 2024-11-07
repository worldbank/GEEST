from qgis.core import QgsMessageLog, Qgis
from geest.gui.widgets.datasource_widgets import (
    BaseDataSourceWidget,
    AcledCsvDataSourceWidget,
    CsvDataSourceWidget,
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
        QgsMessageLog.logMessage(
            f"Datasource widget factory called with key {widget_key}",
            tag="Geest",
            level=Qgis.Info,
        )
        verbose_mode = int(setting(key="verbose_mode", default=0))

        if verbose_mode:

            QgsMessageLog.logMessage(
                "----------------------------", tag="Geest", level=Qgis.Info
            )
            QgsMessageLog.logMessage(f"Key: {widget_key}", tag="Geest", level=Qgis.Info)
            QgsMessageLog.logMessage(f"Value: {value}", tag="Geest", level=Qgis.Info)
            QgsMessageLog.logMessage(
                "----------------------------", tag="Geest", level=Qgis.Info
            )

        try:
            # remove "use_" from start of widget key for passing to the datasource widget where needed
            cleaned_key = widget_key[4:]
            if widget_key == "indicator_required" and value == 0:
                return None
            if widget_key == "use_default_index_score" and value == 1:
                return FixedValueDataSourceWidget(
                    widget_key=widget_key, attributes=attributes
                )
            if widget_key == "use_multi_buffer_point" and value == 1:
                return VectorDataSourceWidget(
                    widget_key=cleaned_key, attributes=attributes
                )
            if widget_key == "use_single_buffer_point" and value == 1:
                return VectorDataSourceWidget(
                    widget_key=cleaned_key, attributes=attributes
                )
            if widget_key == "use_poly_per_cell" and value == 1:
                return VectorDataSourceWidget(
                    widget_key=cleaned_key, attributes=attributes
                )
            if widget_key == "use_polyline_per_cell" and value == 1:
                return VectorDataSourceWidget(
                    widget_key=cleaned_key, attributes=attributes
                )
            if widget_key == "use_point_per_cell" and value == 1:
                return VectorDataSourceWidget(
                    widget_key=cleaned_key, attributes=attributes
                )
            if widget_key == "use_csv_point_per_cell" and value == 1:
                return CsvDataSourceWidget(widget_key=widget_key, attributes=attributes)
            if widget_key == "use_csv_to_point_layer" and value == 1:
                return AcledCsvDataSourceWidget(
                    widget_key=widget_key, attributes=attributes
                )
            if widget_key == "use_classify_poly_into_classes" and value == 1:
                return VectorAndFieldDataSourceWidget(
                    widget_key=cleaned_key, attributes=attributes
                )
            if widget_key == "use_nighttime_lights" and value == 1:
                return RasterDataSourceWidget(
                    widget_key=widget_key, attributes=attributes
                )
            if widget_key == "use_environmental_hazards" and value == 1:
                return RasterDataSourceWidget(
                    widget_key=widget_key, attributes=attributes
                )
            if widget_key == "use_street_lights" and value == 1:
                return RasterDataSourceWidget(
                    widget_key=widget_key, attributes=attributes
                )
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
            import traceback

            QgsMessageLog.logMessage(
                traceback.format_exc(), tag="Geest", level=Qgis.Critical
            )
            return None
