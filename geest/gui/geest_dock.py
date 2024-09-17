from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from qgis.PyQt.QtCore import Qt
from .setup_panel import SetupPanel
from .tree_panel import TreePanel


class GeestDock(QDockWidget):
    def __init__(self, parent=None, json_file=None):
        super().__init__(parent)

        self.setWindowTitle("Geest")  # Set the title of the dock

        self.json_file = json_file

        # Main widget and layout for the dock
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins for a cleaner look
        layout.setSpacing(0)  # Remove spacing between elements

        # Create a tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)  # Tabs at the top
        self.tab_widget.setDocumentMode(True)  # Cleaner look for the tabs
        self.tab_widget.setMovable(False)  # Prevent tabs from being moved

        # Create and add the "Project" tab (SetupPanel)
        self.setup_widget = SetupPanel()
        project_tab = QWidget()
        project_layout = QVBoxLayout(project_tab)
        project_layout.setContentsMargins(0, 0, 0, 0)  # Minimize padding
        project_layout.addWidget(self.setup_widget)
        self.tab_widget.addTab(project_tab, "Project")

        # Create and add the "Inputs" tab (TreePanel)
        self.tree_widget = TreePanel(json_file=self.json_file)
        inputs_tab = QWidget()
        inputs_layout = QVBoxLayout(inputs_tab)
        inputs_layout.setContentsMargins(0, 0, 0, 0)  # Minimize padding
        inputs_layout.addWidget(self.tree_widget)
        self.tab_widget.addTab(inputs_tab, "Inputs")

        # Add the tab widget to the main layout
        layout.addWidget(self.tab_widget)
        main_widget.setLayout(layout)

        # Set the main widget as the widget for the dock
        self.setWidget(main_widget)

        # Optionally, start with the first tab selected (optional)
        self.tab_widget.setCurrentIndex(0)
