from collections import defaultdict

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsLayout,
    QgsLayoutItemLabel,
    QgsLayoutFrame,
    QgsLayoutItemAttributeTable,
    QgsLayoutPoint,
    QgsUnitTypes,
    QgsLayoutExporter,
    QgsLayoutItemMap,
    QgsLayoutSize,
    QgsLayoutItemPage,
    QgsLayoutMeasurement,
    QgsRectangle,
    QgsLayoutItemLabel,
    QgsLayoutItemMap,
    QgsReadWriteContext,
    QgsLayoutExporter,
    QgsVectorLayer,
    QgsLayoutItemMapGrid,
    QgsUnitTypes,
    QgsCoordinateReferenceSystem,
    QgsFeatureRequest,
)
from qgis.PyQt.QtXml import QDomDocument
from qgis.PyQt.QtGui import QFont, QColor
from qgis.PyQt.QtCore import Qt
from geest.utilities import log_message, resources_path
from .base_report import BaseReport


class AnalysisReport(BaseReport):
    """
    A class to generate a PDF report from the analysis results.

    """

    def __init__(self, report_name="Geest Analysis Report"):
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
        super().__init__(report_name)

        self.report_name = report_name
        self.template_path = resources_path(
            "resources", "qpt", f"study_area_report_template.qpt"
        )
        self.page_descriptions = {}
        self.page_descriptions[
            "analysis_summary"
        ] = """
        This shows the elapsed time for each analysis step. The time is in seconds.
        """

    def __del__(self):
        """
        Destructor to clean up layers from the QGIS project.
        """
        pass

    def create_layout(self):
        """
        Create a QGIS layout (report) that includes a title and a label with summary statistics.

        The layout is stored in the attribute self.layout.
        """
        project = QgsProject.instance()
        self.layout = QgsLayout(project)
        self.layout.initializeDefaults()
        self.load_template()

        # Compute statistics and add a summary label
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
        # Add a new page for each layer
        page = self.make_page(
            title="Title",
            description_key="analysis_summary",
            current_page=current_page,
        )

        # Add summary label to the current page
        summary_label = QgsLayoutItemLabel(self.layout)
        summary_label.setText(summary_text)
        summary_label.setFont(QFont("Arial", 12))
        summary_label.adjustSizeToText()
        # Position the label on the current page
        summary_label.attemptMove(
            QgsLayoutPoint(120, 60, QgsUnitTypes.LayoutMillimeters),
            page=current_page,
        )
        self.layout.addLayoutItem(summary_label)

        # Add the page footer
        self.add_header_and_footer(page_number=current_page)
        current_page += 1
