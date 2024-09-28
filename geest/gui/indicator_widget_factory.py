from qgis.core import QgsMessageLog
from .widgets.indicator_index_score_widget import IndexScoreRadioButton
from .widgets.widget_radio_button import WidgetRadioButton


class RadioButtonFactory:
    """
    Factory class for creating radio buttons based on key-value pairs.
    """
    @staticmethod
    def create_radio_button(key: str, value: int):
        """
        Factory method to create a radio button based on key-value pairs.
        """
        try:
            if key == "UseIndexScore" and value == 1:
                return IndexScoreRadioButton("IndexScore")
            elif key == "UseWidget" and value == 1:
                return WidgetRadioButton("Widget")
            else:
                return None
        except Exception as e:
            QgsMessageLog.logMessage(f"Error in create_radio_button: {e}", "Geest")
            return None
