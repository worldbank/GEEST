# -*- coding: utf-8 -*-
"""📦 EPLEX Configuration Widget module.

This module contains functionality for EPLEX score configuration widget.
"""
from .base_configuration_widget import BaseConfigurationWidget


class EPLEXConfigurationWidget(BaseConfigurationWidget):
    """
    A specialized configuration widget for EPLEX score input.
    Uses a table-based layout similar to the dimension aggregation dialog.
    """

    def __init__(self, analysis_mode: str, attributes: dict) -> None:
        humanised_label = "EPLEX Score (Employment Protection Legislation Index)"
        super().__init__(
            humanised_label=humanised_label,
            analysis_mode=analysis_mode,
            attributes=attributes,
        )

    def add_internal_widgets(self) -> None:
        """
        Adds internal widgets specific to EPLEX score input.

        Note: The actual input spinbox is handled by EPLEXDataSourceWidget in the table.
        This configuration widget provides minimal additional context.
        """
        # No additional widgets needed - the datasource widget handles the input
        pass

    def get_data(self) -> dict:
        """
        Return the data as a dictionary.

        Note: EPLEX score is managed by the datasource widget, not here.
        """
        if not self.isChecked():
            return None

        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets based on the state of the radio button.

        Note: No internal widgets for EPLEX - datasource widget handles input.
        """
        pass

    def update_widgets(self, attributes: dict) -> None:
        """
        Updates the internal widgets with the current attributes.

        Note: No internal widgets for EPLEX - datasource widget handles input.
        """
        pass
