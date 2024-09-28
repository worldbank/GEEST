from qgis.PyQt.QtWidgets import QLabel, QDoubleSpinBox
from .base_indicator_widget import BaseIndicatorWidget
from qgis.core import QgsMessageLog, Qgis


class IndexScoreRadioButton(BaseIndicatorWidget):
    """
    A specialized radio button with additional widgets for IndexScore.
    """
    def add_internal_widgets(self) -> None:
        try:
            self.info_label: QLabel = QLabel(self.label_text)
            self.index_input: QDoubleSpinBox = QDoubleSpinBox()
            self.layout.addWidget(self.info_label)
            self.layout.addWidget(self.index_input)
            self.index_input.valueChanged.connect(self.update_data)
        except Exception as e:
            QgsMessageLog.logMessage(f"Error in add_internal_widgets: {e}", "Geest")

    def get_data(self) -> dict:
        """
        Return the data as a dictionary.
        """
        self.attributes["IndexScore"] = f"{self.index_input.value()}"
        return {self.attributes}
