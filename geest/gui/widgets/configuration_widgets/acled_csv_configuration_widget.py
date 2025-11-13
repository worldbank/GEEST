# -*- coding: utf-8 -*-
from qgis.core import Qgis
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QLabel, QWidget

from geest.core.workflows.acled_impact_mappings import buffer_distances, event_scores
from geest.utilities import log_message

from .base_configuration_widget import BaseConfigurationWidget


class AcledCsvConfigurationWidget(BaseConfigurationWidget):
    """
    A widget for indicating that we will be doing an ACLED CSV file based analysis.

    This widget does not provide any options other than checking it on or off.

    See also the AcledCsvLayerWidget which is used to select the CSV file.

    Attributes:
        widget_key (str): The key identifier for this widget.
    """

    # Normally we dont need to reimplement the __init__ method, but in this case we need to
    # change the label text next to the radio button
    def __init__(
        self,
        analysis_mode: str,
        attributes: dict,
        humanised_label: str = None,
        parent: QWidget = None,
    ) -> None:
        humanised_label = "ACLED CSV Point Layer"
        super().__init__(
            humanised_label=humanised_label,  # In this special case we override the label
            analysis_mode=analysis_mode,
            attributes=attributes,
            parent=parent,
        )

    def add_internal_widgets(self) -> None:
        """
        Normally this adds the internal options for this workflow type, but in this case there are none.

        This method is called during the widget initialization and sets up the layout for the UI components.
        """
        try:
            self.widget_key = "use_csv_to_point_layer"
            # Generate HTML table for buffer distances
            buffer_distances_html = ""
            buffer_distances_html += "<table border='1' cellpadding='4' cellspacing='0'>"
            buffer_distances_html += "<tr><th>Event</th><th>buffer distance (m)</th></tr>"
            for event, distance in buffer_distances.items():
                buffer_distances_html += f"<tr><td>{event}</td><td>{distance}</td></tr>"
            buffer_distances_html += "</table>"

            # Generate the HTML table for the event scores
            event_scores_html = ""
            event_scores_html += "<table border='1' cellpadding='4' cellspacing='0'>"
            event_scores_html += "<tr><th>event type</th><th>score</th></tr>"
            for event, score in event_scores.items():
                event_scores_html += f"<tr><td>{event}</td><td>{score}</td></tr>"
            event_scores_html += "</table>"

            combined_table_html = f"""
            <table border="1" cellpadding="4" cellspacing="0">
                <tr>
                    <th>Buffer Distances</th>
                    <th>Scores</th>
                </tr>
                <tr>
                    <td>{buffer_distances_html}</td>
                    <td>{event_scores_html}</td>
                </tr>
            </table>
            """
            self.info_label = QLabel(
                """
                Each point from the ACLED CSV file will be buffered by a
                specified distance based on the following event types. """
            )
            self.info_label.setWordWrap(True)
            self.internal_layout.addWidget(self.info_label)
            self.html_table_label = QLabel()
            self.html_table_label.setWordWrap(True)
            self.html_table_label.setTextFormat(Qt.RichText)
            self.html_table_label.setText(combined_table_html)
            self.internal_layout.addWidget(self.html_table_label)

        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", level=Qgis.Critical)
            import traceback

            log_message(traceback.format_exc(), level=Qgis.Critical)

    def get_data(self) -> dict:
        """
        Return the data as a dictionary, updating attributes with current value.
        """
        if not self.isChecked():
            return None
        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets based on the state of the radio button.
        """
        try:
            pass
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
