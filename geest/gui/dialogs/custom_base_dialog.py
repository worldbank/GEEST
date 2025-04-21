from qgis.PyQt.QtGui import QPixmap, QPainter
from qgis.PyQt.QtCore import QRect, Qt
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout
from geest.utilities import (
    theme_stylesheet,
    theme_background_image,
)


class CustomBaseDialog(QDialog):
    """Custom base dialog with a paintEvent for background image support."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Load the background image (drawn in paintEvent)
        self.background_image = theme_background_image()
        self.setStyleSheet(theme_stylesheet())

    def paintEvent(self, event):
        with QPainter(self) as painter:
            # Scale the background image to match the dialog height
            scaled_background = self.background_image.scaledToHeight(
                self.height(), Qt.SmoothTransformation
            )

            # Draw the image anchored to the right
            painter.drawPixmap(
                self.width() - scaled_background.width(), 0, scaled_background
            )

            # Fill the remaining area with the original background color
            painter.fillRect(
                QRect(0, 0, self.width() - scaled_background.width(), self.height()),
                self.palette().window(),
            )

        super().paintEvent(event)
