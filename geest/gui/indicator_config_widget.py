from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QButtonGroup
from qgis.core import QgsMessageLog, Qgis
from qgis.PyQt.QtCore import pyqtSignal
from .indicator_widget_factory import RadioButtonFactory


class IndicatorConfigWidget(QWidget):
    """
    Widget for configuring indicators based on a dictionary.
    """

    data_changed = pyqtSignal()

    def __init__(self, attributes: dict) -> None:
        super().__init__()
        # This is a reference to the attributes dictionary
        # So any changes made will propogate to the JSONTreeItem
        self.attributes = attributes
        self.layout: QVBoxLayout = QVBoxLayout()
        self.button_group: QButtonGroup = QButtonGroup(self)

        try:
            self.create_radio_buttons(attributes)
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error in create_radio_buttons: {e}", tag="Geest", level=Qgis.Critical
            )

        self.setLayout(self.layout)

    def create_radio_buttons(self, attributes: dict) -> None:
        """
        Uses the factory to create radio buttons from attributes dictionary.
        """
        # make a deep copy of the dictionary in case it changes while we
        # are using it
        attributes = attributes.copy()
        analysis_mode = attributes.get("analysis_mode", "")

        for key, value in attributes.items():
            radio_button_widget = RadioButtonFactory.create_radio_button(
                key, value, attributes
            )
            if radio_button_widget:
                if key == analysis_mode:
                    radio_button_widget.setChecked(True)
                # Special case for "do_not_use" radio button
                if (
                    key == "indicator_required"
                    and value == 0
                    and analysis_mode == "do_not_use"
                ):
                    radio_button_widget.setChecked(True)
                self.button_group.addButton(radio_button_widget)
                self.layout.addWidget(radio_button_widget.get_container())
                radio_button_widget.data_changed.connect(self.update_attributes)

    def update_attributes(self, new_data: dict) -> None:
        """
        Updates the attributes dictionary with new data from radio buttons.
        """
        # In the ctor of the widget factor we humanise the name
        # now we roll it back to the snake case version so it matches keys
        # in the JSON data model
        snake_case_mode = (
            self.button_group.checkedButton().label_text.lower().replace(" ", "_")
        )
        new_data["analysis_mode"] = snake_case_mode
        self.attributes.update(new_data)
        self.data_changed.emit()
        QgsMessageLog.logMessage(
            f"Updated attributes dictionary: {self.attributes}",
            "Geest",
            level=Qgis.Info,
        )
