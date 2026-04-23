# -*- coding: utf-8 -*-
"""📦 EPLEX Datasource Widget module.

This module contains functionality for EPLEX datasource widget.
"""

from qgis.core import Qgis
from qgis.PyQt.QtWidgets import QDoubleSpinBox, QLabel

from geest.utilities import log_message

from .base_datasource_widget import BaseDataSourceWidget


class EPLEXDataSourceWidget(BaseDataSourceWidget):
    """
    A widget for entering EPLEX score value.

    This widget provides a single spinbox with a normalized value range 0-0.99
    for the EPLEX score.

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
            # EPLEX score spinbox (normalized score)
            self.spin_box = QDoubleSpinBox()
            self.spin_box.setRange(0.0, 0.99)
            self.spin_box.setDecimals(2)
            self.spin_box.setSingleStep(0.01)
            raw_value = float(self.attributes.get("eplex_score", 0.0))
            if 1.0 < raw_value <= 5.0:
                # Backward compatibility for older projects storing Likert-scale values.
                raw_value = raw_value / 5.0
            self.spin_box.setValue(max(0.0, min(raw_value, 0.99)))
            self.spin_box.setToolTip(
                "Enter normalized EPLEX score between 0.00 and 0.99. "
                "This is rescaled to the 0-5 Likert scale during processing."
            )
            self.layout.addWidget(self.spin_box)

            self.reference_link_label = QLabel(
                '<a href="https://eplex.ilo.org/en#indicators-section">' "EPLEX indicator reference" "</a>"
            )
            self.reference_link_label.setOpenExternalLinks(True)
            self.layout.addWidget(self.reference_link_label)

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
