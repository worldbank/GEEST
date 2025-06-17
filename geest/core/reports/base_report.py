from collections import defaultdict
import math

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
    QgsFeatureRequest,
    QgsCoordinateTransform,
    QgsReadWriteContext,
    QgsMapLayer,
)
from qgis.PyQt.QtXml import QDomDocument
from qgis.PyQt.QtGui import QFont, QColor
from qgis.PyQt.QtCore import Qt
from geest.utilities import log_message, resources_path


class BaseReport:
    """
    A base class to generate a PDF report using a QGIS Layout.

    """

    def __init__(self, template_path: str, str, report_name="Report"):
        """
        Initialize the report.

        Parameters:
            report_name (str): The title to use for the report.

        """
        self.layout = None  # Will hold the QgsLayout for the report

        self.report_name = report_name
        self.template_path = template_path
        self.page_descriptions = {}

    def __del__(self):
        """
        Destructor to clean up layers from the QGIS project.
        """
        pass

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
            self.layers = []
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
        self.layers = layers  # For cleanup in dtor
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

    def create_layout(self):
        """
        Create a QGIS layout (report) that includes a title and a label with summary statistics.

        The layout is stored in the attribute self.layout.
        """
        project = QgsProject.instance()
        self.layout = QgsLayout(project)
        self.layout.initializeDefaults()

    def load_template(self):

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

    def make_page(self, title: str, description_key: str, current_page: int):
        """
        Create a new page in the layout and add a title and description.

        Parameters:

        """
        # Compute and add summary statistics for each layer on separate pages

        # Add a new page for each layer
        page = QgsLayoutItemPage(self.layout)
        page.setPageSize("A4", QgsLayoutItemPage.Portrait)
        self.layout.pageCollection().addPage(page)
        # Add a title label
        title_label = QgsLayoutItemLabel(self.layout)
        title_label.setText(title)
        title_label.setFont(QFont("Arial", 20))
        title_label.setFixedSize(QgsLayoutSize(200, 40, QgsUnitTypes.LayoutMillimeters))
        title_label.attemptMove(
            QgsLayoutPoint(20, 20, QgsUnitTypes.LayoutMillimeters),
            page=current_page,
        )
        self.layout.addLayoutItem(title_label)
        description_text = self.page_descriptions.get(description_key, "")
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
            QgsLayoutSize(100, 40, QgsUnitTypes.LayoutMillimeters)
        )
        description_label.setHAlign(Qt.AlignJustify)
        self.layout.addLayoutItem(description_label)
        return page

    def make_text_table(
        self, vector_layer: QgsVectorLayer, sort_column: str, current_page: int
    ):
        # I would have liked to just used a table here
        # but the table is not working - it crashes QGIS in 3.42

        start_x = 20
        start_y = 110
        row_height = 8  # mm between rows

        # Create a request to sort by geom_total_duration_secs in descending order
        request = QgsFeatureRequest()
        clause = QgsFeatureRequest.OrderByClause(sort_column, ascending=False)
        orderby = QgsFeatureRequest.OrderBy([clause])
        request.setOrderBy(orderby)

        # Use the request in getFeatures
        for i, feat in enumerate(vector_layer.getFeatures(request)):
            name = feat["area_name"]
            duration = round(feat[sort_column], 2)

            y_offset = start_y + i * row_height
            if y_offset > 240:
                continue
            # Label: Area name
            name_label = QgsLayoutItemLabel(self.layout)
            name_label.setText(f"{name}")
            name_label.adjustSizeToText()
            name_label.attemptMove(
                QgsLayoutPoint(start_x, y_offset, QgsUnitTypes.LayoutMillimeters),
                page=current_page,
            )
            self.layout.addLayoutItem(name_label)

            # Label: Duration
            duration_label = QgsLayoutItemLabel(self.layout)
            duration_label.setText(f"{duration:.2f}")
            duration_label.adjustSizeToText()
            duration_label.attemptMove(
                QgsLayoutPoint(
                    start_x + 60,
                    y_offset,
                    QgsUnitTypes.LayoutMillimeters,
                ),
                page=current_page,
            )
            self.layout.addLayoutItem(duration_label)

    def make_map(
        self,
        layers: list[QgsMapLayer],
        crs,
        current_page: int,
    ):

        # Get the current extent of all the layers
        layers_extent = QgsRectangle()
        for layer in layers:
            layers_extent.combineExtentWith(layer.extent())

        map_item = QgsLayoutItemMap(self.layout)
        # Calculate the aspect ratio of the layer's extent
        layer_aspect_ratio = layers_extent.width() / layers_extent.height()
        map_width_mm = 170
        map_height_mm = 100
        # Initialize variables for the new extent
        new_extent = QgsRectangle(layers_extent)
        # if the extent does not have the same aspect ratio as
        # the map item, the extent will be expanded to fit the map item
        # Calculate the aspect ratio of the map item
        map_aspect_ratio = map_width_mm / map_height_mm
        # Adjust the extent to match the map item's aspect ratio
        if layer_aspect_ratio > map_aspect_ratio:
            # Layer is wider than the map item; adjust height
            new_height = layers_extent.width() / map_aspect_ratio
            height_diff = new_height - layers_extent.height()
            new_extent.setYMinimum(layers_extent.yMinimum() - height_diff / 2)
            new_extent.setYMaximum(layers_extent.yMaximum() + height_diff / 2)
        else:
            # Layer is taller than the map item; adjust width
            new_width = layers_extent.height() * map_aspect_ratio
            width_diff = new_width - layers_extent.width()
            new_extent.setXMinimum(layers_extent.xMinimum() - width_diff / 2)
            new_extent.setXMaximum(layers_extent.xMaximum() + width_diff / 2)

        geo_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = QgsCoordinateTransform(crs, geo_crs, QgsProject.instance())
        # Calculate the extent in EPGS:4326
        geo_extent = transform.transformBoundingBox(new_extent)
        log_message(
            f"Map extent in EPSG:4326: {geo_extent.xMinimum()}, {geo_extent.yMinimum()}, "
            f"{geo_extent.xMaximum()}, {geo_extent.yMaximum()}"
        )
        log_message(
            f"Map extent in CRS: {new_extent.xMinimum()}, {new_extent.yMinimum()}, {new_extent.xMaximum()}, {new_extent.yMaximum()}"
        )
        #
        # Adding these layers to the map item
        log_message(f"Adding {len(layers)} layers to the map item")

        map_item.setLayers(layers)

        map_item.attemptMove(
            QgsLayoutPoint(20, 110, QgsUnitTypes.LayoutMillimeters),
            page=current_page,
        )

        map_item.attemptResize(
            # 170mm width x 100mm height
            QgsLayoutSize(map_width_mm, map_height_mm, QgsUnitTypes.LayoutMillimeters)
        )

        # ---------------------------
        # Set up a grid over the map
        # ---------------------------
        # Create a new map grid for the map item
        grid = QgsLayoutItemMapGrid("Grid 1", map_item)
        grid.setEnabled(True)
        grid.setCrs(geo_crs)

        def round_down_to_sig_fig(x: float) -> float:
            if x == 0:
                return 0
            exp = math.floor(math.log10(abs(x)))
            factor = 10**exp
            return math.floor(x / factor * 10) / 10 * factor

        # Define a grid interval of 1 degree
        interval_x = round_down_to_sig_fig(geo_extent.width() / 10.0)
        interval_y = round_down_to_sig_fig(geo_extent.height() / 10.0)
        log_message(f"Grid interval: {interval_x}, {interval_y}")
        log_message(f"X Range: {geo_extent.xMaximum() - geo_extent.xMinimum()}")
        log_message(f"Y Range: {geo_extent.yMaximum() - geo_extent.yMinimum()}")
        grid.setIntervalX(interval_x)
        grid.setIntervalY(interval_y)

        grid.setAnnotationDirection(
            QgsLayoutItemMapGrid.Vertical, QgsLayoutItemMapGrid.Bottom
        )
        grid.setAnnotationDirection(
            QgsLayoutItemMapGrid.Vertical, QgsLayoutItemMapGrid.Top
        )
        # Set the bottom to show x/ lon  only
        # This prevents stray labels from lon rendering on the lat area and verce versa
        grid.setAnnotationDisplay(
            QgsLayoutItemMapGrid.DisplayMode.LongitudeOnly, QgsLayoutItemMapGrid.Bottom
        )
        grid.setAnnotationDisplay(
            QgsLayoutItemMapGrid.DisplayMode.HideAll, QgsLayoutItemMapGrid.Top
        )
        grid.setAnnotationDisplay(
            QgsLayoutItemMapGrid.DisplayMode.LatitudeOnly, QgsLayoutItemMapGrid.Left
        )
        grid.setAnnotationDisplay(
            QgsLayoutItemMapGrid.DisplayMode.HideAll, QgsLayoutItemMapGrid.Right
        )

        # (Optional) Enable and configure annotations for the grid lines
        grid.setAnnotationEnabled(True)
        # Example format: degrees and minutes (you can customize this format as needed)
        # grid.setAnnotationFormat("dd° mm'")

        # Add the grid to the map item. The map_item.grids() returns a list;
        # append our configured grid to it.
        map_item.grids().addGrid(grid)

        # If needed, refresh or update your layout to see the grid applied.

        self.layout.addLayoutItem(map_item)
        # Add a black frame around the map item
        map_item.setFrameEnabled(True)
        map_item.setFrameStrokeColor(QColor(0, 0, 0))
        map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.5))
        # Set the new extent to the map item
        # Get the QgsProject CRS and set the extent in the map item
        project_crs = QgsProject.instance().crs()
        project_transform = QgsCoordinateTransform(
            crs, project_crs, QgsProject.instance()
        )
        map_extent = project_transform.transformBoundingBox(new_extent)
        log_message(
            f"Map extent in project CRS: {map_extent.xMinimum()}, {map_extent.yMinimum()}, "
            f"{map_extent.xMaximum()}, {map_extent.yMaximum()}"
        )
        map_item.setExtent(map_extent)
        map_item.refresh()

    def make_footer(self, current_page: int):
        """
        Add a footer to the layout.
        """
        # Set the page number
        page_number = QgsLayoutItemLabel(self.layout)
        page_number.setText(f"Page {current_page}")
        page_number.setFont(QFont("Arial", 8))
        page_number.setFixedSize(QgsLayoutSize(160, 40, QgsUnitTypes.LayoutMillimeters))
        # Position the label on the current page
        page_number.attemptMove(
            QgsLayoutPoint(20, 270, QgsUnitTypes.LayoutMillimeters),
            page=current_page,
        )
        self.layout.addLayoutItem(page_number)

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
        # Save it as a qpt too
        qpt_path = output_path.replace(".pdf", ".qpt")
        context = QgsReadWriteContext()
        self.layout.saveAsTemplate(qpt_path, context)
        log_message(f"Saved layout as template: {qpt_path}")
        return result == QgsLayoutExporter.Success
