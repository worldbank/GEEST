# -*- coding: utf-8 -*-
"""GEEST GUI widgets."""

__copyright__ = "Copyright 2022, Tim Sutton"
__license__ = "GPL version 3"
__email__ = "tim@kartoza.com"
__revision__ = "$Format:%H$"

# -----------------------------------------------------------
# Copyright (C) 2022 Tim Sutton
# -----------------------------------------------------------
# Licensed under the terms of GNU GPL 3
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# ---------------------------------------------------------------------

from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QMenu, QStyleOptionMenuItem, QStylePainter

from geest.utilities import is_qgis_dark_theme_active, theme_stylesheet


class SolidMenu(QMenu):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet(theme_stylesheet())

    def paintEvent(self, event):
        painter = QStylePainter(self)
        opt = QStyleOptionMenuItem()
        opt.initFrom(self)
        if is_qgis_dark_theme_active():
            painter.fillRect(self.rect(), QColor("#ffffff"))  # force background
        else:
            painter.fillRect(self.rect(), QColor("#ff0fff"))  # force background
        super().paintEvent(event)
