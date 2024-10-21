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
            if key == "Layer Required" and value == 0:
                return DontUseRadioButton(label_text="Don't Use", attributes=attributes)
            if key == "Use Default Index Score" and value == 1:
                return IndexScoreRadioButton(label_text=key, attributes=attributes)
            if key == "Use Multi Buffer Point" and value == 1:
                return MultiBufferDistancesWidget(label_text=key, attributes=attributes)
            if key == "Use Single Buffer Point" and value == 1:
                return SingleBufferDistanceWidget(label_text=key, attributes=attributes)
            if key == "Use Poly per Cell" and value == 1:
                return PolygonWidget(label_text=key, attributes=attributes)
            if key == "Use Polyline per Cell" and value == 1:
                return PolylineWidget(label_text=key, attributes=attributes)
            if key == "Use Point per Cell" and value == 1:
                return PointLayerWidget(label_text=key, attributes=attributes)
            if key == "Use CSV to Point Layer" and value == 1:
                return AcledCsvLayerWidget(label_text=key, attributes=attributes)
            if key == "Use Classify Poly into Classes" and value == 1:
                return SafetyPolygonWidget(label_text=key, attributes=attributes)
            if key == "Use Nighttime Lights" and value == 1:
                return SafetyRasterWidget(label_text=key, attributes=attributes)
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
