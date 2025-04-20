from qgis.PyQt.QtWidgets import QMenu, QStyleOptionMenuItem, QStylePainter
from qgis.PyQt.QtGui import QColor
from geest.utilities import (
    is_qgis_dark_theme_active,
    menu_stylesheet,
    menu_stylesheet_dark,
)


class SolidMenu(QMenu):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if is_qgis_dark_theme_active():
            self.setStyleSheet(menu_stylesheet_dark)
        else:
            self.setStyleSheet(menu_stylesheet)

    def paintEvent(self, event):
        painter = QStylePainter(self)
        opt = QStyleOptionMenuItem()
        opt.initFrom(self)
        if is_qgis_dark_theme_active():
            painter.fillRect(self.rect(), QColor("#ffffff"))  # force background
        else:
            painter.fillRect(self.rect(), QColor("#ff0fff"))  # force background
        super().paintEvent(event)
