# -*- coding: utf-8 -*-
"""📦 Layer Description module.

This module contains functionality for layer description.
"""

from qgis.gui import QgsMapCanvasItem
from qgis.PyQt.QtCore import QRectF, QSettings, Qt
from qgis.PyQt.QtGui import QColor, QFont, QIcon, QPainter

from geest.core.settings import setting

from ...utilities import resources_path

"""
An overlay item for the QGIS map canvas.

It will show geoe3 lablel on top of the map canvas,
showing which layer is active etc.
"""


class LayerDescriptionItem(QgsMapCanvasItem):
    """🎯 Layer Description Item."""

    def __init__(self, canvas):
        """🏗️ Initialize the instance.

        Args:
            canvas: Canvas.
        """
        super().__init__(canvas)
        self.setZValue(1000)  # Draw on top

    def paint(self, painter: QPainter, option=None, widget=None):
        """⚙️ Paint.

        Args:
            painter: Painter.
            option: Option.
            widget: Widget.
        """
        # TEMPORARY: Disable the top-left layer description overlay.
        # Re-enable the block below when issue triage is complete.
        return

        # show_overlay = setting(key="show_overlay", default=False)
        # if not show_overlay:
        #     return
        # # Get the label text from QSettings
        # label_text = QSettings().value("geoe3/overlay_label", "")
        # if not label_text:
        #     return
        # painter.setPen(QColor(0, 0, 0))
        # font = QFont("Arial", 12, QFont.Bold)
        # painter.setFont(font)
        # painter.setRenderHint(QPainter.Antialiasing)
        # rect_x = 10
        # rect_y = 10
        # # Calculate width based on text
        # font_metrics = painter.fontMetrics()
        # text_width = font_metrics.horizontalAdvance(label_text)
        # text_height = font_metrics.height()
        # padding = 10  # Add some padding
        #
        # # Load geoe3 logo as SVG
        # icon = QIcon(resources_path("resources", "geoe3-main.svg"))
        # logo_x = 0
        # logo_y = 0
        # logo_width = 0
        # if not icon.isNull():
        #     # Get pixmap from icon scaled to match text height
        #     scaled_logo = icon.pixmap(text_height, text_height)
        #     logo_width = scaled_logo.width()
        #     logo_height = scaled_logo.height()
        #     rect = QRectF(
        #         rect_x,
        #         rect_y,
        #         padding + logo_width + padding + text_width + padding,
        #         50,
        #     )
        #
        #     # Draw the logo on the left side of the rectangle
        #     logo_x = int(rect_x + padding)
        #     logo_y = int(rect_y + (rect.height() - logo_height) / 2)
        # else:
        #     rect = QRectF(10, 10, text_width + padding, 50)
        #
        # painter.fillRect(rect, QColor(255, 255, 255, 128))
        # painter.drawRect(rect)
        #
        # if not icon.isNull():
        #     painter.drawPixmap(logo_x, logo_y, scaled_logo)
        # # Modify the rectangle for text to start after the logo
        # new_left = logo_x + scaled_logo.width()
        # rect.setLeft(new_left)
        # # Set white background with 50% transparency
        # painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label_text)
