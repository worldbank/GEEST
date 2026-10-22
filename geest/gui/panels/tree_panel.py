# -*- coding: utf-8 -*-
"""📦 Tree Panel module.

This module contains functionality for tree panel.
"""

import json
import os
import shutil
import traceback
from functools import partial
from logging import getLogger
from typing import Optional

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsFeedback,
    QgsLayerTreeGroup,
    QgsProcessingContext,
    QgsProject,
    QgsTask,
    QgsVectorLayer,
)
from qgis.gui import QgsMessageBar
from qgis.PyQt import sip
from qgis.PyQt.QtCore import QModelIndex, QPoint, QSettings, Qt, QTimer, pyqtSignal, pyqtSlot
from qgis.PyQt.QtGui import QMovie
from qgis.PyQt.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)
from qgis.utils import iface

from geest.core import JsonTreeItem, WorkflowQueueManager
from geest.core.algorithms import (
    OpportunitiesByWeeScorePopulationProcessingTask,
    OpportunitiesByWeeScoreProcessingTask,
    OpportunitiesMaskProcessor,
    PopulationRasterProcessingTask,
    PopulationVectorProcessingTask,
    SubnationalAggregationProcessingTask,
    WEEByPopulationScoreProcessingTask,
)
from geest.core.constants import DEFAULT_S2S_POPULATION_FIELD, MAX_FEATURES_FOR_VECTOR
from geest.core.i18n import tr
from geest.core.reports import StudyAreaReport
from geest.core.settings import set_setting, setting
from geest.core.tasks import AnalysisReportTask
from geest.core.utilities import add_grid_layer_to_map, add_to_map, validate_network_layer
from geest.core.women_considerations import resolve_women_enabling_for_factor
from geest.gui.dialogs import (
    AnalysisAggregationDialog,
    DimensionAggregationDialog,
    FactorAggregationDialog,
)
from geest.gui.views import JsonTreeModel, JsonTreeView
from geest.gui.widgets import SolidMenu
from geest.utilities import log_message, open_with_system_handler, resources_path, theme_stylesheet


class TreePanel(QWidget):
    """🎯 Tree Panel.

    Attributes:
        active_model: Active model.
        help_button: Help button.
        items_to_run: Items to run.
        json_data: Json data.
        json_file: Json file.
    """

    switch_to_next_tab = pyqtSignal()  # Signal to notify the parent to switch tabs
    switch_to_setup_tab = pyqtSignal()
    switch_to_previous_tab = pyqtSignal()  # Signal to notify the parent to switch tabs
    switch_to_network_tab = pyqtSignal()  # Signal to open the road network tab
    switch_to_ors_tab = pyqtSignal()  # Signal to open the ORS setup tab

    def __init__(self, parent=None, json_file=None):
        """🏗️ Initialize the instance.

        Args:
            parent: Parent.
            json_file: Json file.
        """
        super().__init__(parent)

        # Initialize the QueueManager
        self.working_directory = None
        # Pass None to enable dynamic reading of concurrent_tasks setting.
        # This allows users to change the setting without restarting QGIS.
        self.queue_manager = WorkflowQueueManager(pool_size=None)
        self.json_file = json_file
        self.tree_view_visible = True
        self.run_only_incomplete = True  # saves time by not running models that have already been run
        self.items_to_run = 0  # Count of items that need to be run

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        if json_file:
            # Load JSON data
            self.load_json()
        else:
            self.json_data = {"dimensions": []}

        # Inline warning banner (hidden by default)
        self.warning_widget = QWidget()
        self.warning_widget.setVisible(False)
        warning_layout = QHBoxLayout(self.warning_widget)
        warning_layout.setContentsMargins(12, 10, 12, 10)
        warning_layout.setSpacing(12)

        warning_icon = QLabel("⚠️")
        warning_icon.setStyleSheet("font-size: 18px;")
        warning_layout.addWidget(warning_icon)

        self.warning_message_label = QLabel()
        self.warning_message_label.setWordWrap(True)
        self.warning_message_label.setStyleSheet("color: #856404; font-size: 13px;")
        warning_layout.addWidget(self.warning_message_label, 1)

        self.configure_network_button = QPushButton("Configure")
        self.configure_network_button.clicked.connect(self._on_configure_clicked)
        self.configure_network_button.setStyleSheet(
            """
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3E799B, stop:1 #2d5a75);
                color: #ffffff;
                border: 1px solid #2d5a75;
                border-radius: 3px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a8bb0, stop:1 #3E799B);
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2d5a75, stop:1 #3E799B);
            }
        """
        )
        warning_layout.addWidget(self.configure_network_button)

        close_warning_button = QPushButton("✕")
        close_warning_button.setFixedSize(24, 24)
        close_warning_button.setStyleSheet(
            """
            QPushButton {
                border: none;
                color: #856404;
                background: transparent;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
                border-radius: 3px;
            }
        """
        )
        close_warning_button.clicked.connect(self.hide_validation_warning)
        warning_layout.addWidget(close_warning_button)

        self.warning_widget.setStyleSheet(
            """
            QWidget {
                background-color: #fff3cd;
                border-left: 4px solid #ffc107;
                border-radius: 3px;
            }
        """
        )

        layout.addWidget(self.warning_widget)

        # Create a CustomTreeView widget to handle editing and reverts
        self.treeView = JsonTreeView()
        self.treeView.setDragDropMode(QTreeView.DragDropMode.InternalMove)
        self.treeView.setDefaultDropAction(Qt.DropAction.MoveAction)

        # Create a model for the QTreeView using custom JsonTreeModel
        self.model = JsonTreeModel(self.json_data)
        self.active_model = "default"  # or "promotion"
        self.treeView.setModel(self.model)  # Simple model where we allow single childred

        # Connect signals to track changes in the model and save automatically
        self.model.dataChanged.connect(self.save_json_to_working_directory)
        self.model.rowsInserted.connect(self.save_json_to_working_directory)
        self.model.rowsRemoved.connect(self.save_json_to_working_directory)

        self.treeView.setRootIsDecorated(True)  # Ensures tree branches are visible
        self.treeView.setItemsExpandable(True)
        self.treeView.setUniformRowHeights(True)

        # Hide the third column (index 2)
        # Hide the weights column for now - I think later we will remove it completely
        # see https://github.com/kartoza/GEEST2/issues/370
        self.treeView.header().hideSection(2)

        # Enable custom context menu
        self.treeView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.open_context_menu)

        # Expand the whole tree by default
        self.treeView.expandAll()

        # Set the second and third columns to the exact width of their contents
        self.treeView.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.treeView.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        # Expand the first column to use the remaining space and resize with the dialog
        self.treeView.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.treeView.header().setStretchLastSection(False)
        # Now hide the header
        self.treeView.header().hide()
        # Action fow when we double click an item
        self.treeView.setExpandsOnDoubleClick(False)  # Prevent double-click from collapsing the tree view
        self.treeView.doubleClicked.connect(self.on_item_double_clicked)  # Will show properties dialogs

        # Show the item on the map if it is already generated and the
        # user clicks it
        self.treeView.clicked.connect(self.on_item_clicked)

        # Set layout
        layout.addWidget(self.treeView)

        button_bar = QHBoxLayout()

        # Create the split tool button
        self.prepare_analysis_button = QToolButton()
        self.prepare_analysis_button.setText("▶️ Run all")
        self.prepare_analysis_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)

        # Connect the main button click to run all
        self.prepare_analysis_button.clicked.connect(self.run_all)

        # Create the menu for additional options
        prepare_analysis_menu = SolidMenu(self.prepare_analysis_button)

        # Add "Run all" action
        run_all_action = QAction("Run all", self)
        run_all_action.triggered.connect(self.run_all)
        prepare_analysis_menu.addAction(run_all_action)

        # Add "Run incomplete" action
        run_incomplete_action = QAction("Run incomplete", self)
        run_incomplete_action.triggered.connect(self.run_incomplete)
        prepare_analysis_menu.addAction(run_incomplete_action)

        # Add "Download all resources" action
        download_all_resources_action = QAction("Download all resources", self)
        download_all_resources_action.triggered.connect(self.download_all_resources)
        prepare_analysis_menu.addAction(download_all_resources_action)

        # Set the menu on the tool button
        self.prepare_analysis_button.setMenu(prepare_analysis_menu)

        # Add the button to the button bar
        button_bar.addWidget(self.prepare_analysis_button)

        # Add a status label to show current operation
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        self.status_label.setFixedWidth(200)
        self.status_label.setVisible(False)
        button_bar.addWidget(self.status_label)

        self.project_button = QPushButton("Project")
        self.project_button.clicked.connect(self.switch_to_setup_tab)
        button_bar.addWidget(self.project_button)

        self.help_button = QPushButton("Help")
        self.help_button.clicked.connect(self.switch_to_next_tab)
        button_bar.addWidget(self.help_button)
        # Add two progress bars to monitor all workflow progress and individual progress
        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setRange(0, 100)
        self.overall_progress_bar.setValue(0)
        self.overall_progress_bar.setFormat("Overall Progress: %p%")
        self.overall_progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.overall_progress_bar.setVisible(False)
        self.overall_progress_bar.setFixedHeight(20)
        self.overall_progress_bar.setFixedWidth(200)
        button_bar.addWidget(self.overall_progress_bar)
        self.workflow_progress_bar = QProgressBar()
        self.workflow_progress_bar.setRange(0, 100)
        self.workflow_progress_bar.setValue(0)
        self.workflow_progress_bar.setFormat("Task Progress: %p%")
        self.workflow_progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.workflow_progress_bar.setVisible(False)
        self.workflow_progress_bar.setFixedHeight(20)
        self.workflow_progress_bar.setFixedWidth(200)
        button_bar.addWidget(self.workflow_progress_bar)

        self.treeView.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)

        layout.addLayout(button_bar)
        self.setLayout(layout)

        # Connect the working directory changed signal to the slot
        # Workflows need to be run in batches: first indicators, then factors, then dimensions
        # to prevent race conditions
        self.workflow_queue = []
        self.workflow_scope_item = None
        # Set by run_all so a successful complete run ends with the analysis
        # report being generated and opened for the user.
        self._open_report_when_done = False
        self.queue_manager.processing_completed.connect(self.run_next_workflow_queue)
        self.queue_manager.processing_error.connect(self.on_processing_error)

    def on_item_double_clicked(self, index):
        """⚙️ On item double clicked.

        Args:
            index: Index.
        """
        # Action to trigger on double-click
        item = index.internalPointer()

        # Don't allow interaction with disabled items
        if not item.is_enabled():
            return

        if item.role == "indicator":
            self.edit_factor_aggregation(item.parent(), selected_guids=[item.guid])
        elif item.role == "factor":
            self.edit_factor_aggregation(item)
        elif item.role == "dimension":
            self.edit_dimension_aggregation(item)
        elif item.role == "analysis":
            self.edit_analysis_aggregation(item)

    def on_item_clicked(self, index: QModelIndex):
        """
        Slot that runs whenever an item in the tree is clicked.

        Args:
            index: QModelIndex of the clicked item.
        """
        item = index.internalPointer()
        if not item or not item.is_enabled():
            return

        show_layer_on_click = setting(key="show_layer_on_click", default=True)
        if show_layer_on_click:
            analysis_raster_key = "result_file"
            if item.role == "dimension":
                column_name = f"dim_{item.attribute('id').lower().replace(' ', '_').replace('-', '_')}"
            elif item.role == "factor":
                column_name = f"fac_{item.attribute('id').lower().replace(' ', '_').replace('-', '_')}"
            elif item.role == "indicator":
                column_name = item.attribute("id").lower().replace(" ", "_").replace("-", "_")
            elif item.role == "analysis":
                use_masked, analysis_raster_key = self._analysis_display(item)
                column_name = "geoe3_masked" if use_masked else "geoe3"  # Analysis aggregation uses geoe3 column
            else:
                column_name = None

            if column_name is None or self._get_render_strategy() == "raster":
                if item.role == "analysis":
                    add_to_map(item, key=analysis_raster_key, layer_name="GeoE3 Score", group="GeoE3")
                else:
                    add_to_map(item)
            else:
                add_grid_layer_to_map(item, column_name, self.working_directory)
        # TEMPORARY: Disable writing layer name into top-left overlay label.
        # show_overlay = setting(key="show_overlay", default=False)
        # if show_overlay:
        #     QSettings().setValue("geoe3/overlay_label", item.data(0))
        show_pie = setting(key="show_pie_overlay", default=False)
        if show_pie:
            # TODO - calculate the pie data
            QSettings().setValue("geoe3/pie_data", item.data(0))

    def _analysis_display(self, item):
        """Return how the analysis result should be displayed.

        Mirror the decision taken when a workflow completes so that clicking
        the analysis item re-shows the same layer that was last added to the
        map.

        Args:
            item: The analysis tree item.

        Returns:
            tuple: (use_masked, raster_key) where raster_key is the attribute
                holding the GeoE3 score raster, preferring the masked VRT when
                a mask mode is active and the masked product exists.
        """
        mask_mode = item.attribute("mask_mode", "None")
        masked_vrt = item.attribute("geoe3_score_ghsl_masked_result_file", "")
        use_masked = mask_mode not in ("", "None", "none") and bool(masked_vrt)
        raster_key = "geoe3_score_ghsl_masked_result_file" if use_masked else "result_file"
        return use_masked, raster_key

    def on_previous_button_clicked(self):
        """⚙️ On previous button clicked."""
        QSettings().setValue("geoe3/overlay_label", "")
        QSettings().setValue("geoe3/pie_data", "")
        self.switch_to_previous_tab.emit()

    def on_next_button_clicked(self):
        """⚙️ On next button clicked."""
        QSettings().setValue("geoe3/overlay_label", "")
        QSettings().setValue("geoe3/pie_data", "")
        self.switch_to_next_tab.emit()

    def clear_item(self):
        """Clear the outputs for a single item (non-recursive).

        Besides resetting the item's own status/result attributes, this
        also removes its on-disk outputs (masked rasters etc.), blanks its
        own study_area_grid column, and removes its own map layer(s) from
        the legend/registry. Children are left completely untouched -
        their own results, grid columns, rasters, and layers/groups stay
        exactly as they were - matching "clear this item, then re-run it
        trusting its already-complete children".

        A factor with exactly one child indicator is hidden from the tree
        view entirely - JsonTreeModel.data() promotes that indicator's row
        to display in the factor's place (labeled with the factor's name),
        so the one row the user sees and clicks really represents TWO tree
        items sharing a single visible row. Clearing "that row" must clear
        both, or the factor's own column/rasters/layer silently survive
        untouched while the user believes the whole thing was cleared.
        """
        index = self.treeView.currentIndex()
        item = index.internalPointer()

        self._clear_single_item_outputs(item)

        if item.role == "indicator":
            parent = item.parentItem
            if parent and parent.role == "factor" and not parent.is_visible():
                self._clear_single_item_outputs(parent)

        self.save_json_to_working_directory()

    def _clear_single_item_outputs(self, item):
        """Clear one item's own outputs/attributes - see clear_item()."""
        from geest.core.grid_column_utils import clear_grid_column
        from geest.core.utilities import remove_from_map

        # Remove only the files directly inside this item's own workflow
        # directory - never recurse into subdirectories, which belong to
        # this item's children (e.g. a factor's indicators).
        if self.working_directory:
            item_directory = os.path.join(self.working_directory, *item.getPaths())
            if os.path.isdir(item_directory):
                for filename in os.listdir(item_directory):
                    file_path = os.path.join(item_directory, filename)
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        try:
                            os.unlink(file_path)
                        except OSError as error:
                            log_message(
                                f"Failed to delete {file_path}: {error}",
                                tag="GeoE3",
                                level=Qgis.Warning,
                            )

        # Blank this item's own study_area_grid column (not its children's).
        if self.working_directory:
            gpkg_path = os.path.join(self.working_directory, "study_area", "study_area.gpkg")
            if os.path.exists(gpkg_path):
                clear_grid_column(gpkg_path, item.gridColumnName())

        # Remove this item's own layer(s) from the legend/registry, keeping
        # the group that holds its children's layers (if any) intact.
        remove_from_map(item)

        item.clear(recursive=False)

    def clear_workflows(self):
        """
        Recursively mark workflows as not done, delete their working directories and their file_paths.

        It will reset the self.run_only_incomplete flag to only clear incomplete workflows if requested.

        :param parent_item: The parent item to process. If none, start from the root.
        """
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setStyleSheet(theme_stylesheet())
        msg_box.setWindowTitle("Clear Workflows")
        msg_box.setText(
            f"This action will DELETE all files and folders in the working directory ({self.working_directory}). Do you want to continue?"
        )
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        open_folder_button = msg_box.addButton("Open Folder", QMessageBox.ButtonRole.ActionRole)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)

        reply = msg_box.exec()

        if msg_box.clickedButton() == open_folder_button:
            if self.working_directory:
                open_with_system_handler(self.working_directory)
                return

        if reply == QMessageBox.StandardButton.No or reply == QMessageBox.DialogCode.Rejected:
            return
        self.run_only_incomplete = False
        # Remove every file in self.working_directory except
        # mode.json and the study_area folder
        exceptions = [
            "model.json",
            "study_area",
            "study_area_report.pdf",
            "road_network.gpkg",
            "settlements.gpkg",
        ]
        if self.working_directory is None:
            log_message(
                "No working directory set, cannot clear workflows.",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            return
        for filename in os.listdir(self.working_directory):
            file_path = os.path.join(self.working_directory, filename)
            if filename not in exceptions:
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    log_message(
                        f"Failed to delete {file_path}. Reason: {e}",
                        level=Qgis.Critical,
                    )
        root = QgsProject.instance().layerTreeRoot()
        for child in root.children():
            if child.name() == "GeoE3":
                root.removeChildNode(child)
        # Mark all items in the data model as not run
        item = self.model.rootItem
        item.clear(recursive=True)  # sets status to not run and blanks file path

        self.save_json_to_working_directory()

    @pyqtSlot(str)
    def working_directory_changed(self, new_directory):
        """Change the working directory and load the model.json if available.

        Args:
            new_directory: Path to the new working directory.
        """
        log_message(
            f"Working directory changed to {new_directory}",
            tag="GeoE3",
            level=Qgis.Info,
        )
        self.working_directory = new_directory
        # Verify (and self-heal if needed) the study area GeoPackage before
        # the user starts working with this project.
        self.check_study_area_gpkg_health(reason="project open")
        # Offer to sweep orphaned layers (registry entries hidden from the
        # legend, typically left behind by interrupted runs).
        # ⚠️ Deferred: this handler runs inside the project-load signal —
        # showing a modal dialog here re-enters the event loop mid-load, and
        # removing layers at that point deletes layers the loader has
        # registered but not yet attached to the legend (segfault, and every
        # loading layer misdetects as an orphan). Wait until the load has
        # fully settled.
        QTimer.singleShot(3000, self.prompt_remove_orphaned_layers)
        model_path = os.path.join(new_directory, "model.json")

        project_path = QgsProject.instance().fileName()
        if project_path:
            checksum = hash(project_path)
        else:
            checksum = None

        if os.path.exists(model_path):
            try:
                self.json_file = model_path
                self.load_json()  # sets the class member json_data
                self.model.loadJsonData(self.json_data)
                self.apply_women_considerations_logic()  # Hide factors based on women considerations
                # Hide factors that have only a single indicator (indicator shown in their place)
                self.model.toggle_single_child_factors_visibility(hide_single_child=True)
                self.treeView.expandAll()
                log_message(f"Loaded model.json from {model_path}")

                # If this is a first time use of the analysis project lets set some things up
                analysis_item = self.model.get_analysis_item()
                analysis_data = analysis_item.attributes()
                log_message(analysis_item.attributesAsMarkdown())
                if analysis_data.get("working_folder", "Not Set"):
                    analysis_data["working_folder"] = self.working_directory
                else:
                    if not os.path.exists(analysis_data["working_folder"]):
                        analysis_data["working_folder"] = self.working_directory
                # Use the last dir in the working directory path as the analysis name
                if analysis_data.get("analysis_name", "Not Set"):
                    analysis_name = os.path.basename(self.working_directory)
                    analysis_data["analysis_name"] = f"Women's Economic Empowerment - {analysis_name}"
                # analysis_item.setData(0, analysis_data.get("analysis_name", "Analysis"))
                analysis_item.setData(0, "GeoE3 Score")
                settings = QSettings()
                # This is the top level folder for work files
                settings.setValue("last_working_directory", self.working_directory)
                # Use QGIS internal settings for the association between model path and QGIS project
                set_setting(str(checksum), self.working_directory, store_in_project=True)

            except Exception as e:
                log_message(
                    f"Error loading model.json: {str(e)}",
                    tag="GeoE3",
                    level=Qgis.Critical,
                )
        else:
            log_message(
                f"No model.json found in {new_directory}, using default.",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            # copy the default model.json to the working directory
            master_model_path = resources_path("resources", "model.json")
            if os.path.exists(master_model_path):
                try:
                    shutil.copy(master_model_path, model_path)
                    log_message(f"Copied master model.json to {model_path}")
                except Exception as e:
                    log_message(
                        f"Error copying master model.json: {str(e)}",
                        tag="GeoE3",
                        level=Qgis.Critical,
                    )
            self.load_json()
            self.model.loadJsonData(self.json_data)
            self.apply_women_considerations_logic()  # Hide factors based on women considerations
            # Hide factors that have only a single indicator (indicator shown in their place)
            self.model.toggle_single_child_factors_visibility(hide_single_child=True)
            self.treeView.expandAll()
        # Collapse any factors that have only a single indicator
        self.treeView.collapse_single_nodes()

    def check_study_area_gpkg_health(self, reason: str = "") -> None:
        """Run a GeoPackage health check (with in-place self-heal) in the background.

        Checks the study area GeoPackage for corruption (stale WAL journals,
        duplicated schema objects from historic write races, structural btree
        damage) and repairs it in place when possible. Runs as a QgsTask so
        the UI never blocks, even on very large GeoPackages.

        Args:
            reason: Short description of what triggered the check (for logs).
        """
        if not self.working_directory:
            return
        gpkg_path = os.path.join(self.working_directory, "study_area", "study_area.gpkg")
        if not os.path.exists(gpkg_path):
            return

        def _check(task) -> bool:
            from geest.core.gpkg_doctor import heal_geopackage
            from geest.core.grid_column_utils import grid_cell_count

            # Breadcrumb for grid-truncation forensics: every health check
            # records the cell count so logs bracket any loss of grid data.
            log_message(
                f"GeoPackage health check ({reason}): analysis grid has {grid_cell_count(gpkg_path)} cells",
                tag="GeoE3",
                level=Qgis.Info,
            )
            report = heal_geopackage(
                gpkg_path,
                log=lambda message: log_message(message, tag="GeoE3", level=Qgis.Warning),
            )
            if report.was_corrupt:
                log_message(
                    f"GeoPackage health check ({reason}): {report.summary()}",
                    tag="GeoE3",
                    level=Qgis.Warning if report.healthy else Qgis.Critical,
                )
            else:
                log_message(
                    f"GeoPackage health check ({reason}): {os.path.basename(gpkg_path)} is healthy",
                    tag="GeoE3",
                    level=Qgis.Info,
                )
            self._last_gpkg_health_report = report
            return report.healthy

        def _finished(exception, healthy=None) -> None:
            report = getattr(self, "_last_gpkg_health_report", None)
            if exception is not None or report is None:
                return
            if report.was_corrupt and report.healthy:
                try:
                    iface.messageBar().pushMessage(
                        tr("GeoE3"),
                        tr(
                            "The study area GeoPackage was corrupted and has been "
                            "repaired. Please reload the project layers."
                        ),
                        level=Qgis.Warning,
                        duration=15,
                    )
                except Exception:  # nosec B110 — headless/test environments have no iface
                    pass
            elif report.was_corrupt and not report.healthy:
                try:
                    iface.messageBar().pushMessage(
                        tr("GeoE3"),
                        tr(
                            "The study area GeoPackage is corrupted and could not "
                            "be repaired automatically. Re-create the study area "
                            "or restore from a backup."
                        ),
                        level=Qgis.Critical,
                        duration=0,
                    )
                except Exception:  # nosec B110
                    pass

        task = QgsTask.fromFunction(
            f"GeoE3 GeoPackage health check ({reason})",
            _check,
            on_finished=_finished,
        )
        # Keep a reference so the task is not garbage collected mid-run.
        self._gpkg_health_task = task
        QgsApplication.taskManager().addTask(task)

    @pyqtSlot()
    def set_working_directory(self, working_directory):
        """⚙️ Set working directory.

        Args:
            working_directory: Working directory.
        """
        if working_directory:
            self.working_directory = working_directory
            QSettings().setValue("geoe3/overlay_label", "")
            QSettings().setValue("geoe3/pie_data", "")
            self.working_directory_changed(working_directory)

    @pyqtSlot(str)
    def set_road_network_layer_path(self, network_layer_path):
        """⚙️ Set road network layer path.

        Validates the layer before storing it. An empty/None path clears the
        previously stored value instead of being silently ignored, so a
        broken reference detected by the Road Network panel (e.g. the file
        was deleted outside GeoE3) doesn't linger forever in model.json.

        Args:
            network_layer_path: Network layer path, or empty/None to clear it.
        """
        analysis_item = self.model.rootItem.child(0)
        if network_layer_path:
            base_path = network_layer_path.split("|")[0] if "|" in network_layer_path else network_layer_path
            if not os.path.exists(base_path):
                self.show_validation_error(
                    "Road Network Issue",
                    f"Road network layer file not found: {base_path}. "
                    "Please select or download a road network layer again.",
                )
                log_message(
                    f"Refusing to set road_network_layer_path - file not found: {base_path}",
                    level=Qgis.Warning,
                )
                return
            log_message(f"Setting road_network_layer_path in model to {network_layer_path}")
            try:
                analysis_item.setAttribute("road_network_layer_path", network_layer_path)
                self.save_json_to_working_directory()
            except Exception as e:
                log_message(f"Error setting road network path: {str(e)}", level=Qgis.Critical)
        else:
            log_message("Clearing road_network_layer_path in model (no layer selected).")
            try:
                analysis_item.setAttribute("road_network_layer_path", "")
                self.save_json_to_working_directory()
            except Exception as e:
                log_message(f"Error clearing road network path: {str(e)}", level=Qgis.Critical)

    def qgis_project_path(self) -> Optional[str]:
        """Get the associated QGIS project path from the analysis item.

        Returns:
            str: The QGIS project path, or None if not set.
        """
        analysis_item = self.model.get_analysis_item()
        if analysis_item:
            return analysis_item.attribute("qgis_project_path")
        return None

    def set_qgis_project_path(self, qgis_path: str) -> None:
        """Set the associated QGIS project path in the analysis item.

        Args:
            qgis_path: The QGIS project path to store.
        """
        if qgis_path:
            log_message(f"Setting qgis_project_path in model to {qgis_path}")
            analysis_item = self.model.get_analysis_item()
            if analysis_item:
                try:
                    analysis_item.setAttribute("qgis_project_path", qgis_path)
                    self.save_json_to_working_directory()
                except Exception as e:
                    log_message(f"Error setting qgis project path: {str(e)}", level=Qgis.Critical)

    @pyqtSlot()
    def set_ghsl_layer_path(self, ghsl_layer_path: str):
        """⚙️ Set ghsl layer path.

        Args:
            ghsl_layer_path: GHSL layer path.
        """
        if ghsl_layer_path:
            log_message(f"Setting ghsl_layer_path in model to {ghsl_layer_path}")
            analysis_item = self.model.rootItem.child(0)
            try:
                analysis_item.setAttribute("ghsl_layer_path", ghsl_layer_path)
            except Exception as e:
                log_message(f"Error setting ghsl path: {str(e)}", level=Qgis.Critical)
        else:
            log_message("No ghsl layer path provided.")

    @pyqtSlot()
    def save_json_to_working_directory(self):
        """Automatically save the current JSON model to the working directory."""
        if not self.working_directory:
            log_message(
                "No working directory set, cannot save JSON.",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            return
        try:
            json_data = self.model.to_json()

            save_path = os.path.join(self.working_directory, "model.json")
            with open(save_path, "w") as f:
                json.dump(json_data, f, indent=4)
            log_message(f"Saved JSON model to {save_path}")
        except Exception as e:
            log_message(f"Error saving JSON: {str(e)}", level=Qgis.Critical)

    def load_json(self):
        """Load the JSON data from the file."""
        with open(self.json_file, "r") as f:
            self.json_data = json.load(f)
            log_message(f"Loaded JSON data from {self.json_file}")

    def reload_and_apply_women_considerations_logic(self):
        """Reload model.json and apply women considerations logic.

        This method should be called when women considerations settings change
        during runtime (e.g., checkbox toggled in OpenProjectPanel).
        """
        if not hasattr(self, "working_directory") or not self.working_directory:
            log_message(
                "reload_and_apply_women_considerations_logic: working_directory not set",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            return

        model_path = os.path.join(self.working_directory, "model.json")
        if not os.path.exists(model_path):
            log_message(
                f"reload_and_apply_women_considerations_logic: model.json not found at {model_path}",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            return

        self.json_file = model_path
        self.load_json()
        self.apply_women_considerations_logic()

    def apply_women_considerations_logic(self):
        """Apply factor enabled/disabled state based on women considerations setting.

        Uses the women_enabling attribute from model.json for each factor:
        - women_enabling = 1: Women-specific factors (enabled when women considerations ON)
        - women_enabling = 0: Generic factors (always enabled)
        - women_enabling = 2: EPLEX factors (enabled when women considerations OFF - inverse)
        """
        if not hasattr(self, "json_data") or self.json_data is None:
            return

        contextual_data = None
        for dimension in self.json_data.get("dimensions", []):
            if dimension.get("id", "").lower() == "contextual":
                contextual_data = dimension
                break

        if contextual_data is not None:
            women_considerations_enabled = contextual_data.get("women_considerations_enabled")
            eplex_score = contextual_data.get("eplex_score")
        else:
            women_considerations_enabled = None
            eplex_score = None

        if women_considerations_enabled is None:
            women_considerations_enabled = self.json_data.get("women_considerations_enabled", True)
        if eplex_score is None:
            eplex_score = self.json_data.get("eplex_score", 0.0)
        log_message(f"Women considerations enabled: {women_considerations_enabled}, EPLEX score: {eplex_score}")

        # Get all dimensions from the model
        root_item = self.model.get_analysis_item()
        if not root_item:
            return

        # Iterate through dimensions
        for dim_idx in range(root_item.childCount()):
            dimension = root_item.child(dim_idx)
            if not dimension:
                continue

            # Propagate settings to Contextual dimension item attributes
            if dimension.attribute("id", "").lower() == "contextual":
                dimension.setAttribute("women_considerations_enabled", women_considerations_enabled)
                dimension.setAttribute("eplex_score", eplex_score)

            # Iterate through factors in this dimension
            for factor_idx in range(dimension.childCount()):
                factor = dimension.child(factor_idx)
                if not factor:
                    continue

                women_enabling = resolve_women_enabling_for_factor(
                    factor.attribute("id", ""), factor.attribute("women_enabling", 0)
                )
                factor_name = factor.data(0)

                # Determine enabled state based on women_enabling value
                if women_enabling == 1:
                    # Women-specific factors: enabled when women considerations ON, disabled when OFF
                    enabled = women_considerations_enabled
                    log_message(f"Factor '{factor_name}' (women_enabling=1): enabled={enabled}")
                elif women_enabling == 2:
                    # EPLEX factors: enabled when women considerations OFF, disabled when ON (inverse)
                    enabled = not women_considerations_enabled
                    log_message(f"Factor '{factor_name}' (women_enabling=2): enabled={enabled}")
                else:
                    # Generic factors (women_enabling=0): always enabled
                    enabled = True

                # Apply enabled state to factor
                factor.set_enabled(enabled)

                # Also apply to all child indicators
                for indicator_idx in range(factor.childCount()):
                    indicator = factor.child(indicator_idx)
                    if indicator:
                        indicator.set_enabled(enabled)

            # Rebalance eligible factors, preserving factors explicitly
            # excluded by the user so they remain available to re-enable.
            enabled_factors = [
                dimension.child(idx)
                for idx in range(dimension.childCount())
                if dimension.child(idx)
                and dimension.child(idx).is_enabled()
                and dimension.child(idx).attribute("analysis_mode", "") != "Do Not Use"
            ]
            if enabled_factors:
                equal_weight = 1.0 / len(enabled_factors)
            else:
                equal_weight = 0.0

            for factor_idx in range(dimension.childCount()):
                factor = dimension.child(factor_idx)
                if not factor:
                    continue
                is_manually_disabled = factor.attribute("analysis_mode", "") == "Do Not Use"
                new_weight = equal_weight if factor.is_enabled() and not is_manually_disabled else 0.0
                root_item.updateFactorWeighting(factor.guid, new_weight)

        # Force a complete refresh of the tree view
        self.model.beginResetModel()
        self.model.endResetModel()

        # Force viewport repaint
        self.treeView.viewport().update()
        self.treeView.update()

    def load_json_from_file(self):
        """Prompt the user to load a JSON file and update the tree."""
        json_file, _ = QFileDialog.getOpenFileName(
            self, "Open JSON File", os.getcwd(), "JSON Files (*.json);;All Files (*)"
        )
        if json_file:
            self.json_file = json_file
            self.load_json()
            self.model.loadJsonData(self.json_data)
            self.apply_women_considerations_logic()  # Hide factors based on women considerations
            # Hide factors that have only a single indicator (indicator shown in their place)
            self.model.toggle_single_child_factors_visibility(hide_single_child=True)
            self.treeView.expandAll()

    def export_json_to_file(self):
        """Export the current tree data to a JSON file."""
        json_data = self.model.to_json()
        with open("export.json", "w") as f:
            json.dump(json_data, f, indent=4)
        QMessageBox.information(self, "Export Success", "Tree exported to export.json")

    def add_dimension(self):
        """Add a new dimension to the model."""
        self.model.add_dimension()

    def open_context_menu(self, position: QPoint):
        """Handle right-click context menu.

        Args:
            position: Position where the context menu was requested.
        """

        index = self.treeView.indexAt(position)
        if not index.isValid():
            return

        item = index.internalPointer()

        # Don't show context menu for disabled items
        if not item.is_enabled():
            return
        show_json_attributes_action = QAction("Show Attributes", self)
        show_json_attributes_action.triggered.connect(lambda: self.show_attributes(item))
        # We disable items by setting their weight to 0
        if item.getStatus() == "Excluded from analysis":
            disable_action = QAction("Enable", self)
            disable_action.triggered.connect(lambda: self.enable_item(item))
        else:
            disable_action = QAction("Disable", self)
            disable_action.triggered.connect(lambda: self.disable_item(item))

        add_to_map_action = QAction("Add to map", self)
        add_to_map_action.triggered.connect(lambda: add_to_map(item))

        run_item_action = QAction("Run Item Workflow", self)

        # If shift is pressed, change the text to "Rerun Item Workflow"
        def update_action_text():
            """🔄 Update action text."""
            text = (
                "Rerun Item Workflow"
                if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier
                else "Run Item Workflow"
            )
            run_item_action.setText(text)

        # Update initially
        update_action_text()
        clear_item_action = QAction("Clear Item", self)
        clear_item_action.triggered.connect(self.clear_item)
        clear_results_action = QAction("Clear Results", self)
        clear_results_action.triggered.connect(self.clear_workflows)

        # Update when menu shows
        menu = SolidMenu(self)

        menu.aboutToShow.connect(update_action_text)
        # Add event filter to menu to update when shift is pressed while menu is open
        menu.installEventFilter(self)
        run_item_action.triggered.connect(
            lambda: self.run_item(
                item,
                shift_pressed=QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier,
            )
        )
        open_working_directory_action = QAction("Open Working Directory", self)
        open_working_directory_action.triggered.connect(lambda: self.open_working_directory(item))

        if item.role == "analysis":
            menu = SolidMenu(self)
            edit_analysis_action = QAction("🔘 Edit Weights and Settings", self)
            edit_analysis_action.triggered.connect(lambda: self.edit_analysis_aggregation(item))  # Connect to method
            set_network_layers_action = QAction("Set Network Layers")
            set_network_layers_action.triggered.connect(self.switch_to_network_tab)  # Connect to method
            set_ors_action = QAction("Set ORS Options")
            set_ors_action.triggered.connect(self.switch_to_ors_tab)
            remove_unused_layers_action = QAction("Clean Unused Layers from Project")
            remove_unused_layers_action.triggered.connect(self.clean_unused_layers)
            menu.addAction(edit_analysis_action)
            menu.addAction(set_network_layers_action)
            menu.addAction(set_ors_action)
            menu.addAction(show_json_attributes_action)
            menu.addAction(clear_item_action)
            menu.addAction(clear_results_action)
            menu.addAction(run_item_action)
            menu.addAction(open_working_directory_action)
            menu.addAction(remove_unused_layers_action)

            # Add Animate Results action
            animate_results_action = QAction("Animate results", self)
            animate_results_action.triggered.connect(self.animate_results)
            menu.addAction(animate_results_action)

            add_geoe3_score = QAction("Add GeoE3 Score to Map (Raster)")
            add_geoe3_score.triggered.connect(
                lambda: add_to_map(item, key="result_file", layer_name="GeoE3 Score", group="GeoE3")
            )
            menu.addAction(add_geoe3_score)

            add_geoe3_score_grid = QAction("Add GeoE3 Score to Map (Grid)")
            add_geoe3_score_grid.triggered.connect(lambda: add_grid_layer_to_map(item, "geoe3", self.working_directory))
            menu.addAction(add_geoe3_score_grid)

            add_geoe3_by_population = QAction("Add GeoE3 by Pop to Map")
            add_geoe3_by_population.triggered.connect(
                lambda: add_grid_layer_to_map(
                    item,
                    column_name="geoe3_by_population",
                    working_directory=self.working_directory,
                    layer_name="GeoE3 by Population (Grid)",
                    group="GeoE3",
                )
            )
            menu.addAction(add_geoe3_by_population)

            add_geoe3_by_population_aggregate = QAction("Add GeoE3 Aggregates to Map")
            add_geoe3_by_population_aggregate.triggered.connect(lambda: self.add_aggregates_to_map(item))
            menu.addAction(add_geoe3_by_population_aggregate)

            add_masked_scores = QAction("Add Masked Scores to Map")
            add_masked_scores.triggered.connect(lambda: self.add_masked_scores_to_map(item))
            menu.addAction(add_masked_scores)

            add_job_opportunities_mask = QAction("Add Job Opportunities Mask to Map")
            add_job_opportunities_mask.triggered.connect(lambda: self.add_opportunities_mask_to_map(item))
            menu.addAction(add_job_opportunities_mask)

            add_ghsl_settlements = QAction("Add GHSL Settlements to Map")
            add_ghsl_settlements.triggered.connect(self.add_ghsl_settlements_to_map)
            menu.addAction(add_ghsl_settlements)

            add_study_area_layers_action = QAction("Add Study Area to Map", self)
            add_study_area_layers_action.triggered.connect(self.add_study_area_to_map)
            menu.addAction(add_study_area_layers_action)

            add_analysis_report_action = QAction("Show Analysis Report", self)
            add_analysis_report_action.triggered.connect(self.generate_analysis_report)
            menu.addAction(add_analysis_report_action)

            add_study_area_report_action = QAction("Show Study Area Report", self)
            add_study_area_report_action.triggered.connect(self.generate_study_area_report)
            menu.addAction(add_study_area_report_action)

            open_log_file_action = QAction("Open Log File", self)
            open_log_file_action.triggered.connect(self.open_log_file)
            menu.addAction(open_log_file_action)
            open_log_file_action.triggered.connect(self.open_log_file)
            menu.addAction(open_log_file_action)
            menu.addAction(open_working_directory_action)

        # Check the role of the item directly from the stored role
        if item.role == "dimension":
            # Context menu for dimensions
            edit_aggregation_action = QAction("🔘 Edit Weights", self)
            edit_aggregation_action.triggered.connect(
                lambda: self.edit_dimension_aggregation(item)
            )  # Connect to method
            add_factor_action = QAction("Add Factor", self)
            remove_dimension_action = QAction("Remove Dimension", self)

            # Add grid layer action
            add_grid_to_map_action = QAction("Add to map (Grid)", self)
            column_name = f"dim_{item.attribute('id').lower().replace(' ', '_').replace('-', '_')}"
            add_grid_to_map_action.triggered.connect(
                lambda _, col=column_name, i=item: add_grid_layer_to_map(i, col, self.working_directory)
            )

            # Connect actions
            add_factor_action.triggered.connect(lambda: self.model.add_factor(item))
            remove_dimension_action.triggered.connect(lambda: self.model.remove_item(item))
            # Add actions to menu
            menu = SolidMenu(self)
            menu.addAction(edit_aggregation_action)
            menu.addAction(show_json_attributes_action)
            menu.addAction(clear_item_action)
            menu.addAction(add_to_map_action)
            menu.addAction(add_grid_to_map_action)
            menu.addAction(run_item_action)
            menu.addAction(open_working_directory_action)
            menu.addAction(disable_action)

        elif item.role == "factor":
            # Context menu for factors
            edit_aggregation_action = QAction("🔘 Edit Weights", self)  # New action for contextediting aggregation
            add_indicator_action = QAction("Add Indicator", self)
            remove_factor_action = QAction("Remove Factor", self)

            # Add grid layer action
            add_grid_to_map_action = QAction("Add to map (Grid)", self)
            column_name = f"fac_{item.attribute('id').lower().replace(' ', '_').replace('-', '_')}"
            add_grid_to_map_action.triggered.connect(
                lambda _, col=column_name, i=item: add_grid_layer_to_map(i, col, self.working_directory)
            )

            # Connect actions
            edit_aggregation_action.triggered.connect(lambda: self.edit_factor_aggregation(item))  # Connect to method
            add_indicator_action.triggered.connect(lambda: self.model.add_indicator(item))
            remove_factor_action.triggered.connect(lambda: self.model.remove_item(item))

            # Add actions to menu
            menu = SolidMenu(self)
            menu.addAction(edit_aggregation_action)
            menu.addAction(show_json_attributes_action)
            menu.addAction(clear_item_action)
            menu.addAction(add_to_map_action)
            menu.addAction(add_grid_to_map_action)
            menu.addAction(run_item_action)
            menu.addAction(open_working_directory_action)
            menu.addAction(disable_action)

        elif item.role == "indicator":
            # Context menu for layers
            # Editing an indicator will open the attributes dialog
            # of its parent factor...
            show_properties_action = QAction("🔘 Edit Weights", self)

            # Add grid layer action (indicators use raw ID without prefix)
            add_grid_to_map_action = QAction("Add to map (Grid)", self)
            column_name = item.attribute("id").lower().replace(" ", "_").replace("-", "_")
            add_grid_to_map_action.triggered.connect(
                lambda _, col=column_name, i=item: add_grid_layer_to_map(i, col, self.working_directory)
            )

            # Connect actions
            show_properties_action.triggered.connect(
                lambda: self.edit_factor_aggregation(item.parent(), selected_guids=[item.guid])
            )
            # Add actions to menu
            menu = SolidMenu(self)
            menu.addAction(show_properties_action)
            menu.addAction(show_json_attributes_action)
            menu.addAction(clear_item_action)
            menu.addAction(add_to_map_action)
            menu.addAction(add_grid_to_map_action)
            menu.addAction(run_item_action)
            menu.addAction(open_working_directory_action)
            menu.addAction(disable_action)

        # Show the menu at the cursor's position
        menu.exec(self.treeView.viewport().mapToGlobal(position))

    def generate_analysis_report(self):
        """Add a report showing analysis results."""
        if not self.working_directory:
            log_message(
                "No working directory set, cannot generate analysis report.",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            return

        # Show progress bar in indeterminate mode
        self.overall_progress_bar.setVisible(True)
        self.overall_progress_bar.setMinimum(0)
        self.overall_progress_bar.setMaximum(0)  # Indeterminate/bouncing
        self.overall_progress_bar.setFormat("Generating analysis report...")

        # Start report generation in background
        model_path = os.path.join(self.working_directory, "model.json")
        self.analysis_report_task = AnalysisReportTask(self.working_directory, model_path)
        self.analysis_report_task.taskCompleted.connect(self.on_analysis_report_completed)
        self.analysis_report_task.taskTerminated.connect(self.on_analysis_report_failed)

        QgsApplication.taskManager().addTask(self.analysis_report_task)

    def on_analysis_report_completed(self):
        """Slot called when analysis report generation completes successfully."""
        log_message("Analysis report generated successfully.", tag="GeoE3", level=Qgis.Info)

        self.overall_progress_bar.setMinimum(0)
        self.overall_progress_bar.setMaximum(100)
        self.overall_progress_bar.setValue(100)
        self.overall_progress_bar.setFormat("Report generated successfully!")
        self.overall_progress_bar.setVisible(False)

    def on_analysis_report_failed(self):
        """Slot called when analysis report generation fails."""
        error_msg = (
            str(self.analysis_report_task.exception)
            if hasattr(self.analysis_report_task, "exception") and self.analysis_report_task.exception
            else "Unknown error"
        )

        log_message(f"Analysis report generation failed: {error_msg}", tag="GeoE3", level=Qgis.Critical)

        self.overall_progress_bar.setMinimum(0)
        self.overall_progress_bar.setMaximum(100)
        self.overall_progress_bar.setValue(0)
        self.overall_progress_bar.setFormat(f"Error: {error_msg}")
        self.overall_progress_bar.setVisible(False)

    def generate_study_area_report(self):
        """Add a report showing population information for the study area."""
        gpkg_path = os.path.join(self.working_directory, "study_area", "study_area.gpkg")
        with StudyAreaReport(gpkg_path=gpkg_path, report_name="Study Area Summary") as report:
            self.overall_progress_bar.setVisible(True)
            self.overall_progress_bar.setValue(10)
            report.create_layout()
            self.overall_progress_bar.setValue(30)
            report.export_pdf(os.path.join(self.working_directory, "study_area_report.pdf"))
            self.overall_progress_bar.setValue(90)

        # Open the pdf using the system PDF viewer (detached — a blocking
        # call here freezes the QGIS event loop behind the viewer window).
        open_with_system_handler(os.path.join(self.working_directory, "study_area_report.pdf"))
        self.overall_progress_bar.setValue(100)
        self.overall_progress_bar.setVisible(False)

    def add_masked_scores_to_map(self, item):
        """Add the masked scores to the map as grid layers.

        Args:
            item: The analysis item containing masked score data.
        """
        # Add GeoE3 masked score as grid layer
        add_grid_layer_to_map(
            item,
            column_name="geoe3_masked",
            working_directory=self.working_directory,
            layer_name="Masked GeoE3 Score (Grid)",
            group="GeoE3",
        )
        # Add GeoE3 by population masked score as grid layer
        add_grid_layer_to_map(
            item,
            column_name="geoe3_by_population_masked",
            working_directory=self.working_directory,
            layer_name="Masked GeoE3 by Population Score (Grid)",
            group="GeoE3",
        )

    def add_opportunities_mask_to_map(self, item):
        """Add the opportunities mask to the map as a grid layer.

        Args:
            item: The analysis item containing opportunities mask configuration.
        """
        add_grid_layer_to_map(
            item,
            column_name="opportunities_mask",
            working_directory=self.working_directory,
            layer_name="Opportunities Mask (Grid)",
            group="GeoE3",
        )

    def add_ghsl_settlements_to_map(self):
        """Add the GHSL settlements layer from the study area GeoPackage to the map."""
        working_dir = self.working_directory
        if not working_dir:
            iface.messageBar().pushMessage(
                "GHSL Settlements",
                "No working directory set.",
                level=Qgis.Warning,
                duration=5,
            )
            return

        gpkg_path = os.path.join(working_dir, "study_area", "study_area.gpkg")
        if not os.path.exists(gpkg_path):
            iface.messageBar().pushMessage(
                "GHSL Settlements",
                "Study area GeoPackage not found. Create a project first.",
                level=Qgis.Warning,
                duration=5,
            )
            return

        layer_name = "ghsl_settlements"
        layer_path = f"{gpkg_path}|layername={layer_name}"

        # Check if layer exists in the GeoPackage
        from osgeo import ogr

        ds = ogr.Open(gpkg_path, 0)
        if ds is None:
            iface.messageBar().pushMessage(
                "GHSL Settlements",
                "Could not open study area GeoPackage.",
                level=Qgis.Warning,
                duration=5,
            )
            return

        layer_exists = ds.GetLayerByName(layer_name) is not None
        ds = None

        if not layer_exists:
            iface.messageBar().pushMessage(
                "GHSL Settlements",
                "GHSL layer not found. It may not have been downloaded during project creation.",
                level=Qgis.Warning,
                duration=8,
            )
            return

        # Load the layer
        layer = QgsVectorLayer(layer_path, "GHSL Settlements", "ogr")
        if not layer.isValid():
            iface.messageBar().pushMessage(
                "GHSL Settlements",
                "Failed to load GHSL settlements layer.",
                level=Qgis.Warning,
                duration=5,
            )
            return

        # Add to map under Study Area group
        project = QgsProject.instance()
        root = project.layerTreeRoot()
        study_area_group = root.findGroup("GeoE3 Study Area")
        if study_area_group is None:
            study_area_group = root.insertGroup(0, "GeoE3 Study Area")

        project.addMapLayer(layer, False)
        study_area_group.addLayer(layer)

        iface.messageBar().pushMessage(
            "GHSL Settlements",
            "Layer added to map.",
            level=Qgis.Success,
            duration=3,
        )

    def add_aggregates_to_map(self, item):
        """Add all the aggregate products to the map.

        Args:
            item: The analysis item containing aggregate data.
        """
        add_to_map(
            item,
            key="geoe3_score_subnational_aggregation",
            layer_name="GeoE3 Score Aggregate",
            group="GeoE3",
        )
        add_to_map(
            item,
            key="geoe3_by_population_subnational_aggregation",
            layer_name="GeoE3 by Population Aggregate",
            group="GeoE3",
        )
        add_to_map(
            item,
            key="geoe3_score_ghsl_masked_subnational_aggregation",
            layer_name="GeoE3 Score GHSL Masked Aggregate",
            group="GeoE3",
        )
        add_to_map(
            item,
            key="geoe3_score_by_population_ghsl_masked_subnational_aggregation",
            layer_name="GeoE3 Score by Population GHSL Masked Aggregate",
            group="GeoE3",
        )

    def open_working_directory(self, item: JsonTreeItem = None):
        """Open the working directory in the file explorer.

        If the analysis node is clicked, we open the top level working dir, otherwise
        we open the subfolder for the item.

        If item is none we assume that the working directory is the top level working directory.

        Args:
            item: The item to open the working directory for.
        """
        log_message("Opening working directory.")
        if item is None:
            working_directory = self.working_directory
        elif item.role == "analysis":
            working_directory = self.working_directory
        elif item.role == "dimension":
            working_directory = os.path.join(self.working_directory, item.data(0).lower())
        elif item.role == "factor":
            working_directory = os.path.join(
                self.working_directory,
                item.parent().data(0).lower(),
                item.data(0).lower().replace(" ", "_").replace("'", "_"),
            )
        elif item.role == "indicator":
            working_directory = os.path.join(
                self.working_directory,
                item.parent().parent().data(0).lower(),
                item.parent().data(0).lower().replace(" ", "_").replace("'", "_"),
                item.data(0).lower().replace(" ", "_").replace("/", "_"),
            )
        log_message(f"Opening working directory: {working_directory}")
        if working_directory:
            open_with_system_handler(working_directory)
        else:
            QMessageBox.warning(self, "No Working Directory", "The working directory is not set.")

    def open_log_file(self):
        """Open the log file in the default text editor."""
        logger = getLogger()
        log_file_path = logger.handlers[0].baseFilename

        if os.path.exists(log_file_path):
            open_with_system_handler(log_file_path)
        else:
            QMessageBox.warning(self, "Log File Not Found", "The log file does not exist.")

    def disable_item(self, item):
        """Disable the item and its children.

        Args:
            item: The item to disable.
        """
        item.disable()

    def enable_item(self, item):
        """Enable the item and its children.

        Args:
            item: The item to enable.
        """
        item.enable()

    def show_attributes(self, item):
        """Show the attributes of the item in a table.

        Args:
            item: The item whose attributes to display.
        """
        attributes = item.attributes()
        # Sort the data alphabetically by key name
        sorted_data = dict(sorted(attributes.items()))

        dialog = QDialog()
        dialog.setWindowState(Qt.WindowState.WindowMaximized)
        dialog.setWindowTitle("Attributes")
        dialog.resize(
            int(QApplication.primaryScreen().geometry().width() * 0.9),
            int(QApplication.primaryScreen().geometry().height() * 0.9),
        )

        layout = QVBoxLayout()
        dialog.setLayout(layout)

        # Create a table to display the data
        table = QTableWidget()
        table.setRowCount(len(sorted_data))
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Key", "Value"])
        table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )  # Only the second column stretches
        # Track if "error_file" exists
        error_file_content = None
        # Populate the table with the sorted data
        for row, (key, value) in enumerate(sorted_data.items()):
            key_item = QTableWidgetItem(key)
            key_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            table.setItem(row, 0, key_item)

            if isinstance(value, dict):
                # Create a nested table for dictionary values
                nested_table = self.create_nested_table(value)
                table.setCellWidget(row, 1, nested_table)
                # Adjust row height to fit nested table
                table.setRowHeight(row, nested_table.height() + 10)  # Add 10px padding
            else:
                value_item = QTableWidgetItem(str(value))
                value_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                table.setItem(row, 1, value_item)
            # Check if this row contains "error_file"
            if key == "error_file" and isinstance(value, str):
                try:
                    with open(value, "r") as file:
                        error_file_content = file.read()
                except (OSError, IOError):
                    error_file_content = f"Unable to read file: {value}"
                except Exception as e:
                    error_file_content = f"Error reading file: {e}"

        layout.addWidget(table)

        # Add buttons
        button_layout = QHBoxLayout()

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.close)
        button_layout.addWidget(close_button)

        # Maximize button
        maximize_button = QPushButton("AutoSize Columns")
        maximize_button.clicked.connect(lambda: self.maximize_dialog(dialog, table))
        button_layout.addWidget(maximize_button)

        # Copy button
        copy_button = QPushButton("Copy to Clipboard")
        copy_button.clicked.connect(lambda: self.copy_to_clipboard_as_markdown(table))
        button_layout.addWidget(copy_button)

        # Show Error File button
        if error_file_content is not None:
            show_error_file_button = QPushButton("Show Error File")
            button_layout.addWidget(show_error_file_button)
            show_error_file_button.clicked.connect(lambda: self.show_error_file_popup(error_file_content))
        layout.addLayout(button_layout)

        # Enable custom context menu for the table
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(lambda pos: self.show_context_menu(table, pos))
        log_message("----------------------")
        log_message("Showing descendant Dimensions.")
        log_message("----------------------")
        for child in item.getDescendantDimensions():
            log_message(child.data(0))
        log_message("----------------------")
        log_message("Showing descendant Factors.")
        log_message("----------------------")
        for child in item.getDescendantFactors():
            log_message(child.data(0))
        log_message("----------------------")
        log_message("Descendant Indicators:")
        log_message("----------------------")
        for child in item.getDescendantIndicators():
            log_message(child.data(0))
        log_message("----------------------")
        dialog.exec()

    def show_error_file_popup(self, error_file_content):
        """Show a popup message with the contents of the error file.

        Args:
            error_file_content: Content of the error file to display.
        """
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Error File Contents")
        msg_box.setText(error_file_content)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    def copy_to_clipboard_as_markdown(self, table: QTableWidget):
        """Copy the table content as Markdown to the clipboard.

        Args:
            table: The table widget to copy.
        """
        headers = [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]
        markdown_lines = ["| " + " | ".join(headers) + " |"]
        markdown_lines.append("| " + " | ".join("---" for _ in headers) + " |")

        for row in range(table.rowCount()):
            row_data = []
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item:
                    row_data.append(item.text())
                else:
                    # Handle cell widgets like nested tables
                    cell_widget = table.cellWidget(row, col)
                    if isinstance(cell_widget, QTableWidget):
                        nested_headers = [
                            cell_widget.horizontalHeaderItem(i).text() for i in range(cell_widget.columnCount())
                        ]
                        nested_data = []
                        for nested_row in range(cell_widget.rowCount()):
                            nested_row_data = [
                                cell_widget.item(nested_row, nested_col).text()
                                for nested_col in range(cell_widget.columnCount())
                            ]
                            nested_data.append(", ".join(nested_row_data))
                        row_data.append(f"Nested: {', '.join(nested_headers)} ({'; '.join(nested_data)})")
                    else:
                        row_data.append("")
            markdown_lines.append("| " + " | ".join(row_data) + " |")

        # Copy the Markdown content to the clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(markdown_lines))

        log_message("Table copied to clipboard as Markdown.")

    def create_nested_table(self, nested_data: dict) -> QTableWidget:
        """Create a QTableWidget to display nested dictionary data.

        Args:
            nested_data: Dictionary data to display in the table.

        Returns:
            QTableWidget configured to display the nested data.
        """
        nested_table = QTableWidget()
        nested_table.setRowCount(len(nested_data))
        nested_table.setColumnCount(2)
        nested_table.setHorizontalHeaderLabels(["Key", "Value"])
        nested_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        for row, (key, value) in enumerate(nested_data.items()):
            key_item = QTableWidgetItem(str(key))  # Convert key to string
            value_item = QTableWidgetItem(str(value))  # Convert value to string
            key_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            value_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)

            nested_table.setItem(row, 0, key_item)
            nested_table.setItem(row, 1, value_item)

        nested_table.setFixedHeight(len(nested_data) * 25)  # Adjust height based on the number of rows
        nested_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        nested_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        nested_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        return nested_table

    def maximize_dialog(self, dialog, table):
        """Maximize the dialog and adjust the table column widths.

        Args:
            dialog: The dialog to maximize.
            table: The table whose columns to adjust.
        """
        dialog.showMaximized()
        # Adjust the first column to fit its content
        table.resizeColumnToContents(0)

    def show_context_menu(self, table, pos):
        """Show a context menu with a copy option on right-click.

        Args:
            table: The table widget.
            pos: Position where the context menu was requested.
        """
        # Get the cell at the position where the right-click occurred
        item = table.itemAt(pos)
        if not item:
            return  # If no cell is clicked, do nothing

        # Create the context menu
        menu = SolidMenu()
        copy_action = menu.addAction("Copy")

        # Execute the menu at the position and check if an action was selected
        action = menu.exec(table.viewport().mapToGlobal(pos))
        if action == copy_action:
            # If "Copy" was selected, copy the cell's content to the clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(item.text())

    def _orphaned_layer_ids(self) -> list:
        """Registry layers that are not shown anywhere in the legend."""
        from qgis.core import QgsLayerTreeGroup, QgsLayerTreeLayer

        project = QgsProject.instance()

        def collect_layer_ids(node):
            ids = set()
            if isinstance(node, QgsLayerTreeLayer):
                layer = node.layer()
                if layer:
                    ids.add(layer.id())
            elif isinstance(node, QgsLayerTreeGroup):
                for child in node.children():
                    ids.update(collect_layer_ids(child))
            return ids

        layers_in_legend = collect_layer_ids(project.layerTreeRoot())
        return [layer_id for layer_id in project.mapLayers() if layer_id not in layers_in_legend]

    def _remove_orphaned_layers(self) -> int:
        """Remove all orphaned layers; returns how many were removed."""
        project = QgsProject.instance()
        orphans = self._orphaned_layer_ids()
        for layer_id in orphans:
            layer = project.mapLayer(layer_id)
            log_message(f"Removing orphaned layer: {layer.name() if layer else layer_id}")
            project.removeMapLayer(layer_id)
        return len(orphans)

    def clean_unused_layers(self):
        """Remove any layers from the project that are not in the QGIS legend."""
        removed_count = self._remove_orphaned_layers()
        # Show a message box to confirm completion and how many layers were removed
        QMessageBox.information(self, "Clean Unused Layers", f"Unused layers have been removed: {removed_count}")

    def prompt_remove_orphaned_layers(self) -> None:
        """Offer to sweep orphaned layers when a project is opened.

        Orphans (registry layers absent from the legend) accumulate from
        crashed runs and, once saved, persist inside the project file —
        so opening a project is the natural moment to offer a cleanup.
        """
        # This runs from a QTimer.singleShot, so the panel may have been
        # destroyed (plugin reload) before the timer fired.
        if sip.isdeleted(self):
            return
        # Never sweep while background tasks run: an in-flight analysis or
        # report task legitimately holds registry layers that are not in the
        # legend, and removing them mid-render crashes QGIS.
        if QgsApplication.taskManager().countActiveTasks() > 0:
            log_message("Skipping orphaned-layer sweep: background tasks are running")
            return
        orphan_count = len(self._orphaned_layer_ids())
        if not orphan_count:
            return
        answer = QMessageBox.question(
            self,
            tr("GeoE3"),
            tr(
                "This project contains {count} orphaned layer(s) — layers loaded in the "
                "project but not shown in the layers panel, usually left behind by an "
                "interrupted run.\n\nRemove them now?"
            ).format(count=orphan_count),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer == QMessageBox.StandardButton.Yes:
            removed = self._remove_orphaned_layers()
            try:
                iface.messageBar().pushMessage(
                    tr("GeoE3"),
                    tr("Removed {count} orphaned layer(s).").format(count=removed),
                    level=Qgis.Info,
                    duration=5,
                )
            except Exception:  # nosec B110 — headless/test environments have no iface
                pass

    def add_study_area_to_map(self):
        """Add the study area layers to the map.

        Note that the area grid layer can be slow to draw!.
        """
        gpkg_path = os.path.join(self.working_directory, "study_area", "study_area.gpkg")
        project = QgsProject.instance()

        # Check if 'GeoE3' group exists, otherwise create it
        root = project.layerTreeRoot()
        geoe3_group = root.findGroup("GeoE3 Study Area")
        if geoe3_group is None:
            geoe3_group = root.insertGroup(0, "GeoE3 Study Area")  # Insert at the top of the layers panel

        layers = [
            "ghsl_settlements",
            "study_area_polygons",
            "study_area_clip_polygons",
            "study_area_grid",
            "study_area_bboxes",
            "study_area_bbox",
            "study_area_creation_status",
            "chunks",
        ]
        for layer_name in layers:
            gpkg_layer_path = f"{gpkg_path}|layername={layer_name}"
            layer = QgsVectorLayer(gpkg_layer_path, layer_name, "ogr")

            if not layer.isValid():
                log_message(
                    f"Failed to add '{layer_name}' layer to the map.",
                    tag="GeoE3",
                    level=Qgis.Critical,
                )
                continue

            source_qml = resources_path("resources", "qml", f"{layer_name}.qml")
            result = layer.loadNamedStyle(source_qml)
            if result[0]:  # loadNamedStyle returns (success, error_message)
                log_message(f"Successfully applied QML style to layer '{layer_name}'")
            else:
                log_message(f"Failed to apply QML style: {result[1]}")

            # Check if a layer with the same data source exists in the correct group
            existing_layer = None
            for child in geoe3_group.children():
                if isinstance(child, QgsLayerTreeGroup):
                    continue
                if child.layer().source() == gpkg_layer_path:
                    existing_layer = child.layer()
                    break

            # If the layer exists, refresh it instead of removing and re-adding
            if existing_layer is not None:
                log_message(f"Refreshing existing layer: {existing_layer.name()}")
                existing_layer.reload()
            else:
                # Add the new layer to the appropriate subgroup
                QgsProject.instance().addMapLayer(layer, False)
                _ = geoe3_group.addLayer(layer)
                log_message(f"Added layer: {layer.name()} to group: {geoe3_group.name()}")

    def edit_analysis_aggregation(self, analysis_item):
        """Open the AnalysisAggregationDialog for editing the weightings of factors in the analysis.

        Args:
            analysis_item: The analysis item to edit.
        """
        dialog = AnalysisAggregationDialog(analysis_item, parent=self)
        if dialog.exec():  # If OK was clicked
            dialog.saveWeightingsToModel()
            self.save_json_to_working_directory()  # Save changes to the JSON if necessary

    def edit_dimension_aggregation(self, dimension_item):
        """Open the DimensionAggregationDialog for editing the weightings of factors in a dimension.

        Args:
            dimension_item: The dimension item to edit.
        """
        dimension_name = dimension_item.data(0)
        dimension_data = dimension_item.attributes()
        if not dimension_data:
            dimension_data = {}
        dialog = DimensionAggregationDialog(dimension_name, dimension_data, dimension_item, parent=self)
        if dialog.exec():  # If OK was clicked
            dialog.saveWeightingsToModel()
            self.save_json_to_working_directory()  # Save changes to the JSON if necessary

    def edit_factor_aggregation(self, factor_item, selected_guids=None):
        """Open the FactorAggregationDialog for editing the weightings of layers in a factor.

        Args:
            factor_item: The factor item to edit.
            selected_guids: Optional subset of indicator GUIDs to display in the dialog.
        """
        factor_name = factor_item.data(0)
        factor_data = factor_item.attributes()
        if not factor_data:
            factor_data = {}
        dialog = FactorAggregationDialog(
            factor_name,
            factor_data,
            factor_item,
            parent=self,
            selected_guids=selected_guids,
        )
        if dialog.exec():  # If OK was clicked
            dialog.save_weightings_to_model()
            self.save_json_to_working_directory()  # Save changes to the JSON if necessary

    def start_workflows(self, workflow_type=None):
        """Start a workflow for each 'layer' node in the tree.

        We process in the order of layers, factors, and dimensions since there
        is a dependency between them. For example, a factor depends on its layers.

        Args:
            workflow_type: Type of workflow to start (indicators, factors, dimensions, analysis).
        """
        scope_item = self.workflow_scope_item or self.model.rootItem
        log_message("\n############################################")
        log_message(f"Starting {workflow_type} workflows")
        log_message("############################################\n")
        if workflow_type == "indicators":
            for item in scope_item.getDescendantIndicators(
                include_completed=not self.run_only_incomplete, include_disabled=False
            ):
                self.queue_workflow_task(item, item.role)
        elif workflow_type == "factors":
            for item in scope_item.getDescendantFactors(
                include_completed=not self.run_only_incomplete, include_disabled=False
            ):
                self.queue_workflow_task(item, item.role)
        elif workflow_type == "dimensions":
            for item in scope_item.getDescendantDimensions(
                include_completed=not self.run_only_incomplete, include_disabled=False
            ):
                self.queue_workflow_task(item, item.role)
        elif workflow_type == "analysis":
            analyses = scope_item.getDescendantAnalyses(include_completed=not self.run_only_incomplete)
            for analysis_item in analyses:
                log_message("############################################")
                log_message(f"Starting analysis workflow for {analysis_item.data(0)}")
                log_message("############################################")
                self.queue_workflow_task(analysis_item, analysis_item.role)

    def _count_workflows_to_run(self, parent_item=None):
        """
        Recursively count workflows that need to be run visiting each node in the tree.

        Args:
            parent_item: The parent item to process. If none, start from the root.
        """
        if parent_item is None:
            parent_item = self.model.rootItem

        count = parent_item.childCount(recursive=True)
        self.items_to_run = count

    def cell_size_m(self):
        """Get the cell size in meters from the analysis item.

        Returns:
            float: Cell size in meters.
        """
        cell_size_m = self.model.get_analysis_item().attributes().get("analysis_cell_size_m", 100.0)
        return cell_size_m

    def analysis_scale(self):
        """Get the analysis scale from the analysis item.

        Returns:
            str: Analysis scale (national or regional).
        """
        analysis_scale = self.model.get_analysis_item().attributes().get("analysis_scale", "national")
        return analysis_scale

    def _get_study_area_area_km2(self) -> float:
        """Get total study area area in km² from study_area_clip_polygons layer.

        Returns:
            float: Total area in km².
        """
        gpkg_path = os.path.join(self.working_directory, "study_area", "study_area.gpkg")
        layer = QgsVectorLayer(f"{gpkg_path}|layername=study_area_clip_polygons", "study_area", "ogr")
        if not layer.isValid():
            log_message(
                f"Could not load study_area_clip_polygons from {gpkg_path}",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            return 0.0
        total_area = 0.0
        for feature in layer.getFeatures():
            geom = feature.geometry()
            if geom:
                total_area += geom.area()
        return total_area / 1_000_000

    def _get_render_strategy(self) -> str:
        """Determine render strategy based on analysis scale and feature count.

        Uses feature count estimate to decide whether raster or vector rendering
        is more appropriate for performance.

        Returns:
            str: 'raster' or 'vector'
        """

        analysis_scale = self.analysis_scale()

        if analysis_scale == "regional":
            return "vector"

        study_area_area_km2 = self._get_study_area_area_km2()
        cell_size_m = self.cell_size_m()
        estimated_features = (study_area_area_km2 * 1_000_000) / (cell_size_m**2)

        return "raster" if estimated_features > MAX_FEATURES_FOR_VECTOR else "vector"

    def road_network_layer_path(self):
        """Get the layer used for network analysis.

        Returns:
            str: Path to the road network layer.
        """
        analysis_item = self.model.get_analysis_item()
        log_message(analysis_item.attributesAsMarkdown())
        road_network_layer_path = analysis_item.attributes().get("road_network_layer_path", "")
        log_message(f"Road Network layer path: {road_network_layer_path}")
        return road_network_layer_path

    def show_validation_error(self, title: str, message: str):
        """Show validation error in inline banner.

        Args:
            title: Title of the validation error.
            message: Error message to display.
        """
        self.warning_message_label.setText(f"<b>{title}:</b> {message}")
        self.warning_widget.setVisible(True)

    def hide_validation_warning(self):
        """Hide validation warning banner."""
        self.warning_widget.setVisible(False)
        self.warning_message_label.setText("")

    def _on_configure_clicked(self):
        """Navigate to network config panel and dismiss warning."""
        self.hide_validation_warning()
        self.switch_to_network_tab.emit()

    def ghsl_layer(self):
        """Get the layer used for ghsl analysis.

        Returns:
            QgsVectorLayer: The GHSL layer.
        """
        ghsl_layer = QgsVectorLayer(
            self.model.get_analysis_item().attributes().get("ghsl_layer", ""),
            "GHSL Layer",
            "ogr",
        )
        return ghsl_layer

    def ghsl_layer_path(self):
        """Get the layer used for ghsl analysis.

        Returns:
            str: Path to the GHSL layer.
        """
        analysis_item = self.model.get_analysis_item()
        log_message(analysis_item.attributesAsMarkdown())
        ghsl_layer_path = analysis_item.attributes().get("ghsl_layer_path", "")
        log_message(f"GHSL layer path: {ghsl_layer_path}")
        return ghsl_layer_path

    def queue_workflow_task(self, item, role):
        """Queue a workflow task based on the role of the item.

        ⭐️ These calls all pass a reference of the item to the workflow task.
            The task directly modifies the item's properties to update the tree.

        Args:
            item: The tree item to queue workflow for.
            role: The role of the item (indicator, factor, dimension, analysis).
        """
        task = None

        attributes = item.attributes()

        if role == "indicator" and attributes.get("analysis_mode", "") == "Do Not Use":
            attributes["factor_weighting"] = 0.0
            attributes["result"] = "Excluded from analysis"
            attributes["result_file"] = ""
            log_message(
                f"Skipping {item.attribute('id')} because it is set to 'Do Not Use'.",
                tag="GeoE3",
                level=Qgis.Info,
            )
            return

        # Validate road network layer if needed (skip for Regional scale - uses simple buffer)
        analysis_mode = attributes.get("analysis_mode", "")
        analysis_scale = self.model.get_analysis_item().attributes().get("analysis_scale", "national")
        needs_road_network = analysis_mode in ["use_multi_buffer_point"] and analysis_scale != "regional"
        road_network_path = self.road_network_layer_path()
        if needs_road_network:
            # Get expected CRS from study area
            study_area_gpkg = os.path.join(self.working_directory, "study_area", "study_area.gpkg")
            study_area_layer = QgsVectorLayer(f"{study_area_gpkg}|layername=study_area_polygons", "study_area", "ogr")
            expected_crs = study_area_layer.crs() if study_area_layer.isValid() else None

            if expected_crs:
                is_valid, error_msg = validate_network_layer(road_network_path, expected_crs)
                if not is_valid:
                    self.show_validation_error("Road Network Issue", error_msg)
                    return
        attributes["road_network_layer_path"] = road_network_path

        # Include the GHSL layer in the attributes by default
        attributes["ghsl_layer_path"] = self.ghsl_layer_path()

        if attributes.get("result_file", None) and self.run_only_incomplete:
            return
        if role == item.role and role == "factor":
            attributes["analysis_mode"] = "factor_aggregation"
        if role == item.role and role == "dimension":
            attributes["analysis_mode"] = "dimension_aggregation"
        if role == item.role and role == "analysis":
            attributes["analysis_mode"] = "analysis_aggregation"
        task = self.queue_manager.add_workflow(item, self.cell_size_m(), self.analysis_scale())
        if task is None:
            # The workflow declined the job (data source missing or broken).
            # The queue manager has already marked the item (failed icon and
            # error tooltip); repaint so that is visible, tell the user in
            # plain language, and let the rest of the run continue.
            reason = item.attribute("error", "") or tr("configure its data source and run it again.")
            self.treeView.viewport().update()
            try:
                iface.messageBar().pushMessage(
                    tr("GeoE3"),
                    tr("'{name}' was skipped — {reason}").format(name=item.attribute("id", item.guid), reason=reason),
                    level=Qgis.Warning,
                    duration=10,
                )
            except Exception:  # nosec B110 — headless/test environments have no iface
                pass
            return

        self.hide_validation_warning()

        # Connect workflow signals to TreePanel slots
        task.job_queued.connect(partial(self.on_workflow_created, item))
        task.job_started.connect(partial(self.on_workflow_started, item))
        task.job_canceled.connect(partial(self.on_workflow_completed, item, False))
        task.job_finished.connect(lambda success: self.on_workflow_completed(item, success))
        # Hook up the QTask feedback signal to the progress bar
        task.progressChanged.connect(self.task_progress_updated)
        # Hook up the status message signal to the status label
        task.status_message.connect(self.task_status_updated)

    def run_item(self, item, shift_pressed):
        """Run the item and the ones below it.

        If the user holds shift whilst running the item, it will force the
        recalculation of all workflows under the item, regardless of their status.

        Args:
            item (TreeItem): The item to run.
            shift_pressed (bool): Whether the shift key is pressed.

        """
        self.items_to_run = 0
        self.workflow_scope_item = item
        self._open_report_when_done = False
        if shift_pressed:
            self.run_only_incomplete = False
        else:
            self.run_only_incomplete = True

        workflow_queue = []
        if item.role == "indicator":
            workflow_queue = ["indicators"]
        elif item.role == "factor":
            workflow_queue = ["indicators", "factors"]
        elif item.role == "dimension":
            workflow_queue = ["indicators", "factors", "dimensions"]
        elif item.role == "analysis":
            workflow_queue = ["indicators", "factors", "dimensions", "analysis"]
        self.overall_progress_bar.setVisible(True)
        self.workflow_progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.status_label.setText("Starting...")
        self.prepare_analysis_button.setVisible(False)
        self.help_button.setVisible(False)
        self.project_button.setVisible(False)
        self.overall_progress_bar.setValue(0)
        self.overall_progress_bar.setMaximum(self.items_to_run)
        self.workflow_progress_bar.setValue(0)

        items_to_run = 0
        if "indicators" in workflow_queue:
            items_to_run += len(
                item.getDescendantIndicators(include_completed=not self.run_only_incomplete, include_disabled=False)
            )
        if "factors" in workflow_queue:
            items_to_run += len(
                item.getDescendantFactors(include_completed=not self.run_only_incomplete, include_disabled=False)
            )
        if "dimensions" in workflow_queue:
            items_to_run += len(item.getDescendantDimensions(include_completed=not self.run_only_incomplete))
        if "analysis" in workflow_queue:
            items_to_run += len(item.getDescendantAnalyses(include_completed=not self.run_only_incomplete))
        self.items_to_run = items_to_run
        log_message(f"Total workflows to run: {self.items_to_run}")
        self.overall_progress_bar.setMaximum(self.items_to_run)

        self.workflow_queue = workflow_queue
        self.run_next_workflow_queue()

    @pyqtSlot()
    def on_workflow_created(self, item):
        """
        Slot for handling when a workflow is created.
        Does nothing right now...

        Args:
            item: The workflow item that was created.
        """
        pass

    @pyqtSlot()
    def on_workflow_started(self, item):
        """
        Slot for handling when a workflow starts.
        Update the tree item to indicate that the workflow is running.

        Args:
            item: The workflow item that was started.
        """
        # Get the node index for the item
        node_index = self.model.itemIndex(item)
        if not node_index.isValid():
            log_message(
                f"Failed to find index for item {item} - animation not started",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            return

        # Ensure we work with QModelIndex instead of QPersistentModelIndex
        child_index = QModelIndex(node_index)

        # Get row height and prepare movies
        row_height = self.treeView.rowHeight(child_index)
        self.child_movie = QMovie(resources_path("resources", "throbber.gif"))
        self.parent_movie = QMovie(resources_path("resources", "throbber.gif"))

        # If this is an indicator, caclulate height for parent in case the indicator is hidden
        if item.role == "indicator":
            parent_item = item.parent()
            parent_index = self.model.itemIndex(parent_item)
            row_height = self.treeView.rowHeight(parent_index)

        # Scale movies
        self.child_movie.setScaledSize(
            self.child_movie.currentPixmap().size().scaled(row_height, row_height, Qt.AspectRatioMode.KeepAspectRatio)
        )
        self.parent_movie.setScaledSize(
            self.parent_movie.currentPixmap().size().scaled(row_height, row_height, Qt.AspectRatioMode.KeepAspectRatio)
        )

        # Set animated icon for the child
        child_label = QLabel()
        child_label.setMovie(self.child_movie)
        self.child_movie.start()

        # Place child animation
        second_column_index = self.model.index(child_index.row(), 1, child_index.parent())
        self.treeView.setIndexWidget(second_column_index, child_label)

        # Always show parent animation if this is an indicator
        if item.role == "indicator":
            parent_item = item.parent()
            if parent_item:
                parent_index = self.model.itemIndex(parent_item)
                if parent_index.isValid():
                    # Create parent animation
                    parent_label = QLabel()
                    parent_label.setMovie(self.parent_movie)
                    self.parent_movie.start()

                    # Get parent's second column index
                    parent_second_column_index = self.model.index(parent_index.row(), 1, parent_index.parent())

                    # Set parent animation and ensure it's visible
                    self.treeView.setIndexWidget(parent_second_column_index, parent_label)
                    parent_label.show()

                    # Force immediate update
                    self.treeView.viewport().update()

    def task_progress_updated(self, progress):
        """Slot to be called when the task progress is updated.

        Args:
            progress: Progress value (0-100).
        """
        log_message(f"Task progress: {progress}")
        self.workflow_progress_bar.setValue(int(progress))

    def task_status_updated(self, status: str):
        """Slot to be called when the task status message is updated.

        Args:
            status: A short description of the current operation.
        """
        # Truncate long status messages to fit the label
        max_len = 35
        if len(status) > max_len:
            status = status[: max_len - 3] + "..."
        self.status_label.setText(status)
        self.status_label.setToolTip(status)  # Show full text on hover

    def set_message_bar(self, message_bar: "QgsMessageBar") -> None:
        """Set the dock-level message bar used for error notifications.

        Args:
            message_bar: The QgsMessageBar embedded in the plugin dock widget.
        """
        self._message_bar = message_bar

    def on_processing_error(self, error_message: str):
        """Slot called when a workflow job reports an error.

        Updates the status label and pushes a visible error notification
        to the plugin's own message bar (top of the dock panel).

        Args:
            error_message: The error message from the failed workflow job.
        """
        log_message(f"Processing error: {error_message}", level=Qgis.Critical)
        # Update the status label (truncated, full text on hover)
        max_len = 35
        short = error_message if len(error_message) <= max_len else error_message[: max_len - 3] + "..."
        self.status_label.setText(short)
        self.status_label.setToolTip(error_message)
        # Push to the plugin-level message bar (top of dock), falling back to
        # the QGIS main window bar if set_message_bar() was never called.
        bar = getattr(self, "_message_bar", None) or iface.messageBar()
        bar.pushMessage(
            "GeoE3 Processing Error",
            error_message,
            level=Qgis.Critical,
            duration=0,  # stays until dismissed
        )

    @pyqtSlot(bool)
    def on_workflow_completed(self, item, success):
        """
        Slot for handling when a workflow is completed.
        Update the tree item to indicate success or failure.

        Args:
            item: The workflow item that was completed.
            success: Whether the workflow completed successfully.
        """
        queue_length = self.queue_manager.workflow_queue.active_queue_size()
        log_message(f"Queued {queue_length} workflows for processing.")
        self.overall_progress_bar.setValue(self.overall_progress_bar.value() + 1)
        self.overall_progress_bar.setMaximum(self.items_to_run - 1)
        self.workflow_progress_bar.setValue(0)
        self.save_json_to_working_directory()

        # For the analysis item run the post-processing insights first, so
        # masked products exist before we decide which layer to add to the map.
        if item.role == "analysis" and success:
            self.calculate_analysis_insights(item)

        # Add layer to map after workflow completes using auto-determined strategy
        use_masked = False
        analysis_raster_key = "result_file"
        if item.role == "analysis":
            use_masked, analysis_raster_key = self._analysis_display(item)
        if item.role == "dimension":
            column_name = f"dim_{item.attribute('id').lower().replace(' ', '_').replace('-', '_')}"
        elif item.role == "factor":
            column_name = f"fac_{item.attribute('id').lower().replace(' ', '_').replace('-', '_')}"
        elif item.role == "indicator":
            column_name = item.attribute("id").lower().replace(" ", "_").replace("-", "_")
        elif item.role == "analysis":
            column_name = "geoe3_masked" if use_masked else "geoe3"  # Analysis aggregation uses geoe3 column
        else:
            column_name = None

        if item.role == "analysis" and use_masked and self._get_render_strategy() == "raster":
            add_to_map(
                item,
                key=analysis_raster_key,
                layer_name="GeoE3 Score",
                group="GeoE3",
            )
        elif column_name is None or self._get_render_strategy() == "raster":
            add_to_map(item)
        else:
            add_grid_layer_to_map(item, column_name, self.working_directory)

        self._stop_item_spinner(item)

    def _stop_item_spinner(self, item) -> None:
        """Stop and clear the animated throbber on_workflow_started() placed on item's row.

        Shared by on_workflow_completed() and download_all_resources() - any
        caller that started the spinner via on_workflow_started() must pair
        it with this to clear it, including the parent row's spinner for an
        indicator.
        """
        node_index = self.model.itemIndex(item)

        if not node_index.isValid():
            log_message(
                f"Failed to find index for item {item} - animation not started",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            return

        parent_second_column_index = None
        if item.role == "indicator":
            # Stop the animation on its parent too
            parent_index = node_index.parent()
            parent_second_column_index = self.model.index(parent_index.row(), 1, parent_index.parent())

        if hasattr(self, "child_movie") and self.child_movie is not None:
            self.child_movie.stop()
        if hasattr(self, "parent_movie") and self.parent_movie is not None:
            self.parent_movie.stop()

        second_column_index = self.model.index(node_index.row(), 1, node_index.parent())
        self.treeView.setIndexWidget(second_column_index, None)
        if parent_second_column_index:
            self.treeView.setIndexWidget(parent_second_column_index, None)

        # Emit dataChanged to refresh the decoration
        self.model.dataChanged.emit(second_column_index, second_column_index)

    def download_all_resources(self):
        """Walk every indicator, download missing resources, and wire up cached ones.

        Covers nighttime lights, environmental hazard rasters, and
        OSM-matched buffer-point indicators today - see
        geest.core.download_all_resources' module docstring for what's not
        covered yet and why. An indicator whose resource is already cached
        on disk but not yet set as its source (e.g. a duplicated
        indicator, or a resource a sibling indicator already downloaded)
        is configured immediately, with no download needed; only a
        genuinely missing resource is actually downloaded. The tree view
        is refreshed afterward so newly-configured indicators show their
        updated status immediately.
        """
        bar = getattr(self, "_message_bar", None) or iface.messageBar()

        if not self.working_directory:
            bar.pushMessage("Download All Resources", "No working directory set.", level=Qgis.Warning, duration=5)
            return

        from geest.core.download_all_resources import (
            DownloadAllResourcesController,
            collect_missing_resources,
            sync_cached_resource_attributes,
        )

        configured = sync_cached_resource_attributes(self.model.rootItem, self.working_directory)
        if configured:
            self.save_json_to_working_directory()
            self._refresh_tree_view()

        missing = collect_missing_resources(self.model.rootItem, self.working_directory)
        if not missing:
            message = (
                f"Configured {len(configured)} indicator(s) from already-cached files. " if configured else ""
            ) + "All downloadable resources are already cached."
            bar.pushMessage("Download All Resources", message, level=Qgis.Info, duration=5)
            return

        gpkg_path = os.path.join(self.working_directory, "study_area", "study_area.gpkg")
        bbox_layer = QgsVectorLayer(f"{gpkg_path}|layername=study_area_bboxes", "study_area_bboxes", "ogr")
        if not bbox_layer.isValid() or bbox_layer.featureCount() == 0:
            bar.pushMessage(
                "Download All Resources",
                "Could not load study_area_bboxes from study_area.gpkg.",
                level=Qgis.Warning,
                duration=5,
            )
            return
        extent = bbox_layer.extent()
        extent_crs_authid = bbox_layer.crs().authid()

        self.overall_progress_bar.setVisible(True)
        self.workflow_progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.status_label.setText("Starting downloads...")
        self.prepare_analysis_button.setVisible(False)
        self.help_button.setVisible(False)
        self.project_button.setVisible(False)
        self.overall_progress_bar.setValue(0)
        self.overall_progress_bar.setMaximum(len(missing))
        self.workflow_progress_bar.setValue(0)

        def _on_item_started(item, spec):
            self.status_label.setText(f"Downloading {spec.label}...")
            self.status_label.setToolTip(spec.label)
            self.workflow_progress_bar.setValue(0)
            # Same animated throbber a normal single-indicator run shows on
            # its tree row - highlights which item is downloading without
            # touching the tree's structure/expand state.
            self.on_workflow_started(item)

        def _on_item_progress(item, spec, message):
            self.status_label.setText(message[:60])
            self.status_label.setToolTip(message)

        def _on_item_finished(item, spec, success, message):
            self._stop_item_spinner(item)
            self.overall_progress_bar.setValue(self.overall_progress_bar.value() + 1)
            self.workflow_progress_bar.setValue(100)
            if not success:
                log_message(f"Download failed for {spec.label}: {message}", tag="GeoE3", level=Qgis.Warning)

        def _on_all_finished(succeeded, failed):
            self.overall_progress_bar.setVisible(False)
            self.workflow_progress_bar.setVisible(False)
            self.status_label.setVisible(False)
            self.status_label.setText("")
            self.prepare_analysis_button.setVisible(True)
            self.help_button.setVisible(True)
            self.project_button.setVisible(True)
            self.save_json_to_working_directory()
            self._refresh_tree_view()
            summary = f"Downloaded {len(succeeded)} resource(s)."
            if configured:
                summary += f" Configured {len(configured)} from already-cached files."
            if failed:
                failed_labels = ", ".join(spec.label for _item, spec in failed)
                summary += f" {len(failed)} failed: {failed_labels}"
                bar.pushMessage("Download All Resources", summary, level=Qgis.Warning, duration=10)
            else:
                bar.pushMessage("Download All Resources", summary, level=Qgis.Info, duration=5)

        self._download_all_resources_controller = DownloadAllResourcesController(
            items_and_specs=missing,
            working_directory=self.working_directory,
            extent=extent,
            extent_crs_authid=extent_crs_authid,
            on_item_started=_on_item_started,
            on_item_progress=_on_item_progress,
            on_item_finished=_on_item_finished,
            on_all_finished=_on_all_finished,
        )
        self._download_all_resources_controller.start()

    def _refresh_tree_view(self) -> None:
        """Repaint every item's status (e.g. "ready to run") without collapsing the tree.

        Attribute changes made directly on JsonTreeItem (not through the
        view's own edit flow) don't trigger a repaint on their own - the
        status column is computed live from attributes each time the view
        paints, but nothing tells it to paint again. Deliberately
        layoutChanged, not beginResetModel()/endResetModel(): a full model
        reset invalidates persistent indexes, which collapses every
        expanded node and clears the current selection/scroll position -
        needlessly disruptive here, since only item data changed, not the
        tree's structure. layoutChanged tells the view to re-read and
        repaint without touching expand state.
        """
        self.model.layoutChanged.emit()
        self.treeView.viewport().update()

    def calculate_analysis_insights(self, item: JsonTreeItem):
        """Calculate insights for the analysis.

        Post process the analysis aggregation and store the output in the item.

        Here we compute various other insights from the aggregated data:

        - GeoE3 x Population Score
        - Opportunities Mask
        - Subnational Aggregation

        Args:
            item: The analysis item to calculate insights for.
        """
        log_message("############################################")
        log_message("Calculating analysis insights")
        log_message("############################################")
        log_message(item.attributesAsMarkdown())
        gpkg_path = os.path.join(self.working_directory, "study_area", "study_area.gpkg")
        feedback = QgsFeedback()
        context = QgsProcessingContext()

        analysis_scale = item.attribute("analysis_scale", "national")
        s2s_pop_path = item.attribute("population_s2s_output_path", None)
        population_source = item.attribute("population_source", "raster")

        use_s2s = (
            analysis_scale == "regional"
            and population_source == "s2s"
            and s2s_pop_path
            and os.path.exists(s2s_pop_path)
        )

        if use_s2s:
            s2s_field = item.attribute("population_s2s_field", "") or DEFAULT_S2S_POPULATION_FIELD
            log_message(
                f"Using S2S demographics for population processing: {s2s_field}",
                tag="GeoE3",
                level=Qgis.Info,
            )
            population_processor = PopulationVectorProcessingTask(
                s2s_output_path=s2s_pop_path,
                s2s_field=s2s_field,
                study_area_gpkg_path=gpkg_path,
                working_directory=self.working_directory,
                cell_size_m=self.cell_size_m(),
            )
            population_processor.run()
        else:
            population_data = item.attribute("population_layer_source", None)
            population_path = str(population_data or "").split("|")[0]
            if not population_path or not os.path.exists(population_path):
                self.on_processing_error("Select a valid population raster before running the analysis.")
                return False
            population_processor = PopulationRasterProcessingTask(
                population_raster_path=population_path,
                working_directory=self.working_directory,
                study_area_gpkg_path=gpkg_path,
                cell_size_m=self.cell_size_m(),
                feedback=feedback,
                force_clear=True,
            )
            if not population_processor.run():
                self.on_processing_error("Population raster processing failed. Check the QGIS log for details.")
                return False
        geoe3_processor = WEEByPopulationScoreProcessingTask(
            study_area_gpkg_path=gpkg_path,
            working_directory=self.working_directory,
            force_clear=True,
        )
        if not geoe3_processor.run():
            self.on_processing_error("GeoE3 by population processing failed. Check the QGIS log for details.")
            return False
        # Shamelessly hard coded for now, needs to move to the geoe3 processor class
        output = os.path.join(
            self.working_directory,
            "geoe3_by_population_score",
            "geoe3_by_population_score.vrt",
        )
        if not os.path.exists(output):
            self.on_processing_error("GeoE3 by population processing did not create an output raster.")
            return False
        item.setAttribute("geoe3_by_population", output)

        # Prepare the polygon mask data if provided
        # The mask (job opportunities / GHSL) is optional - only run the
        # mask pipeline when the user has selected a mask source in the
        # analysis weightings dialog.
        mask_mode = item.attribute("mask_mode", "None")
        if mask_mode not in ("", "None", "none"):
            try:
                opportunities_mask_workflow = OpportunitiesMaskProcessor(
                    item=item,
                    study_area_gpkg_path=gpkg_path,
                    cell_size_m=self.cell_size_m(),
                    feedback=feedback,
                    context=context,
                    working_directory=self.working_directory,
                )
                opportunities_mask_workflow.run()

                # Now apply the opportunities mask to the GeoE3 Score and GeoE3 Score x Population
                # leaving us with 4 potential products:
                # GeoE3 Score Unmasked (already created above)
                # GeoE3 Score x Population Unmasked (already created above)
                # GeoE3 Score Masked by Job Opportunities
                # GeoE3 Score x Population masked by Job Opportunities
                mask_processor = OpportunitiesByWeeScoreProcessingTask(
                    item=item,
                    study_area_gpkg_path=gpkg_path,
                    working_directory=self.working_directory,
                    force_clear=False,
                )
                mask_processor.run()

                mask_processor = OpportunitiesByWeeScorePopulationProcessingTask(
                    item=item,
                    study_area_gpkg_path=gpkg_path,
                    working_directory=self.working_directory,
                    force_clear=False,
                )
                mask_processor.run()
            except Exception as e:
                log_message(
                    f"Failed to run opportunities mask pipeline: {e}",
                    tag="GeoE3",
                    level=Qgis.Critical,
                )
                log_message(traceback.format_exc(), level=Qgis.Critical)
        else:
            log_message(
                f"No mask source selected (mask_mode={mask_mode!r}), skipping opportunities mask.",
                tag="GeoE3",
                level=Qgis.Info,
            )
        # Now prepare the aggregation layers if an aggregation polygon layer is provided
        # leaving us with 2 potential products:
        # Subnational Aggregation fpr GeoE3 Score x Population Unmasked
        # Subnational Aggregation for GeoE3 Score x Population masked by Job Opportunities
        try:
            subnational_processor = SubnationalAggregationProcessingTask(
                item,
                study_area_gpkg_path=gpkg_path,
                working_directory=self.working_directory,
                force_clear=False,
            )
            subnational_processor.run()
        except Exception as e:
            log_message(f"Failed to run subnational aggregation: {e}")
            log_message(traceback.format_exc())
        self.save_json_to_working_directory()
        log_message("############################################")
        log_message("END")
        log_message("############################################")

    def update_tree_item_status(self, item, status):
        """
        Update the tree item to show the workflow status.

        Args:
            item: The tree item representing the workflow.
            status: The status message or icon to display.
        """
        # Assuming column 1 is where status updates are shown
        item.setData(1, status)

    def run_all(self):
        """Run all workflows in the tree, regardless of their status."""
        self.run_only_incomplete = False
        self.workflow_scope_item = None
        self._open_report_when_done = True
        self.clear_workflows()
        self._count_workflows_to_run()
        log_message(f"Total items to process: {self.items_to_run}")
        self._queue_workflows()

    def run_incomplete(self):
        """
        This function processes all nodes in the QTreeView that have the 'indicator' role.
        It iterates over the entire tree, collecting nodes with the 'indicator' role, and
        processes each one whilst showing an animated icon.
        """
        self.run_only_incomplete = True
        self.workflow_scope_item = None
        self._open_report_when_done = False
        self._count_workflows_to_run()
        self._queue_workflows()

    def _queue_workflows(self):
        """
        This function processes all nodes in the QTreeView working through them in
        logical order of indicators then factors then dimensions, then the whole analysis.
        """
        self.workflow_queue = ["indicators", "factors", "dimensions", "analysis"]
        self.overall_progress_bar.setVisible(True)
        self.workflow_progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.status_label.setText("Starting...")
        self.prepare_analysis_button.setVisible(False)
        self.help_button.setVisible(False)
        self.project_button.setVisible(False)
        self.overall_progress_bar.setValue(0)
        self.overall_progress_bar.setMaximum(self.items_to_run)
        self.workflow_progress_bar.setValue(0)
        self.run_next_workflow_queue()

    def run_next_workflow_queue(self):
        """
        Run the next group of workflows in the queue.
        If self.workflow_queue is empty, the function will return.
        """
        if len(self.workflow_queue) == 0:
            self.overall_progress_bar.setVisible(False)
            self.workflow_progress_bar.setVisible(False)
            self.status_label.setVisible(False)
            self.status_label.setText("")
            self.prepare_analysis_button.setVisible(True)
            self.help_button.setVisible(True)
            self.project_button.setVisible(True)
            self.workflow_scope_item = None
            # All workflows have finished writing — verify the study area
            # GeoPackage is still sound and self-heal it if not.
            self.check_study_area_gpkg_health(reason="after workflows")
            open_report = self._open_report_when_done
            self._open_report_when_done = False
            if open_report:
                analysis_item = self.model.get_analysis_item()
                status = analysis_item.getStatus() if analysis_item else ""
                if status == "Completed successfully":
                    log_message("Complete analysis run succeeded — generating the analysis report")
                    self.generate_analysis_report()
                else:
                    log_message(
                        f"Analysis run finished with status '{status}' — skipping the automatic report",
                        tag="GeoE3",
                        level=Qgis.Warning,
                    )
            return
        # pop the first item from the queue
        next_workflow = self.workflow_queue.pop(0)
        self.start_workflows(workflow_type=next_workflow)

        debug_env = int(os.getenv("GEOE3_DEBUG") or os.getenv("GEEST_DEBUG", 0))
        if debug_env:
            self.queue_manager.start_processing_in_foreground()
        else:
            self.queue_manager.start_processing()

    def expand_all_nodes(self, index=None):
        """
        Recursively expand all nodes in the tree view starting from the root.

        Args:
            index: QModelIndex - if None the root index is used.
        """
        if self.treeView.model() is None:
            return
        else:
            model = self.treeView.model()
        if index is None:
            index = model.index(0, 0, QModelIndex())

        if not index.isValid():
            return

        self.treeView.expand(index)

        # Loop through all children and expand them as well
        row_count = self.treeView.model().rowCount(index)
        for row in range(row_count):
            child_index = self.treeView.model().index(row, 0, index)
            self.expand_all_nodes(child_index)

    def disable_widgets(self):
        """Disable all widgets in the panel."""
        for widget in self.findChildren(QWidget):
            widget.setEnabled(False)

    def enable_widgets(self):
        """Enable all widgets in the panel."""
        for widget in self.findChildren(QWidget):
            widget.setEnabled(True)

    def animate_results(self):
        """
        Animate the selection of tree items sequentially with a 2s pause on each.
        """
        from qgis.PyQt.QtCore import QTimer

        # If already animating, do nothing
        if getattr(self, "_is_animating", False):
            return
        self._is_animating = True

        # Get all items in the tree in a flat list (preorder traversal)
        def collect_items(item, items):
            """🔄 Collect items.

            Args:
                item: Item.
                items: Items.
            """
            items.append(item)
            for i in range(item.childCount()):
                collect_items(item.child(i), items)

        items = []
        collect_items(self.model.rootItem, items)
        # Remove the root item if you don't want to animate it
        if len(items) > 1:
            items = items[1:]

        self._animate_items = items
        self._animate_index = 0

        if hasattr(self, "_animate_timer") and self._animate_timer is not None:
            self._animate_timer.stop()

        self._animate_timer = QTimer(self)
        self._animate_timer.setInterval(1000)  # 1s
        self._animate_timer.timeout.connect(self._animate_next_item)
        self._animate_next_item()  # Start immediately
        self._animate_timer.start()

    def stop_animation(self):
        """Stop the animation if running."""
        if hasattr(self, "_animate_timer") and self._animate_timer is not None:
            self._animate_timer.stop()
        self._is_animating = False
        self._animate_items = []
        self._animate_index = 0

    def _animate_next_item(self):
        if not hasattr(self, "_animate_items") or self._animate_index >= len(self._animate_items):
            if hasattr(self, "_animate_timer"):
                self._animate_timer.stop()
            self._is_animating = False
            return
        item = self._animate_items[self._animate_index]
        index = self.model.itemIndex(item)
        if index.isValid():
            self.treeView.setCurrentIndex(index)
            self.treeView.scrollTo(index)
            # Call the item clicked logic for each item as it is selected
            self.on_item_clicked(index)
        self._animate_index += 1
