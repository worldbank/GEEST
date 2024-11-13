from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QButtonGroup
from qgis.core import Qgis
from qgis.PyQt.QtCore import pyqtSignal
from .configuration_widget_factory import ConfigurationWidgetFactory
from geest.core import JsonTreeItem
from geest.utilities import log_message


class FactorConfigurationWidget(QWidget):
    """
    Widget for configuring factors.

    The idea here is that you do the configuration of the factor and it is
    applied to all of the indicators that are part of the factor.

    It assumes that all indicators belonging to the factor have the same
    configuration options.
    """

    data_changed = pyqtSignal()

    def __init__(self, item: JsonTreeItem, guids: list) -> None:
        """
        Initialize the widget with the item and guids.
        :param item: Item containing the factor configuration.
        :param guids: List of guids for the indicators that the settings in the config will be applied to.
        """
        super().__init__()
        self.guids = guids  # List of guids for the indicators that the settings in the config will be applied to
        self.item = item
        # This returns a reference so any changes you make to attributes
        # will also update the indicator item
        attributes = item.getItemByGuid(guids[0]).attributes()
        self.attributes = attributes
        self.layout: QVBoxLayout = QVBoxLayout()
        self.button_group: QButtonGroup = QButtonGroup(self)

        try:
            self.create_radio_buttons(attributes)
        except Exception as e:
            log_message(
                f"Error in create_radio_buttons: {e}", tag="Geest", level=Qgis.Critical
            )

        self.setLayout(self.layout)

    def create_radio_buttons(self, attributes: dict) -> None:
        """
        Uses the factory to create radio buttons from attributes dictionary.
        """
        analysis_mode = attributes.get("analysis_mode", "")
        log_message(
            f"Creating radio buttons for analysis mode: {analysis_mode}",
            tag="Geest",
            level=Qgis.Info,
        )
        for key, value in attributes.items():
            if key.startswith("use_") or key == "indicator_required":
                log_message(
                    f"Creating radio button for key: {key} with value: {value}",
                    tag="Geest",
                    level=Qgis.Info,
                )
                # We pass a copy of the attributes dictionary to the widget factory
                # so that we can update the attributes as needed
                # The widget factory will update the attributes dictionary with new data
                radio_button_widget = ConfigurationWidgetFactory.create_radio_button(
                    key, value, attributes.copy()
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
        # snake_case_mode = (
        #    self.button_group.checkedButton().label_text.lower().replace(" ", "_")
        # )
        # new_data["analysis_mode"] = snake_case_mode

        # calculate the changes between new_data and self.attributes
        # so that we can apply them to every indicator in self.guids list
        changed_attributes = {
            key: new_data[key]
            for key in new_data
            if key in self.attributes and self.attributes[key] != new_data[key]
        }
        for guid in self.guids:
            indicator = self.item.getItemByGuid(guid)
            indicator.attributes().update(changed_attributes)

        self.data_changed.emit()
