# -*- coding: utf-8 -*-
"""Urban/Rural share selector datasource widget.

The urban/rural split is population data carried by the S2S demographics layer
(fetched alongside the main population field), so the Education indicator does
not download its own data. This widget only lets the user choose which share to
score: the urban population share or the inverted rural population share.
"""

from qgis.PyQt.QtWidgets import QComboBox, QLabel, QSizePolicy

from geest.core.constants import DEFAULT_S2S_URBAN_RURAL_MEASURES
from geest.utilities import log_message

from .base_datasource_widget import BaseDataSourceWidget


class UrbanRuralShareDataSourceWidget(BaseDataSourceWidget):
    """A single-dropdown selector for the urban/rural population-share measure."""

    def add_internal_widgets(self) -> None:
        """Build the dropdown and an explanatory label."""
        self.measure_combo = QComboBox()
        default_measure = str(self.attributes.get("education_measure", "") or "urban").strip().lower()

        index = 0
        for position, (key, label) in enumerate(DEFAULT_S2S_URBAN_RURAL_MEASURES.items()):
            self.measure_combo.addItem(label, key)
            if key == default_measure:
                index = position
        self.measure_combo.setCurrentIndex(index)
        self.measure_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.measure_combo.currentIndexChanged.connect(self.update_attributes)

        self.measure_label = QLabel("Measure:")
        self.measure_label.setToolTip(
            "Which population share to score: the urban population share, or the "
            "rural population share (with a higher rural share scoring lower)."
        )

        self.info_label = QLabel("Data comes from the project's S2S population layer.")
        self.info_label.setStyleSheet("color: #666; font-size: 11px;")

        self.layout.addWidget(self.measure_label)
        self.layout.addWidget(self.measure_combo, 1)
        self.layout.addWidget(self.info_label)
        self.layout.addStretch(1)

    def update_attributes(self):
        """Persist the selected measure onto the item attributes."""
        measure = self.measure_combo.currentData() or "urban"
        self.attributes["education_measure"] = str(measure).lower()
        log_message(f"Education measure set to '{measure}'.")
