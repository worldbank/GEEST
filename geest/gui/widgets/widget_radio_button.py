from qgis.PyQt.QtWidgets import QLabel
from .base_indicator_widget import BaseIndicatorWidget
from qgis.core import QgsMessageLog, Qgis


class WidgetRadioButton(BaseIndicatorWidget):
    """
    A specialized radio button with additional widgets for Widget details.
    """
    def add_internal_widgets(self) -> None:
        try:
            self.widget_label: QLabel = QLabel("Widget Details:")
            self.layout.addWidget(self.widget_label)
        except Exception as e:
            QgsMessageLog.logMessage(f"Error in add_internal_widgets: {e}", "Geest")

    def get_data(self) -> dict:
        """
        Return the data as a dictionary.
        """
        return self.attributes
