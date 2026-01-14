# -*- coding: utf-8 -*-
from qgis.core import Qgis
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QLabel

from geest.core.workflows.mappings import CYCLEWAY_CLASSIFICATION, HIGHWAY_CLASSIFICATION
from geest.utilities import log_message

from .base_configuration_widget import BaseConfigurationWidget


#
# This combines the point per cell, polyline per cell, osm_transport_polyline_per_cell and polygon per cell
# widgets that are in combined widgets. The reason for this is that
# when working at the factor level, it can have indicators requiring different
# spatial data types, but the user should only select one configuration type.
# The logic for whether to accept point, line or polygons will be implemented in the
# datasource widget.
#
class OsmTransportConfigurationWidget(BaseConfigurationWidget):
    """
    A widget to define inputs counting features per cell.
    """

    # Normally we dont need to reimplement the __init__ method, but in this case we need to
    # change the label text next to the radio button
    def __init__(self, analysis_mode: str, attributes: dict) -> None:
        humanised_label = "OSM transport feature"
        super().__init__(
            humanised_label=humanised_label,  # In this special case we override the label
            analysis_mode=analysis_mode,
            attributes=attributes,
        )

    def add_internal_widgets(self) -> None:
        """
        Adds internal widgets specific to self.set_internal_widgets_visible(self.isChecked()) - in this case there are none.
        """
        try:
            self.info_label = QLabel(
                "Rank cells based on most beneficial active transport features (walkable and cyclable infrastructure) "
                "in the cell. Uses best score when multiple road types exist in a cell."
            )
            self.info_label.setWordWrap(True)
            self.internal_layout.addWidget(self.info_label)
            # make a label as an html table showing the unified active transport scores
            self.html_table_label = QLabel()
            self.html_table_label.setWordWrap(True)
            self.html_table_label.setTextFormat(Qt.RichText)
            analysis_scale = self.attributes.get("analysis_scale") or "national"
            cycleway_config = CYCLEWAY_CLASSIFICATION.get(analysis_scale, CYCLEWAY_CLASSIFICATION["national"])

            def build_wrapped_rows(items, max_rows=8):
                columns = []
                for col in range(0, len(items), max_rows):
                    columns.append(items[col : col + max_rows])

                rows = []
                for row_index in range(max_rows):
                    row_cells = []
                    for col in columns:
                        if row_index < len(col):
                            key, value = col[row_index]
                            row_cells.append(f"<td>{key}</td><td>{value}</td>")
                        else:
                            row_cells.append("<td></td><td></td>")
                    rows.append(f"<tr>{''.join(row_cells)}</tr>")
                header = "".join("<th>Type</th><th>Score</th>" for _ in columns)
                return f"<tr>{header}</tr>\n" + "\n".join(rows)

            highway_items = sorted(HIGHWAY_CLASSIFICATION.items(), key=lambda item: (item[1], item[0]))
            cycleway_items = sorted(cycleway_config.items(), key=lambda item: (item[1], item[0]))

            highway_rows = build_wrapped_rows(highway_items, max_rows=8)
            cycleway_rows = build_wrapped_rows(cycleway_items, max_rows=8)

            active_transport_html = f"""
            <table border="1" cellpadding="4" cellspacing="0">
                <tr>
                    <th>Highway Classification</th>
                    <th>Cycleway Classification ({analysis_scale.title()})</th>
                </tr>
                <tr>
                    <td>
                        <table border="1" cellpadding="4" cellspacing="0">
                            {highway_rows}
                        </table>
                    </td>
                    <td>
                        <table border="1" cellpadding="4" cellspacing="0">
                            {cycleway_rows}
                        </table>
                    </td>
                </tr>
            </table>
            """

            self.html_table_label.setText(active_transport_html)
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

        return None  # Important to return None in this case as we dont want to assign
        # different analysis modes to the indicators because this config widget is a
        # special case where it caters for 4 different analysis modes.

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
