# -*- coding: utf-8 -*-
"""📦 Toggle Switch module.

This module contains functionality for toggle switch.
"""
from qgis.PyQt.QtCore import QRect, QSize, pyqtSignal
from qgis.PyQt.QtGui import QColor, QPainter
from qgis.PyQt.QtWidgets import QWidget


class ToggleSwitch(QWidget):
    """Custom Toggle Switch with a modern design."""

    toggled = pyqtSignal(bool)

    def __init__(self, initial_value=False, parent=None):
        """🏗️ Initialize the instance.

        Args:
            initial_value: Initial value.
            parent: Parent.
        """
        super().__init__(parent)
        self.setFixedSize(QSize(60, 26))  # Size of the toggle switch
        self.checked = initial_value

    def paintEvent(self, event):
        """Draw the toggle switch with a modern design.

        Args:
            event: The paint event.
        """
        painter = QPainter(self)
        rect = self.rect()

        # Background color based on state
        if self.checked:
            painter.setBrush(QColor("#fffdcf"))  # Active state color (blue) from WB Style Guide
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
        """Toggle the switch on mouse click.

        Args:
            event: The mouse press event.
        """
        self.checked = not self.checked
        self.toggled.emit(self.checked)
        self.update()

    def isChecked(self):
        """Return the current state of the toggle.

        Returns:
            bool: True if the toggle is checked, False otherwise.
        """
        return self.checked

    def setChecked(self, checked):
        """Set the state of the toggle and update the UI.

        Args:
            checked: The new checked state for the toggle.
        """
        if self.checked != checked:
            self.checked = checked
            self.update()
