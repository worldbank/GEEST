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

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont, QPainter, QPixmap
from qgis.PyQt.QtWidgets import QLabel, QSizePolicy


class CustomBannerLabel(QLabel):
    """🎯 Custom Banner Label.
    
    Attributes:
        banner_pixmap: Banner pixmap.
        text: Text.
    """
    def __init__(self, text, banner_path, parent=None):
        """🏗️ Initialize the instance.
        
        Args:
            text: Text.
            banner_path: Banner path.
            parent: Parent.
        """
        super().__init__(parent)
        self.text = text
        self.banner_pixmap = QPixmap(banner_path)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(self.banner_pixmap.height())

    def paintEvent(self, event):
        """⚙️ Paintevent.
        
        Args:
            event: Event.
        """
        painter = QPainter(self)

        # Draw the banner image
        painter.drawPixmap(self.rect(), self.banner_pixmap)

        # Draw the title text
        painter.setPen(QColor("white"))
        text_rect = self.rect().adjusted(10, 0, -10, -5)
        # Scale the font size to fit the text in the available space
        font_size = 16
        threshold = 430
        # log_message(f"Banner Label Width: {self.rect().width()}")
        if self.rect().width() < threshold:
            font_size = int(14 * (self.rect().width() / threshold))
        # log_message(f"Font Size: {font_size}")
        painter.setFont(QFont("Arial", font_size))
        painter.drawText(text_rect, Qt.AlignCenter | Qt.AlignBottom, self.text)

        painter.end()
