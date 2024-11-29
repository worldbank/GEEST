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

    selection_changed = pyqtSignal()  # New signal for selection changes

    def __init__(self, item: JsonTreeItem, guids: list) -> None:
        """
        Initialize the widget with the item and guids.
        :param item: Item containing the factor configuration.
        :param guids: List of guids for the indicators that the settings in the config will be applied to.
        """
        super().__init__()
        log_message(
            f"Creating FactorConfigurationWidget for guids: {guids}",
            tag="Geest",
            level=Qgis.Info,
        )
        self.guids = guids  # List of guids for the indicators that the settings in the config will be applied to
        self.item = item
        self.widgets = {}  # guid as key, widget as value
        # Get the first indicator in the list to get the attributes
        # and use those attributes to create the configuration widgets

        # We work with a copy so any changes you make to attributes
        # will NOT update the indicator item
        attributes = item.getItemByGuid(guids[0]).attributes().copy()
        self.attributes = attributes
        self.layout: QVBoxLayout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.button_group: QButtonGroup = QButtonGroup(self)
        # Connect the button group's buttonClicked signal to the selection change handler
        self.button_group.buttonClicked.connect(self.on_selection_changed)

        try:
            self.create_radio_buttons(attributes)
        except Exception as e:
            log_message(f"Error in create_radio_buttons: {e}", level=Qgis.Critical)
        self.setLayout(self.layout)

    def create_radio_buttons(self, attributes: dict) -> None:
        """
        Uses the factory to create radio buttons from attributes dictionary.
        """
        analysis_mode = attributes.get("analysis_mode", "")
        log_message(f"Creating radio buttons for analysis mode: {analysis_mode}")
        widget_count = 0
        for key, value in attributes.items():
            if key.startswith("use_") or key == "indicator_required" and value == 1:
                log_message(f"Creating radio button for key: {key} with value: {value}")
                # We pass a copy of the attributes dictionary to the widget factory
                # so that we can update the attributes as needed
                # The widget factory will update the attributes dictionary with new data
                configuration_widget = ConfigurationWidgetFactory.create_widget(
                    key, value, attributes.copy()
                )
                if configuration_widget:
                    self.widgets[key] = configuration_widget
                    widget_count += 1
                    if key == analysis_mode:
                        configuration_widget.setChecked(True)
                    self.button_group.addButton(configuration_widget.radio_button)
                    self.layout.addWidget(configuration_widget)
                    configuration_widget.data_changed.connect(self.update_attributes)
                else:
                    log_message(
                        f"Could not create radio button for key: {key}",
                        level=Qgis.Warning,
                    )
        checked_button = self.button_group.checkedButton()
        if not checked_button:
            default_radio = self.button_group.buttons()[0]
            default_radio.setChecked(True)

    def refresh_radio_buttons(self, attributes: dict) -> None:
        """
        Refreshes the radio buttons.
        """
        log_message("Refreshing radio buttons")
        for key, value in attributes.items():
            log_message(f"Key: {key}, Value: {value}")
        for key, widget in self.widgets.items():
            log_message(f"Updating widget for key: {key}")
            widget.update_widgets(attributes)

    def on_selection_changed(self, button) -> None:
        """
        Slot called when the selection in the radio button group changes.
        Emits the selection_changed signal.
        :param button: The button that was clicked.
        """
        log_message("Radio button selection changed")
        self.update_attributes(self.button_group.checkedButton().parent().get_data())
        self.selection_changed.emit()

    def update_attributes(self, new_data: dict) -> None:
        """
        Updates the attributes dictionary with new data from the selected radio button.

        Compares the incoming data with the current attributes and applies updates
        to each indicator associated with the GUIDs in self.guids.

        A change is detected if:
        - A key exists in `new_data` but not in `self.attributes`.
        - A key exists in both, but their values are different.

        :param new_data: A dictionary containing the new attribute values to be updated.
        """
        # Log the received data
        # log_message(f"Received new data: {new_data}", tag="Geest", level=Qgis.Info)

        # Identify changed attributes: keys present in new_data with differing or new values
        if not new_data:
            changed_attributes = {}
        else:
            changed_attributes = {
                key: new_data[key]
                for key in new_data
                if key not in self.attributes or self.attributes[key] != new_data[key]
            }
            for guid in self.guids:
                indicator = self.item.getItemByGuid(guid)
                if indicator is not None:
                    indicator.setAnalysisMode(new_data.get("analysis_mode", ""))

        # Log the changes that will be applied
        if changed_attributes:
            log_message(
                f"\n\n\n\n\nUpdating attributes with the following changes: {changed_attributes}\n\n\n\n\n"
            )
        else:
            log_message(
                "\n\n\n\n\n\nNo changes detected in the new data. No updates will be applied.\n\n\n\n\n"
            )
            return  # Exit early if there are no changes

        # Apply the changes to each indicator associated with the GUIDs
        for guid in self.guids:
            indicator = self.item.getItemByGuid(guid)
            if indicator is not None:
                indicator_attributes = indicator.attributes()
                indicator_attributes.update(changed_attributes)
                log_message(f"Updated attributes for GUID {guid}:")
                log_message(f"{indicator.attributesAsMarkdown()}")
            else:
                log_message(
                    f"GUID {guid} could not be found. Skipping update.",
                    tag="Geest",
                    level=Qgis.Warning,
                )
