from qgis.core import QgsMessageLog, Qgis
from geest.gui.widgets import (
    BaseIndicatorWidget,
    IndexScoreRadioButton,
    DontUseRadioButton,
    MultiBufferDistancesWidget,
    SingleBufferDistanceWidget,
    PolylineWidget,
    PointLayerWidget,
    PolygonWidget,
    AcledCsvLayerWidget,
    SafetyPolygonWidget,
    SafetyRasterWidget,
    RasterReclassificationWidget,
)
from geest.core import setting


class RadioButtonFactory:
    """
    Factory class for creating radio buttons based on key-value pairs.
    """

    @staticmethod
    def create_radio_button(
        key: str, value: int, attributes: dict
    ) -> BaseIndicatorWidget:
        """
        Factory method to create a radio button based on key-value pairs.
        """
        verbose_mode = int(setting(key="verbose_mode", default=0))
        if verbose_mode:
            QgsMessageLog.logMessage(
                "Dialog widget factory called", tag="Geest", level=Qgis.Info
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
            if key == "indicator_required" and value == 0:
                return DontUseRadioButton(
                    label_text="do_not_use", attributes=attributes
                )
            if key == "use_default_index_score" and value == 1:
                return IndexScoreRadioButton(label_text=key, attributes=attributes)
            if key == "use_multi_buffer_point" and value == 1:
                return MultiBufferDistancesWidget(label_text=key, attributes=attributes)
            if key == "use_single_buffer_point" and value == 1:
                return SingleBufferDistanceWidget(label_text=key, attributes=attributes)
            if key == "use_poly_per_cell" and value == 1:
                return PolygonWidget(label_text=key, attributes=attributes)
            if key == "use_polyline_per_cell" and value == 1:
                return PolylineWidget(label_text=key, attributes=attributes)
            if key == "use_point_per_cell" and value == 1:
                return PointLayerWidget(label_text=key, attributes=attributes)
            if key == "use_csv_to_point_layer" and value == 1:
                return AcledCsvLayerWidget(label_text=key, attributes=attributes)
            if key == "use_classify_poly_into_classes" and value == 1:
                return SafetyPolygonWidget(label_text=key, attributes=attributes)
            if key == "use_nighttime_lights" and value == 1:
                return SafetyRasterWidget(label_text=key, attributes=attributes)
            if key == "use_environmental_hazards" and value == 1:
                return RasterReclassificationWidget(
                    label_text=key, attributes=attributes
                )
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
