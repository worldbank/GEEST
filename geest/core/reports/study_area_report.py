from collections import defaultdict

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsLayout,
    QgsLayoutItemLabel,
    QgsLayoutPoint,
    QgsUnitTypes,
    QgsLayoutExporter,
    QgsLayoutItemMap,
    QgsLayoutSize,
    QgsLayoutItemPage,
    QgsLayoutMeasurement,
    QgsPrintLayout,
    QgsLayoutItemLabel,
    QgsLayoutItemMap,
    QgsReadWriteContext,
    QgsLayoutExporter,
    QgsVectorLayer,
)
from qgis.PyQt.QtXml import QDomDocument
from qgis.PyQt.QtGui import QFont, QColor
from geest.utilities import log_message, resources_path


class StudyAreaReport:
    """
    A class to generate a PDF report from a GeoPackage table of study area creation status data.

    The report computes summary statistics (based on the field "geom_total_duration_secs")
    and creates a QGIS layout (report) that is then exported to PDF.
    """

    def __init__(self, gpkg_path: str, report_name="Study Area Creation Report"):
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

        uri = f"{gpkg_path}|layername=study_area_creation_status"
        self.gpkg_path = gpkg_path
        layer = QgsVectorLayer(uri, "study_area_creation_status", "ogr")
        if not layer.isValid():
            raise ValueError("Failed to load layer from the given file path.")

        self.report_name = report_name
        self.layout = None  # Will hold the QgsLayout for the report
        self.layers = self.load_layers_from_gpkg()
        self.template_path = resources_path(
            "resources", "qpt", f"study_area_report_template.qpt"
        )

    def __del__(self):
        """
        Destructor to clean up layers from the QGIS project.
        """
        for layer_name, layer in self.layers.items():
            if layer:
                del layer
                log_message(f"Layer '{layer_name}' deleted.")

    def load_layers_from_gpkg(self):
        """
        Load all vector layers from the specified GeoPackage.

        Returns:
            dict: A dictionary mapping layer names to QgsVectorLayer objects.
        """
        layers = {}
        # Create a temporary layer to access the data provider
        temp_layer = QgsVectorLayer(self.gpkg_path, "temp", "ogr")
        if not temp_layer.isValid():
            log_message(f"Failed to load GeoPackage: {self.gpkg_path}")
            return layers

        # Retrieve subLayers information
        sub_layers = temp_layer.dataProvider().subLayers()
        for sub_layer in sub_layers:
            # sub_layer is a string in the format "layer_id!!::!!layer_name"
            log_message(f"Loading layer: {sub_layer}")
            parts = sub_layer.split("!!::!!")
            layer_id = parts[0]
            layer_name = parts[1]
            uri = f"{self.gpkg_path}|layername={layer_name}"
            layer = QgsVectorLayer(uri, layer_name, "ogr")
            if layer.isValid():
                layers[layer_name] = layer
            else:
                log_message(f"Failed to load layer: {layer_name}")
        return layers

    def compute_statistics(self, layer):
        """
        Compute summary statistics for a given vector layer.

        Parameters:
            layer (QgsVectorLayer): The vector layer to analyze.

        Returns:
            dict: A dictionary containing summary statistics.
        """
        area_counts = defaultdict(int)
        total_count = 0

        for feature in layer.getFeatures():
            area_name = feature["area_name"]
            area_counts[area_name] += 1
            total_count += 1

        return {"area_counts": dict(area_counts), "total_count": total_count}

    def compute_study_area_creation_statistics(
        self, field_name="geom_total_duration_secs"
    ):
        """
        Compute statistical summary for a given field in the layer.

        Parameters:
            field_name (str): The attribute field on which to compute statistics.

        Returns:
            dict: A dictionary containing 'count', 'min', 'max', 'mean', 'sum', and 'std_dev'.
        """
        values = []
        uri = f"{self.gpkg_path}|layername=study_area_creation_status"
        layer = QgsVectorLayer(uri, "study_area_creation_status", "ogr")
        for feat in layer.getFeatures():
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

        self.layout.initializeDefaults()

        # Load the QPT template
        try:
            with open(self.template_path, "r") as template_file:
                template_content = template_file.read()
        except IOError:
            raise FileNotFoundError(
                f"Template file '{self.template_path}' not found or cannot be read."
            )

        document = QDomDocument()
        if not document.setContent(template_content):
            raise ValueError(
                f"Failed to parse the template content from '{self.template_path}'."
            )

        context = QgsReadWriteContext()
        if not self.layout.loadFromTemplate(document, context):
            raise ValueError(
                f"Failed to load the template into the layout from '{self.template_path}'."
            )

        # self.layout.setTitle(self.report_name)
        page = QgsLayoutItemPage(self.layout)
        page.setPageSize("A4", QgsLayoutItemPage.Portrait)
        self.layout.pageCollection().addPage(page)
        # Add a title label
        title = QgsLayoutItemLabel(self.layout)
        title.setText(self.report_name)
        title.setFont(QFont("Arial", 20))
        title.adjustSizeToText()
        title.attemptMove(
            QgsLayoutPoint(20, 20, QgsUnitTypes.LayoutMillimeters), page=1
        )
        self.layout.addLayoutItem(title)

        # Compute statistics and add a summary label
        stats = self.compute_study_area_creation_statistics()
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
            QgsLayoutPoint(20, 40, QgsUnitTypes.LayoutMillimeters), page=1
        )
        self.layout.addLayoutItem(summary_label)

        # Compute and add summary statistics for each layer on separate pages
        current_page = 1
        for page_number, (layer_name, layer) in enumerate(self.layers.items()):
            # Add a new page for each layer
            page = QgsLayoutItemPage(self.layout)
            page.setPageSize("A4", QgsLayoutItemPage.Portrait)
            self.layout.pageCollection().addPage(page)
            # Compute statistics for the current layer
            try:
                stats = self.compute_statistics(layer)
                summary_text = f"Layer: {layer_name}\n"
                # feature_count = 0
                # for area_name, count in stats["area_counts"].items():
                #    feature_count += count
                summary_text += f"Total count: {stats['total_count']} features"
            except Exception as e:
                log_message(f"Error computing statistics for layer '{layer_name}': {e}")
                continue
            # Add summary label to the current page
            summary_label = QgsLayoutItemLabel(self.layout)
            summary_label.setText(summary_text)
            summary_label.setFont(QFont("Arial", 12))
            summary_label.adjustSizeToText()
            # Position the label on the current page
            summary_label.attemptMove(
                QgsLayoutPoint(100, 40, QgsUnitTypes.LayoutMillimeters),
                page=current_page,
            )
            self.layout.addLayoutItem(summary_label)

            # Add a map item for the current layer
            map_item = QgsLayoutItemMap(self.layout)
            map_item.setLayers([layer])
            map_item.attemptMove(
                QgsLayoutPoint(20, 110, QgsUnitTypes.LayoutMillimeters),
                page=current_page,
            )
            map_item.attemptResize(
                # 170mm width x 100mm height
                QgsLayoutSize(170, 100, QgsUnitTypes.LayoutMillimeters)
            )
            map_item.setExtent(layer.extent())
            map_item.refresh()
            self.layout.addLayoutItem(map_item)
            # Add a black frame around the map item
            map_item.setFrameEnabled(True)
            map_item.setFrameStrokeColor(QColor(0, 0, 0))
            map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.5))
            # Add the page footer
            self.add_header_and_footer(page_number=current_page)
            current_page += 1

    def add_header_and_footer(self, page_number):
        """_summary_

        Args:
            page_number (_type_): _description_
        """
        footer_text = """
         <p>This plugin is built with support from the <strong>Canada Clean Energy and 
         Forest Climate Facility (CCEFCF)</strong>, the <strong>Geospatial Operational 
         Support Team (GOST, DECSC)</strong> for the project Geospatial Assessment of 
         Women Employment and Business Opportunities in the Renewable Energy Sector. 
         This project is open source; you can download the code at 
         <a href="https://github.com/worldbank/GEEST">https://github.com/worldbank/GEEST</a>.</p>
"""
        credits_text = """Developed by <a href="https://kartoza.com">Kartoza</a> for and 
        with The World Bank."""
        # Add summary label to the current page
        footer_label = QgsLayoutItemLabel(self.layout)
        footer_label.setText(footer_text)
        footer_label.setFont(QFont("Arial", 8))
        footer_label.setFixedSize(
            QgsLayoutSize(180, 40, QgsUnitTypes.LayoutMillimeters)
        )
        # Use html mode
        footer_label.setMode(QgsLayoutItemLabel.ModeHtml)
        # Position the label on the current page
        footer_label.attemptMove(
            QgsLayoutPoint(20, 270, QgsUnitTypes.LayoutMillimeters), page=page_number
        )
        self.layout.addLayoutItem(footer_label)

        # Add summary label to the current page
        credits_label = QgsLayoutItemLabel(self.layout)
        credits_label.setText(credits_text)
        credits_label.setFont(QFont("Arial", 8))
        credits_label.setFixedSize(
            QgsLayoutSize(180, 40, QgsUnitTypes.LayoutMillimeters)
        )
        # Use html mode
        credits_label.setMode(QgsLayoutItemLabel.ModeHtml)
        # Position the label on the current page
        credits_label.attemptMove(
            QgsLayoutPoint(20, 280, QgsUnitTypes.LayoutMillimeters), page=page_number
        )
        self.layout.addLayoutItem(credits_label)

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
