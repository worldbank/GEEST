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
    QgsLayoutFrame,
    QgsLayoutItemLabel,
    QgsLayoutItemMap,
    QgsLayoutItemMapGrid,
    QgsLayoutItemPage,
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
    QgsUnitTypes,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtXml import QDomDocument

from geest.utilities import log_message, resources_path

# analysis_summary_report_template.qpt's two picture items used to embed
# these same two images as base64 (QGIS's own "Embedded" picture mode) -
# byte-identical duplicates of files the plugin already ships separately,
# inflating the template from ~20KB to ~4MB for nothing. Stripped down to
# these placeholders (see the .qpt's "file=" attributes); load_template()
# below substitutes the real resolved path at load time, so the template
# itself never has to hardcode an absolute, install-location-specific path.
_TEMPLATE_RESOURCE_PLACEHOLDERS = {
    "PLUGIN_RESOURCE:images/geoe3-bg.png": lambda: resources_path("resources", "images", "geoe3-bg.png"),
    "PLUGIN_RESOURCE:geoe3-banner.png": lambda: resources_path("resources", "geoe3-banner.png"),
}

# ---------------------------------------------------------------------------
# Report design system — a clean, flat palette appropriate for a World Bank
# publication (deliberately not vendor-branded).
# ---------------------------------------------------------------------------
NAVY = QColor("#002244")  # deep blue: header band, emphasis
CYAN = QColor("#009FDA")  # accent: rules, chart bars
CHARCOAL = QColor("#333333")  # body text
GREY = QColor("#6E7B85")  # secondary text, captions
MIST = QColor("#EEF4F8")  # subtle row/panel tint
RULE = QColor("#D6DEE4")  # hairlines
WHITE = QColor("#FFFFFF")

PAGE_W = 210  # A4 portrait, mm
PAGE_H = 297
MARGIN = 15
CONTENT_W = PAGE_W - 2 * MARGIN
HEADER_H = 22
FOOTER_Y = 284


def _flat_fill(item: QgsLayoutItemShape, color: QColor) -> None:
    """Give a layout shape a flat fill with no stroke."""
    fill = QgsSimpleFillSymbolLayer()
    fill.setColor(color)
    fill.setStrokeColor(QColor(0, 0, 0, 0))
    symbol = item.symbol()
    symbol.deleteSymbolLayer(0)
    symbol.appendSymbolLayer(fill)
    item.setSymbol(symbol)


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

        # See _TEMPLATE_RESOURCE_PLACEHOLDERS - substitute each picture
        # item's placeholder for this install's actual resolved path
        # before parsing, rather than embedding a base64 copy (duplicate
        # data) or an install-location-specific absolute path (not
        # portable) in the template file itself.
        for placeholder, resolve_path in _TEMPLATE_RESOURCE_PLACEHOLDERS.items():
            if placeholder in template_content:
                resolved = resolve_path().replace("\\", "/")
                template_content = template_content.replace(f'file="{placeholder}"', f'file="{resolved}"')

        document = QDomDocument()
        if not document.setContent(template_content):
            raise ValueError(f"Failed to parse the template content from '{self.template_path}'.")

        context = QgsReadWriteContext()
        if not self.layout.loadFromTemplate(document, context):
            raise ValueError(f"Failed to load the template into the layout from '{self.template_path}'.")

    def style_cover_page(self) -> None:
        """Restyle the template cover: dark title inside the frosted panel.

        The template ships the plugin title as light text across the top
        banner, plus HTML frames carrying a heading and credits. HTML
        frames render unreliably in headless exports and the credits have
        their own page (see make_credits_page), so all frames are dropped
        and the title is redrawn as a dark label centred in the frosted
        white panel, with the report name as a subtitle.
        """
        title_text = "The Geospatial Enabling Environments for Employment Tool"
        frosted_panel = None
        for item in list(self.layout.items()):
            if isinstance(item, QgsLayoutFrame):
                multi_frame = item.multiFrame()
                self.layout.removeLayoutItem(item)
                if multi_frame is not None:
                    self.layout.removeMultiFrame(multi_frame)
            elif isinstance(item, QgsLayoutItemLabel):
                # Template labels are cover furniture (main title, old
                # subtitle text); pages are rebuilt programmatically, so
                # only the title text is kept.
                if item.text().strip().startswith("The Geospatial"):
                    title_text = item.text().strip()
                self.layout.removeLayoutItem(item)
            elif isinstance(item, QgsLayoutItemShape) and frosted_panel is None:
                # The frosted white panel is the only shape on the template
                # cover; everything else there is a picture or a label.
                frosted_panel = item
        if frosted_panel is None:
            # Older templates have no panel — draw one at the standard spot.
            frosted_panel = QgsLayoutItemShape(self.layout)
            frosted_panel.setShapeType(QgsLayoutItemShape.Rectangle)
            frosted_panel.setCornerRadius(QgsLayoutMeasurement(8, QgsUnitTypes.LayoutUnit.LayoutMillimeters))
            frosted_panel.attemptMove(QgsLayoutPoint(8.5, 39.6, QgsUnitTypes.LayoutUnit.LayoutMillimeters), page=0)
            frosted_panel.setFixedSize(QgsLayoutSize(193, 29.1, QgsUnitTypes.LayoutUnit.LayoutMillimeters))
            _flat_fill(frosted_panel, WHITE)
            self.layout.addLayoutItem(frosted_panel)
        # The template panel is quite translucent (0.76); over the dark cover
        # artwork that muddies to blue-grey and dark text loses contrast.
        frosted_panel.setItemOpacity(0.94)
        panel_pos = frosted_panel.positionWithUnits()
        panel_size = frosted_panel.sizeWithUnits()
        x, y = panel_pos.x(), panel_pos.y()
        w, h = panel_size.width(), panel_size.height()
        title = self._label(
            title_text,
            x + 6,
            y + 3.5,
            w - 12,
            h - 13,
            0,
            size=16.5,
            color=NAVY,
            bold=True,
            halign=Qt.AlignmentFlag.AlignHCenter,
            valign=Qt.AlignmentFlag.AlignVCenter,
        )
        title.setMarginY(0)
        subtitle = self._label(
            self.report_name,
            x + 6,
            y + h - 9,
            w - 12,
            6,
            0,
            size=10.5,
            color=GREY,
            halign=Qt.AlignmentFlag.AlignHCenter,
        )
        # Template items stack up to zValue 11; keep the text above the panel.
        title.setZValue(frosted_panel.zValue() + 1)
        subtitle.setZValue(frosted_panel.zValue() + 1)

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
            self._label(
                title,
                MARGIN,
                18,
                CONTENT_W,
                14,
                current_page,
                size=18,
                color=NAVY,
                bold=True,
            )
        description_text = self.page_descriptions.get(description_key, "")
        if description_text.strip():
            description_label = self._label(
                description_text,
                MARGIN,
                HEADER_H + 6,
                CONTENT_W,
                18,
                current_page,
                size=9.5,
                color=GREY,
                html=True,
            )
            description_label.setHAlign(Qt.AlignmentFlag.AlignJustify)
        return page

    def make_text_table(self, vector_layer: QgsVectorLayer, sort_column: str, current_page: int, start_y: float = 64):
        """Draw a duration table as zebra rows with proportional bars.

        A hand-drawn table (QgsLayoutItemAttributeTable crashes QGIS 3.42)
        in the same visual language as the analysis report's processing
        times page: name right-aligned in the left column, a cyan bar
        scaled to the longest duration, and the value alongside.
        """
        row_pitch = 7
        bar_h = 3.6
        label_w = 72
        bar_x = MARGIN + label_w + 5
        bar_max_w = PAGE_W - MARGIN - bar_x - 22
        max_rows = int((272 - start_y) / row_pitch)

        request = QgsFeatureRequest()
        clause = QgsFeatureRequest.OrderByClause(sort_column, ascending=False)
        request.setOrderBy(QgsFeatureRequest.OrderBy([clause]))
        rows = [(feat["area_name"], float(feat[sort_column] or 0)) for feat in vector_layer.getFeatures(request)]
        if not rows:
            return
        longest = max(duration for _, duration in rows) or 1.0

        self._label(
            "Area",
            MARGIN,
            start_y - 6,
            label_w,
            5,
            current_page,
            size=8,
            color=GREY,
            bold=True,
            halign=Qt.AlignmentFlag.AlignRight,
        )
        self._label(
            "Processing time",
            bar_x,
            start_y - 6,
            60,
            5,
            current_page,
            size=8,
            color=GREY,
            bold=True,
        )
        for i, (name, duration) in enumerate(rows[:max_rows]):
            y = start_y + i * row_pitch
            if i % 2 == 0:
                self._rect(MARGIN, y - 1.2, CONTENT_W, row_pitch - 1, MIST, current_page)
            self._label(
                str(name),
                MARGIN,
                y,
                label_w,
                5,
                current_page,
                size=8.5,
                color=CHARCOAL,
                halign=Qt.AlignmentFlag.AlignRight,
            )
            self._rect(bar_x, y + (5 - bar_h) / 2, max(bar_max_w * duration / longest, 0.8), bar_h, CYAN, current_page)
            self._label(
                f"{duration:.2f} s",  # noqa E231
                bar_x + bar_max_w + 2,
                y,
                20,
                5,
                current_page,
                size=8,
                color=GREY,
            )
        if len(rows) > max_rows:
            self._label(
                f"… and {len(rows) - max_rows} more areas not shown",
                MARGIN,
                start_y + max_rows * row_pitch + 2,
                CONTENT_W,
                5,
                current_page,
                size=8,
                color=GREY,
            )

    def make_map(
        self,
        layers: list[QgsMapLayer],
        crs,
        current_page: int,
        x: float = MARGIN,
        y: float = 34,
        map_width_mm: float = CONTENT_W,
        map_height_mm: float = 150,
        show_annotations: bool = True,
    ):
        """Add a map to the layout.

        Args:
            layers: Layers to render (top first).
            crs: CRS of the extent calculation.
            current_page: Page to place the map on.
            x, y: Top-left position in mm.
            map_width_mm, map_height_mm: Map size in mm.
            show_annotations: When True, draw frame-edge coordinate
                annotations; minimaps switch this off for a clean look.
        """
        # Get the current extent of all the layers
        layers_extent = QgsRectangle()
        for layer in layers:
            # On Windows, GeoPackage layers can have stale extents right after
            # study area creation. Force the provider to reload data and recompute.
            try:
                layer.dataProvider().reloadData()
                layer.updateExtents()
            except Exception:  # nosec B110
                pass
            layers_extent.combineExtentWith(layer.extent())

        map_item = QgsLayoutItemMap(self.layout)
        # Calculate the aspect ratio of the layer's extent
        layer_aspect_ratio = layers_extent.width() / layers_extent.height()
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
            QgsLayoutPoint(x, y, QgsUnitTypes.LayoutUnit.LayoutMillimeters),
            page=current_page,
        )

        map_item.attemptResize(QgsLayoutSize(map_width_mm, map_height_mm, QgsUnitTypes.LayoutUnit.LayoutMillimeters))

        # ⚠️ Ordering matters for thread safety: the report is built inside a
        # QgsTask worker thread, and mutating CRS/extent on a map item that
        # is not yet part of the layout spawns render objects parented across
        # threads ("QObject::setParent ... different thread" warnings
        # followed by a segfault). Add the item to the layout FIRST, then
        # configure it, then attach the grid (after the extent is valid so
        # proj never sees the default infinite extent).
        self.layout.addLayoutItem(map_item)
        # Thin charcoal neatline around the map
        map_item.setFrameEnabled(True)
        map_item.setFrameStrokeColor(CHARCOAL)
        map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.3))
        # The map is pinned to the data CRS: transforming into the *project*
        # CRS hangs inside proj when the project has no CRS set (headless
        # report generation, fresh projects) and made report maps depend on
        # whatever CRS the user's project happened to use.
        map_item.setCrs(crs)
        map_item.setExtent(new_extent)

        if show_annotations:
            # Clean neatline: coordinate ticks on the frame edges only — no
            # crosses or lines across the map face.
            grid = QgsLayoutItemMapGrid("Grid 1", map_item)
            grid.setEnabled(True)
            grid.setCrs(geo_crs)

            def round_down_to_sig_fig(value: float) -> float:
                if value == 0 or math.isnan(value) or math.isinf(value):
                    return 1.0  # fallback grid interval for invalid extents
                exp = math.floor(math.log10(abs(value)))
                factor = 10**exp
                return math.floor(value / factor * 10) / 10 * factor

            interval_x = round_down_to_sig_fig(geo_extent.width() / 4.0)
            interval_y = round_down_to_sig_fig(geo_extent.height() / 4.0)
            grid.setIntervalX(interval_x)
            grid.setIntervalY(interval_y)

            # Bottom shows longitude horizontally, left shows latitude
            # vertically, both OUTSIDE the frame so labels never overlap the
            # map face; the opposite edges stay clean.
            grid.setAnnotationDirection(QgsLayoutItemMapGrid.Horizontal, QgsLayoutItemMapGrid.Bottom)
            grid.setAnnotationDirection(QgsLayoutItemMapGrid.Vertical, QgsLayoutItemMapGrid.Left)
            grid.setAnnotationPosition(QgsLayoutItemMapGrid.OutsideMapFrame, QgsLayoutItemMapGrid.Bottom)
            grid.setAnnotationPosition(QgsLayoutItemMapGrid.OutsideMapFrame, QgsLayoutItemMapGrid.Left)
            grid.setAnnotationDisplay(QgsLayoutItemMapGrid.DisplayMode.LongitudeOnly, QgsLayoutItemMapGrid.Bottom)
            grid.setAnnotationDisplay(QgsLayoutItemMapGrid.DisplayMode.HideAll, QgsLayoutItemMapGrid.Top)
            grid.setAnnotationDisplay(QgsLayoutItemMapGrid.DisplayMode.LatitudeOnly, QgsLayoutItemMapGrid.Left)
            grid.setAnnotationDisplay(QgsLayoutItemMapGrid.DisplayMode.HideAll, QgsLayoutItemMapGrid.Right)
            grid.setAnnotationEnabled(True)
            grid.setStyle(QgsLayoutItemMapGrid.GridStyle.FrameAnnotationsOnly)
            grid.setAnnotationTextFormat(self._text_format(7, GREY))
            grid.setFramePenSize(0.2)
            map_item.grids().addGrid(grid)

        map_item.refresh()

    def make_minimap(
        self,
        caption: str,
        layers: list[QgsMapLayer],
        crs,
        current_page: int,
        x: float,
        y: float,
        w: float,
        h: float,
    ) -> None:
        """Add a small captioned map: clean face (no grid), thin neatline.

        Args:
            caption: Short label rendered beneath the map.
            layers: Layers to render.
            crs: CRS for extent calculation.
            current_page: Page to place the minimap on.
            x, y: Top-left position in mm.
            w, h: Total cell size in mm (map + caption).
        """
        caption_h = 7
        self.make_map(
            layers=layers,
            crs=crs,
            current_page=current_page,
            x=x,
            y=y,
            map_width_mm=w,
            map_height_mm=h - caption_h,
            show_annotations=False,
        )
        self._label(
            caption,
            x,
            y + h - caption_h + 1,
            w,
            caption_h,
            current_page,
            size=8,
            color=GREY,
            halign=Qt.AlignmentFlag.AlignHCenter,
        )

    def _text_format(self, size: float, color: QColor, bold: bool = False) -> QgsTextFormat:
        """Build a flat text format in the report typeface."""
        text_format = QgsTextFormat()
        font = QFont("Arial")
        font.setBold(bold)
        text_format.setFont(font)
        text_format.setSize(size)
        text_format.setSizeUnit(QgsUnitTypes.RenderUnit.RenderPoints)
        text_format.setColor(color)
        return text_format

    def _rect(self, x: float, y: float, w: float, h: float, color: QColor, page: int) -> None:
        """Add a flat rectangle to the layout."""
        shape = QgsLayoutItemShape(self.layout)
        shape.setShapeType(QgsLayoutItemShape.Rectangle)
        shape.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutUnit.LayoutMillimeters), page=page)
        shape.setFixedSize(QgsLayoutSize(w, h, QgsUnitTypes.LayoutUnit.LayoutMillimeters))
        _flat_fill(shape, color)
        self.layout.addLayoutItem(shape)

    def _label(
        self,
        text: str,
        x: float,
        y: float,
        w: float,
        h: float,
        page: int,
        size: float = 10,
        color: QColor = CHARCOAL,
        bold: bool = False,
        halign=Qt.AlignmentFlag.AlignLeft,
        valign=Qt.AlignmentFlag.AlignTop,
        html: bool = False,
    ) -> QgsLayoutItemLabel:
        """Add a text label to the layout and return it."""
        label = QgsLayoutItemLabel(self.layout)
        label.setText(text)
        if html:
            label.setMode(QgsLayoutItemLabel.ModeHtml)
        label.setTextFormat(self._text_format(size, color, bold))
        label.setFixedSize(QgsLayoutSize(w, h, QgsUnitTypes.LayoutUnit.LayoutMillimeters))
        label.setHAlign(halign)
        label.setVAlign(valign)
        label.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutUnit.LayoutMillimeters), page=page)
        self.layout.addLayoutItem(label)
        return label

    def make_header(self, current_page: int, title: str = ""):
        """Add a flat header band with the page title.

        Args:
            current_page (int): The current page number.
            title (str, optional): The title to display in the header. Defaults to "".
        """
        self._rect(0, 0, PAGE_W, HEADER_H, NAVY, current_page)
        self._rect(0, HEADER_H, PAGE_W, 1.2, CYAN, current_page)
        self._label(
            title,
            MARGIN,
            0,
            CONTENT_W - 40,
            HEADER_H,
            current_page,
            size=15,
            color=WHITE,
            bold=True,
            valign=Qt.AlignmentFlag.AlignVCenter,
        )
        self._label(
            self.report_name,
            PAGE_W - MARGIN - 60,
            0,
            60,
            HEADER_H,
            current_page,
            size=8,
            color=QColor("#9FC5DE"),
            halign=Qt.AlignmentFlag.AlignRight,
            valign=Qt.AlignmentFlag.AlignVCenter,
        )

    def make_footer(self, current_page: int):
        """Add a minimal footer: hairline, running title and page number."""
        self._rect(MARGIN, FOOTER_Y, CONTENT_W, 0.3, RULE, current_page)
        self._label(
            "GeoE3 — Geospatial Enabling Environments for Employment",
            MARGIN,
            FOOTER_Y + 1.5,
            CONTENT_W - 30,
            6,
            current_page,
            size=7.5,
            color=GREY,
        )
        self._label(
            f"Page {current_page}",
            PAGE_W - MARGIN - 30,
            FOOTER_Y + 1.5,
            30,
            6,
            current_page,
            size=7.5,
            color=GREY,
            halign=Qt.AlignmentFlag.AlignRight,
        )

    def add_header_and_footer(self, page_number, title: str = ""):
        """Add the standard page furniture (header band + minimal footer).

        The funding and data attribution text lives on the credits page (see
        make_credits_page) instead of being repeated on every page.

        Args:
            page_number: Page to decorate.
            title (str, optional): Header title. Defaults to "".
        """
        self.make_header(page_number, title)
        self.make_footer(page_number)

    def make_credits_page(self, current_page: int) -> None:
        """Add the credits page: funders, developers and data attribution.

        Sits directly behind the cover, giving the people and institutions
        that make the tool possible a prominent, designed home rather than a
        footnote at the back of the report.
        """
        self.make_page(
            title="Credits",
            description_key="__no_description__",
            current_page=current_page,
            show_header_and_footer=True,
        )
        lead = self._label(
            "GeoE3 — Geospatial Enabling Environments for Employment — is an "
            "open-source QGIS plugin developed by The World Bank to evaluate how "
            "supportive locations are of employment and business opportunities.",
            MARGIN,
            HEADER_H + 10,
            CONTENT_W,
            16,
            current_page,
            size=10.5,
            color=GREY,
        )
        lead.setHAlign(Qt.AlignmentFlag.AlignJustify)

        def credit_card(y: float, h: float, heading: str, body: str) -> None:
            """A flat panel with a cyan accent bar, heading and body text."""
            self._rect(MARGIN, y, CONTENT_W, h, MIST, current_page)
            self._rect(MARGIN, y, 2.2, h, CYAN, current_page)
            self._label(
                heading,
                MARGIN + 8,
                y + 4.5,
                CONTENT_W - 16,
                7,
                current_page,
                size=12,
                color=NAVY,
                bold=True,
            )
            body_label = self._label(
                body,
                MARGIN + 8,
                y + 13,
                CONTENT_W - 16,
                h - 17,
                current_page,
                size=9.5,
                color=CHARCOAL,
                html=True,
            )
            body_label.setHAlign(Qt.AlignmentFlag.AlignJustify)

        credit_card(
            54,
            36,
            "Funding partners",
            "<p>Built with the generous support of the <strong>Canada Clean Energy and "
            "Forest Climate Facility (CCEFCF)</strong> and the <strong>Global Data "
            "Facility (GDF)</strong>, for the project <em>Geospatial Assessment of "
            "Employment and Business Opportunities in the Renewable Energy "
            "Sector</em>.</p>",
        )
        credit_card(
            98,
            36,
            "Developed by",
            "<p>Designed and directed by the <strong>Geospatial Operational Support "
            "Team (GOST)</strong> in the <strong>Development Economics Data Group "
            "(DECDG)</strong> of The World Bank, and built together with "
            '<a href="https://kartoza.com">Kartoza</a>.</p>',
        )
        credit_card(
            142,
            26,
            "Open source",
            "<p>GeoE3 is free and open-source software. Source code, documentation "
            "and the issue tracker live at "
            '<a href="https://github.com/worldbank/GeoE3">github.com/worldbank/GeoE3</a>.</p>',
        )
        credit_card(
            176,
            40,
            "Data attribution",
            "<p>Analysis workflows may include data and services from OpenStreetMap, "
            "OpenRouteService, GHSL, Ookla Open Data, Space2Stats, ACLED, VIIRS "
            "Nighttime Lights, and user-supplied datasets. Please review source "
            "terms and citation requirements before republication.</p>",
        )
        self._label(
            "Generated with GeoE3 for The World Bank",
            MARGIN,
            230,
            CONTENT_W,
            6,
            current_page,
            size=8.5,
            color=GREY,
            halign=Qt.AlignmentFlag.AlignHCenter,
        )

    def export_pdf(self, output_path, dpi=None):
        """
        Export the current layout as a PDF file in raster mode.

        Parameters:
            output_path (str): The full file path (including filename) for the output PDF.
            dpi (int, optional): Export resolution override. Lower values
                (e.g. 96) give fast, small draft exports.

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
        if dpi:
            export_settings.dpi = dpi
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
