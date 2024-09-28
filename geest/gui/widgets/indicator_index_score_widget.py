from qgis.PyQt.QtWidgets import QLabel, QLineEdit
from .base_indicator_widget import BaseIndicatorWidget
from qgis.core import QgsMessageLog


class IndexScoreRadioButton(BaseIndicatorWidget):
    """
    A specialized radio button with additional widgets for IndexScore.
    """
    def add_internal_widgets(self) -> None:
        try:
            self.info_label: QLabel = QLabel("Index:")
            self.index_input: QLineEdit = QLineEdit()
            self.layout.addWidget(self.info_label)
            self.layout.addWidget(self.index_input)
            self.index_input.textChanged.connect(self.update_data)
        except Exception as e:
            QgsMessageLog.logMessage(f"Error in add_internal_widgets: {e}", "Geest")

    def get_data(self) -> dict:
        """
        Return the data as a dictionary.
        """
        return {"IndexScore": self.index_input.text()}
