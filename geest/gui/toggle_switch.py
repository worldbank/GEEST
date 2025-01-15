from qgis.PyQt.QtWidgets import QWidget
from qgis.PyQt.QtCore import Qt, pyqtSignal, QSize, QRect
from qgis.PyQt.QtGui import QColor, QPainter


class ToggleSwitch(QWidget):
    """Custom Toggle Switch with a modern design."""

    toggled = pyqtSignal(bool)

    def __init__(self, initial_value=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(QSize(60, 26))  # Size of the toggle switch
        self.checked = initial_value

    def paintEvent(self, event):
        """Draw the toggle switch with a modern design."""
        painter = QPainter(self)
        rect = self.rect()

        # Background color based on state
        if self.checked:
            painter.setBrush(
                QColor("#fffdcf")
            )  # Active state color (blue) from WB Style Guide
        else:
            painter.setBrush(QColor("#fffdcf"))  # Inactive state color (gray)

        # Draw the rounded rectangle as the background
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawRoundedRect(rect, rect.height() // 4, rect.height() // 4)

        # Draw the circle (slider knob)
        knob_radius = rect.height() // 4
        knob_x = rect.x() if not self.checked else rect.right() - 30
        knob_rect = QRect(knob_x, rect.y(), 30, 26)
        # knob_rect.setWidth(30)
        painter.setBrush(QColor("#6FB7B5"))  # From WB Style Guide
        painter.drawRoundedRect(knob_rect, knob_radius, knob_radius)

    def mousePressEvent(self, event):
        """Toggle the switch on mouse click."""
        self.checked = not self.checked
        self.toggled.emit(self.checked)
        self.update()

    def isChecked(self):
        """Return the current state of the toggle."""
        return self.checked

    def setChecked(self, checked):
        """Set the state of the toggle and update the UI."""
        if self.checked != checked:
            self.checked = checked
            self.update()
