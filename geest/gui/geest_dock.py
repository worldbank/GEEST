from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsMessageLog, Qgis
from typing import Optional
from geest.gui.panels import SetupPanel
from geest.gui.panels import TreePanel


class GeestDock(QDockWidget):
    def __init__(
        self, parent: Optional[QWidget] = None, json_file: Optional[str] = None
    ) -> None:
        """
        Initializes the GeestDock with a parent and an optional JSON file.
        Sets up the main widget and tabs.

        :param parent: The parent widget for the dock.
        :param json_file: Path to a JSON file used for the TreePanel.
        """
        super().__init__(parent)

        self.setWindowTitle("Geest")  # Set the title of the dock
        self.json_file: Optional[str] = json_file

        # Initialize main widget and layout for the dock
        main_widget: QWidget = QWidget()
        layout: QVBoxLayout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins for a cleaner look
        layout.setSpacing(0)  # Remove spacing between elements

        # Create a tab widget
        self.tab_widget: QTabWidget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)  # Tabs at the top
        self.tab_widget.setDocumentMode(True)  # Cleaner look for the tabs
        self.tab_widget.setMovable(False)  # Prevent tabs from being moved

        try:
            # Create and add the "Project" tab (SetupPanel)
            self.setup_widget: SetupPanel = SetupPanel()
            project_tab: QWidget = QWidget()
            project_layout: QVBoxLayout = QVBoxLayout(project_tab)
            project_layout.setContentsMargins(0, 0, 0, 0)  # Minimize padding
            project_layout.addWidget(self.setup_widget)
            self.tab_widget.addTab(project_tab, "Project")

            # Create and add the "Inputs" tab (TreePanel)
            self.tree_widget: TreePanel = TreePanel(json_file=self.json_file)
            inputs_tab: QWidget = QWidget()
            inputs_layout: QVBoxLayout = QVBoxLayout(inputs_tab)
            inputs_layout.setContentsMargins(0, 0, 0, 0)  # Minimize padding
            inputs_layout.addWidget(self.tree_widget)
            self.tab_widget.addTab(inputs_tab, "Inputs")

            # Add the tab widget to the main layout
            layout.addWidget(self.tab_widget)

            # Set the main widget as the widget for the dock
            self.setWidget(main_widget)

            # Start with the first tab selected
            self.tab_widget.setCurrentIndex(0)

            # Customize allowed areas for docking
            self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
            self.setFeatures(
                QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable
            )

            # Connect tab change event if custom logic is needed when switching tabs
            self.tab_widget.currentChanged.connect(self.on_tab_changed)

            QgsMessageLog.logMessage("GeestDock initialized successfully.", "Geest")

        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error initializing GeestDock: {str(e)}",
                "Geest",
                level=Qgis.Critical,
            )

    def on_tab_changed(self, index: int) -> None:
        """
        Handle tab change events and log the tab switch.

        :param index: The index of the newly selected tab.
        """
        if index == 0:
            QgsMessageLog.logMessage("Switched to Project tab", "Geest", Qgis.Info)
        elif index == 1:
            QgsMessageLog.logMessage("Switched to Tree tab", "Geest", Qgis.Info)
            self.tree_widget.set_working_directory(self.setup_widget.working_dir)

    def load_json_file(self, json_file: str) -> None:
        """
        Load a new JSON file into the TreePanel.

        :param json_file: The path to the new JSON file to be loaded.
        """
        try:
            self.json_file = json_file
            self.tree_widget.load_data_from_json(json_file)
            QgsMessageLog.logMessage(
                f"Loaded JSON file: {json_file}", "Geest", Qgis.Info
            )
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error loading JSON file: {str(e)}",
                tag="Geest",
                level=Qgis.Critical,
            )
