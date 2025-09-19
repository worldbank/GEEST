import math

from qgis.gui import QgsMapCanvasItem
from qgis.PyQt.QtCore import QRectF, Qt
from qgis.PyQt.QtGui import QColor, QFont, QImage, QPainter

from geest.core.settings import setting

"""
A pie chart overlay item for the QGIS map canvas.

It will show a pie chart for the current layer indicating the relative
proportions of different categories in the data.
"""


class PieChartItem(QgsMapCanvasItem):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.setZValue(1000)  # Draw on top
        # self.counts = QSettings().value("geest/pie_data", None)
        self.counts = [10, 20, 30, 40, 50, 60]
        labels = ["0–0.5", "0.5–1.5", "1.5–2.5", "2.5–3.5", "3.5–4.5", "4.5–5.0"]
        self.labels = labels or [str(i) for i in range(len(self.counts))]
        colors = [
            QColor("#d7191c"),  # red
            QColor("#fdae61"),  # orange
            QColor("#ffffbf"),  # yellow
            QColor("#d1eeea"),  # light blue
            QColor("#abd9e9"),  # medium blue
            QColor("#2c7bb6"),  # dark blue
        ]
        self.colors = colors or [
            Qt.red,
            Qt.blue,
            Qt.green,
            Qt.yellow,
            Qt.cyan,
            Qt.magenta,
        ]

    def paint(self, painter: QPainter, option=None, widget=None):
        """Create a pie chart as a QImage with the specified diameter.

        This is called by QGIS to render a QgsMapCanvasItem.
        """
        show_overlay = setting(key="show_pie_overlay", default=False)
        if not show_overlay:
            return
        diameter = 100
        image = QImage(diameter, diameter, QImage.Format_ARGB32)
        image.fill(Qt.white)

        chart_x = painter.device().width() - (diameter + 20)
        chart_y = 10
        rect = QRectF(chart_x, chart_y, diameter, diameter)
        self.painter = painter
        self.draw(rect)

    def draw(self, rect):
        """This is the actual drawing method for the pie chart."""
        total = sum(self.counts)
        start_angle = 0
        # Find the largest slice
        max_count = max(self.counts)
        max_index = self.counts.index(max_count)
        # Draw drop shadow
        shadow_offset = 5
        _ = QRectF(  # shadow rectangle, not used further
            rect.x() + shadow_offset,
            rect.y() + shadow_offset,
            rect.width(),
            rect.height(),
        )
        for i, count in enumerate(self.counts):
            if i == max_index:
                continue  # Skip the largest slice for the initial pie chart
            angle_span = 360 * count / total
            self.painter.setPen(Qt.NoPen)
            self.painter.setBrush(self.colors[i % len(self.colors)])
            self.painter.drawPie(rect, int(start_angle * 16), int(angle_span * 16))
            # Draw drop shadow for each slice
            self.painter.setBrush(Qt.gray)

            self.painter.setOpacity(0.3)
            self.painter.drawPie(rect, int(start_angle * 16), int(angle_span * 16))

            self.painter.setOpacity(1.0)
            start_angle += angle_span

        # Draw exploded largest slice
        start_angle = 0
        explode_distance = 4

        for i, count in enumerate(self.counts):
            angle_span = 360 * count / total

            if i == max_index:
                # Calculate explode offset
                mid_angle = start_angle + angle_span / 2
                explode_x = explode_distance * math.cos(math.radians(-mid_angle))
                explode_y = explode_distance * math.sin(math.radians(-mid_angle))
                exploded_rect = QRectF(
                    rect.x() + explode_x,
                    rect.y() + explode_y,
                    rect.width(),
                    rect.height(),
                )

                # Draw drop shadow for exploded slice
                shadow_offset = 3
                shadow_exploded_rect = QRectF(
                    rect.x() + explode_x + shadow_offset,
                    rect.y() + explode_y + shadow_offset,
                    rect.width(),
                    rect.height(),
                )
                self.painter.setBrush(Qt.gray)
                self.painter.setPen(Qt.NoPen)
                self.painter.setOpacity(0.3)
                self.painter.drawPie(
                    shadow_exploded_rect, int(start_angle * 16), int(angle_span * 16)
                )
                self.painter.setOpacity(1.0)

                # Draw the exploded slice
                self.painter.setBrush(self.colors[i % len(self.colors)])
                self.painter.setPen(Qt.NoPen)
                self.painter.drawPie(
                    exploded_rect, int(start_angle * 16), int(angle_span * 16)
                )

                # Label at the end of exploded slice
                radius = min(rect.width(), rect.height()) / 2
                label_x = (
                    rect.center().x()  # noqa W503
                    + explode_x  # noqa W503
                    + radius * math.cos(math.radians(-mid_angle))  # noqa W503
                )
                label_y = (
                    rect.center().y()  # noqa W503
                    + explode_y  # noqa W503
                    + radius * math.sin(math.radians(-mid_angle))  # noqa W503
                )

                self.painter.setPen(Qt.black)
                self.painter.setFont(QFont("Arial", 8))
                self.painter.drawText(int(label_x), int(label_y), self.labels[i])

            start_angle += angle_span
