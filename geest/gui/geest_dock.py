import os
from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsMessageLog, Qgis, QgsProject
from typing import Optional
from geest.gui.panels import (
    IntroPanel,
    SetupPanel,
    TreePanel,
    HelpPanel,
    OrsPanel,
    OpenProjectPanel,
    CreateProjectPanel,
)
from geest.core import set_setting, setting


class GeestDock(QDockWidget):
    def __init__(
        self, parent: Optional[QWidget] = None, json_file: Optional[str] = None
    ) -> None:
        """
        Initializes the GeestDock with a parent and an optional JSON file.
        Sets up the main widget and stacked panels.

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

        # Create a stacked widget
        self.stacked_widget: QStackedWidget = QStackedWidget()

        try:
            # Create and add the "Intro" panel (IntroPanel)
            self.intro_widget: IntroPanel = IntroPanel()
            intro_panel: QWidget = QWidget()
            intro_layout: QVBoxLayout = QVBoxLayout(intro_panel)
            intro_layout.setContentsMargins(0, 0, 0, 0)  # Minimize padding
            intro_layout.addWidget(self.intro_widget)
            self.stacked_widget.addWidget(intro_panel)
            self.intro_widget.switch_to_next_tab.connect(
                # Switch to the next tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(1)
            )
            # Create and add the "ORS" panel (ORSPanel)
            self.ors_widget: OrsPanel = OrsPanel()
            ors_panel: QWidget = QWidget()
            ors_layout: QVBoxLayout = QVBoxLayout(ors_panel)
            ors_layout.setContentsMargins(0, 0, 0, 0)  # Minimize padding
            ors_layout.addWidget(self.ors_widget)
            self.stacked_widget.addWidget(ors_panel)
            self.ors_widget.switch_to_next_tab.connect(
                # Switch to the next tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(2)
            )

            # Create and add the "Project" panel (SetupPanel)
            self.setup_widget: SetupPanel = SetupPanel()
            setup_panel: QWidget = QWidget()
            setup_layout: QVBoxLayout = QVBoxLayout(setup_panel)
            setup_layout.setContentsMargins(0, 0, 0, 0)  # Minimize padding
            setup_layout.addWidget(self.setup_widget)
            self.stacked_widget.addWidget(setup_panel)

            self.setup_widget.switch_to_load_project_tab.connect(
                # Switch to the next tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(3)
            )

            self.setup_widget.switch_to_create_project_tab.connect(
                # Switch to the next tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(4)
            )

            # Create and add the "Open Project" panel
            self.open_project_widget: OpenProjectPanel = OpenProjectPanel()
            open_project_panel: QWidget = QWidget()
            open_project_layout: QVBoxLayout = QVBoxLayout(open_project_panel)
            open_project_layout.setContentsMargins(0, 0, 0, 0)  # Minimize padding
            open_project_layout.addWidget(self.open_project_widget)
            self.stacked_widget.addWidget(open_project_panel)

            self.open_project_widget.switch_to_next_tab.connect(
                # Switch to the next tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(5)
            )

            # Create and add the "Create Project" panel
            self.create_project_widget: CreateProjectPanel = CreateProjectPanel()
            create_project_panel: QWidget = QWidget()
            create_project_layout: QVBoxLayout = QVBoxLayout(create_project_panel)
            create_project_layout.setContentsMargins(0, 0, 0, 0)  # Minimize padding
            create_project_layout.addWidget(self.create_project_widget)
            self.stacked_widget.addWidget(create_project_panel)

            self.create_project_widget.switch_to_next_tab.connect(
                # Switch to the next tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(5)
            )

            # Create and add the "Tree" panel (TreePanel)
            self.tree_widget: TreePanel = TreePanel(json_file=self.json_file)
            tree_panel: QWidget = QWidget()
            tree_layout: QVBoxLayout = QVBoxLayout(tree_panel)
            tree_layout.setContentsMargins(0, 0, 0, 0)  # Minimize padding
            tree_layout.addWidget(self.tree_widget)
            self.stacked_widget.addWidget(tree_panel)
            self.tree_widget.switch_to_next_tab.connect(
                # Switch to the next tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(4)
            )
            self.tree_widget.switch_to_previous_tab.connect(
                # Switch to the previous tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(1)
            )
            # Create and add the "Help" panel (HelpPanel)
            help_widget: HelpPanel = HelpPanel()
            help_panel: QWidget = QWidget()
            help_layout: QVBoxLayout = QVBoxLayout(help_panel)
            help_layout.setContentsMargins(0, 0, 0, 0)  # Minimize padding
            help_layout.addWidget(help_widget)
            self.stacked_widget.addWidget(help_panel)
            help_widget.switch_to_previous_tab.connect(
                # Switch to the previous tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(5)
            )
            # Add the stacked widget to the main layout
            layout.addWidget(self.stacked_widget)

            # Set the main widget as the widget for the dock
            self.setWidget(main_widget)

            # Start with the first panel selected
            self.stacked_widget.setCurrentIndex(0)

            # Customize allowed areas for docking
            self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
            self.setFeatures(
                QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable
            )

            # Connect panel change event if custom logic is needed when switching panels
            self.stacked_widget.currentChanged.connect(self.on_panel_changed)
            QgsMessageLog.logMessage("GeestDock initialized successfully.", "Geest")

        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error initializing GeestDock: {str(e)}",
                "Geest",
                level=Qgis.Critical,
            )

    def qgis_project_changed(self) -> None:
        """
        Handle QGIS project change events.

        This is called by the main plugin class whenever the QGIS project changes.
        """
        project_path = QgsProject.instance().fileName()
        QgsMessageLog.logMessage(
            f"QGIS project changed to {project_path}", "Geest", Qgis.Info
        )
        if project_path:
            checksum = hash(project_path)
            # Check our settings to see if we have a Geest project associated with this project
            geest_project = setting(str(checksum), None, prefer_project_setting=True)
            QgsMessageLog.logMessage(
                f"Geest project path: {geest_project} ({checksum})", "Geest", Qgis.Info
            )
            if geest_project and os.path.exists(geest_project):
                self.tree_widget.set_working_directory(geest_project)
                self.stacked_widget.setCurrentIndex(2)  # Tree tab

    def on_panel_changed(self, index: int) -> None:
        """
        Handle panel change events and log the panel switch.

        :param index: The index of the newly selected panel.
        """
        if index == 0:
            QgsMessageLog.logMessage("Switched to Intro panel", "Geest", Qgis.Info)
        if index == 1:
            QgsMessageLog.logMessage("Switched to ORS panel", "Geest", Qgis.Info)
        elif index == 2:
            QgsMessageLog.logMessage("Switched to Project panel", "Geest", Qgis.Info)
        elif index == 3:
            QgsMessageLog.logMessage("Switched to Tree panel", "Geest", Qgis.Info)
            # self.tree_widget.set_working_directory(self.setup_widget.working_dir)
        elif index == 4:
            QgsMessageLog.logMessage("Switched to Help panel", "Geest", Qgis.Info)
