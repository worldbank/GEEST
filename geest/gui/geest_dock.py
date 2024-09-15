from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QTreeView,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QWidget,
    QLabel,
    QMenu,
    QAction,
    QMessageBox,
    QFileDialog,
    QHeaderView,
    QTreeView,
    QMenu,
    QCheckBox,  # Add QCheckBox for Edit Toggle
)
from qgis.PyQt.QtCore import QPoint, Qt, QTimer
from qgis.PyQt.QtGui import QMovie
import json
import os
from .geest_treeview import CustomTreeView, JsonTreeModel
from .setup_panel import SetupPanel
from .tree_panel import TreePanel
from .layer_detail_dialog import LayerDetailDialog
from ..utilities import resources_path


class GeestDock(QDockWidget):
    def __init__(self, parent=None, json_file=None):
        super().__init__(parent)

        self.json_file = json_file
        self.tree_view_visible = False
        widget = QWidget()
        layout = QVBoxLayout(widget)
        button_bar = QHBoxLayout()

        # setup instance (hidden by default)
        self.setup_widget = SetupPanel()
        self.setup_widget.setVisible(True)
        layout.addWidget(self.setup_widget)

        self.tree_widget = TreePanel()
        self.tree_widget.setVisible(False)
        layout.addWidget(self.tree_widget)
        # Button to toggle between Tree View and Setup Panel
        self.toggle_view_button = QPushButton("⚙️ Setup")
        self.toggle_view_button.clicked.connect(self.toggle_view)

        button_bar.addWidget(self.toggle_view_button)
        layout.addLayout(button_bar)

        widget.setLayout(layout)
        self.setWidget(widget)
        self.toggle_view()  # start in on start panel

    def toggle_view(self):
        """Toggle between the tree view and the GeospatialWidget."""
        if self.tree_view_visible:
            self.tree_widget.setVisible(False)
            self.setup_widget.setVisible(True)
            self.toggle_view_button.setText("Tree")
        else:
            self.tree_widget.setVisible(True)
            self.setup_widget.setVisible(False)
            self.toggle_view_button.setText("Setup")

        self.tree_view_visible = not self.tree_view_visible
