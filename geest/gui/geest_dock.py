import os
from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QPixmap, QPainter

from qgis.core import Qgis, QgsProject
from typing import Optional
from geest.gui.panels import (
    IntroPanel,
    CreditsPanel,
    SetupPanel,
    TreePanel,
    HelpPanel,
    OrsPanel,
    OpenProjectPanel,
    CreateProjectPanel,
)
from geest.core import set_setting, setting
from geest.utilities import (
    resources_path,
    log_message,
    is_qgis_dark_theme_active,
    version,
)

INTRO_PANEL = 0
CREDITS_PANEL = 1
ORS_PANEL = 2
SETUP_PANEL = 3
OPEN_PROJECT_PANEL = 4
CREATE_PROJECT_PANEL = 5
TREE_PANEL = 6
HELP_PANEL = 7


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
        # Get the plugin version from metadata.txt
        self.plugin_version = version()

        self.setWindowTitle(
            f"Women's Enablement Environments - {self.plugin_version}"
        )  # Set the title of the dock
        self.json_file: Optional[str] = json_file

        # Initialize main widget and layout for the dock
        main_widget: QWidget = QWidget()
        layout: QVBoxLayout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins for a cleaner look
        layout.setSpacing(0)  # Remove spacing between elements

        # Load the background image
        if is_qgis_dark_theme_active():
            self.background_image = QPixmap(
                resources_path("resources", "images", "background-dark.png")
            )
        else:
            self.background_image = QPixmap(
                resources_path("resources", "images", "background.png")
            )

        # Create a stacked widget
        self.stacked_widget: QStackedWidget = QStackedWidget()

        try:
            # Create and add the "Intro" panel (IntroPanel)
            self.intro_widget: IntroPanel = IntroPanel()
            intro_panel: QWidget = QWidget()
            intro_layout: QVBoxLayout = QVBoxLayout(intro_panel)
            intro_layout.setContentsMargins(10, 10, 10, 10)  # Minimize padding
            intro_layout.addWidget(self.intro_widget)
            self.stacked_widget.addWidget(intro_panel)
            self.intro_widget.switch_to_next_tab.connect(
                # Switch to the next tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(CREDITS_PANEL)
            )
            # Create and add the "Credits" panel (CreditsPanel)
            self.credits_widget: CreditsPanel = CreditsPanel()
            credits_panel: QWidget = QWidget()
            credits_layout: QVBoxLayout = QVBoxLayout(credits_panel)
            credits_layout.setContentsMargins(10, 10, 10, 10)  # Minimize padding
            credits_layout.addWidget(self.credits_widget)
            self.stacked_widget.addWidget(credits_panel)
            self.credits_widget.switch_to_previous_tab.connect(
                # Switch to the next tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(INTRO_PANEL)
            )
            self.credits_widget.switch_to_next_tab.connect(
                # Switch to the next tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(ORS_PANEL)
            )

            # Create and add the "ORS" panel (ORSPanel)
            self.ors_widget: OrsPanel = OrsPanel()
            ors_panel: QWidget = QWidget()
            ors_layout: QVBoxLayout = QVBoxLayout(ors_panel)
            ors_layout.setContentsMargins(10, 10, 10, 10)  # Minimize padding
            ors_layout.addWidget(self.ors_widget)
            self.stacked_widget.addWidget(ors_panel)
            self.ors_widget.switch_to_previous_tab.connect(
                # Switch to the next tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(CREDITS_PANEL)
            )
            self.ors_widget.switch_to_next_tab.connect(
                # Switch to the next tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(SETUP_PANEL)
            )
            # Create and add the "Project" panel (SetupPanel)
            self.setup_widget: SetupPanel = SetupPanel()
            setup_panel: QWidget = QWidget()
            setup_layout: QVBoxLayout = QVBoxLayout(setup_panel)
            setup_layout.setContentsMargins(10, 10, 10, 10)  # Minimize padding
            setup_layout.addWidget(self.setup_widget)
            self.stacked_widget.addWidget(setup_panel)

            self.setup_widget.switch_to_load_project_tab.connect(
                # Switch to the next tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(OPEN_PROJECT_PANEL)
            )

            self.setup_widget.switch_to_create_project_tab.connect(
                # Switch to the next tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(CREATE_PROJECT_PANEL)
            )

            self.setup_widget.switch_to_previous_tab.connect(
                # Switch to the previous tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(ORS_PANEL)
            )

            # Create and add the "Open Project" panel
            self.open_project_widget: OpenProjectPanel = OpenProjectPanel()
            open_project_panel: QWidget = QWidget()
            open_project_layout: QVBoxLayout = QVBoxLayout(open_project_panel)
            open_project_layout.setContentsMargins(10, 10, 10, 10)  # Minimize padding
            open_project_layout.addWidget(self.open_project_widget)
            self.stacked_widget.addWidget(open_project_panel)

            self.open_project_widget.switch_to_previous_tab.connect(
                # Switch to the previous tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(SETUP_PANEL)
            )

            self.open_project_widget.switch_to_next_tab.connect(
                # Switch to the next tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(TREE_PANEL)
            )

            self.open_project_widget.set_working_directory.connect(
                # Switch to the previous tab when the button is clicked
                lambda: self.tree_widget.set_working_directory(
                    self.open_project_widget.working_dir
                )
            )

            # Create and add the "Create Project" panel
            self.create_project_widget: CreateProjectPanel = CreateProjectPanel()
            create_project_panel: QWidget = QWidget()
            create_project_layout: QVBoxLayout = QVBoxLayout(create_project_panel)
            create_project_layout.setContentsMargins(10, 10, 10, 10)  # Minimize padding
            create_project_layout.addWidget(self.create_project_widget)
            self.stacked_widget.addWidget(create_project_panel)

            self.create_project_widget.switch_to_previous_tab.connect(
                # Switch to the next tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(SETUP_PANEL)
            )

            self.create_project_widget.switch_to_next_tab.connect(
                # Switch to the next tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(TREE_PANEL)
            )

            self.create_project_widget.set_working_directory.connect(
                # Switch to the previous tab when the button is clicked
                lambda: self.tree_widget.set_working_directory(
                    self.create_project_widget.working_dir
                )
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
                lambda: self.stacked_widget.setCurrentIndex(HELP_PANEL)
            )
            self.tree_widget.switch_to_previous_tab.connect(
                # Switch to the previous tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(SETUP_PANEL)
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
                lambda: self.stacked_widget.setCurrentIndex(TREE_PANEL)
            )
            # Add the stacked widget to the main layout
            layout.addWidget(self.stacked_widget)

            # Set the main widget as the widget for the dock
            self.setWidget(main_widget)

            # Start with the first panel selected
            self.stacked_widget.setCurrentIndex(INTRO_PANEL)

            # Customize allowed areas for docking
            self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
            self.setFeatures(
                QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable
            )

            # Connect panel change event if custom logic is needed when switching panels
            self.stacked_widget.currentChanged.connect(self.on_panel_changed)

            log_message("GeestDock initialized successfully.")

        except Exception as e:
            log_message(
                f"Error initializing GeestDock: {str(e)}",
                tag="Geest",
                level=Qgis.Critical,
            )
            import traceback

    def paintEvent(self, event):
        with QPainter(self) as painter:
            # Calculate the scaling and cropping offsets
            scaled_background = self.background_image.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding
            )

            # Calculate the offset to crop from top and right to keep bottom left anchored
            x_offset = max(0, scaled_background.width() - self.width())
            y_offset = max(0, scaled_background.height() - self.height())

            # Draw the image at the negative offsets
            painter.drawPixmap(-x_offset, -y_offset, scaled_background)

        super().paintEvent(event)

    def qgis_project_changed(self) -> None:
        """
        Handle QGIS project change events.

        This is called by the main plugin class whenever the QGIS project changes.
        """
        project_path = QgsProject.instance().fileName()
        log_message(f"QGIS project changed to {project_path}")
        if project_path:
            checksum = hash(project_path)
            # Check our settings to see if we have a Geest project associated with this project
            geest_project = setting(str(checksum), None, prefer_project_setting=True)
            log_message(
                f"Geest project path: {geest_project} ({checksum})",
                tag="Geest",
                level=Qgis.Info,
            )
            if geest_project and os.path.exists(
                os.path.join(geest_project, "model.json")
            ):
                self.tree_widget.set_working_directory(geest_project)
                self.stacked_widget.setCurrentIndex(TREE_PANEL)  # Tree tab

    def on_panel_changed(self, index: int) -> None:
        """
        Handle panel change events and log the panel switch.

        :param index: The index of the newly selected panel.
        """
        if index == INTRO_PANEL:
            log_message("Switched to Intro panel")
            self.intro_widget.set_font_size()
        elif index == CREDITS_PANEL:
            log_message("Switched to Credits panel")
            self.credits_widget.set_font_size()
        elif index == SETUP_PANEL:
            log_message("Switched to Setup panel")
        elif index == ORS_PANEL:
            self.ors_widget.set_font_size()
            log_message("Switched to ORS panel")
        elif index == OPEN_PROJECT_PANEL:
            log_message("Switched to Open Project panel")
        elif index == CREATE_PROJECT_PANEL:
            self.create_project_widget.set_font_size()
            log_message("Switched to Create Project panel")
        elif index == TREE_PANEL:
            log_message("Switched to Tree panel")
            # self.tree_widget.set_working_directory(self.setup_widget.working_dir)
        elif index == HELP_PANEL:
            log_message("Switched to Help panel")
