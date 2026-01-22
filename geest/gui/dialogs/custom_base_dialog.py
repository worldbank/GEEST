# -*- coding: utf-8 -*-
"""📦 Custom Base Dialog module.

This module contains functionality for custom base dialog.
"""

from qgis.PyQt.QtCore import QRect, Qt
from qgis.PyQt.QtGui import QPainter
from qgis.PyQt.QtWidgets import QDialog

from geest.utilities import theme_background_image, theme_stylesheet


class CustomBaseDialog(QDialog):
    """Custom base dialog with a paintEvent for background image support."""

    def __init__(self, parent=None):
        """🏗️ Initialize the instance.

        Args:
            parent: Parent.
        """
        super().__init__(parent)
        # Load the background image (drawn in paintEvent)
        self.background_image = theme_background_image()
        self.setStyleSheet(theme_stylesheet())

    def paintEvent(self, event):
        """⚙️ Paintevent.

        Args:
            event: Event.
        """
        with QPainter(self) as painter:
            # Scale the background image to match the dialog height
            scaled_background = self.background_image.scaledToHeight(self.height(), Qt.SmoothTransformation)

            # Draw the image anchored to the right
            painter.drawPixmap(self.width() - scaled_background.width(), 0, scaled_background)

            # Fill the remaining area with the original background color
            painter.fillRect(
                QRect(0, 0, self.width() - scaled_background.width(), self.height()),
                self.palette().window(),
            )

        super().paintEvent(event)
