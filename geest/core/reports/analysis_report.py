from collections import defaultdict
import json
from datetime import datetime
from typing import List, Dict, Optional

from qgis.core import (
    QgsProject,
    QgsLayout,
    QgsLayoutItemLabel,
    QgsLayoutPoint,
    QgsUnitTypes,
    QgsLayoutSize,
    QgsLayoutItemLabel,
    QgsLayoutItemShape,
    QgsSimpleFillSymbolLayer,
    QgsUnitTypes,
    QgsRasterLayer,
)
from qgis.PyQt.QtGui import QFont, QColor
from geest.utilities import log_message, resources_path, setting
from geest.core.utilities import (
    create_layer,
    find_existing_layer,
    add_layer_to_group,
    ensure_visibility,
    traverse_and_create_subgroups,
    get_or_create_group,
)
from .base_report import BaseReport


class AnalysisReport(BaseReport):
    """
    A class to generate a PDF report from the analysis results.

    """

    def __init__(self, model_path: str, report_name="Geest Analysis Report"):
        """
        Initialize the report.

        Parameters:
            layer_input (str): A file path to the GeoPackage (from which the
                layer "study_area_creation_status" and other layers will be loaded).
            report_name (str): The title to use for the report.

        Raises:
            ValueError: If the layer cannot be loaded from the given file path.
            TypeError: If layer_input is neither a string nor a QgsVectorLayer.
        """
        template_path = resources_path(
            "resources", "qpt", f"analysis_summary_report_template.qpt"
        )
        super().__init__(template_path, report_name)

        self.report_name = report_name
        self.model_path = model_path
        self.page_descriptions[
            "analysis_summary"
        ] = """
        This shows the relative elapsed time for each analysis step. The time is in minutes.
        """

    def __del__(self):
        """
        Destructor to clean up layers from the QGIS project.
        """
        pass

    def create_layout(self):
        """
        Create a QGIS layout (report) that includes a title, summary statistics,
        and individual pages for each indicator.
        """
        project = QgsProject.instance()
        self.title = "Analysis Report"
        self.layout = QgsLayout(project)
        self.layout.initializeDefaults()
        self.load_template()

        # Add a summary page
        summary_text = "Analysis Summary\n"
        summary_label = QgsLayoutItemLabel(self.layout)
        summary_label.setText(summary_text)
        summary_label.setFont(QFont("Arial", 12))
        summary_label.adjustSizeToText()
        summary_label.attemptMove(
            QgsLayoutPoint(80, 200, QgsUnitTypes.LayoutMillimeters), page=0
        )
        self.layout.addLayoutItem(summary_label)

        # Compute and add summary statistics for each layer on separate pages
        current_page = 1
        page = self.make_page(
            title="Processing Times",
            description_key="analysis_summary",
            current_page=current_page,
        )
        self.create_execution_time_layout(
            entries=self.extract_execution_times_with_colors(),
            max_bar_width_mm=10.0,
            page=current_page,
        )

        # Add footer for the summary page
        self.add_header_and_footer(page_number=current_page)
        current_page += 1

        # Add pages for each indicator
        # check if developer mode is enabled
        developer_mode = int(setting(key="developer_mode", default=0))
        if developer_mode:
            log_message(
                "Developer mode is enabled. Creating detail pages for each indicator."
            )
            self.create_detail_pages(current_page=current_page)
        else:
            log_message(
                "Developer mode is disabled. Skipping detail pages for each indicator."
            )
            return

    def create_detail_pages(self, current_page: int = 1):
        """
        Iterate over each indicator and create a detail page for it.

        Parameters
        ----------
        current_page : int
            The current page number to start from. This is incremented for each new page created.
        """

        with open(self.model_path, "r", encoding="utf-8") as f:
            model = json.load(f)

        results = []

        for dimension in model.get("dimensions", []):
            dim_name = dimension.get("name", "")
            for factor in dimension.get("factors", []):
                factor_name = factor.get("name", "")
                self.page_descriptions[factor_name] = factor.get(
                    "description", f"Analysis for factor: {factor_name}"
                )
                for indicator in factor.get("indicators", []):
                    indicator_name = indicator.get("indicator", "")
                    start_str = indicator.get("execution_start_time", "")
                    end_str = indicator.get("execution_end_time", "")

                    start_datetime = self.parse_iso_datetime(start_str)
                    end_datetime = self.parse_iso_datetime(end_str)

                    if start_datetime and end_datetime:
                        duration = round(
                            (end_datetime - start_datetime).total_seconds() / 60, 2
                        )
                    else:
                        duration = None
                    layer_uri = indicator.get(f"result_file")
                    log_message(f"Adding {layer_uri} to map")
                    if not layer_uri:
                        continue

                    # check if the layer is already loaded in the project
                    # and get its legend layer
                    parent_group = get_or_create_group(group="accessibility")
                    layer, tree_layer = find_existing_layer(parent_group, layer_uri)
                    if not layer:
                        continue
                    # Create a new page for the indicator
                    page = self.make_page(
                        title=f"Indicator: {indicator_name}",
                        description_key=factor_name,
                        current_page=current_page,
                    )

                    ensure_visibility(
                        layer_tree_layer=tree_layer, parent_group=parent_group
                    )
                    layers = [layer]
                    crs = layer.crs()
                    self.make_map(
                        layers=layers,
                        current_page=current_page,
                        crs=crs,
                    )
                    # Add footer for the indicator page
                    self.add_header_and_footer(page_number=current_page)

                    # Increment the page counter
                    current_page += 1

    def parse_iso_datetime(self, iso_str: str) -> Optional[datetime]:
        """Parse ISO 8601 datetime string safely."""
        try:
            return datetime.fromisoformat(iso_str)
        except Exception:
            return None

    def interpolate_color(self, rel: float) -> str:
        """
        Linearly interpolate between forest green and off-red.
        rel = 0.0 => forest green (#228B22), rel = 1.0 => off-red (#CC4444)
        """
        fg = (34, 139, 34)  # Forest Green
        or_ = (204, 68, 68)  # Off Red
        r = int(fg[0] + (or_[0] - fg[0]) * rel)
        g = int(fg[1] + (or_[1] - fg[1]) * rel)
        b = int(fg[2] + (or_[2] - fg[2]) * rel)
        return f"#{r:02x}{g:02x}{b:02x}"

    def extract_execution_times_with_colors(self) -> List[Dict[str, Optional[str]]]:
        """
        Extracts execution times for indicators and adds relative time and a color gradient.

        Parameters
        ----------
        model_path : str
            Path to the GEEST model JSON file.

        Returns
        -------
        List[Dict[str, Optional[str]]]
            A sorted list of dictionaries with:
                - indicator
                - factor
                - dimension
                - execution_time_minutes
                - relative_time (float from 0.0 to 1.0)
                - color (string "rgb(r, g, b)")
        """

        with open(self.model_path, "r", encoding="utf-8") as f:
            model = json.load(f)

        results = []

        for dimension in model.get("dimensions", []):
            dim_name = dimension.get("name", "")
            for factor in dimension.get("factors", []):
                factor_name = factor.get("name", "")
                for indicator in factor.get("indicators", []):
                    ind_name = indicator.get("indicator", "")
                    start_str = indicator.get("execution_start_time", "")
                    end_str = indicator.get("execution_end_time", "")

                    start_dt = self.parse_iso_datetime(start_str)
                    end_dt = self.parse_iso_datetime(end_str)

                    if start_dt and end_dt:
                        duration = round((end_dt - start_dt).total_seconds() / 60, 2)
                    else:
                        duration = None

                    results.append(
                        {
                            "indicator": ind_name,
                            "factor": factor_name,
                            "dimension": dim_name,
                            "execution_time_minutes": duration,
                        }
                    )

        # Compute relative times
        valid_times = [
            r["execution_time_minutes"]
            for r in results
            if r["execution_time_minutes"] is not None
        ]

        if valid_times:
            min_time = min(valid_times)
            max_time = max(valid_times)
            range_time = (
                max_time - min_time if max_time > min_time else 1.0
            )  # avoid division by zero

            for r in results:
                exec_time = r["execution_time_minutes"]
                if exec_time is not None:
                    rel = (exec_time - min_time) / range_time
                    r["relative_time"] = round(rel, 2)
                    r["color"] = self.interpolate_color(rel)
                else:
                    r["relative_time"] = None
                    r["color"] = None

        # Sort by execution time descending, placing None last
        results.sort(
            key=lambda r: (
                r["execution_time_minutes"] is None,
                -(r["execution_time_minutes"] or 0),
            )
        )

        return results

    def create_execution_time_layout(
        self, entries: list, max_bar_width_mm: float = 10.0, page: int = 1
    ):
        """
        Creates a QGIS layout showing execution times with colored bars and labels.

        Parameters
        ----------
        layout_name : str
            Name of the layout to create.
        entries : list of dict
            Output from `extract_execution_times_with_colors()`.
        max_bar_width_mm : float
            Maximum width (in mm) for the bar representing the slowest task.
        """
        y_offset = 80  # mm
        row_height = 5  # mm
        margin_left = 20  # mm
        log_message(f"Entries: {entries}")
        for i, entry in enumerate(entries[:28]):
            y = y_offset + i * (row_height + 2)

            # Add label

            duration_label = QgsLayoutItemLabel(self.layout)
            indicator = entry["indicator"]
            duration = entry["execution_time_minutes"]
            duration_label.setText(f"{indicator} - {duration} min")
            duration_label.setFont(QFont("Arial", 10))
            duration_label.adjustSizeToText()
            duration_label.attemptMove(
                QgsLayoutPoint(
                    margin_left + 10.0 + max_bar_width_mm,
                    y,
                    QgsUnitTypes.LayoutMillimeters,
                ),
                page=page,
            )
            self.layout.addLayoutItem(duration_label)

            # Skip if no timing data
            # if entry["execution_time_minutes"] is None or entry["color"] is None:
            #    continue

            # Add bar (shape item)
            bar = QgsLayoutItemShape(self.layout)
            log_message(f"Processing entry: {entry}")
            if entry.get("color", None) is None:
                bar_width = 10.0
                color = "#ff0000"
            else:
                color = entry["color"]
                bar_width = max_bar_width_mm * entry["relative_time"]

            bar.attemptMove(
                QgsLayoutPoint(
                    margin_left,
                    y,
                    QgsUnitTypes.LayoutMillimeters,
                ),
                page=page,
            )
            bar.setFixedSize(
                QgsLayoutSize(bar_width, row_height, QgsUnitTypes.LayoutMillimeters)
            )

            color = QColor(color)
            symbol = QgsSimpleFillSymbolLayer(color=color)
            log_message(f"Bar color: {color.name()}")
            log_message(f"Bar width: {bar_width} mm")
            log_message(f"Bar height: {row_height} mm")
            symbol.setStrokeColor(QColor(0, 0, 0, 0))  # Set border color to transparent
            bar_symbol = bar.symbol()
            bar_symbol.deleteSymbolLayer(0)
            bar_symbol.appendSymbolLayer(symbol)
            bar.setSymbol(bar_symbol)

            self.layout.addLayoutItem(bar)
