# -*- coding: utf-8 -*-
"""📦 Analysis Aggregation Dialog module.

This module contains functionality for analysis aggregation dialog.
"""

import json
import os
from urllib.parse import unquote

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsGeometry,
    QgsMapLayerProxyModel,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
)
from qgis.gui import QgsMapLayerComboBox
from qgis.PyQt.QtCore import QByteArray, QSettings, Qt, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QPixmap
from qgis.PyQt.QtWidgets import (
    QAbstractScrollArea,
    QApplication,
    QCheckBox,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from geest.core import S2STaskGate
from geest.core.constants import (
    DEFAULT_S2S_EDUCATION_URBANIZATION_FIELDS,
    DEFAULT_S2S_POPULATION_FIELD,
)
from geest.core.settings import setting
from geest.core.tasks import S2SDownloaderTask
from geest.gui.widgets import CustomBannerLabel
from geest.gui.widgets.datasource_widgets.download_task_controls import DownloadTaskControls
from geest.utilities import (
    get_ui_class,
    is_qgis_dark_theme_active,
    log_message,
    log_window_geometry,
    resources_path,
)

from .custom_base_dialog import CustomBaseDialog

FORM_CLASS = get_ui_class("analysis_dialog_base.ui")


class AnalysisAggregationDialog(FORM_CLASS, CustomBaseDialog):
    """🎯 Analysis Aggregation Dialog.

    Attributes:
        analysis_data: Analysis data.
        analysis_name: Analysis name.
        custom_label: Custom label.
        guid_column_visible: Guid column visible.
        guids: Guids.
    """

    def __init__(self, analysis_item, parent=None):
        """🏗️ Initialize the instance.

        Args:
            analysis_item: Analysis item.
            parent: Parent.
        """
        super().__init__(parent)
        # Dynamically load the .ui file
        self.setupUi(self)

        self.analysis_name = analysis_item.attribute("analysis_name")
        self.analysis_data = analysis_item.attributes()
        self.tree_item = analysis_item  # Reference to the QTreeView item to update

        self.setWindowTitle(f"Edit weightings for analysis: {self.analysis_name}")
        # Need to be redimensioned...
        self.guids = self.tree_item.getAnalysisDimensionGuids()
        self.weightings = {}  # To store the temporary weightings
        # Banner label
        self.custom_label = CustomBannerLabel(
            "The Geospatial Enabling Environments for Employment Tool",
            resources_path("resources", "geoe3-banner.png"),
        )
        parent_layout = self.banner_label.parent().layout()
        parent_layout.replaceWidget(self.banner_label, self.custom_label)
        self.banner_label.deleteLater()
        parent_layout.update()

        self.setup_table()

        self.aggregation_lineedit.hide()
        self.population_lineedit.hide()
        self.point_lineedit.hide()
        self.polygon_lineedit.hide()
        self.raster_lineedit.hide()

        # Set up the aggregation layer widgets
        self.aggregation_combo.setAllowEmptyLayer(True)
        self.aggregation_combo.setCurrentIndex(-1)
        self.aggregation_combo.setFilters(QgsMapLayerProxyModel.Filter.PolygonLayer)
        self.aggregation_combo.currentIndexChanged.connect(self.aggregation_selected)
        self.aggregation_toolbutton.clicked.connect(self.aggregation_toolbutton_clicked)
        self.aggregation_lineedit.textChanged.connect(self.aggregation_lineedit_text_changed)
        self.load_combo_from_model(self.aggregation_combo, self.aggregation_lineedit, "aggregation")

        # Set up the population raster widgets. Accept both raster and vector
        # layers so the user can freely choose between a raster population grid
        # and the S2S demographics vector layer downloaded via the S2S button.
        self.population_combo.setAllowEmptyLayer(True)
        self.population_combo.setCurrentIndex(-1)
        self.population_combo.setFilters(
            QgsMapLayerProxyModel.Filter.RasterLayer | QgsMapLayerProxyModel.Filter.VectorLayer
        )
        self.population_combo.currentIndexChanged.connect(self.population_selected)
        self.population_toolbutton.clicked.connect(self.population_toolbutton_clicked)
        self.population_lineedit.textChanged.connect(self.population_lineedit_text_changed)
        self.load_combo_from_model(self.population_combo, self.population_lineedit, "population")

        # S2S demographics download state
        self.s2s_demographics_task = None
        self._s2s_gate_token = None
        self._s2s_error_handled = False

        self._setup_s2s_demographics_ui()

        # Set up the point layer widgets
        self.point_combo.setAllowEmptyLayer(True)
        self.point_combo.setCurrentIndex(-1)
        self.point_combo.setFilters(QgsMapLayerProxyModel.Filter.PointLayer)
        self.point_combo.currentIndexChanged.connect(self.point_selected)
        self.population_toolbutton.clicked.connect(self.point_toolbutton_clicked)
        self.point_lineedit.textChanged.connect(self.point_lineedit_text_changed)
        self.load_combo_from_model(self.point_combo, self.point_lineedit, "point_mask")

        # set up the polygon layer widgets
        self.polygon_combo.setAllowEmptyLayer(True)
        self.polygon_combo.setCurrentIndex(-1)
        self.polygon_combo.setFilters(QgsMapLayerProxyModel.Filter.PolygonLayer)
        self.polygon_combo.currentIndexChanged.connect(self.polygon_selected)
        self.polygon_toolbutton.clicked.connect(self.polygon_toolbutton_clicked)
        self.polygon_lineedit.textChanged.connect(self.polygon_lineedit_text_changed)
        self.load_combo_from_model(self.polygon_combo, self.polygon_lineedit, "polygon_mask")

        # Set up the raster layer widgets
        self.raster_combo.setAllowEmptyLayer(True)
        self.raster_combo.setCurrentIndex(-1)
        self.raster_combo.setFilters(QgsMapLayerProxyModel.Filter.RasterLayer)
        self.raster_combo.currentIndexChanged.connect(self.raster_selected)
        self.raster_toolbutton.clicked.connect(self.raster_toolbutton_clicked)
        self.raster_lineedit.textChanged.connect(self.raster_lineedit_text_changed)
        self.load_combo_from_model(self.raster_combo, self.raster_lineedit, "raster_mask")

        help_layout = QHBoxLayout()
        help_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        self.help_icon = QPixmap(resources_path("resources", "images", "help.png"))
        self.help_icon = self.help_icon.scaledToWidth(20)
        self.help_label_icon = QLabel()
        self.help_label_icon.setPixmap(self.help_icon)
        self.help_label_icon.setScaledContents(True)
        self.help_label_icon.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.help_label_icon.setMaximumWidth(20)
        self.help_label_icon.setAlignment(Qt.AlignmentFlag.AlignRight)
        help_layout.addWidget(self.help_label_icon)

        self.help_label = QLabel(
            "For detailed instructions on how to use this tool, please refer to the <a href='https://worldbank.github.io/GEOE3/docs/user_guide.html'>GeoE3 User Guide</a>."
        )
        self.help_label.setOpenExternalLinks(True)
        self.help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.help_label.linkActivated.connect(self.open_link_in_browser)
        help_layout.addWidget(self.help_label)
        help_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        self.help_widget.setLayout(help_layout)

        auto_calculate_button = QPushButton("Balance Weights")
        self.button_box.addButton(auto_calculate_button, QDialogButtonBox.ButtonRole.ActionRole)
        self.button_box.accepted.connect(self.accept_changes)
        self.button_box.rejected.connect(self.reject)
        auto_calculate_button.clicked.connect(self.auto_calculate_weightings)

        toggle_guid_button = QPushButton("Show GUIDs")
        self.button_box.addButton(auto_calculate_button, QDialogButtonBox.ButtonRole.ActionRole)
        verbose_mode = setting(key="verbose_mode", default=0)
        if verbose_mode:
            self.button_box.addButton(toggle_guid_button, QDialogButtonBox.ButtonRole.ActionRole)
        toggle_guid_button.clicked.connect(self.toggle_guid_column)
        self.guid_column_visible = False  # Track GUID column visibility
        self.table.setColumnHidden(4, not self.guid_column_visible)  # Hide GUID column by default

        # Initial validation check
        self.validate_weightings()

        # Restore the radio button state
        mask_mode = self.tree_item.attribute("mask_mode", "")
        if mask_mode in ("", "None", "none"):
            self.none_radio_button.setChecked(True)
        elif mask_mode == "point":
            self.point_radio_button.setChecked(True)
        elif mask_mode == "polygon":
            self.polygon_radio_button.setChecked(True)
        elif mask_mode == "raster":
            self.raster_radio_button.setChecked(True)
        elif mask_mode == "ghsl":
            # use the global human settlements layer configured during project setup
            self.ghsl_radio_button.setChecked(True)
        else:
            # Unknown value - default to no mask rather than silently choosing GHSL
            self.none_radio_button.setChecked(True)

        buffer_distance = self.tree_item.attribute("buffer_distance_m", 0)
        self.buffer_distance_m.setValue(int(buffer_distance))

        # Restore the dialog geometry
        self.restore_dialog_geometry()

    def _setup_s2s_demographics_ui(self) -> None:
        """Configure population UI for Regional projects with S2S demographics.

        For Regional projects the population source is pre-selected to S2S
        demographics. A download button is shown so the user can fetch the S2S
        data on demand (and re-download if desired). While no S2S data has been
        downloaded yet, the raster selection widgets remain available as a
        fallback. National/Local projects keep the standard raster widgets
        unchanged.
        """
        analysis_scale = self.tree_item.attribute("analysis_scale", "national")

        if analysis_scale != "regional":
            return

        s2s_field = self.tree_item.attribute("population_s2s_field", "") or DEFAULT_S2S_POPULATION_FIELD
        s2s_pop_path = self.tree_item.attribute("population_s2s_output_path", None)
        has_s2s_data = bool(s2s_pop_path) and os.path.exists(s2s_pop_path)

        s2s_label = QLabel(f"S2S Demographics: {s2s_field}")
        s2s_label.setStyleSheet("font-weight: bold; padding: 4px;")

        self.s2s_demographics_controls = DownloadTaskControls(
            button_text="Download from S2S",
            tooltip="Download population demographics data from Space2Stats",
            click_handler=self.fetch_s2s_demographics,
        )

        self.s2s_demographics_status_label = QLabel()
        self.s2s_demographics_status_label.setStyleSheet("color: #666666; font-size: 11px;")

        # Keep the population combo visible so the user can freely choose
        # between the S2S demographics layer and a raster population grid.
        self.population_combo.setVisible(True)
        self.population_toolbutton.setVisible(True)
        self.population_lineedit.setVisible(False)

        containing_layout = self._find_layout_containing_widget(self.population_combo)
        if containing_layout is not None:
            containing_layout.addWidget(s2s_label)
            containing_layout.addWidget(self.s2s_demographics_controls.container)

        if has_s2s_data:
            # Load the existing S2S layer and pre-select it in the combo.
            layer_name = os.path.splitext(os.path.basename(s2s_pop_path))[0]
            output_layer = self._load_or_reuse_vector_layer(s2s_pop_path, layer_name)
            if output_layer is not None:
                self.population_combo.setLayer(output_layer)
                self.tree_item.setAttribute("population_layer_id", output_layer.id())
                self.tree_item.setAttribute("population_layer_name", output_layer.name())
                self.tree_item.setAttribute("population_layer_source", output_layer.source())
                self.tree_item.setAttribute("population_layer_provider_type", output_layer.providerType())
                self.tree_item.setAttribute("population_layer_crs", output_layer.crs().authid())
            self.s2s_demographics_status_label.setText("✓ S2S data available")
            self.s2s_demographics_status_label.setStyleSheet("color: #2e7d32; font-size: 11px;")
            self.s2s_demographics_controls.set_downloaded()
        else:
            self.s2s_demographics_status_label.setText(
                "Click download to fetch S2S data (raster may be used as a fallback)"
            )

        self._insert_status_label_below(containing_layout)

    @staticmethod
    def _find_layout_containing_widget(widget: QWidget):
        """Return the immediate child layout that directly contains the widget.

        Args:
            widget: The child widget to locate.

        Returns:
            The QLayout that directly contains the widget, or None.
        """
        parent = widget.parentWidget()
        if parent is None or parent.layout() is None:
            return None
        for index in range(parent.layout().count()):
            item = parent.layout().itemAt(index)
            if item is not None and item.layout() is not None and item.layout().indexOf(widget) != -1:
                return item.layout()
        return None

    def _insert_status_label_below(self, containing_layout) -> None:
        """Insert the status label into the parent grid, below the population row.

        Args:
            containing_layout: The layout holding the population widgets
                (horizontalLayout_2), which sits inside gridLayout_2.
        """
        parent = self.population_combo.parentWidget()
        if parent is None or containing_layout is None:
            return
        grid = parent.layout()
        if grid is None:
            return
        for index in range(grid.count()):
            item = grid.itemAt(index)
            if item is not None and item.layout() is containing_layout:
                row, col, _, _ = grid.getItemPosition(index)
                grid.addWidget(self.s2s_demographics_status_label, row + 1, col)
                break

    def fetch_s2s_demographics(self) -> None:
        """Download S2S demographics data for the current study area."""
        working_dir = self.tree_item.attribute("working_folder", "")
        if not working_dir or not os.path.exists(working_dir):
            QMessageBox.warning(
                self,
                "S2S Download",
                "Working directory not found. Please set up a project first.",
            )
            return

        gpkg_path = os.path.join(working_dir, "study_area", "study_area.gpkg")
        if not os.path.exists(gpkg_path):
            QMessageBox.warning(
                self,
                "S2S Download",
                "Study area not found. Please create a study area first.",
            )
            return

        aoi_feature = self._build_aoi_feature(gpkg_path)
        if not aoi_feature:
            QMessageBox.warning(
                self,
                "S2S Download",
                "Could not determine study area boundary for S2S query.",
            )
            return

        token = S2STaskGate.acquire("dialog:analysis_aggregation")
        if not token:
            active = S2STaskGate.active_label() or "another panel"
            QMessageBox.information(
                self,
                "S2S Busy",
                f"Another S2S download is running ({active}). Please wait.",
            )
            return
        self._s2s_gate_token = token

        self.s2s_demographics_controls.set_running()
        self.s2s_demographics_status_label.setText("Fetching S2S data...")
        self.s2s_demographics_status_label.setStyleSheet("color: #1976d2; font-size: 11px;")
        self._s2s_error_handled = False

        s2s_field = self.tree_item.attribute("population_s2s_field", "") or DEFAULT_S2S_POPULATION_FIELD
        demographics_fields = [s2s_field]
        for field in DEFAULT_S2S_EDUCATION_URBANIZATION_FIELDS:
            if field not in demographics_fields:
                demographics_fields.append(field)
        self.s2s_demographics_task = S2SDownloaderTask(
            aoi=aoi_feature,
            fields=demographics_fields,
            working_dir=working_dir,
            filename="s2s_demographics",
            spatial_join_method="centroid",
            geometry="point",
            delete_existing=True,
        )

        self.s2s_demographics_task.progress_updated.connect(self._on_s2s_demographics_progress)
        self.s2s_demographics_task.error_occurred.connect(self._on_s2s_demographics_error)
        self.s2s_demographics_task.taskCompleted.connect(self._on_s2s_demographics_completed)
        self.s2s_demographics_task.taskTerminated.connect(self._on_s2s_demographics_terminated)

        QgsApplication.taskManager().addTask(self.s2s_demographics_task)

    def _on_s2s_demographics_progress(self, message: str) -> None:
        """Update UI with S2S download progress.

        Args:
            message: Progress message from the S2S download task.
        """
        self.s2s_demographics_status_label.setText(message)
        self.s2s_demographics_controls.update_progress(message)

    def _on_s2s_demographics_error(self, message: str) -> None:
        """Handle S2S download error.

        Args:
            message: Error message from the S2S download task.
        """
        self._s2s_error_handled = True
        self._release_s2s_gate()
        self.s2s_demographics_status_label.setText(f"Download failed: {message}")
        self.s2s_demographics_status_label.setStyleSheet("color: #d32f2f; font-size: 11px;")
        self.s2s_demographics_controls.set_download_failed(message)
        QMessageBox.warning(
            self,
            "S2S Download Failed",
            f"Failed to download S2S demographics data:\n\n{message}\n\n"
            "You can still use a raster layer for population data.",
        )

    def _on_s2s_demographics_terminated(self) -> None:
        """Handle S2S download termination (cancel or failure)."""
        self._release_s2s_gate()
        if self._s2s_error_handled:
            return
        self.s2s_demographics_status_label.setText("Download cancelled")
        self.s2s_demographics_status_label.setStyleSheet("color: #f57c00; font-size: 11px;")
        self.s2s_demographics_controls.set_cancelled()

    def _on_s2s_demographics_completed(self) -> None:
        """Handle successful S2S download."""
        self._release_s2s_gate()
        self.s2s_demographics_controls.reset()

        working_dir = self.tree_item.attribute("working_folder", "")
        output_path = os.path.join(working_dir, "study_area", "s2s_demographics.gpkg")

        if not os.path.exists(output_path):
            self.s2s_demographics_status_label.setText("Download completed but file not found")
            self.s2s_demographics_status_label.setStyleSheet("color: #d32f2f; font-size: 11px;")
            self.s2s_demographics_controls.set_not_found(output_path)
            return

        s2s_field = self.tree_item.attribute("population_s2s_field", "") or DEFAULT_S2S_POPULATION_FIELD
        self.tree_item.setAttribute("population_s2s_output_path", output_path)
        self.tree_item.setAttribute("population_s2s_field", s2s_field)
        self.tree_item.setAttribute("population_source", "s2s")

        # Load the downloaded layer and pre-select it in the combo so the user
        # can freely switch between the S2S demographics and a raster layer.
        layer_name = os.path.splitext(os.path.basename(output_path))[0]
        output_layer = self._load_or_reuse_vector_layer(output_path, layer_name)
        if output_layer is not None:
            self.population_combo.setLayer(output_layer)
            self.tree_item.setAttribute("population_layer_id", output_layer.id())
            self.tree_item.setAttribute("population_layer_name", output_layer.name())
            self.tree_item.setAttribute("population_layer_source", output_layer.source())
            self.tree_item.setAttribute("population_layer_provider_type", output_layer.providerType())
            self.tree_item.setAttribute("population_layer_crs", output_layer.crs().authid())

        self.s2s_demographics_status_label.setText("✓ S2S data downloaded successfully")
        self.s2s_demographics_status_label.setStyleSheet("color: #2e7d32; font-size: 11px;")
        self.s2s_demographics_controls.set_downloaded()

        log_message(
            f"S2S demographics downloaded to {output_path}",
            tag="GeoE3",
            level=Qgis.Info,
        )

    def _release_s2s_gate(self) -> None:
        """Release the S2S task gate if held by this dialog."""
        if self._s2s_gate_token:
            S2STaskGate.release(self._s2s_gate_token)
            self._s2s_gate_token = None

    @staticmethod
    def _build_aoi_feature(gpkg_path: str) -> dict:
        """Build a GeoJSON Feature from study area bounding boxes.

        Args:
            gpkg_path: Path to the study area GeoPackage.

        Returns:
            GeoJSON Feature dict with geometry in EPSG:4326, or empty dict on error.
        """
        layer = QgsVectorLayer(
            f"{gpkg_path}|layername=study_area_bboxes",
            "study_area_bboxes",
            "ogr",
        )
        if not layer.isValid() or layer.featureCount() == 0:
            return {}

        source_crs = layer.crs()
        target_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = None
        if source_crs.isValid() and source_crs != target_crs:
            transform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())

        geometries = []
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

    @staticmethod
    def _load_or_reuse_vector_layer(layer_path: str, layer_name: str):
        """Load a vector layer once, reusing an existing project layer when possible.

        Args:
            layer_path: Path (or URI) to the GPKG/vector file.
            layer_name: Layer name to use.

        Returns:
            The loaded QgsVectorLayer, or None if invalid.
        """
        target_path = os.path.normpath(os.path.abspath(layer_path))
        for existing_layer in QgsProject.instance().mapLayers().values():
            if not isinstance(existing_layer, QgsVectorLayer):
                continue
            source = existing_layer.source() or ""
            source_path = os.path.normpath(os.path.abspath(source.split("|")[0]))
            if source_path != target_path:
                continue
            return existing_layer

        output_layer = QgsVectorLayer(f"{layer_path}|layername={layer_name}", layer_name, "ogr")
        if not output_layer.isValid():
            output_layer = QgsVectorLayer(layer_path, layer_name, "ogr")
        if not output_layer.isValid():
            return None

        QgsProject.instance().addMapLayer(output_layer)
        return output_layer

    def restore_dialog_geometry(self):
        """
        Restore the dialog geometry from QSettings.
        """
        settings = QSettings()
        geometry = settings.value("AnalysisAggregationDialog/geometry_v2", QByteArray())
        log_window_geometry(geometry)
        if geometry:
            log_message("Restoring dialog geometry")
            try:
                self.restoreGeometry(geometry)
                # Sanity-check: if the restored size is still oversized, discard it
                screen = QApplication.primaryScreen().geometry()
                if self.width() > int(screen.width() * 0.85) or self.height() > int(screen.height() * 0.85):
                    log_message("Restored geometry too large, resetting to default", tag="GeoE3", level=Qgis.Warning)
                    settings.remove("AnalysisAggregationDialog/geometry_v2")
                else:
                    return
            except Exception:
                log_message("Restoring geometry failed", tag="GeoE3", level=Qgis.Warning)
        log_message("No saved geometry found, resizing dialog")
        # Sensible default: cap at 900px wide, 80% screen height
        screen = QApplication.primaryScreen().geometry()
        width = min(900, int(screen.width() * 0.65))
        height = min(int(screen.height() * 0.80), 750)
        self.resize(width, height)

    def save_geometry(self):
        """
        Save the dialog geometry to QSettings.
        """
        log_message("Saving dialog geometry")
        settings = QSettings()
        settings.setValue("AnalysisAggregationDialog/geometry_v2", self.saveGeometry())

    def closeEvent(self, event):
        """⚙️ Closeevent.

        Args:
            event: Event.
        """
        self.save_geometry()
        super().closeEvent(event)

    def setup_table(self):
        """
        Set up the QTableWidget to display the analysis dimensions.

        """
        # Table setup
        self.table = QTableWidget(self)
        self.table.setRowCount(len(self.guids))
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Dimension", "Weight 0-1", "Use", "", "Guid"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Adjust column widths
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )  # dimension column expands
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # Weight 0-1 column fixed
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Use column fixed
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Reset column fixed
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Guid column fixed

        # Set fixed widths for the last three columns
        self.table.setColumnWidth(1, 100)  # Weight 0-1 column width
        self.table.setColumnWidth(2, 50)  # Use column (checkbox) width
        self.table.setColumnWidth(3, 75)  # Reset button column width
        self.table.setColumnWidth(3, 100)  # GUID button column width

        # Populate the table
        for row, guid in enumerate(self.guids):
            item = self.tree_item.getItemByGuid(guid)
            attributes = item.attributes()
            dimension_id = attributes.get("name")
            analysis_weighting = float(attributes.get("analysis_weighting", 0.0))
            default_analysis_weighting = attributes.get("default_analysis_weighting", 0)
            is_included_in_analysis = item.getStatus() != "Excluded from analysis" and analysis_weighting > 0

            name_item = QTableWidgetItem(dimension_id)
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, 0, name_item)

            # weightings
            weighting_item = QDoubleSpinBox(self)
            weighting_item.setRange(0.0, 1.0)
            weighting_item.setDecimals(4)
            weighting_item.setValue(analysis_weighting)
            weighting_item.setSingleStep(0.01)
            weighting_item.valueChanged.connect(self.validate_weightings)
            self.table.setCellWidget(row, 1, weighting_item)
            self.weightings[guid] = weighting_item

            # Use checkboxes
            checkbox_widget = self.create_checkbox_widget(row, is_included_in_analysis)
            self.table.setCellWidget(row, 2, checkbox_widget)

            # Reset button
            reset_button = QPushButton("Reset")
            reset_button.clicked.connect(lambda checked, item=weighting_item: item.setValue(default_analysis_weighting))
            self.table.setCellWidget(row, 3, reset_button)

            # Guid column
            guid_item = QTableWidgetItem(guid)
            guid_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, 4, guid_item)
            guid_item.setToolTip(str(item.attributes()))

            # Ensure row widgets are in sync with initial checkbox state.
            initial_state = Qt.CheckState.Checked if self.is_checkbox_checked(row) else Qt.CheckState.Unchecked
            self.toggle_row_widgets(row, initial_state)
        # Set the table widget height to be no taller than its content
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        self.table.setMaximumHeight(
            self.table.verticalHeader().length()  # noqa W503
            + self.table.horizontalHeader().height()  # noqa W503
            + 4  # noqa W503
        )  # Add 2 pixels to prevent scrollbar showing
        self.table.setFrameStyle(QTableWidget.Shape.NoFrame)
        parent_layout = self.geoe3_container.parent().layout()
        parent_layout.replaceWidget(self.geoe3_container, self.table)
        self.geoe3_container.deleteLater()
        parent_layout.update()

    def aggregation_selected(self):
        """Handle combo selection change"""
        self.aggregation_lineedit.hide()

    def population_selected(self):
        """Handle combo selection change"""
        self.population_lineedit.hide()

    def point_selected(self):
        """Handle combo selection change"""
        self.point_lineedit.hide()

    def polygon_selected(self):
        """Handle combo selection change"""
        self.polygon_lineedit.hide()

    def raster_selected(self):
        """Handle combo selection change"""
        self.raster_lineedit.hide()

    def aggregation_toolbutton_clicked(self):
        """⚙️ Aggregation toolbutton clicked."""
        # Show a file dialog to select a raster file
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("Vector files (*.shp *.gpkg)")
        if file_dialog.exec():
            self.aggregation_combo.setCurrentIndex(0)
            file_path = file_dialog.selectedFiles()[0]
            self.aggregation_lineedit.setText(file_path)
            self.aggregation_lineedit.show()

    def population_toolbutton_clicked(self):
        """⚙️ Population toolbutton clicked."""
        # Show a file dialog to select a raster file
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("Raster files (*.tif *.tiff *.asc)")
        if file_dialog.exec():
            self.population_combo.setCurrentIndex(0)
            file_path = file_dialog.selectedFiles()[0]
            self.population_lineedit.setText(file_path)
            self.population_lineedit.show()

    def point_toolbutton_clicked(self):
        """⚙️ Point toolbutton clicked."""
        # Show a file dialog to select a raster file
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("Vector files (*.shp *.gpkg)")
        if file_dialog.exec():
            self.point_combo.setCurrentIndex(0)
            file_path = file_dialog.selectedFiles()[0]
            self.point_lineedit.setText(file_path)
            self.point_lineedit.show()

    def polygon_toolbutton_clicked(self):
        """⚙️ Polygon toolbutton clicked."""
        # Show a file dialog to select a raster file
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("Vector files (*.shp *.gpkg)")
        if file_dialog.exec():
            self.polygon_combo.setCurrentIndex(0)
            file_path = file_dialog.selectedFiles()[0]
            self.polygon_lineedit.setText(file_path)
            self.polygon_lineedit.show()

    def raster_toolbutton_clicked(self):
        """⚙️ Raster toolbutton clicked."""
        # Show a file dialog to select a raster file
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("Raster files (*.tif *.tiff *.asc)")
        if file_dialog.exec():
            self.raster_combo.setCurrentIndex(0)
            file_path = file_dialog.selectedFiles()[0]
            self.raster_lineedit.setText(file_path)
            self.raster_lineedit.show()

    def aggregation_lineedit_text_changed(self):
        """Handle text change in the line edit"""
        self.aggregation_combo.setCurrentIndex(0)

    def population_lineedit_text_changed(self):
        """Handle text change in the line edit"""
        self.population_combo.setCurrentIndex(0)

    def point_lineedit_text_changed(self):
        """Handle text change in the line edit"""
        self.point_combo.setCurrentIndex(0)

    def polygon_lineedit_text_changed(self):
        """Handle text change in the line edit"""
        self.polygon_combo.setCurrentIndex(0)

    def raster_lineedit_text_changed(self):
        """Handle text change in the line edit"""
        self.raster_combo.setCurrentIndex(0)

    def open_link_in_browser(self, url: str):
        """Open the given URL in the user's default web browser.

        Args:
            url: The URL to open in the browser.
        """
        QDesktopServices.openUrl(QUrl(url))

    def toggle_guid_column(self):
        """Toggle the visibility of the GUID column."""
        log_message("Toggling GUID column visibility")
        self.guid_column_visible = not self.guid_column_visible
        self.table.setColumnHidden(4, not self.guid_column_visible)

    def create_checkbox_widget(self, row: int, is_checked: bool) -> QWidget:
        """Create a QWidget containing a QCheckBox for a specific row and center it.

        Args:
            row: The row index for which to create the checkbox.
            is_checked: Initial checked state for the row.

        Returns:
            A QWidget containing a centered QCheckBox.
        """
        checkbox = QCheckBox()
        checkbox.setChecked(is_checked)
        checkbox.stateChanged.connect(lambda state, r=row: self.toggle_row_widgets(r, state))
        checkbox.setEnabled(True)  # Enable by default
        # Create a container widget with a centered layout
        container = QWidget()
        layout = QHBoxLayout()
        layout.addWidget(checkbox)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center the checkbox
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        container.setLayout(layout)

        return container

    def toggle_row_widgets(self, row: int, state: int):
        """Enable or disable widgets in the row based on checkbox state.

        Args:
            row: The row index containing the widgets to toggle.
            state: The checkbox state (Qt.CheckState.Checked or Qt.CheckState.Unchecked).
        """
        is_enabled = state == Qt.CheckState.Checked
        for col in range(self.table.columnCount()):
            # Skip the column containing the checkbox (assumed to be column 2)
            if col == 2:
                continue
            # Disable QTableWidgetItems
            item = self.table.item(row, col)
            if item:
                item.setFlags(Qt.ItemFlag.ItemIsEnabled if is_enabled else Qt.ItemFlag.NoItemFlags)

            # Disable widgets inside cells
            widget = self.table.cellWidget(row, col)
            if widget:
                if isinstance(widget, QDoubleSpinBox) and not is_enabled:
                    widget.setValue(0)  # Reset weightings to zero
                widget.setEnabled(is_enabled)
        self.validate_weightings()

    def auto_calculate_weightings(self):
        """Calculate and set equal weighting for each enabled indicator."""
        log_message("Auto-calculating weightings")
        # Filter rows where the checkbox is checked
        enabled_rows = [row for row in range(self.table.rowCount()) if self.is_checkbox_checked(row)]
        disabled_rows = [row for row in range(self.table.rowCount()) if not self.is_checkbox_checked(row)]
        if not enabled_rows:
            log_message("No enabled rows found, skipping auto-calculation")
            return  # No enabled rows, avoid division by zero

        if len(enabled_rows) == 0:
            equal_weighting = 0.0
        else:
            equal_weighting = 1.0 / len(enabled_rows)  # Divide equally among enabled rows

        # Set the weighting for each enabled row
        for row in enabled_rows:
            log_message(f"Setting equal weighting for row: {row}")
            widget = self.table.cellWidget(row, 1)  # Assuming weight is in column 1
            widget.setValue(equal_weighting)
        # Rest of the rows get assigned zero
        for row in disabled_rows:
            log_message(f"Setting zero weighting for row: {row}")
            widget = self.table.cellWidget(row, 1)  # Assuming weight is in column 1
            widget.setValue(0)
        self.validate_weightings()

    def is_checkbox_checked(self, row: int) -> bool:
        """Check if the checkbox in the specified row is checked.

        Args:
            row: The row index to check.

        Returns:
            True if the checkbox is checked, False otherwise.
        """
        log_message(f"Checking checkbox state for row: {row}")
        checkbox = self.get_checkbox_in_row(row)  # Assuming the checkbox is in column 2
        return checkbox.isChecked() if checkbox else False

    def get_checkbox_in_row(self, row: int) -> QCheckBox:
        """Retrieve the checkbox widget in the specified row.

        Args:
            row: The row index to retrieve the checkbox from.

        Returns:
            The QCheckBox widget, or None if not found.
        """
        container = self.table.cellWidget(row, 2)  # Assuming the checkbox is in column 2
        if container and isinstance(container, QWidget):
            layout = container.layout()
            if layout and layout.count() > 0:
                checkbox = layout.itemAt(0).widget()
                if isinstance(checkbox, QCheckBox):
                    return checkbox
        return None

    def saveWeightingsToModel(self):
        """Assign new weightings to the analysiss's dimensions."""
        for dimension_guid, spin_box in self.weightings.items():
            try:
                new_weighting = spin_box.value()
                self.tree_item.updateDimensionWeighting(dimension_guid, new_weighting)
            except ValueError:
                log_message(
                    f"Invalid weighting input for GUID: {dimension_guid}",
                    tag="GeoE3",
                    level=Qgis.Warning,
                )

    def validate_weightings(self):
        """Validate weightings to ensure they sum to 1 and are within range."""
        try:
            total_weighting = sum(float(spin_box.value() or 0) for spin_box in self.weightings.values())
            valid_sum = abs(total_weighting - 1.0) < 0.001  # Allow slight floating-point tolerance
        except ValueError:
            valid_sum = False

        # In the case that all rows are disabled, the sum is valid
        enabled_rows = [row for row in range(self.table.rowCount()) if self.is_checkbox_checked(row)]
        enabled_rows_count = len(enabled_rows)
        if enabled_rows_count == 0:
            valid_sum = True

        if is_qgis_dark_theme_active():
            normal_color = "color: white;"
        else:
            normal_color = "color: black;"
        # Update button state and cell highlighting
        for spin_box in self.weightings.values():
            if valid_sum:
                spin_box.setStyleSheet(normal_color)  # Reset font color to black if valid
            else:
                spin_box.setStyleSheet("color: red;")  # Set font color to red if invalid

        # Enable or disable the OK button based on validation result
        if hasattr(self, "button_box"):
            ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
            if ok_button:
                ok_button.setEnabled(valid_sum)

    def accept_changes(self):
        """Handle the OK button by applying changes and closing the dialog."""
        previous_population_source = self._persisted_population_input_source()
        self.save_use_state_to_model()
        self.saveWeightingsToModel()  # Assign weightings when changes are accepted
        self.save_combo_to_model(self.aggregation_combo, self.aggregation_lineedit, "aggregation")
        self.save_combo_to_model(self.population_combo, self.population_lineedit, "population")
        # Determine the population source from the layer actually selected in
        # the combo: if it is the S2S demographics layer, use the S2S vector
        # pipeline; otherwise (raster selected) use the raster pipeline.
        self._save_population_source_from_combo()
        if self._population_input_source() != previous_population_source:
            # A population change affects the analysis-derived products. Clearing
            # the completed result makes the normal Run action queue the analysis.
            self.tree_item.clear()
            self.tree_item.setAttribute("geoe3_by_population", "")
        self.save_combo_to_model(self.point_combo, self.point_lineedit, "point_mask")
        self.save_combo_to_model(self.polygon_combo, self.polygon_lineedit, "polygon_mask")
        self.save_combo_to_model(self.raster_combo, self.raster_lineedit, "raster_mask")
        # Save the radio button state
        if self.none_radio_button.isChecked():
            self.tree_item.setAttribute("mask_mode", "None")
        elif self.point_radio_button.isChecked():
            self.tree_item.setAttribute("mask_mode", "point")
        elif self.polygon_radio_button.isChecked():
            self.tree_item.setAttribute("mask_mode", "polygon")
        elif self.raster_radio_button.isChecked():
            self.tree_item.setAttribute("mask_mode", "raster")
        elif self.ghsl_radio_button.isChecked():
            self.tree_item.setAttribute("mask_mode", "ghsl")  # gloabl human settlements layer

        self.tree_item.setAttribute("buffer_distance_m", self.buffer_distance_m.value())
        # Save the dialog geometry
        self.save_geometry()
        self.accept()

    def _save_population_source_from_combo(self) -> None:
        """Store population_source based on the layer selected in the combo.

        If the selected layer source matches the downloaded S2S demographics
        GeoPackage, the S2S vector pipeline is used; otherwise the raster
        pipeline is used.
        """
        s2s_pop_path = self.tree_item.attribute("population_s2s_output_path", None)
        layer = self.population_combo.currentLayer()

        if layer is None:
            self.tree_item.setAttribute("population_source", "raster")
            return

        source_path = self._layer_source_path(layer)
        s2s_path = self._layer_source_path_from_string(s2s_pop_path)
        if s2s_pop_path and source_path == s2s_path:
            self.tree_item.setAttribute("population_source", "s2s")
        else:
            self.tree_item.setAttribute("population_source", "raster")

    def _population_input_source(self) -> str:
        """Return the normalized effective population input source."""
        layer = self.population_combo.currentLayer()
        if layer:
            return self._layer_source_path(layer)
        return self._layer_source_path_from_string(self.population_lineedit.text())

    def _persisted_population_input_source(self) -> str:
        """Return the normalized population source currently stored in the model."""
        source = self.tree_item.attribute("population_layer_source", "") or self.tree_item.attribute(
            "population_raster", ""
        )
        return self._layer_source_path_from_string(source)

    @staticmethod
    def _layer_source_path(layer) -> str:
        """Return the normalized file path portion of a layer source URI.

        Args:
            layer: A QgsVectorLayer.

        Returns:
            Absolute normalized path of the source file (without sublayer URI).
        """
        return AnalysisAggregationDialog._layer_source_path_from_string(str(layer.source()))

    @staticmethod
    def _layer_source_path_from_string(source: str) -> str:
        """Return the normalized file path portion of a layer source string.

        Strips the ``|layername=...`` sublayer suffix so a GPKG URI and its bare
        file path compare equal.

        Args:
            source: A layer source URI/path string.

        Returns:
            Absolute normalized path of the source file.
        """
        return os.path.normpath(os.path.abspath(str(source or "").split("|")[0]))

    def save_use_state_to_model(self) -> None:
        """Persist the Use checkbox state to dimension analysis_weighting values."""
        for row, dimension_guid in enumerate(self.guids):
            dimension_item = self.tree_item.getItemByGuid(dimension_guid)
            if dimension_item is None:
                continue

            checkbox_checked = self.is_checkbox_checked(row)
            spin_box = self.weightings.get(dimension_guid)
            if checkbox_checked:
                if spin_box and float(spin_box.value() or 0.0) == 0.0:
                    default_weighting = float(dimension_item.attribute("default_analysis_weighting", 1.0) or 1.0)
                    spin_box.setValue(default_weighting)
                    dimension_item.setAttribute("analysis_weighting", default_weighting)
            else:
                if spin_box:
                    spin_box.setValue(0.0)
                dimension_item.setAttribute("analysis_weighting", 0.0)

    def save_combo_to_model(self, combo: QgsMapLayerComboBox, lineedit: QLineEdit, prefix: str):
        """Save the state of a QgsMapLayerComboBox to the json tree item.

        Args:
            combo: The QgsMapLayerComboBox containing the selected layer.
            lineedit: The QLineEdit containing the layer path.
            prefix: The prefix for attribute keys in the tree item.
        """
        item = self.tree_item
        layer = combo.currentLayer()
        if not layer:
            item.setAttribute(f"{prefix}_layer", None)
            item.setAttribute(f"{prefix}_layer_id", "")
            item.setAttribute(f"{prefix}_layer_name", "")
            item.setAttribute(f"{prefix}_layer_provider_type", "")
            item.setAttribute(f"{prefix}_layer_crs", "")
        else:
            item.setAttribute(f"{prefix}_layer_name", layer.name())
            item.setAttribute(f"{prefix}_layer_source", layer.source())
            item.setAttribute(f"{prefix}_layer_provider_type", layer.providerType())
            item.setAttribute(f"{prefix}_layer_crs", layer.crs().authid())
            if layer.providerType() != "gdal":
                item.setAttribute(f"{prefix}_layer_wkb_type", layer.wkbType())
            item.setAttribute(f"{prefix}_layer_id", layer.id())
        if lineedit.objectName() in ("raster_lineedit", "population_lineedit"):
            item.setAttribute(f"{prefix}_raster", lineedit.text())
            if prefix == "population" and lineedit.text() and not layer:
                item.setAttribute(f"{prefix}_layer_source", lineedit.text())
        else:
            item.setAttribute(f"{prefix}_shapefile", lineedit.text())

    def load_combo_from_model(self, combo: QgsMapLayerComboBox, lineedit: QLineEdit, prefix: str):
        """Load the state of a QgsMapLayerComboBox from the json tree item.

        Args:
            combo: The QgsMapLayerComboBox to populate with the layer.
            lineedit: The QLineEdit to populate with the layer path.
            prefix: The prefix for attribute keys in the tree item.
        """
        item = self.tree_item
        layer_id = item.attribute(f"{prefix}_layer_id", None)
        if layer_id:
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer:
                combo.setLayer(layer)
                return
        source = item.attribute(f"{prefix}_layer_source", "")
        if prefix == "population" and source and os.path.exists(self._layer_source_path_from_string(source)):
            layer = QgsRasterLayer(source, os.path.basename(self._layer_source_path_from_string(source)))
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                combo.setLayer(layer)
                return
        if item.attribute(f"{prefix}_shapefile", False):
            lineedit.setText(unquote(item.attribute(f"{prefix}_shapefile")))
            lineedit.setVisible(True)
        if item.attribute(f"{prefix}_raster", False):
            lineedit.setText(unquote(item.attribute(f"{prefix}_raster")))
            lineedit.setVisible(True)
