from qgis.PyQt.QtWidgets import (
    QLabel,
    QSizePolicy,
)
from qgis.PyQt.QtGui import QPixmap, QPainter, QColor, QFont
from qgis.PyQt.QtCore import Qt


class CustomBannerLabel(QLabel):
    def __init__(self, text, banner_path, parent=None):
        super().__init__(parent)
        self.text = text
        self.banner_pixmap = QPixmap(banner_path)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(self.banner_pixmap.height())

    def paintEvent(self, event):
        painter = QPainter(self)

        # Draw the banner image
        painter.drawPixmap(self.rect(), self.banner_pixmap)

        # Draw the title text
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Arial", 16))
        text_rect = self.rect().adjusted(10, 0, -10, -5)
        painter.drawText(text_rect, Qt.AlignCenter | Qt.AlignBottom, self.text)

        painter.end()
