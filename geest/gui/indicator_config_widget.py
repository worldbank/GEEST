from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QButtonGroup
from qgis.core import QgsMessageLog, Qgis
from qgis.PyQt.QtCore import pyqtSignal
from .indicator_widget_factory import RadioButtonFactory


class IndicatorConfigWidget(QWidget):
    """
    Widget for configuring indicators based on a dictionary.
    """
    data_changed = pyqtSignal(dict)
    def __init__(self, attributes_dict: dict) -> None:
        super().__init__()
        self.attributes_dict = attributes_dict
        self.layout: QVBoxLayout = QVBoxLayout()
        self.button_group: QButtonGroup = QButtonGroup(self)

        try:
            self.create_radio_buttons(attributes_dict)
        except Exception as e:
            QgsMessageLog.logMessage(f"Error in create_radio_buttons: {e}", tag="Geest", level=Qgis.Critical)

        self.setLayout(self.layout)

    def create_radio_buttons(self, attributes_dict: dict) -> None:
        """
        Uses the factory to create radio buttons from attributes dictionary.
        """
        for key, value in attributes_dict.items():
            radio_button_widget = RadioButtonFactory.create_radio_button(
                key, value, attributes_dict)
            if radio_button_widget:
                self.button_group.addButton(radio_button_widget)
                self.layout.addWidget(radio_button_widget.get_container())
                radio_button_widget.data_changed.connect(self.update_attributes)

    def update_attributes(self, new_data: dict) -> None:
        """
        Updates the attributes dictionary with new data from radio buttons.
        """
        new_data["Analysis Mode"] = self.button_group.checkedButton().label_text
        self.attributes_dict.update(new_data)
        self.data_changed.emit(self.attributes_dict)
        QgsMessageLog.logMessage(
            f"Updated attributes dictionary: {self.attributes_dict}", "Geest", level=Qgis.Info)
