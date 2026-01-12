# -*- coding: utf-8 -*-
"""📦 EPLEX Datasource Widget module.

This module contains functionality for EPLEX datasource widget.
"""
from qgis.core import Qgis
from qgis.PyQt.QtWidgets import QDoubleSpinBox

from geest.utilities import log_message

from .base_datasource_widget import BaseDataSourceWidget


class EPLEXDataSourceWidget(BaseDataSourceWidget):
    """
    A widget for entering EPLEX score value.

    This widget provides a single spinbox with a value range 0-5 for the EPLEX score.

    Attributes:
        widget_key (str): The key identifier for this widget.
        spin_box (QDoubleSpinBox): A spinbox for entering the EPLEX score.
    """

    def add_internal_widgets(self) -> None:
        """
        Adds the internal widgets required for entering EPLEX score.
        This method is called during the widget initialization and sets up the layout for the UI components.
        """
        try:
            # EPLEX score spinbox
            self.spin_box = QDoubleSpinBox()
            self.spin_box.setRange(0.0, 5.0)
            self.spin_box.setDecimals(2)
            self.spin_box.setSingleStep(0.1)
            self.spin_box.setValue(self.attributes.get("eplex_score", 0.0))
            self.spin_box.setToolTip("Enter EPLEX score between 0 (weakest protection) and 5 (strongest protection)")
            self.layout.addWidget(self.spin_box)

            # Connect signal to update the data when user changes value
            self.spin_box.valueChanged.connect(self.update_attributes)

        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", level=Qgis.Critical)
            import traceback

            log_message(traceback.format_exc(), level=Qgis.Critical)

    def update_attributes(self):
        """
        Updates the attributes dict to match the current state of the widget.

        The attributes dict is a reference so any tree item attributes will be updated directly.

        Returns:
            None
        """
        value = self.spin_box.value()
        self.attributes["eplex_score"] = value
