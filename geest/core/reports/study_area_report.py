from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsLayout,
    QgsLayoutItemLabel,
    QgsLayoutPoint,
    QgsUnitTypes,
    QgsLayoutExporter,
    QgsStatisticalSummary,
)
from qgis.PyQt.QtGui import QFont


class StudyAreaReport:
    """
    A class to generate a PDF report from a GeoPackage table of study area creation status data.

    The report computes summary statistics (based on the field "geom_total_duration_secs")
    and creates a QGIS layout (report) that is then exported to PDF.
    """

    def __init__(self, layer_input, report_name="Study Area Creation Report"):
        """
        Initialize the report.

        Parameters:
            layer_input (str or QgsVectorLayer): Either a file path to the GeoPackage (from which the
                layer "study_area_creation_status" will be loaded) or an existing QgsVectorLayer.
            report_name (str): The title to use for the report.

        Raises:
            ValueError: If the layer cannot be loaded from the given file path.
            TypeError: If layer_input is neither a string nor a QgsVectorLayer.
        """
        if isinstance(layer_input, str):
            uri = f"{layer_input}|layername=study_area_creation_status"
            self.layer = QgsVectorLayer(uri, "study_area_creation_status", "ogr")
            if not self.layer.isValid():
                raise ValueError("Failed to load layer from the given file path.")
        elif isinstance(layer_input, QgsVectorLayer):
            self.layer = layer_input
        else:
            raise TypeError(
                "layer_input must be a file path (str) or a QgsVectorLayer instance."
            )

        self.report_name = report_name
        self.layout = None  # Will hold the QgsLayout for the report

    def compute_statistics(self, field_name="geom_total_duration_secs"):
        """
        Compute statistical summary for a given field in the layer.

        Parameters:
            field_name (str): The attribute field on which to compute statistics.

        Returns:
            dict: A dictionary containing 'count', 'min', 'max', 'mean', 'sum', and 'std_dev'.
        """
        values = []
        for feat in self.layer.getFeatures():
            val = feat[field_name]
            if val is not None:
                values.append(val)
        if not values:
            raise ValueError(f"No valid data found for field '{field_name}'.")

        count_val = len(values)
        sum_val = sum(values)
        min_val = min(values)
        max_val = max(values)
        mean_val = sum_val / count_val
        # Compute population standard deviation
        var = sum((x - mean_val) ** 2 for x in values) / count_val
        std_dev = var**0.5

        return {
            "count": count_val,
            "min": min_val,
            "max": max_val,
            "mean": mean_val,
            "sum": sum_val,
            "std_dev": std_dev,
        }

    def create_layout(self):
        """
        Create a QGIS layout (report) that includes a title and a label with summary statistics.

        The layout is stored in the attribute self.layout.
        """
        project = QgsProject.instance()
        self.layout = QgsLayout(project)
        self.layout.initializeDefaults()
        # self.layout.setTitle(self.report_name)

        # Add a title label
        title = QgsLayoutItemLabel(self.layout)
        title.setText(self.report_name)
        title.setFont(QFont("Arial", 20))
        title.adjustSizeToText()
        title.attemptMove(QgsLayoutPoint(20, 20, QgsUnitTypes.LayoutMillimeters))
        self.layout.addLayoutItem(title)

        # Compute statistics and add a summary label
        stats = self.compute_statistics()
        summary_text = (
            f"Total parts: {stats['count']}\n"
            f"Minimum processing time: {stats['min']:.3f} sec\n"
            f"Maximum processing time: {stats['max']:.3f} sec\n"
            f"Average processing time: {stats['mean']:.3f} sec\n"
            f"Total processing time: {stats['sum']:.3f} sec\n"
            f"Standard Deviation: {stats['std_dev']:.3f} sec"
        )
        summary_label = QgsLayoutItemLabel(self.layout)
        summary_label.setText(summary_text)
        summary_label.setFont(QFont("Arial", 12))
        summary_label.adjustSizeToText()
        summary_label.attemptMove(
            QgsLayoutPoint(20, 40, QgsUnitTypes.LayoutMillimeters)
        )
        self.layout.addLayoutItem(summary_label)

    def export_pdf(self, output_path):
        """
        Export the current layout as a PDF file.

        Parameters:
            output_path (str): The full file path (including filename) for the output PDF.

        Returns:
            bool: True if the export was successful, False otherwise.
        """
        if self.layout is None:
            self.create_layout()
        export_settings = QgsLayoutExporter.PdfExportSettings()
        exporter = QgsLayoutExporter(self.layout)
        result = exporter.exportToPdf(output_path, export_settings)
        return result == QgsLayoutExporter.Success
