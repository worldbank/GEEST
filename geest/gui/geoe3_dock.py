# -*- coding: utf-8 -*-
"""📦 GeoE3 Dock module.

This module contains functionality for geoe3 dock.
"""

import os
import json
from typing import Optional

from qgis.core import Qgis, QgsProject
from qgis.gui import QgsMessageBar
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QPainter
from qgis.PyQt.QtWidgets import QDockWidget, QStackedWidget, QVBoxLayout, QWidget

from geest.core.settings import setting
from geest.gui.panels import (
    CreateProjectPanel,
    CreditsPanel,
    HelpPanel,
    IntroPanel,
    OpenProjectPanel,
    OrsPanel,
    RoadNetworkPanel,
    S2SPanel,
    SetupPanel,
    TreePanel,
)
from geest.utilities import (
    log_message,
    theme_background_image,
    theme_stylesheet,
    version,
)

INTRO_PANEL = 0
CREDITS_PANEL = 1
SETUP_PANEL = 2
OPEN_PROJECT_PANEL = 3
CREATE_PROJECT_PANEL = 4
S2S_PANEL = 5
ORS_PANEL = 6
ROAD_NETWORK_PANEL = 7
TREE_PANEL = 8
HELP_PANEL = 9


class GeoE3Dock(QDockWidget):
    """🎯 GeoE3 Dock.

    Attributes:
        background_image: Background image.
        initialised: Initialised.
        plugin_version: Plugin version.
        study_area_bbox: Study area bbox.
    """

    def __init__(self, parent: Optional[QWidget] = None, json_file: Optional[str] = None) -> None:
        """
        Initializes the GeoE3Dock with a parent and an optional JSON file.
        Sets up the main widget and stacked panels.

        Args:
            parent: The parent widget for the dock.
            json_file: Path to a JSON file used for the TreePanel.
        """
        self.initialised = False
        self._suppress_qgis_project_changed = False  # Flag to prevent signal loop
        super().__init__(parent)
        self.background_image = theme_background_image()
        # Get the plugin version from metadata.txt
        self.plugin_version = version()

        self.setWindowTitle(
            f"Enabling Environments for Employment - {self.plugin_version}"
        )  # Set the title of the dock
        self.json_file: Optional[str] = json_file

        # Initialize main widget and layout for the dock
        main_widget: QWidget = QWidget()
        layout: QVBoxLayout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins for a cleaner look
        layout.setSpacing(0)  # Remove spacing between elements

        # Add a message bar at the top of the dock widget
        self.message_bar: QgsMessageBar = QgsMessageBar()
        layout.addWidget(self.message_bar)

        # Create a stacked widget
        self.stacked_widget: QStackedWidget = QStackedWidget()
        self.study_area_bbox = None

        # Create the widgets early to be ready for connections
        self.intro_widget: IntroPanel = IntroPanel()
        self.credits_widget: CreditsPanel = CreditsPanel()
        self.setup_widget: SetupPanel = SetupPanel()
        self.open_project_widget: OpenProjectPanel = OpenProjectPanel()
        self.road_network_widget: RoadNetworkPanel = RoadNetworkPanel()
        self.road_network_widget.set_message_bar(self.message_bar)  # Pass message bar reference
        self.create_project_widget: CreateProjectPanel = CreateProjectPanel()
        self.s2s_widget: S2SPanel = S2SPanel()
        self.ors_widget: OrsPanel = OrsPanel()
        self.tree_widget: TreePanel = TreePanel(json_file=self.json_file)
        help_widget: HelpPanel = HelpPanel()

        try:
            # INTRO_PANEL = 0
            # Create and add the "Intro" panel (IntroPanel)
            intro_panel: QWidget = QWidget()
            intro_layout: QVBoxLayout = QVBoxLayout(intro_panel)
            intro_layout.setContentsMargins(10, 10, 10, 10)  # Minimize padding
            intro_layout.addWidget(self.intro_widget)
            self.stacked_widget.addWidget(intro_panel)
            self.intro_widget.switch_to_next_tab.connect(
                # Switch to the next tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(CREDITS_PANEL)
            )
            # CREDITS_PANEL = 1
            # Create and add the "Credits" panel (CreditsPanel)

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
                lambda: self.stacked_widget.setCurrentIndex(SETUP_PANEL)
            )
            # SETUP_PANEL = 2
            # Create and add the "Project" panel (SetupPanel)

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
                lambda: self.stacked_widget.setCurrentIndex(CREDITS_PANEL)
            )
            # OPEN_PROJECT_PANEL = 3
            # Create and add the "Open Project" panel

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
                lambda: self.tree_widget.set_working_directory(self.open_project_widget.working_dir)
            )

            self.open_project_widget.project_loaded.connect(
                # Open the associated QGIS project after project is loaded
                lambda: self.open_associated_qgis_project()
            )

            # CREATE_PROJECT_PANEL = 4
            # Create and add the "Create Project" panel

            create_project_panel: QWidget = QWidget()
            create_project_layout: QVBoxLayout = QVBoxLayout(create_project_panel)
            create_project_layout.setContentsMargins(10, 10, 10, 10)  # Minimize padding
            create_project_layout.addWidget(self.create_project_widget)
            self.stacked_widget.addWidget(create_project_panel)

            self.create_project_widget.switch_to_previous_tab.connect(
                # Switch to the next tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(SETUP_PANEL)
            )

            self.create_project_widget.switch_to_next_tab.connect(self._open_next_panel_after_project_creation)

            self.create_project_widget.working_directory_changed.connect(
                lambda _path: self.tree_widget.set_working_directory(self.create_project_widget.working_dir)
            )
            self.create_project_widget.working_directory_changed.connect(
                lambda _path: self.s2s_widget.set_working_directory(self.create_project_widget.working_dir)
            )

            # S2S_PANEL = 5
            # Create and add the "S2S" panel

            s2s_panel: QWidget = QWidget()
            s2s_layout: QVBoxLayout = QVBoxLayout(s2s_panel)
            s2s_layout.setContentsMargins(10, 10, 10, 10)
            s2s_layout.addWidget(self.s2s_widget)
            self.stacked_widget.addWidget(s2s_panel)

            self.s2s_widget.switch_to_previous_tab.connect(
                lambda: self.stacked_widget.setCurrentIndex(CREATE_PROJECT_PANEL)
            )
            self.s2s_widget.switch_to_next_tab.connect(lambda: self.stacked_widget.setCurrentIndex(ORS_PANEL))

            # ORS_PANEL = 6
            # Create and add the "ORS" panel

            ors_panel: QWidget = QWidget()
            ors_layout: QVBoxLayout = QVBoxLayout(ors_panel)
            ors_layout.setContentsMargins(10, 10, 10, 10)  # Minimize padding
            ors_layout.addWidget(self.ors_widget)
            self.stacked_widget.addWidget(ors_panel)

            self.ors_widget.switch_to_previous_tab.connect(self._open_previous_panel_before_ors)

            self.ors_widget.switch_to_next_tab.connect(self._open_road_network_from_ors)

            # ROAD_NETWORK_PANEL = 6
            # Create and add the "Road Network" panel

            road_network_panel: QWidget = QWidget()
            road_network_layout: QVBoxLayout = QVBoxLayout(road_network_panel)
            road_network_layout.setContentsMargins(10, 10, 10, 10)  # Minimize padding
            road_network_layout.addWidget(self.road_network_widget)
            self.stacked_widget.addWidget(road_network_panel)

            self.road_network_widget.switch_to_previous_tab.connect(
                lambda: self.stacked_widget.setCurrentIndex(ORS_PANEL)
            )

            self.road_network_widget.switch_to_next_tab.connect(
                # Switch to the next tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(TREE_PANEL)
            )
            # We are only interested in storing the network layer path
            # (and not the cycle path) as it is used for the native
            # network analysis algorithms internally
            self.road_network_widget.road_network_layer_path_changed.connect(
                lambda: self.tree_widget.set_road_network_layer_path(self.road_network_widget.road_network_layer_path())
            )
            self.open_project_widget.set_working_directory.connect(
                # Switch to the previous tab when the button is clicked
                lambda: self.tree_widget.set_working_directory(self.open_project_widget.working_dir)
            )
            # TREE_PANEL = 6
            # Create and add the "Tree" panel (TreePanel)
            tree_panel: QWidget = QWidget()
            tree_layout: QVBoxLayout = QVBoxLayout(tree_panel)
            tree_layout.setContentsMargins(0, 0, 0, 0)  # Minimize padding
            tree_layout.addWidget(self.tree_widget)
            self.stacked_widget.addWidget(tree_panel)
            self.tree_widget.set_message_bar(self.message_bar)  # Pass dock message bar for error notifications
            self.tree_widget.switch_to_next_tab.connect(
                # Switch to the next tab when the button is clicked
                lambda: self.stacked_widget.setCurrentIndex(HELP_PANEL)
            )
            self.tree_widget.switch_to_network_tab.connect(
                # Switch to the road network tab when the button is clicked
                # This is also called from the context menu in the tree_panel
                lambda: [
                    self.stacked_widget.setCurrentIndex(ROAD_NETWORK_PANEL),
                ]
            )
            self.tree_widget.switch_to_ors_tab.connect(
                lambda: [
                    self.stacked_widget.setCurrentIndex(ORS_PANEL),
                ]
            )
            self.tree_widget.switch_to_setup_tab.connect(
                # Switch to the project tab when the button is clicked
                lambda: [
                    self.stacked_widget.setCurrentIndex(SETUP_PANEL),
                ]
            )

            # HELP_PANEL = 8
            # Create and add the "Help" panel (HelpPanel)
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
            self.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)

            # Connect panel change event if custom logic is needed when switching panels
            self.stacked_widget.currentChanged.connect(self.on_panel_changed)
            log_message("GeoE3Dock initialized successfully.")

        except Exception as e:
            log_message(
                f"Error initializing GeoE3Dock: {str(e)}",
                tag="GeoE3",
                level=Qgis.Critical,
            )
            import traceback

            log_message(traceback.format_exc(), tag="GeoE3", level=Qgis.Critical)

        # Load the background image and style sheet
        # do this last so it applies to all the widgets
        main_widget.setStyleSheet(theme_stylesheet())
        self.initialised = True

    def paintEvent(self, event):
        """⚙️ Paintevent.

        Args:
            event: Event.
        """
        background_image = getattr(self, "background_image", None)
        if background_image is None or background_image.isNull():
            super().paintEvent(event)
            return

        with QPainter(self) as painter:
            # Calculate the scaling and cropping offsets
            scaled_background = background_image.scaled(self.size(), Qt.KeepAspectRatioByExpanding)

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
        if self._suppress_qgis_project_changed:
            return
        project_path = QgsProject.instance().fileName()
        log_message(f"QGIS project changed to {project_path}")
        if project_path:
            checksum = hash(project_path)
            geoe3_project = setting(str(checksum), None, prefer_project_setting=True)
            log_message(
                f"GeoE3 project path : {geoe3_project} ({checksum})",  # noqa E225
                tag="GeoE3",  # noqa E225
                level=Qgis.Info,  # noqa E225
            )
            if geoe3_project and os.path.exists(os.path.join(geoe3_project, "model.json")):
                self.tree_widget.set_working_directory(geoe3_project)
                self.stacked_widget.setCurrentIndex(TREE_PANEL)  # Tree tab
                self.road_network_widget.set_working_directory(geoe3_project)
                saved_path = self.tree_widget.road_network_layer_path()
                if saved_path:
                    log_message(f"Restoring road network layer from model: {saved_path}")
                    self.road_network_widget.restore_layer_from_path(saved_path)
                if self.tree_widget.working_directory:
                    self.tree_widget.set_qgis_project_path(project_path)

    def open_associated_qgis_project(self) -> None:
        """Open the QGIS project associated with the current GeoE3 project.

        Reads the qgis_project_path from the model and opens it if it exists
        and differs from the current project.
        """
        qgis_path = self.tree_widget.qgis_project_path()
        if not qgis_path or not qgis_path.strip():
            return
        if not os.path.exists(qgis_path):
            log_message(
                f"Associated QGIS project not found: {qgis_path}",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            return
        current_path = QgsProject.instance().fileName()
        if qgis_path == current_path:
            log_message("QGIS project is already open", tag="GeoE3", level=Qgis.Info)
            return
        log_message(f"Opening associated QGIS project: {qgis_path}", tag="GeoE3", level=Qgis.Info)
        self._suppress_qgis_project_changed = True
        try:
            QgsProject.instance().read(qgis_path)
        except Exception as e:
            log_message(
                f"Failed to open QGIS project: {e}",
                tag="GeoE3",
                level=Qgis.Critical,
            )
        finally:
            self._suppress_qgis_project_changed = False

    def on_panel_changed(self, index: int) -> None:
        """
        Handle panel change events and log the panel switch.

        Args:
            index: The index of the newly selected panel.
        """
        if index == INTRO_PANEL:
            log_message("Switched to Intro panel")
            self.intro_widget.set_font_size()
        elif index == CREDITS_PANEL:
            log_message("Switched to Credits panel")
            self.credits_widget.set_font_size()
        elif index == SETUP_PANEL:
            log_message("Switched to Setup panel")
        elif index == OPEN_PROJECT_PANEL:
            log_message("Switched to Open Project panel")
        elif index == CREATE_PROJECT_PANEL:
            self.create_project_widget.set_font_size()
            log_message("Switched to Create Project panel")
        elif index == ORS_PANEL:
            log_message("Switched to ORS panel")
        elif index == S2S_PANEL:
            if not self._is_regional_project_flow():
                self.stacked_widget.setCurrentIndex(ORS_PANEL)
                return
            working_directory = self.create_project_widget.working_dir or self.tree_widget.working_directory
            self.s2s_widget.set_working_directory(working_directory)
            log_message("Switched to S2S panel")
        elif index == ROAD_NETWORK_PANEL:
            working_directory = self.tree_widget.working_directory
            log_message(f"Setting road network panel working directory to: {working_directory}")
            self.road_network_widget.set_working_directory(working_directory)
            self.road_network_widget.set_reference_layer(self.create_project_widget.reference_layer())
            self.road_network_widget.set_crs(self.create_project_widget.crs(working_directory=working_directory))

            # Restore saved road network layer from model
            saved_path = self.tree_widget.road_network_layer_path()
            if saved_path:
                log_message(f"Restoring road network layer from model: {saved_path}")
                self.road_network_widget.restore_layer_from_path(saved_path)
        elif index == TREE_PANEL:
            log_message("Switched to Tree panel")
            # self.tree_widget.set_working_directory(self.setup_widget.working_dir)
        elif index == HELP_PANEL:
            log_message("Switched to Help panel")

    def _open_road_network_from_ors(self) -> None:
        """Open the road network panel from ORS with a valid working directory."""
        working_directory = self.create_project_widget.working_dir or self.tree_widget.working_directory
        if not working_directory:
            self.message_bar.pushWarning(
                "Missing working directory",
                "Open or create a project before setting network layers.",
            )
            return
        self.stacked_widget.setCurrentIndex(ROAD_NETWORK_PANEL)
        self.road_network_widget.set_working_directory(working_directory)
        if self.create_project_widget.working_dir:
            self.road_network_widget.set_reference_layer(self.create_project_widget.reference_layer())
            self.road_network_widget.set_crs(
                self.create_project_widget.crs(working_directory=self.create_project_widget.working_dir)
            )

    def _open_next_panel_after_project_creation(self) -> None:
        """Open the next panel after project creation based on analysis scale."""
        if self._is_regional_project_flow():
            self.stacked_widget.setCurrentIndex(S2S_PANEL)
        else:
            self.stacked_widget.setCurrentIndex(ORS_PANEL)

    def _open_previous_panel_before_ors(self) -> None:
        """Open the previous panel before ORS based on analysis scale."""
        if self._is_regional_project_flow():
            self.stacked_widget.setCurrentIndex(S2S_PANEL)
        else:
            self.stacked_widget.setCurrentIndex(CREATE_PROJECT_PANEL)

    def _is_regional_project_flow(self) -> bool:
        """Return True when current project analysis_scale is regional."""
        working_directory = self.create_project_widget.working_dir or self.tree_widget.working_directory
        if not working_directory:
            return False

        model_path = os.path.join(working_directory, "model.json")
        if not os.path.exists(model_path):
            return False

        try:
            with open(model_path, "r", encoding="utf-8") as model_file:
                model = json.load(model_file)
            return model.get("analysis_scale") == "regional"
        except Exception as error:
            log_message(f"Failed reading model.json for panel routing: {error}", tag="GeoE3", level=Qgis.Warning)
            return False
