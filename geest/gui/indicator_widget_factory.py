from qgis.core import QgsMessageLog, Qgis
from .widgets.base_indicator_widget import BaseIndicatorWidget
from .widgets import IndexScoreRadioButton
from .widgets import DontUseRadioButton


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
