from qgis.gui import QgsMapCanvasItem
from qgis.PyQt.QtGui import QPainter, QColor, QFont
from qgis.PyQt.QtCore import QRectF, Qt

"""
An overlay item for the QGIS map canvas.

It will show geest lablel on top of the map canvas,
showing which layer is active etc.
"""
from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtGui import QPixmap, QImage, QIcon, QPainter
from ...utilities import resources_path
from geest.core import (
    setting,
)


class LayerDescriptionItem(QgsMapCanvasItem):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.setZValue(1000)  # Draw on top

    def paint(self, painter: QPainter, option=None, widget=None):
        show_overlay = setting(key="show_overlay", default=False)
        if not show_overlay:
            return
        # Get the label text from QSettings
        label_text = QSettings().value("geest/overlay_label", "Geest Overlay")
        painter.setPen(QColor(0, 0, 0))
        font = QFont("Arial", 12, QFont.Bold)
        painter.setFont(font)
        painter.setRenderHint(QPainter.Antialiasing)
        rect_x = 10
        rect_y = 10
        # Calculate width based on text
        font_metrics = painter.fontMetrics()
        text_width = font_metrics.horizontalAdvance(label_text)
        text_height = font_metrics.height()
        padding = 10  # Add some padding

        # Load geest logo as SVG
        icon = QIcon(resources_path("resources", "geest-main.svg"))
        logo_x = 0
        logo_y = 0
        logo_width = 0
        if not icon.isNull():
            # Get pixmap from icon scaled to match text height
            scaled_logo = icon.pixmap(text_height, text_height)
            logo_width = scaled_logo.width()
            logo_height = scaled_logo.height()
            rect = QRectF(
                rect_x,
                rect_y,
                padding + logo_width + padding + text_width + padding,
                50,
            )

            # Draw the logo on the left side of the rectangle
            logo_x = int(rect_x + padding)
            logo_y = int(rect_y + (rect.height() - logo_height) / 2)
        else:
            rect = QRectF(10, 10, text_width + padding, 50)

        painter.fillRect(rect, QColor(255, 255, 255, 128))
        painter.drawRect(rect)

        if not icon.isNull():
            painter.drawPixmap(logo_x, logo_y, scaled_logo)
        # Modify the rectangle for text to start after the logo
        new_left = logo_x + scaled_logo.width()
        rect.setLeft(new_left)
        # Set white background with 50% transparency
        painter.drawText(rect, Qt.AlignCenter, label_text)
