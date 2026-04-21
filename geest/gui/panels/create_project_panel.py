# -*- coding: utf-8 -*-
"""📦 Create Project Panel module.

This module contains functionality for create project panel.
"""

import json
import os
import shutil
import traceback
from typing import Dict, List

from qgis.core import (
    QgsApplication,
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeedback,
    QgsFieldProxyModel,
    QgsGeometry,
    QgsLayerTreeGroup,
    QgsMapLayerProxyModel,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QSettings, pyqtSignal
from qgis.PyQt.QtGui import QFont, QPixmap
from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox, QWidget

from geest.core.constants import DEFAULT_S2S_ENV_HAZARD_FIELDS, DEFAULT_S2S_NTL_FIELD
from geest.core import WorkflowQueueManager
from geest.core.tasks import S2SDownloaderTask, StudyAreaProcessingTask, StudyAreaReportTask
from geest.gui.widgets import CustomBannerLabel
from geest.utilities import (
    calculate_utm_zone_from_layer,
    get_ui_class,
    linear_interpolation,
    log_message,
    resources_path,
)

FORM_CLASS = get_ui_class("create_project_panel_base.ui")


class CreateProjectPanel(FORM_CLASS, QWidget):
    """🎯 Create Project Panel.

    Attributes:
        queue_manager: Queue manager.
        settings: Settings.
        working_dir: Working dir.
    """

    switch_to_next_tab = pyqtSignal()  # Signal to notify the parent to switch tabs
    # Signal to notify the parent to switch tabs
    switch_to_previous_tab = pyqtSignal()
    # Signal to set the working directory
    working_directory_changed = pyqtSignal(str)

    def __init__(self):
        """🏗️ Initialize the instance."""
        super().__init__()
        self.setWindowTitle("GeoE3")
        # For running study area processing in a separate thread
        self.queue_manager = WorkflowQueueManager(pool_size=1)

        self.working_dir = ""
        self.settings = QSettings()  # Initialize QSettings to store and retrieve settings
        self._s2s_prefetch_jobs: List[Dict] = []
        self._s2s_prefetch_index = 0
        self._s2s_prefetch_warnings: List[str] = []
        self._s2s_prefetch_updates: List[Dict] = []
        self._s2s_prefetch_task = None
        self._s2s_prefetch_error_for_current_task = False
        # Dynamically load the .ui file
        self.setupUi(self)
        log_message("Loading setup panel")
        self.initUI()

    def initUI(self):
        """⚙️ Initui."""
        self.enable_widgets()  # Re-enable widgets in case they were disabled
        self.custom_label = CustomBannerLabel(
            "The Geospatial Enabling Environments for Employment Spatial Tool",
            resources_path("resources", "geoe3-banner.png"),
        )
        parent_layout = self.banner_label.parent().layout()
        parent_layout.replaceWidget(self.banner_label, self.custom_label)
        self.banner_label.deleteLater()
        parent_layout.update()

        self.folder_status_label.setPixmap(QPixmap(resources_path("resources", "icons", "failed.svg")))
        self.regional_scale.clicked.connect(lambda: self.spatial_scale_changed("regional"))
        self.national_scale.clicked.connect(lambda: self.spatial_scale_changed("national"))
        self.local_scale.clicked.connect(lambda: self.spatial_scale_changed("local"))
        if self.regional_scale.isChecked():
            self.spatial_scale_changed("regional")
        elif self.local_scale.isChecked():
            self.spatial_scale_changed("local")
        else:
            self.spatial_scale_changed("national")
        self.layer_combo.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        # Regional scale uses H3 hexagonal grids (L6 resolution)
        # National and Local scales use square grids
        # Local mode enabled for National vs Local analysis implementation
        # self.local_scale.setEnabled(False)
        # self.regional_scale.setEnabled(False)
        self.regional_scale.setStyleSheet("QRadioButton:disabled { color: grey; }")

        # Women Considerations toggle
        self.women_considerations_checkbox.stateChanged.connect(self.women_considerations_changed)
        # Initialize EPLEX widgets visibility based on checkbox state
        self.women_considerations_changed()

        # self.field_combo = QgsFieldComboBox()  # QgsFieldComboBox for selecting fields
        self.field_combo.setFilters(QgsFieldProxyModel.String)

        # Link the map layer combo box with the field combo box
        self.layer_combo.layerChanged.connect(self.layer_changed)
        self.field_combo.setLayer(self.layer_combo.currentLayer())

        self.create_project_directory_button.clicked.connect(self.create_new_project_folder)
        # We only allow the user to select a CRS based on the admin layer
        # if the admin CRS is not WGS84
        self.use_boundary_crs.setChecked(False)
        self.use_boundary_crs.setEnabled(False)
        self.use_boundary_crs.toggled.connect(self.update_crs)  # Update the CRS label when the checkbox is toggled

        self.next_button.clicked.connect(self.create_project)
        self.previous_button.clicked.connect(self.on_previous_button_clicked)

        self.load_boundary_button.clicked.connect(self.load_boundary)

        self.progress_bar.setVisible(False)
        self.child_progress_bar.setVisible(False)
        self.processing_info_label.setVisible(False)
        self.processing_info_label.setText("")
        # Ensure crs is set on first load
        self.layer_changed(self.layer_combo.currentLayer())

    def layer_changed(self, layer):
        """Slot to be called when the layer in the combo box changes.

        Args:
            layer: The new layer selected in the combo box.
        """
        log_message(f"Layer changed: {layer.name() if layer else 'None'}")
        if self.crs() is None:
            log_message(
                "CRS is None, cannot set layer or field combo box.",
                tag="GeoE3",
                level=Qgis.Critical,
            )
            self.crs_label.setText("Invalid CRS")
            return
        log_message(f"Layer crs: {layer.crs().authid() if layer else 'None'}")
        if layer:
            self.field_combo.setLayer(layer)
            # Check if the layer has a valid CRS
            if layer.crs().authid() == "EPSG:4326":
                self.use_boundary_crs.setChecked(False)
                self.use_boundary_crs.setEnabled(False)
            else:
                self.use_boundary_crs.setEnabled(True)
        else:
            self.field_combo.clear()
            self.use_boundary_crs.setEnabled(False)
        self.crs_label.setText(self.crs().authid())

    def spatial_scale_changed(self, value: str):
        """Slot to be called when the spatial scale changes.

        Args:
            value (str): The new spatial scale value ("regional", "national", or "local").
        """
        log_message(f"Spatial scale changed: {value}")
        if value == "regional":
            # Regional scale uses H3 hexagonal grids (resolution L6) - fixed size
            self.cell_size_spinbox.hide()
            self.groupBox_4.show()
        elif value == "national":
            self.cell_size_spinbox.show()
            self.description2.show()
            self.cell_size_spinbox.setValue(1000)
            self.cell_size_spinbox.setSingleStep(100)
            self.cell_size_spinbox.setSuffix(" m")
            self.groupBox_4.hide()
        elif value == "local":
            self.cell_size_spinbox.show()
            self.description2.show()
            self.cell_size_spinbox.setValue(100)
            self.cell_size_spinbox.setSingleStep(10)
            self.cell_size_spinbox.setSuffix(" m")
            self.groupBox_4.hide()

    def women_considerations_changed(self):
        """Slot to be called when the women considerations checkbox changes."""
        is_checked = self.women_considerations_checkbox.isChecked()
        log_message(f"Women considerations changed: {is_checked}")

    def update_crs(self):
        """Update the CRS label based on the checkbox state."""
        if self.use_boundary_crs.isChecked():
            self.crs_label.setText(f"CRS: {self.layer_combo.currentLayer().crs().authid()}")
        else:
            epsg = calculate_utm_zone_from_layer(self.layer_combo.currentLayer())
            self.crs_label.setText(f"CRS: EPSG:{epsg}")  # noqa E231

    def on_previous_button_clicked(self):
        """⚙️ On previous button clicked."""
        self.switch_to_previous_tab.emit()

    def load_boundary(self):
        """Load a boundary layer from a file."""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Shapefile (*.shp);;GeoPackage (*.gpkg)")
        if file_dialog.exec_():
            file_path = file_dialog.selectedFiles()[0]
            layer = QgsVectorLayer(file_path, "Boundary", "ogr")
            if not layer.isValid():
                QMessageBox.critical(self, "Error", "Could not load the boundary layer.")
                return
            # Load the layer in QGIS
            QgsProject.instance().addMapLayer(layer)
            self.layer_combo.setLayer(layer)
            self.field_combo.setLayer(layer)

    def create_new_project_folder(self):
        """⚙️ Create new project folder."""
        directory = QFileDialog.getExistingDirectory(self, "Create New Project Folder", self.working_dir)
        if directory:
            self.working_dir = directory
            self.update_recent_projects(directory)  # Update recent projects
            self.settings.setValue("last_working_directory", directory)  # Update last used project
            self.project_path_label.setText(directory)
            self.create_project_directory_button.setText("📂 Change Project Folder")
            self.folder_status_label.setPixmap(QPixmap(resources_path("resources", "icons", "completed-success.svg")))

    def create_project(self):
        """Triggered when the Continue button is pressed."""
        self.disable_widgets()
        if self.use_boundary_crs.isChecked():
            crs = self.layer_combo.currentLayer().crs()
        else:
            crs = None  # will be calculated from UTM zone

        model_path = os.path.join(self.working_dir, "model.json")
        if os.path.exists(model_path):
            self.settings.setValue("last_working_directory", self.working_dir)  # Update last used project
            self.enable_widgets()
            # Switch to the next tab if an existing project is found
            self.switch_to_next_tab.emit()
        else:
            # Process the study area if no model.json exists
            layer = self.layer_combo.currentLayer()
            if not layer:
                QMessageBox.critical(self, "Error", "Please select a study area layer.")
                self.enable_widgets()
                return

            if not self.working_dir:
                QMessageBox.critical(self, "Error", "Please select a working directory.")
                self.enable_widgets()
                return

            field_name = self.field_combo.currentField()
            if not field_name or field_name not in layer.fields().names():
                QMessageBox.critical(self, "Error", f"Invalid area name field '{field_name}'.")
                self.enable_widgets()
                return

            # Copy default model.json if not present
            default_model_path = resources_path("resources", "model.json")
            try:
                shutil.copy(default_model_path, model_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to copy model.json: {e}")
                self.enable_widgets()
                return
            # open the model.json to set the analysis cell size and the network layer path, then close it again
            with open(model_path, "r") as f:
                model = json.load(f)
                model["analysis_cell_size_m"] = self.cell_size_spinbox.value()
                if self.regional_scale.isChecked():
                    model["analysis_scale"] = "regional"
                elif self.local_scale.isChecked():
                    model["analysis_scale"] = "local"
                else:
                    model["analysis_scale"] = "national"
                # Save women considerations settings
                model["women_considerations_enabled"] = self.women_considerations_checkbox.isChecked()
                model["s2s_prefetch_enabled"] = self.prefetch_s2s_checkbox.isChecked()
                # Save reference layer source path
                ref_layer = self.reference_layer()
                if ref_layer and ref_layer.source():
                    model["admin_boundary_layer_source"] = ref_layer.source()
            with open(model_path, "w") as f:
                json.dump(model, f, indent=2)

            # Create the processor instance and process the features
            debug_env = int(os.getenv("GEOE3_DEBUG") or os.getenv("GEEST_DEBUG", 0))
            feedback = QgsFeedback()  # Used to cancel tasks and measure subtask progress
            try:

                # Determine analysis scale
                if self.regional_scale.isChecked():
                    analysis_scale = "regional"
                elif self.local_scale.isChecked():
                    analysis_scale = "local"
                else:
                    analysis_scale = "national"

                processor = StudyAreaProcessingTask(
                    layer=layer,
                    field_name=field_name,
                    cell_size_m=self.cell_size_spinbox.value(),
                    crs=crs,
                    working_dir=self.working_dir,
                    feedback=feedback,
                    analysis_scale=analysis_scale,
                )
                # Hook up the QTask feedback signal to the progress bar
                # Measure overall task progress from the task object itself
                processor.progressChanged.connect(self.progress_updated)
                processor.taskCompleted.connect(self.on_task_completed)
                processor.taskTerminated.connect(self.on_task_terminated)
                # Connect GHSL download failure signal to prompt user
                processor.ghsl_download_failed.connect(lambda msg, p=processor: self.on_ghsl_download_failed(msg, p))
                # Measure subtask progress from the feedback object
                feedback.progressChanged.connect(self.subtask_progress_updated)
                self.disable_widgets()
                if debug_env:
                    processor.run()
                else:
                    self.queue_manager.add_task(processor)
                    self.queue_manager.start_processing()
            except Exception as e:
                trace = traceback.format_exc()
                QMessageBox.critical(self, "Error", f"Error processing study area: {e}\n{trace}")
                self.enable_widgets()
                return
            self.settings.setValue("last_working_directory", self.working_dir)
            self.working_directory_changed.emit(self.working_dir)
            self.enable_widgets()

    def disable_widgets(self):
        """Disable all widgets in the panel."""
        for widget in self.findChildren(QWidget):
            widget.setEnabled(False)

    def enable_widgets(self):
        """Enable all widgets in the panel."""
        for widget in self.findChildren(QWidget):
            # Regional scale is now enabled with H3 hexagonal grids
            widget.setEnabled(True)
        self.processing_info_label.setVisible(False)
        self.processing_info_label.setText("")

    def reference_layer(self):
        """Get the admin boundary reference layer.

        Returns:
            QgsVectorLayer: The currently selected admin boundary layer.
        """
        return self.layer_combo.currentLayer()

    def crs(self, working_directory=None):
        """Get the CRS for the GEOE3 study area (NOT QGIS project CRS).

        If study area already exists, return its CRS from study_area.gpkg.
        Otherwise, calculate CRS from the boundary layer (UTM zone or boundary layer CRS).

        IMPORTANT: This returns the study area CRS, not QgsProject.instance().crs()

        Args:
            working_directory: Optional working directory path. If not provided, uses self.working_dir

        Returns:
            QgsCoordinateReferenceSystem: The study area CRS, or None if unavailable.
        """
        # Use provided working_directory, otherwise fall back to self.working_dir
        work_dir = working_directory or self.working_dir

        # First, try to get CRS from existing study area
        if work_dir and os.path.exists(work_dir):
            study_area_gpkg = os.path.join(work_dir, "study_area", "study_area.gpkg")
            if os.path.exists(study_area_gpkg):
                try:
                    study_area_layer = QgsVectorLayer(
                        f"{study_area_gpkg}|layername=study_area_polygons", "study_area", "ogr"
                    )
                    if study_area_layer.isValid():
                        crs = study_area_layer.crs()
                        self.crs_label.setText(f"CRS: {crs.authid()}")
                        return crs
                except Exception as e:
                    log_message(f"Could not load study area CRS: {e}", level=Qgis.Warning)

        # If no study area exists yet, calculate CRS from boundary layer
        crs = None
        if self.use_boundary_crs.isChecked():
            log_message("Using boundary CRS")
            crs = self.layer_combo.currentLayer().crs()
        else:
            log_message("Using UTM zone CRS")
            try:
                epsg = calculate_utm_zone_from_layer(self.layer_combo.currentLayer())
            except Exception as e:
                log_message(
                    f"Error calculating UTM zone from layer: {e}",
                    tag="GeoE3",
                    level=Qgis.Critical,
                )
                return None
            crs = QgsCoordinateReferenceSystem(f"EPSG:{epsg}")  # noqa E231
        self.crs_label.setText(f"CRS: {crs.authid()}" if crs else "CRS: Not set")
        return crs

    # Slot that listens for changes in the study_area task object which is used to measure overall task progress
    def progress_updated(self, progress: float):
        """Slot to be called when the task progress is updated.

        Args:
            progress: The current progress value (0-100).
        """
        log_message(f"\n\n\n\n\n\nProgress: {progress}\n\n\n\n\n\n\n\n")
        self.progress_bar.setVisible(True)
        self.progress_bar.setEnabled(True)
        self.progress_bar.setValue(int(progress))
        if progress == 0:
            self.progress_bar.setFormat("Downloading GHSL data and building analysis grid...")
            self.progress_bar.setMinimum(0)
            self.progress_bar.setMaximum(0)  # makes it bounce indefinitely
            self.processing_info_label.setText("Downloading GHSL data and building analysis grid. Do not close QGIS.")
            self.processing_info_label.setVisible(True)
            self.processing_info_label.setEnabled(True)
        else:
            # This is a sneaky hack to show the exact progress in the label
            # since QProgressBar only takes ints. See Qt docs for more info.
            # Use the 'setFormat' method to display the exact float:
            float_value_as_string = f"Processing study area — {progress}%"
            self.progress_bar.setFormat(float_value_as_string)
            self.progress_bar.setMinimum(0)
            self.progress_bar.setMaximum(100)
            self.processing_info_label.setText(
                "Processing study area. Bounding boxes will appear on the map as each area completes."
            )
            self.processing_info_label.setVisible(True)
            self.processing_info_label.setEnabled(True)
        self.add_bboxes_to_map()  # will just refresh them if already there

    # Slot that listens for changes in the progress object which is used to measure subtask progress
    def subtask_progress_updated(self, progress: float):
        """⚙️ Subtask progress updated.

        Args:
            progress: Progress.
        """
        self.child_progress_bar.setVisible(True)
        self.child_progress_bar.setEnabled(True)
        self.child_progress_bar.setValue(int(progress))
        # This is a sneaky hack to show the exact progress in the label
        # since QProgressBar only takes ints. See Qt docs for more info.
        # Use the 'setFormat' method to display the exact float:
        float_value_as_string = f"Current area: {progress}%"
        self.child_progress_bar.setFormat(float_value_as_string)

    def on_task_terminated(self):
        """Slot to be called when the study area processing task is terminated (aborted or failed)."""
        log_message(
            "Study area processing was terminated.",
            tag="GeoE3",
            level=Qgis.Warning,
        )
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Aborted — check settings and retry")
        self.child_progress_bar.setVisible(False)
        self.enable_widgets()

    def on_task_completed(self):
        """Slot to be called when the task completes successfully."""
        log_message(
            "*** Study area processing completed successfully. ***",
            tag="GeoE3",
            level=Qgis.Info,
        )

        # Use child progress bar for report generation (main bar stays at 100%)
        self.child_progress_bar.setMinimum(0)
        self.child_progress_bar.setMaximum(0)  # Indeterminate/bouncing
        self.child_progress_bar.setFormat("Generating study area report...")
        self.child_progress_bar.setVisible(True)

        self.processing_info_label.setText("Generating study area report — will open automatically when ready.")
        self.processing_info_label.setVisible(True)
        self.processing_info_label.setEnabled(True)

        # Start report generation in background
        gpkg_path = os.path.join(self.working_dir, "study_area", "study_area.gpkg")
        self.report_task = StudyAreaReportTask(self.working_dir, gpkg_path)
        self.report_task.taskCompleted.connect(self.on_report_completed)
        self.report_task.taskTerminated.connect(self.on_report_failed)

        from qgis.core import QgsApplication

        QgsApplication.taskManager().addTask(self.report_task)

    def on_report_completed(self):
        """Slot called when report generation completes successfully."""
        log_message("Study area report generated successfully.", tag="GeoE3", level=Qgis.Info)

        self.child_progress_bar.setMinimum(0)
        self.child_progress_bar.setMaximum(100)
        self.child_progress_bar.setValue(100)
        self.child_progress_bar.setFormat("Complete")

        if not self._start_s2s_prefetch_if_enabled():
            self.enable_widgets()
            self.switch_to_next_tab.emit()

    def on_report_failed(self):
        """Slot called when report generation fails."""
        error_msg = str(self.report_task.exception) if hasattr(self.report_task, "exception") else "Unknown error"

        log_message(f"Study area report generation failed: {error_msg}", tag="GeoE3", level=Qgis.Critical)

        self.child_progress_bar.setMinimum(0)
        self.child_progress_bar.setMaximum(100)
        self.child_progress_bar.setValue(0)
        self.child_progress_bar.setFormat("Report failed — continuing")

        if not self._start_s2s_prefetch_if_enabled():
            self.enable_widgets()
            self.switch_to_next_tab.emit()

    def _start_s2s_prefetch_if_enabled(self) -> bool:
        """Start S2S prefetch when configured for regional projects."""
        model_path = os.path.join(self.working_dir, "model.json")
        if not os.path.exists(model_path):
            return False

        try:
            with open(model_path, "r", encoding="utf-8") as model_file:
                model = json.load(model_file)
        except Exception as error:
            log_message(f"Failed to read model.json for S2S prefetch: {error}", tag="GeoE3", level=Qgis.Warning)
            return False

        if model.get("analysis_scale") != "regional":
            return False
        if not bool(model.get("s2s_prefetch_enabled", False)):
            return False

        study_area_gpkg = os.path.join(self.working_dir, "study_area", "study_area.gpkg")
        if not os.path.exists(study_area_gpkg):
            log_message("S2S prefetch skipped: study area geopackage missing.", tag="GeoE3", level=Qgis.Warning)
            return False

        aoi_layer = QgsVectorLayer(f"{study_area_gpkg}|layername=study_area_bboxes", "study_area_bboxes", "ogr")
        if not aoi_layer.isValid() or aoi_layer.featureCount() == 0:
            log_message("S2S prefetch skipped: study_area_bboxes unavailable.", tag="GeoE3", level=Qgis.Warning)
            return False

        aoi_feature = self._build_aoi_feature(aoi_layer)
        if not aoi_feature:
            log_message("S2S prefetch skipped: failed to build AOI feature.", tag="GeoE3", level=Qgis.Warning)
            return False

        jobs, warnings = self._prepare_s2s_prefetch_jobs(model)
        self._s2s_prefetch_warnings = warnings
        if not jobs:
            if warnings:
                QMessageBox.information(self, "S2S Fetch", "\n".join(warnings))
            return False

        self._s2s_prefetch_jobs = jobs
        self._s2s_prefetch_updates = []
        self._s2s_prefetch_index = 0
        self.processing_info_label.setText("Fetching S2S data for regional indicators...")
        self.processing_info_label.setVisible(True)
        self.child_progress_bar.setVisible(True)
        self.child_progress_bar.setMinimum(0)
        self.child_progress_bar.setMaximum(100)
        self.child_progress_bar.setValue(0)

        self._run_next_s2s_prefetch_job(aoi_feature)
        return True

    def _prepare_s2s_prefetch_jobs(self, model: dict) -> tuple[list, list]:
        """Build a list of S2S prefetch jobs and non-blocking warnings."""
        jobs: List[Dict] = []
        warnings: List[str] = []

        ntl_indicators: List[str] = []
        ntl_field = DEFAULT_S2S_NTL_FIELD

        for dimension in model.get("dimensions", []):
            for factor in dimension.get("factors", []):
                for indicator in factor.get("indicators", []):
                    indicator_id = str(indicator.get("id", "")).strip()
                    if not indicator_id:
                        continue

                    if int(indicator.get("use_nighttime_lights", 0)) == 1:
                        ntl_indicators.append(indicator_id)
                        indicator_field = str(indicator.get("s2s_ntl_field") or "").strip()
                        if indicator_field:
                            ntl_field = indicator_field

                    if int(indicator.get("use_environmental_hazards", 0)) == 1:
                        hazard_id = indicator_id.lower()
                        hazard_field = str(indicator.get("s2s_hazard_field") or "").strip()
                        if not hazard_field:
                            hazard_field = DEFAULT_S2S_ENV_HAZARD_FIELDS.get(hazard_id, "")
                        if not hazard_field:
                            warnings.append(f"Skipped {indicator_id}: no S2S hazard field configured.")
                            continue
                        jobs.append(
                            {
                                "type": "hazard",
                                "indicator_ids": [indicator_id],
                                "fields": [hazard_field],
                                "filename": f"s2s_environmental_hazards_{hazard_id}",
                                "metadata": {"s2s_hazard_field": hazard_field, "s2s_ntl_field": ""},
                            }
                        )

                    if int(indicator.get("use_polygon_per_cell", 0)) == 1:
                        fields = indicator.get("s2s_fields", [])
                        if isinstance(fields, str):
                            fields = [token.strip() for token in fields.split(",") if token.strip()]
                        elif isinstance(fields, list):
                            fields = [str(token).strip() for token in fields if str(token).strip()]
                        else:
                            fields = []

                        unique_fields = []
                        for field in fields:
                            if field not in unique_fields:
                                unique_fields.append(field)

                        if not unique_fields:
                            warnings.append(f"Skipped {indicator_id}: no s2s_fields configured.")
                            continue

                        sanitized_id = indicator_id.lower().replace(" ", "_").replace("-", "_")
                        jobs.append(
                            {
                                "type": "polygon_per_cell",
                                "indicator_ids": [indicator_id],
                                "fields": unique_fields,
                                "filename": f"s2s_polygon_per_cell_{sanitized_id}",
                                "metadata": {
                                    "s2s_fields": unique_fields,
                                    "s2s_fields_text": ",".join(unique_fields),
                                },
                            }
                        )

        if ntl_indicators:
            jobs.insert(
                0,
                {
                    "type": "nighttime_lights",
                    "indicator_ids": ntl_indicators,
                    "fields": [ntl_field],
                    "filename": "s2s_nighttime_lights",
                    "metadata": {"s2s_ntl_field": ntl_field},
                },
            )

        return jobs, warnings

    def _run_next_s2s_prefetch_job(self, aoi_feature: dict):
        """Run next queued S2S prefetch job."""
        if self._s2s_prefetch_index >= len(self._s2s_prefetch_jobs):
            self._finalize_s2s_prefetch()
            return

        job = self._s2s_prefetch_jobs[self._s2s_prefetch_index]
        job_index = self._s2s_prefetch_index + 1
        total = len(self._s2s_prefetch_jobs)
        self.processing_info_label.setText(f"Fetching S2S dataset {job_index}/{total}: {job['filename']}")
        self.child_progress_bar.setFormat(f"S2S {job_index}/{total}: %p%")

        self._s2s_prefetch_task = S2SDownloaderTask(
            aoi=aoi_feature,
            fields=job["fields"],
            working_dir=self.working_dir,
            filename=job["filename"],
            spatial_join_method="centroid",
            geometry="point",
            delete_existing=True,
        )
        self._s2s_prefetch_task.progress_updated.connect(self._on_s2s_prefetch_progress_message)
        self._s2s_prefetch_task.progressChanged.connect(self._on_s2s_prefetch_progress_value)
        self._s2s_prefetch_task.error_occurred.connect(self._on_s2s_prefetch_error)
        self._s2s_prefetch_error_for_current_task = False
        self._s2s_prefetch_task.taskCompleted.connect(
            lambda aoi=aoi_feature, current_job=job: self._on_s2s_prefetch_task_completed(current_job, aoi)
        )
        self._s2s_prefetch_task.taskTerminated.connect(
            lambda aoi=aoi_feature, current_job=job: self._on_s2s_prefetch_task_terminated(current_job, aoi)
        )
        QgsApplication.taskManager().addTask(self._s2s_prefetch_task)

    def _on_s2s_prefetch_progress_message(self, message: str):
        """Update status label with S2S task progress text."""
        self.processing_info_label.setText(message)

    def _on_s2s_prefetch_progress_value(self, progress: float):
        """Update progress bar from S2S task progress."""
        self.child_progress_bar.setValue(int(progress))

    def _on_s2s_prefetch_error(self, message: str):
        """Record non-blocking S2S prefetch errors."""
        self._s2s_prefetch_error_for_current_task = True
        self._s2s_prefetch_warnings.append(message)

    def _on_s2s_prefetch_task_completed(self, job: dict, aoi_feature: dict):
        """Handle successful S2S prefetch task and run next."""
        output_path = os.path.join(self.working_dir, "study_area", f"{job['filename']}.gpkg")
        if os.path.exists(output_path):
            self._s2s_prefetch_updates.append(
                {
                    "indicator_ids": job["indicator_ids"],
                    "output_path": output_path,
                    "metadata": job["metadata"],
                }
            )
        else:
            self._s2s_prefetch_warnings.append(f"S2S output not found for {job['filename']}.")

        self._s2s_prefetch_index += 1
        self._run_next_s2s_prefetch_job(aoi_feature)

    def _on_s2s_prefetch_task_terminated(self, job: dict, aoi_feature: dict):
        """Handle terminated S2S prefetch tasks and continue queue."""
        if not self._s2s_prefetch_error_for_current_task:
            self._s2s_prefetch_warnings.append(f"S2S prefetch task terminated: {job['filename']}")
        self._s2s_prefetch_index += 1
        self._run_next_s2s_prefetch_job(aoi_feature)

    def _finalize_s2s_prefetch(self):
        """Write S2S prefetch metadata into model and complete setup flow."""
        model_path = os.path.join(self.working_dir, "model.json")
        try:
            with open(model_path, "r", encoding="utf-8") as model_file:
                model = json.load(model_file)
            self._apply_s2s_updates_to_model(model, self._s2s_prefetch_updates)
            with open(model_path, "w", encoding="utf-8") as model_file:
                json.dump(model, model_file, indent=2)
        except Exception as error:
            self._s2s_prefetch_warnings.append(f"Failed to store S2S prefetch metadata: {error}")

        self.child_progress_bar.setValue(100)
        self.child_progress_bar.setFormat("S2S fetch complete")
        self.processing_info_label.setText("S2S fetch completed.")

        if self._s2s_prefetch_warnings:
            QMessageBox.information(self, "S2S Fetch", "\n".join(self._s2s_prefetch_warnings))

        self.working_directory_changed.emit(self.working_dir)
        self.enable_widgets()
        self.switch_to_next_tab.emit()

    @staticmethod
    def _apply_s2s_updates_to_model(model: dict, updates: List[Dict]) -> None:
        """Persist S2S output metadata into matching indicator attributes."""
        updates_by_indicator: Dict[str, List[Dict]] = {}
        for update in updates:
            for indicator_id in update.get("indicator_ids", []):
                updates_by_indicator.setdefault(indicator_id, []).append(update)

        for dimension in model.get("dimensions", []):
            for factor in dimension.get("factors", []):
                for indicator in factor.get("indicators", []):
                    indicator_id = indicator.get("id")
                    if indicator_id not in updates_by_indicator:
                        continue
                    for update in updates_by_indicator[indicator_id]:
                        indicator["s2s_output_path"] = update["output_path"]
                        indicator["s2s_spatial_join_method"] = "centroid"
                        for key, value in update.get("metadata", {}).items():
                            indicator[key] = value

    @staticmethod
    def _build_aoi_feature(layer: QgsVectorLayer) -> dict:
        """Build a WGS84 GeoJSON AOI feature from a vector layer."""
        geometries = []
        source_crs = layer.crs()
        target_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = None
        if source_crs.isValid() and source_crs != target_crs:
            transform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())

        for feature in layer.getFeatures():
            geometry = feature.geometry()
            if not geometry or geometry.isEmpty():
                continue
            transformed_geometry = QgsGeometry(geometry)
            if transform is not None:
                transformed_geometry.transform(transform)
            geometries.append(transformed_geometry)

        if not geometries:
            return {}

        union_geometry = QgsGeometry.unaryUnion(geometries)
        if not union_geometry or union_geometry.isEmpty():
            return {}

        return {
            "type": "Feature",
            "geometry": json.loads(union_geometry.asJson()),
            "properties": {},
        }

    def on_ghsl_download_failed(self, error_message, processor):
        """Slot called when GHSL download fails during study area processing.

        Prompts user to continue without GHSL data or abort the task.

        Args:
            error_message: Description of what failed and consequences.
            processor: The StudyAreaProcessingTask instance to send response to.
        """
        log_message("GHSL download failed, prompting user for response", tag="GeoE3", level=Qgis.Warning)

        reply = QMessageBox.warning(
            self,
            "GHSL Download Failed",
            error_message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            log_message("User chose to continue without GHSL data", tag="GeoE3", level=Qgis.Info)
            processor.set_ghsl_user_response(continue_without=True)
        else:
            log_message("User chose to abort due to GHSL failure", tag="GeoE3", level=Qgis.Info)
            processor.set_ghsl_user_response(continue_without=False)
            # Update progress bar to show abort
            self.progress_bar.setFormat("Aborted — GHSL download failed")
            self.enable_widgets()

    def update_recent_projects(self, directory):
        """Updates the recent projects list with the new directory.

        Args:
            directory: The directory path to add to the recent projects list.
        """
        recent_projects = self.settings.value("recent_projects", [])

        if directory in recent_projects:
            recent_projects.remove(directory)  # Remove if already in the list (to reorder)

        recent_projects.insert(0, directory)  # Add to the top of the list

        # Limit the list to a certain number of recent projects (e.g., 15)
        if len(recent_projects) > 15:
            recent_projects = recent_projects[:15]

        # Save back to QSettings
        self.settings.setValue("recent_projects", recent_projects)

    def resizeEvent(self, event):
        """⚙️ Resizeevent.

        Args:
            event: Event.
        """
        self.set_font_size()
        super().resizeEvent(event)

    def set_font_size(self):
        """⚙️ Set font size."""
        # Scale the font size to fit the text in the available space
        # log_message(f"Description Label Width: {self.description.rect().width()}")
        # scale the font size linearly from 16 pt to 8 ps as the width of the panel decreases
        font_size = int(linear_interpolation(self.description.rect().width(), 12, 16, 400, 600))

        # log_message(f"Description Label Font Size: {font_size}")
        self.description.setFont(QFont("Arial", font_size))
        self.description2.setFont(QFont("Arial", font_size))
        self.description3.setFont(QFont("Arial", font_size))
        self.create_project_directory_button.setFont(QFont("Arial", font_size))
        self.load_boundary_button.setFont(QFont("Arial", font_size))
        self.cell_size_spinbox.setFont(QFont("Arial", font_size))
        self.layer_combo.setFont(QFont("Arial", font_size))
        self.field_combo.setFont(QFont("Arial", font_size))

        # Women's considerations section
        self.women_considerations_checkbox.setFont(QFont("Arial", font_size))
        self.women_considerations_description.setFont(QFont("Arial", font_size))
        self.prefetch_s2s_checkbox.setFont(QFont("Arial", font_size))
        self.prefetch_s2s_description.setFont(QFont("Arial", font_size))

        # Processing info label
        self.processing_info_label.setFont(QFont("Arial", font_size))

        # Progress bars use a fixed small font so text never wraps inside the bar
        self.progress_bar.setFont(QFont("Arial", 9))
        self.child_progress_bar.setFont(QFont("Arial", 9))

    def add_bboxes_to_map(self):
        """Add the study area layers to the map.

        If it is already there we will just refresh it.

        This provides the user with visual feedback as each geometry gets processed.

        This method is a cut and paste of the same method in tree_panel.py
        but only adds two layers (well one layer and one table) to the map.

        Raises:
            RuntimeError: If the GeoPackage cannot be opened for an unexpected reason.
        """
        gpkg_path = os.path.join(self.working_dir, "study_area", "study_area.gpkg")
        project = QgsProject.instance()

        # Check if 'GeoE3' group exists, otherwise create it
        root = project.layerTreeRoot()
        geoe3_group = root.findGroup("GeoE3 Study Area")
        if geoe3_group is None:
            geoe3_group = root.insertGroup(0, "GeoE3 Study Area")  # Insert at the top of the layers panel

        layers = [
            "study_area_bboxes",
            "study_area_creation_status",
        ]
        for layer_name in layers:
            # Check if GeoPackage file exists first
            if not os.path.exists(gpkg_path):
                log_message(
                    f"GeoPackage not yet created: {gpkg_path}",
                    tag="GeoE3",
                    level=Qgis.Info,
                )
                return

            # Check if file size is stable (not being actively written)
            # A very small file might still be initializing
            try:
                file_size = os.path.getsize(gpkg_path)
                if file_size < 1024:  # Less than 1KB suggests still initializing
                    log_message(
                        f"GeoPackage still initializing (size: {file_size} bytes)",
                        tag="GeoE3",
                        level=Qgis.Info,
                    )
                    return
            except OSError:
                return  # File might be locked

            # Check if layer exists in GeoPackage
            from osgeo import ogr

            try:
                ds = ogr.Open(gpkg_path, 0)
                if ds is None:
                    log_message(f"Could not open GeoPackage: {gpkg_path}", tag="GeoE3", level=Qgis.Warning)
                    continue

                layer_exists = ds.GetLayerByName(layer_name) is not None
                ds = None
            except RuntimeError as e:
                error_str = str(e).lower()
                # Skip if database is busy, temporarily corrupted, or still initializing
                if (
                    "database is locked" in error_str
                    or "malformed" in error_str
                    or "gpkg_spatial_ref_sys" in error_str
                    or "gpkg_contents" in error_str
                ):
                    log_message(
                        f"Database busy or still initializing, skipping map refresh for {layer_name}",
                        tag="GeoE3",
                        level=Qgis.Info,
                    )
                    continue
                raise

            if not layer_exists:
                log_message(
                    f"Layer '{layer_name}' does not exist in GeoPackage yet (will be created during processing).",
                    tag="GeoE3",
                    level=Qgis.Info,
                )
                continue

            gpkg_layer_path = f"{gpkg_path}|layername={layer_name}"
            layer = QgsVectorLayer(gpkg_layer_path, layer_name, "ogr")

            if not layer.isValid():
                log_message(
                    f"Failed to load '{layer_name}' layer from GeoPackage.",
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

            # Refresh existing layer instead of removing and re-adding
            if existing_layer is not None:
                log_message(f"Refreshing existing layer: {existing_layer.name()}")
                try:
                    existing_layer.reload()
                except Exception as e:
                    # Skip refresh if layer is locked by background write operation
                    log_message(
                        f"Could not refresh layer {existing_layer.name()}: {e}. "
                        "Layer may be locked (this is normal during processing).",
                        tag="GeoE3",
                        level=Qgis.Info,
                    )
            else:
                # Add the new layer to the appropriate subgroup
                QgsProject.instance().addMapLayer(layer, False)
                _ = geoe3_group.addLayer(layer)
                log_message(f"Added layer: {layer.name()} to group: {geoe3_group.name()}")
