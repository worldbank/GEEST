# -*- coding: utf-8 -*-
"""📦 Base Report module.

This module contains functionality for base report.
"""

import math
from collections import defaultdict

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeatureRequest,
    QgsLayout,
    QgsLayoutExporter,
    QgsLayoutItemLabel,
    QgsLayoutItemMap,
    QgsLayoutItemMapGrid,
    QgsLayoutItemPage,
    QgsLayoutItemPicture,
    QgsLayoutItemShape,
    QgsLayoutMeasurement,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsMapLayer,
    QgsProject,
    QgsReadWriteContext,
    QgsRectangle,
    QgsSimpleFillSymbolLayer,
    QgsTextFormat,
    QgsTextShadowSettings,
    QgsUnitTypes,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtXml import QDomDocument

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
        self._cleanup_done = False

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup happens."""
        self.cleanup()
        return False  # Don't suppress exceptions

    def cleanup(self):
        """
        Explicitly clean up resources. Call this when done with the report,
        or use the context manager pattern. Subclasses should override this
        to clean up their specific resources.
        """
        if self._cleanup_done:
            return
        self._cleanup_done = True

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
            parts = sub_layer.split("!!::!!")  # noqa E231
            # layer_id = parts[0]
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
            raise FileNotFoundError(f"Template file '{self.template_path}' not found or cannot be read.")

        document = QDomDocument()
        if not document.setContent(template_content):
            raise ValueError(f"Failed to parse the template content from '{self.template_path}'.")

        context = QgsReadWriteContext()
        if not self.layout.loadFromTemplate(document, context):
            raise ValueError(f"Failed to load the template into the layout from '{self.template_path}'.")

    def make_page(self, title: str, description_key: str, current_page: int, show_header_and_footer: bool = False):
        """
        Create a new page in the layout and add a title and description.

        Parameters:
            title (str): The title to display on the page.
            description_key (str): The key to retrieve the description text.
            current_page (int): The current page number.
            show_header_and_footer (bool): Whether to show the header and footer on the page.

        Returns:
            QgsLayoutItemPage: The created page item.

        """
        # Compute and add summary statistics for each layer on separate pages

        # Add a new page for each layer
        page = QgsLayoutItemPage(self.layout)
        page.setPageSize("A4", QgsLayoutItemPage.Portrait)
        self.layout.pageCollection().addPage(page)
        if show_header_and_footer:
            self.add_header_and_footer(current_page, title)
        else:
            # Add a title label
            title_label = QgsLayoutItemLabel(self.layout)
            title_label.setText(title)
            title_label.setFont(QFont("Arial", 20))
            title_label.setFixedSize(QgsLayoutSize(160, 40, QgsUnitTypes.LayoutMillimeters))
            title_label.attemptMove(
                QgsLayoutPoint(20, 20, QgsUnitTypes.LayoutMillimeters),
                page=current_page,
            )
            self.layout.addLayoutItem(title_label)
        description_text = self.page_descriptions.get(description_key, "")
        # Add description label to the current page
        description_label = QgsLayoutItemLabel(self.layout)
        description_label.setText(description_text)
        description_label.setFont(QFont("Arial", 10))

        description_label.setMode(QgsLayoutItemLabel.ModeHtml)

        # Position the label on the current page
        description_label.attemptMove(
            QgsLayoutPoint(20, 40, QgsUnitTypes.LayoutMillimeters),
            page=current_page,
        )
        # description_label.adjustSizeToText()
        description_label.setFixedSize(QgsLayoutSize(160, 40, QgsUnitTypes.LayoutMillimeters))
        description_label.setHAlign(Qt.AlignJustify)
        self.layout.addLayoutItem(description_label)
        return page

    def make_text_table(self, vector_layer: QgsVectorLayer, sort_column: str, current_page: int):
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
            duration_label.setText(f"{duration:.2f}")  # noqa E231
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
            f"Map extent in EPSG:4326: {geo_extent.xMinimum()}, {geo_extent.yMinimum()}, "  # noqa E231
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

        grid.setAnnotationDirection(QgsLayoutItemMapGrid.Vertical, QgsLayoutItemMapGrid.Bottom)
        grid.setAnnotationDirection(QgsLayoutItemMapGrid.Vertical, QgsLayoutItemMapGrid.Top)
        # Set the bottom to show x/ lon  only
        # This prevents stray labels from lon rendering on the lat area and verce versa
        grid.setAnnotationDisplay(QgsLayoutItemMapGrid.DisplayMode.LongitudeOnly, QgsLayoutItemMapGrid.Bottom)
        grid.setAnnotationDisplay(QgsLayoutItemMapGrid.DisplayMode.HideAll, QgsLayoutItemMapGrid.Top)
        grid.setAnnotationDisplay(QgsLayoutItemMapGrid.DisplayMode.LatitudeOnly, QgsLayoutItemMapGrid.Left)
        grid.setAnnotationDisplay(QgsLayoutItemMapGrid.DisplayMode.HideAll, QgsLayoutItemMapGrid.Right)

        # (Optional) Enable and configure annotations for the grid lines
        grid.setAnnotationEnabled(True)

        # Set the GridStyle to cross
        grid.setStyle(QgsLayoutItemMapGrid.GridStyle.Cross)
        grid.setCrossLength(0.5)  # Length of the cross arms in mm
        # Set the grid line color to gray
        grid.setGridLineColor(QColor(128, 128, 128))
        grid.setGridLineWidth(0.2)  # Width of the grid lines in mm
        grid.setAnnotationFont(QFont("Arial", 8))
        grid.setFramePenSize(0.2)
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
        project_transform = QgsCoordinateTransform(crs, project_crs, QgsProject.instance())
        map_extent = project_transform.transformBoundingBox(new_extent)
        log_message(
            f"Map extent in project CRS: {map_extent.xMinimum()}, {map_extent.yMinimum()}, "
            f"{map_extent.xMaximum()}, {map_extent.yMaximum()}"
        )
        map_item.setExtent(map_extent)
        map_item.refresh()

    def make_header(self, current_page: int, title: str = ""):
        """
        Add a header to the layout with page number and title.

        Args:
            current_page (int): The current page number.
            title (str, optional): The title to display in the header. Defaults to "".
        """

        # Add background image
        bg_image = QgsLayoutItemPicture(self.layout)
        bg_image_path = resources_path("resources", "images", "geest-page-header-bg.png")
        bg_image.setPicturePath(bg_image_path)
        bg_image.attemptMove(
            QgsLayoutPoint(0, 0, QgsUnitTypes.LayoutMillimeters),
            page=current_page,
        )
        bg_image.setFixedSize(QgsLayoutSize(210, 30, QgsUnitTypes.LayoutMillimeters))
        # Ensure image fills the frame
        bg_image.setResizeMode(QgsLayoutItemPicture.Stretch)
        self.layout.addLayoutItem(bg_image)

        # Setup the font to render the heading and page no
        text_format = QgsTextFormat()
        text_format.setColor(QColor(255, 255, 255))
        font = QFont("Arial")
        text_format.setFont(font)
        text_format.setSize(18)
        text_format.setSizeUnit(QgsUnitTypes.RenderPoints)
        shadow_settings = QgsTextShadowSettings()
        shadow_settings.setEnabled(True)
        text_format.setShadow(shadow_settings)

        # Set the page title label on top left
        page_title = QgsLayoutItemLabel(self.layout)
        page_title.setText(title)
        page_title.setTextFormat(text_format)
        page_title.setMode(QgsLayoutItemLabel.ModeFont)
        page_title.setVAlign(Qt.AlignCenter)
        page_title.setHAlign(Qt.AlignLeft)
        # wrap the text if too long
        page_title.setFixedSize(QgsLayoutSize(180, 40, QgsUnitTypes.LayoutMillimeters))
        # Position the label on the current page
        page_title.attemptMove(
            QgsLayoutPoint(10, 1, QgsUnitTypes.LayoutMillimeters),
            page=current_page,
        )
        self.layout.addLayoutItem(page_title)

        # Make a semi-opaque white circle to go behind the page no
        circle = QgsLayoutItemShape(self.layout)
        circle.setShapeType(QgsLayoutItemShape.Ellipse)
        circle.setFixedSize(QgsLayoutSize(10, 10, QgsUnitTypes.LayoutMillimeters))
        circle.attemptMove(
            QgsLayoutPoint(195, 5, QgsUnitTypes.LayoutMillimeters),
            page=current_page,
        )
        fill_symbol = QgsSimpleFillSymbolLayer()
        fill_symbol.setColor(QColor(255, 255, 255, 200))  # White with 200/255 opacity
        # fill_symbol.setStrokeStyle(None)
        self.layout.addLayoutItem(circle)

        # Set the page number label on top
        page_number = QgsLayoutItemLabel(self.layout)
        page_number.setText(f"{current_page}")
        text_format.setSize(12)
        text_format.setColor(QColor(0, 0, 0))
        page_number.setVAlign(Qt.AlignCenter)
        page_number.setHAlign(Qt.AlignCenter)
        page_number.setTextFormat(text_format)

        page_number.setFixedSize(QgsLayoutSize(10, 10, QgsUnitTypes.LayoutMillimeters))
        # Position the label on the current page
        page_number.attemptMove(
            QgsLayoutPoint(195, 5, QgsUnitTypes.LayoutMillimeters),
            page=current_page,
        )
        self.layout.addLayoutItem(page_number)

    def make_footer(self, current_page: int):
        """
        Add a footer to the layout with background image, rounded rectangle, and label.
        """

        # Add background image
        bg_image = QgsLayoutItemPicture(self.layout)
        bg_image_path = resources_path("resources", "images", "geest-page-footer-bg.png")
        bg_image.setPicturePath(bg_image_path)
        bg_image.attemptMove(
            QgsLayoutPoint(0, 260, QgsUnitTypes.LayoutMillimeters),
            page=current_page,
        )
        bg_image.setFixedSize(QgsLayoutSize(210, 30, QgsUnitTypes.LayoutMillimeters))
        # Ensure image fills the frame
        bg_image.setResizeMode(QgsLayoutItemPicture.Stretch)
        self.layout.addLayoutItem(bg_image)

    def add_header_and_footer(self, page_number, title: str = ""):
        """_summary_

        Args:
            page_number (_type_): _description_
            title (str, optional): _description_. Defaults to "".
        """
        self.make_header(page_number, title)
        self.make_footer(page_number)

        footer_text = """
         <p>This plugin is built with support from the <strong>Canada Clean Energy and
         Forest Climate Facility (CCEFCF)</strong>, the <strong>Geospatial Operational
         Support Team (GOST, DECSC)</strong> for the project Geospatial Assessment of
         Employment and Business Opportunities in the Renewable Energy Sector.
         This project is open source; you can download the code at
         <a href="https://github.com/worldbank/GEEST">https://github.com/worldbank/GEEST</a>.</p>
"""
        credits_text = """Developed by <a href="https://kartoza.com">Kartoza</a> for and
        with The World Bank."""
        # Add summary label to the current page
        footer_label = QgsLayoutItemLabel(self.layout)
        footer_label.setText(footer_text)
        footer_label.setFixedSize(QgsLayoutSize(120, 40, QgsUnitTypes.LayoutMillimeters))
        # Use html mode
        footer_label.setMode(QgsLayoutItemLabel.ModeHtml)
        # Position the label on the current page
        footer_label.attemptMove(QgsLayoutPoint(80, 265, QgsUnitTypes.LayoutMillimeters), page=page_number)
        footer_label.setHAlign(Qt.AlignJustify)
        # Set the font to white
        text_format = QgsTextFormat()
        text_format.setColor(QColor(255, 255, 255))
        font = QFont("Arial")
        text_format.setFont(font)
        text_format.setSize(7)
        text_format.setSizeUnit(QgsUnitTypes.RenderPoints)

        footer_label.setTextFormat(text_format)
        self.layout.addLayoutItem(footer_label)

        # Add credits label to the current page
        credits_label = QgsLayoutItemLabel(self.layout)
        credits_label.setText(credits_text)
        credits_label.setFixedSize(QgsLayoutSize(120, 40, QgsUnitTypes.LayoutMillimeters))
        # Use html mode
        credits_label.setMode(QgsLayoutItemLabel.ModeHtml)
        credits_label.setTextFormat(text_format)
        # Position the label on the current page
        credits_label.attemptMove(QgsLayoutPoint(80, 278, QgsUnitTypes.LayoutMillimeters), page=page_number)
        credits_label.setHAlign(Qt.AlignRight)
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
        # Makes links clickable etc.
        # caution - changing to False make html links work but
        # breaks map rendering
        export_settings.rasterizeWholeImage = True
        exporter = QgsLayoutExporter(self.layout)
        result = exporter.exportToPdf(output_path, export_settings)
        # Save it as a qpt too
        qpt_path = output_path.replace(".pdf", ".qpt")
        context = QgsReadWriteContext()
        self.layout.saveAsTemplate(qpt_path, context)
        log_message(f"Saved layout as template: {qpt_path}")
        return result == QgsLayoutExporter.Success

    def export_qpt(self, output_path):
        """
        Export the current layout as a QGIS Print Template (.qpt) file.

        Parameters:
            output_path (str): The full file path (including filename) for the output QPT.

        Returns:
            bool: True if the export was successful, False otherwise.
        """
        if self.layout is None:
            self.create_layout()
        context = QgsReadWriteContext()
        result = self.layout.saveAsTemplate(output_path, context)
        log_message(f"Saved layout as QPT template: {output_path}")
        return result
