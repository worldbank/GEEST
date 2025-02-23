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
    QgsRectangle,
    QgsLayoutItemLabel,
    QgsLayoutItemMap,
    QgsReadWriteContext,
    QgsLayoutExporter,
    QgsVectorLayer,
    QgsLayoutItemMapGrid,
    QgsUnitTypes,
    QgsCoordinateReferenceSystem,
)
from qgis.PyQt.QtXml import QDomDocument
from qgis.PyQt.QtGui import QFont, QColor
from qgis.PyQt.QtCore import Qt
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
        self.page_descriptions = {}
        self.page_descriptions[
            "study_area_bbox"
        ] = """
        The study area bounding box (bbox) is the outer extent of the entire study area.
        The bounding box width and height is guaranteed to be a factor of the
        analysis dimension. All other data products are then aligned to this bbox.
        """
        self.page_descriptions[
            "study_area_bboxes"
        ] = """
        The study area bboxes are a set of smaller bounding boxes that surround each 
        polygon in the study area. They are grid aligned such that the origin and
        furthest corners are guaranteed to be a factor of the analysis dimension
        apart.
        """
        self.page_descriptions[
            "study_area_polygons"
        ] = """
        The study area polygons are the single part form of all polygons in the 
        study area. Any invalid geometries will have been discarded.
        """
        self.page_descriptions[
            "study_area_grid"
        ] = """
        The study area grid is a set of polygon squares that each have the 
        x and y dimension of the analysis cell size. They are guaranteed to
        be aligned to the study area bbox and bboxes layers. The grid is used
        to create a version of the study_area_polygons that have been expanded
        out so that the edges align exactly to the grid.

        The grid is also used to perform certain types of spatial analysis such as
        the Active Transport layer analyses.
        """
        self.page_descriptions[
            "chunks"
        ] = """
        The chunks are the result of splitting the study area grid into smaller
        chunks that are used to process the study area more efficiently. Each chunk
        is labelled as to whether it is inside, on the edge of, or outside the
        geometry of a study area polygon. Grid cells in chunks that are 'inside' can be processed
        more efficiently as we can skip the intersection test with the study area polygons.
        """
        self.page_descriptions[
            "study_area_clip_polygons"
        ] = """
        The study area clip polygons are the original polygon areas but expanded so that the edges
        of the polygon exactly coincide with the edges of the grid. This will ensure that all analysis
        results are coherant with the grid."""
        self.page_descriptions[
            "study_area_creation_status"
        ] = """
        The study area creation status is a record of the time taken to process each part of the study area.
        """

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
            QgsLayoutPoint(80, 200, QgsUnitTypes.LayoutMillimeters), page=0
        )
        self.layout.addLayoutItem(summary_label)

        # Compute and add summary statistics for each layer on separate pages
        current_page = 1
        for page_number, (layer_name, layer) in enumerate(self.layers.items()):
            # Add a new page for each layer
            page = QgsLayoutItemPage(self.layout)
            page.setPageSize("A4", QgsLayoutItemPage.Portrait)
            self.layout.pageCollection().addPage(page)
            # Add a title label
            title = QgsLayoutItemLabel(self.layout)
            # Put title in title case
            title_text = layer_name.replace("_", " ").title()
            title.setText(title_text)
            title.setFont(QFont("Arial", 20))
            title.setFixedSize(QgsLayoutSize(200, 40, QgsUnitTypes.LayoutMillimeters))
            title.attemptMove(
                QgsLayoutPoint(20, 20, QgsUnitTypes.LayoutMillimeters),
                page=current_page,
            )
            self.layout.addLayoutItem(title)
            # Compute statistics for the current layer
            try:
                summary_text = f"Layer: {layer_name}\n"
                stats = self.compute_statistics(layer)
                # feature_count = 0
                # for area_name, count in stats["area_counts"].items():
                #    feature_count += count
                summary_text += f"Total count: {stats['total_count']} features"
            except Exception as e:
                log_message(f"Error computing statistics for layer '{layer_name}': {e}")

            description_text = self.page_descriptions.get(layer_name, "")
            # Add description label to the current page
            description_label = QgsLayoutItemLabel(self.layout)
            description_label.setText(description_text)
            description_label.setFont(QFont("Arial", 12))
            description_label.adjustSizeToText()
            description_label.setMode(QgsLayoutItemLabel.ModeHtml)

            # Position the label on the current page
            description_label.attemptMove(
                QgsLayoutPoint(20, 40, QgsUnitTypes.LayoutMillimeters),
                page=current_page,
            )
            description_label.setFixedSize(
                QgsLayoutSize(80, 40, QgsUnitTypes.LayoutMillimeters)
            )
            description_label.setHAlign(Qt.AlignJustify)
            self.layout.addLayoutItem(description_label)

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

            # Add a map item for the current layer
            map_item = QgsLayoutItemMap(self.layout)
            map_item.setLayers([layer])
            map_item.attemptMove(
                QgsLayoutPoint(20, 110, QgsUnitTypes.LayoutMillimeters),
                page=current_page,
            )
            map_width_mm = 170
            map_height_mm = 100
            map_item.attemptResize(
                # 170mm width x 100mm height
                QgsLayoutSize(
                    map_width_mm, map_height_mm, QgsUnitTypes.LayoutMillimeters
                )
            )
            # if the extent does not have the same aspect ratio as
            # the map item, the extent will be expanded to fit the map item
            # Calculate the aspect ratio of the map item
            map_aspect_ratio = map_width_mm / map_height_mm
            # ---------------------------
            # Set up a grid over the map
            # ---------------------------
            # Create a new map grid for the map item
            grid = QgsLayoutItemMapGrid("Grid 1", map_item)
            grid.setEnabled(True)
            grid.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))

            # Specify that the grid is a graticule (i.e. based on geographic coordinates)
            # grid.setGridType(QgsLayoutItemMapGrid.Graticule)

            # Define a grid interval of 1 degree.
            grid.setIntervalX(1)
            grid.setIntervalY(1)

            grid.setAnnotationDirection(
                QgsLayoutItemMapGrid.Vertical, QgsLayoutItemMapGrid.Bottom
            )
            grid.setAnnotationDirection(
                QgsLayoutItemMapGrid.Vertical, QgsLayoutItemMapGrid.Top
            )

            # (Optional) Enable and configure annotations for the grid lines
            grid.setAnnotationEnabled(True)
            # Example format: degrees and minutes (you can customize this format as needed)
            # grid.setAnnotationFormat("dd° mm'")

            # Add the grid to the map item. The map_item.grids() returns a list;
            # append our configured grid to it.
            map_item.grids().addGrid(grid)

            # If needed, refresh or update your layout to see the grid applied.

            # Get the current extent of the layer
            layer_extent = layer.extent()

            # Calculate the aspect ratio of the layer's extent
            layer_aspect_ratio = layer_extent.width() / layer_extent.height()

            # Initialize variables for the new extent
            new_extent = QgsRectangle(layer_extent)

            # Adjust the extent to match the map item's aspect ratio
            if layer_aspect_ratio > map_aspect_ratio:
                # Layer is wider than the map item; adjust height
                new_height = layer_extent.width() / map_aspect_ratio
                height_diff = new_height - layer_extent.height()
                new_extent.setYMinimum(layer_extent.yMinimum() - height_diff / 2)
                new_extent.setYMaximum(layer_extent.yMaximum() + height_diff / 2)
            else:
                # Layer is taller than the map item; adjust width
                new_width = layer_extent.height() * map_aspect_ratio
                width_diff = new_width - layer_extent.width()
                new_extent.setXMinimum(layer_extent.xMinimum() - width_diff / 2)
                new_extent.setXMaximum(layer_extent.xMaximum() + width_diff / 2)

            # Set the new extent to the map item
            map_item.setExtent(new_extent)

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
            QgsLayoutSize(160, 40, QgsUnitTypes.LayoutMillimeters)
        )
        # Use html mode
        footer_label.setMode(QgsLayoutItemLabel.ModeHtml)
        # Position the label on the current page
        footer_label.attemptMove(
            QgsLayoutPoint(20, 270, QgsUnitTypes.LayoutMillimeters), page=page_number
        )
        footer_label.setHAlign(Qt.AlignJustify)
        self.layout.addLayoutItem(footer_label)

        # Add credits label to the current page
        credits_label = QgsLayoutItemLabel(self.layout)
        credits_label.setText(credits_text)
        credits_label.setFont(QFont("Arial", 8))
        credits_label.setFixedSize(
            QgsLayoutSize(160, 40, QgsUnitTypes.LayoutMillimeters)
        )
        # Use html mode
        credits_label.setMode(QgsLayoutItemLabel.ModeHtml)
        # Position the label on the current page
        credits_label.attemptMove(
            QgsLayoutPoint(20, 288, QgsUnitTypes.LayoutMillimeters), page=page_number
        )
        credits_label.setHAlign(Qt.AlignCenter)
        self.layout.addLayoutItem(credits_label)

    def export_pdf(self, output_path):
        """
        Export the current layout as a PDF file in raster mode.

        Parameters:
            output_path (str): The full file path (including filename) for the output PDF.

        Returns:
            bool: True if the export was successful, False otherwise.
        """
        if self.layout is None:
            self.create_layout()
        export_settings = QgsLayoutExporter.PdfExportSettings()
        export_settings.rasterizeWholeImage = True
        exporter = QgsLayoutExporter(self.layout)
        result = exporter.exportToPdf(output_path, export_settings)
        return result == QgsLayoutExporter.Success
