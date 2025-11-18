# -*- coding: utf-8 -*-
from qgis.core import Qgis
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QLabel

from geest.core.workflows.contextual_index_score_mappings import score_mapping
from geest.utilities import log_message

from .base_configuration_widget import BaseConfigurationWidget


class ContextualIndexScoreConfigurationWidget(BaseConfigurationWidget):
    """
    A specialized radio button with additional widgets for Contextual IndexScore.
    """

    # Normally we dont need to reimplement the __init__ method, but in this case we need to
    # change the label text next to the radio button
    def __init__(self, analysis_mode: str, attributes: dict) -> None:
        humanised_label = "Index Score in the contextual dimension"
        super().__init__(
            humanised_label=humanised_label,  # In this special case we override the label
            analysis_mode=analysis_mode,
            attributes=attributes,
        )

    def add_internal_widgets(self) -> None:
        """
        Adds internal widgets specific to IndexScore.
        """
        try:
            self.info_label: QLabel = QLabel("Fill each polygon in the contextual dimension with a fixed value")
            self.internal_layout.addWidget(self.info_label)
            mapping_table_html = """
            The following mapping scheme is used to convert values to index scores:
            <table border="1" cellpadding="4" cellspacing="0">
                <tr>
                    <th>Value Range</th>
                    <th>Index Score</th>
                </tr>
            """
            for value_range, index_score in score_mapping.items():
                mapping_table_html += f"""
                <tr>
                    <td>{value_range}+</td>
                    <td>{index_score}</td>
                </tr>
                """
            mapping_table_html += "</table>"
            self.html_table_label: QLabel = QLabel()
            self.html_table_label.setWordWrap(True)
            self.html_table_label.setTextFormat(Qt.RichText)
            self.html_table_label.setText(mapping_table_html)
            self.internal_layout.addWidget(self.html_table_label)
        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", "Geest", level=Qgis.Critical)

    def get_data(self) -> dict:
        """
        Return the data as a dictionary, updating attributes with current value.
        """
        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets based on the state of the radio button.
        """
        try:
            self.info_label.setEnabled(enabled)
            self.html_table_label.setEnabled(enabled)
        except Exception as e:
            log_message(
                f"Error in set_internal_widgets_enabled: {e}",
                tag="Geest",
                level=Qgis.Critical,
            )

    def update_widgets(self, attributes: dict) -> None:
        """
        Updates the internal widgets with the current attributes.

        Only needed in cases where a) there are internal widgets and b)
        the attributes may change externally e.g. in the datasource widget.
        """
        pass
