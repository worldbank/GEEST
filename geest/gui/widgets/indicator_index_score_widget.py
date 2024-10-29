from qgis.PyQt.QtWidgets import QLabel, QDoubleSpinBox
from .base_indicator_widget import BaseIndicatorWidget
from qgis.core import QgsMessageLog, Qgis


class IndexScoreRadioButton(BaseIndicatorWidget):
    """
    A specialized radio button with additional widgets for IndexScore.
    """

    def add_internal_widgets(self) -> None:
        """
        Adds internal widgets specific to IndexScore.
        """
        try:
            self.info_label: QLabel = QLabel(self.label_text)
            self.index_input: QDoubleSpinBox = QDoubleSpinBox()
            self.index_input.setRange(0, 100)
            self.layout.addWidget(self.info_label)
            self.layout.addWidget(self.index_input)
            self.index_input.setValue(self.attributes["default_index_score"])
            # Connect the valueChanged signal to update data
            self.index_input.valueChanged.connect(self.update_data)
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error in add_internal_widgets: {e}", "Geest", level=Qgis.Critical
            )

    def get_data(self) -> dict:
        """
        Return the data as a dictionary, updating attributes with current value.
        """
        if self.isChecked():
            self.attributes["default_index_score"] = self.index_input.value()
        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets based on the state of the radio button.
        """
        try:
            self.info_label.setEnabled(enabled)
            self.index_input.setEnabled(enabled)
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error in set_internal_widgets_enabled: {e}",
                "Geest",
                level=Qgis.Critical,
            )
