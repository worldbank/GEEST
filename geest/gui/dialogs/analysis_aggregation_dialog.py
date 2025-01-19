from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QAbstractScrollArea,
    QHeaderView,
    QLabel,
    QDoubleSpinBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTableWidget,
    QTableWidgetItem,
    QCheckBox,
    QWidget,
    QHBoxLayout,
    QSpacerItem,
    QSizePolicy,
    QFileDialog,
    QLineEdit,
)
from qgis.PyQt.QtGui import QPixmap, QDesktopServices
from qgis.PyQt.QtCore import Qt, QUrl, QSettings, QByteArray
from qgis.core import Qgis, QgsMapLayerProxyModel, QgsProject
from geest.utilities import (
    resources_path,
    log_message,
    setting,
    is_qgis_dark_theme_active,
    get_ui_class,
    log_window_geometry,
)
from qgis.gui import QgsMapLayerComboBox
from geest.gui.widgets import CustomBannerLabel
from geest.core import setting

FORM_CLASS = get_ui_class("analysis_dialog_base.ui")


class AnalysisAggregationDialog(FORM_CLASS, QDialog):
    def __init__(self, analysis_item, parent=None):
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
            "The Gender Enabling Environments Spatial Tool",
            resources_path("resources", "geest-banner.png"),
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
        self.aggregation_combo.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.aggregation_combo.currentIndexChanged.connect(self.aggregation_selected)
        self.aggregation_toolbutton.clicked.connect(self.aggregation_toolbutton_clicked)
        self.aggregation_lineedit.textChanged.connect(
            self.aggregation_lineedit_text_changed
        )
        self.load_combo_from_model(
            self.aggregation_combo, self.aggregation_lineedit, "aggregation"
        )

        # Set up the population raster widgets
        self.population_combo.setAllowEmptyLayer(True)
        self.population_combo.setCurrentIndex(-1)
        self.population_combo.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.population_combo.currentIndexChanged.connect(self.population_selected)
        self.population_toolbutton.clicked.connect(self.population_toolbutton_clicked)
        self.population_lineedit.textChanged.connect(
            self.population_lineedit_text_changed
        )
        self.load_combo_from_model(
            self.population_combo, self.population_lineedit, "population"
        )

        # Set up the point layer widgets
        self.point_combo.setAllowEmptyLayer(True)
        self.point_combo.setCurrentIndex(-1)
        self.point_combo.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.point_combo.currentIndexChanged.connect(self.point_selected)
        self.population_toolbutton.clicked.connect(self.point_toolbutton_clicked)
        self.point_lineedit.textChanged.connect(self.point_lineedit_text_changed)
        self.load_combo_from_model(self.point_combo, self.point_lineedit, "point_mask")

        # set up the polygon layer widgets
        self.polygon_combo.setAllowEmptyLayer(True)
        self.polygon_combo.setCurrentIndex(-1)
        self.polygon_combo.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.polygon_combo.currentIndexChanged.connect(self.polygon_selected)
        self.polygon_toolbutton.clicked.connect(self.polygon_toolbutton_clicked)
        self.polygon_lineedit.textChanged.connect(self.polygon_lineedit_text_changed)
        self.load_combo_from_model(
            self.polygon_combo, self.polygon_lineedit, "polygon_mask"
        )

        # Set up the raster layer widgets
        self.raster_combo.setAllowEmptyLayer(True)
        self.raster_combo.setCurrentIndex(-1)
        self.raster_combo.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.raster_combo.currentIndexChanged.connect(self.raster_selected)
        self.raster_toolbutton.clicked.connect(self.raster_toolbutton_clicked)
        self.raster_lineedit.textChanged.connect(self.raster_lineedit_text_changed)
        self.load_combo_from_model(
            self.raster_combo, self.raster_lineedit, "raster_mask"
        )

        help_layout = QHBoxLayout()
        help_layout.addItem(
            QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )
        self.help_icon = QPixmap(resources_path("resources", "images", "help.png"))
        self.help_icon = self.help_icon.scaledToWidth(20)
        self.help_label_icon = QLabel()
        self.help_label_icon.setPixmap(self.help_icon)
        self.help_label_icon.setScaledContents(True)
        self.help_label_icon.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.help_label_icon.setMaximumWidth(20)
        self.help_label_icon.setAlignment(Qt.AlignRight)
        help_layout.addWidget(self.help_label_icon)

        self.help_label = QLabel(
            "For detailed instructions on how to use this tool, please refer to the <a href='https://worldbank.github.io/GEEST/docs/user_guide.html'>GEEST User Guide</a>."
        )
        self.help_label.setOpenExternalLinks(True)
        self.help_label.setAlignment(Qt.AlignCenter)

        self.help_label.linkActivated.connect(self.open_link_in_browser)
        help_layout.addWidget(self.help_label)
        help_layout.addItem(
            QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )
        self.help_widget.setLayout(help_layout)

        auto_calculate_button = QPushButton("Balance Weights")
        self.button_box.addButton(auto_calculate_button, QDialogButtonBox.ActionRole)
        self.button_box.accepted.connect(self.accept_changes)
        self.button_box.rejected.connect(self.reject)
        auto_calculate_button.clicked.connect(self.auto_calculate_weightings)

        toggle_guid_button = QPushButton("Show GUIDs")
        self.button_box.addButton(auto_calculate_button, QDialogButtonBox.ActionRole)
        verbose_mode = setting(key="verbose_mode", default=0)
        if verbose_mode:
            self.button_box.addButton(toggle_guid_button, QDialogButtonBox.ActionRole)
        toggle_guid_button.clicked.connect(self.toggle_guid_column)
        self.guid_column_visible = False  # Track GUID column visibility
        self.table.setColumnHidden(
            4, not self.guid_column_visible
        )  # Hide GUID column by default

        # Initial validation check
        self.validate_weightings()

        # Restore the radio button state
        mask_mode = self.tree_item.attribute("mask_mode", "")
        if mask_mode == "point":
            self.point_radio_button.setChecked(True)
        elif mask_mode == "polygon":
            self.polygon_radio_button.setChecked(True)
        elif mask_mode == "raster":
            self.raster_radio_button.setChecked(True)

        buffer_distance = self.tree_item.attribute("buffer_distance_m", 0)
        self.buffer_distance_m.setValue(int(buffer_distance))

        # Restore the dialog geometry
        self.restore_dialog_geometry()

    def restore_dialog_geometry(self):
        """
        Restore the dialog geometry from QSettings.
        """
        settings = QSettings()
        # Restore geometry (fall back to empty QByteArray if setting not found)
        geometry = settings.value("AnalysisAggregationDialog/geometry", QByteArray())
        log_window_geometry(geometry)
        if geometry:
            log_message("Restoring dialog geometry")
            try:
                self.restoreGeometry(geometry)
            except Exception as e:
                log_message(
                    "Restoring geometry failed", tag="Geest", level=Qgis.Warning
                )
                pass
        else:
            log_message("No saved geometry found, resizing dialog")
            # Resize the dialog to be almost as large as the main window
            main_window = (
                self.parent().window()
                if self.parent()
                else self.screen().availableGeometry()
            )
            self.resize(int(main_window.width() * 0.9), int(main_window.height() * 0.9))

    def save_geometry(self):
        """
        Save the dialog geometry to QSettings.
        """
        log_message("Saving dialog geometry")
        settings = QSettings()
        settings.setValue("AnalysisAggregationDialog/geometry", self.geometry())

    def closeEvent(self, event):
        # Save geometry before closing
        settings = QSettings()
        settings.setValue("AnalysisAggregationDialog/geometry", self.saveGeometry())
        super().closeEvent(event)

    def setup_table(self):
        """
        Set up the QTableWidget to display the analysis dimensions.

        """
        # Table setup
        self.table = QTableWidget(self)
        self.table.setRowCount(len(self.guids))
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Dimension", "Weight 0-1", "Use", "", "Guid"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Adjust column widths
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )  # dimension column expands
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Fixed
        )  # Weight 0-1 column fixed
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Fixed
        )  # Use column fixed
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.Fixed
        )  # Reset column fixed
        self.table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.Fixed
        )  # Guid column fixed

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

            name_item = QTableWidgetItem(dimension_id)
            name_item.setFlags(Qt.ItemIsEnabled)
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
            checkbox_widget = self.create_checkbox_widget(row, analysis_weighting)
            self.table.setCellWidget(row, 2, checkbox_widget)

            # Reset button
            reset_button = QPushButton("Reset")
            reset_button.clicked.connect(
                lambda checked, item=weighting_item: item.setValue(
                    default_analysis_weighting
                )
            )
            self.table.setCellWidget(row, 3, reset_button)

            # Guid column
            guid_item = QTableWidgetItem(guid)
            guid_item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 4, guid_item)
            guid_item.setToolTip(str(item.attributes()))

            # disable the table row if the checkbox is unchecked
            # Have to do this last after all widgets are initialized
            # First check if the dimension is required
            # and disable the checkbox if it is
            for col in range(4):
                try:
                    item = self.table.item(row, col)
                    item.setEnabled(False)
                    # item.setFlags(Qt.ItemIsEnabled)
                except AttributeError:
                    pass
        # Set the table widget height to be no taller than its content
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        self.table.setMaximumHeight(
            self.table.verticalHeader().length()
            + self.table.horizontalHeader().height()
            + 4
        )  # Add 2 pixels to prevent scrollbar showing
        self.table.setFrameStyle(QTableWidget.NoFrame)
        parent_layout = self.wee_container.parent().layout()
        parent_layout.replaceWidget(self.wee_container, self.table)
        self.wee_container.deleteLater()
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
        # Show a file dialog to select a raster file
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Vector files (*.shp *.gpkg)")
        if file_dialog.exec_():
            self.aggregation_combo.setCurrentIndex(0)
            file_path = file_dialog.selectedFiles()[0]
            self.aggregation_lineedit.setText(file_path)
            self.aggregation_lineedit.show()

    def population_toolbutton_clicked(self):
        # Show a file dialog to select a raster file
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Raster files (*.tif *.tiff *.asc)")
        if file_dialog.exec_():
            self.population_combo.setCurrentIndex(0)
            file_path = file_dialog.selectedFiles()[0]
            self.population_lineedit.setText(file_path)
            self.population_lineedit.show()

    def point_toolbutton_clicked(self):
        # Show a file dialog to select a raster file
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Vector files (*.shp *.gpkg)")
        if file_dialog.exec_():
            self.point_combo.setCurrentIndex(0)
            file_path = file_dialog.selectedFiles()[0]
            self.point_lineedit.setText(file_path)
            self.point_lineedit.show()

    def polygon_toolbutton_clicked(self):
        # Show a file dialog to select a raster file
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Vector files (*.shp *.gpkg)")
        if file_dialog.exec_():
            self.polygon_combo.setCurrentIndex(0)
            file_path = file_dialog.selectedFiles()[0]
            self.polygon_lineedit.setText(file_path)
            self.polygon_lineedit.show()

    def raster_toolbutton_clicked(self):
        # Show a file dialog to select a raster file
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Raster files (*.tif *.tiff *.asc)")
        if file_dialog.exec_():
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
        """Open the given URL in the user's default web browser using QDesktopServices."""
        QDesktopServices.openUrl(QUrl(url))

    def toggle_guid_column(self):
        """Toggle the visibility of the GUID column."""
        log_message("Toggling GUID column visibility")
        self.guid_column_visible = not self.guid_column_visible
        self.table.setColumnHidden(4, not self.guid_column_visible)

    def create_checkbox_widget(self, row: int, analysis_weighting: float) -> QWidget:
        """
        Create a QWidget containing a QCheckBox for a specific row and center it.
        """
        checkbox = QCheckBox()
        if analysis_weighting > 0:
            checkbox.setChecked(True)  # Initially checked
        else:
            checkbox.setChecked(False)
        checkbox.stateChanged.connect(
            lambda state, r=row: self.toggle_row_widgets(r, state)
        )
        checkbox.setEnabled(True)  # Enable by default
        # Create a container widget with a centered layout
        container = QWidget()
        layout = QHBoxLayout()
        layout.addWidget(checkbox)
        layout.setAlignment(Qt.AlignCenter)  # Center the checkbox
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        container.setLayout(layout)

        return container

    def toggle_row_widgets(self, row: int, state: int):
        """
        Enable or disable widgets in the row based on the checkbox state.
        """
        is_enabled = state == Qt.Checked
        for col in range(self.table.columnCount()):
            # Skip the column containing the checkbox (assumed to be column 2)
            if col == 2:
                continue
            # Disable QTableWidgetItems
            item = self.table.item(row, col)
            if item:
                item.setFlags(Qt.ItemIsEnabled if is_enabled else Qt.NoItemFlags)

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
        enabled_rows = [
            row for row in range(self.table.rowCount()) if self.is_checkbox_checked(row)
        ]
        disabled_rows = [
            row
            for row in range(self.table.rowCount())
            if not self.is_checkbox_checked(row)
        ]
        if not enabled_rows:
            log_message("No enabled rows found, skipping auto-calculation")
            return  # No enabled rows, avoid division by zero

        if len(enabled_rows) == 0:
            equal_weighting = 0.0
        else:
            equal_weighting = 1.0 / len(
                enabled_rows
            )  # Divide equally among enabled rows

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
        """
        Check if the checkbox in the specified row is checked.
        :param row: The row index to check.
        :return: True if the checkbox is checked, False otherwise.
        """
        log_message(f"Checking checkbox state for row: {row}")
        checkbox = self.get_checkbox_in_row(row)  # Assuming the checkbox is in column 2
        return checkbox.isChecked()

    def get_checkbox_in_row(self, row: int) -> QCheckBox:
        """
        Retrieve the checkbox widget in the specified row.
        :param row: The row index to retrieve the checkbox from.
        :return: The QCheckBox widget, or None if not found.
        """
        container = self.table.cellWidget(
            row, 2
        )  # Assuming the checkbox is in column 2
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
                    tag="Geest",
                    level=Qgis.Warning,
                )

    def validate_weightings(self):
        """Validate weightings to ensure they sum to 1 and are within range."""
        try:
            total_weighting = sum(
                float(spin_box.value() or 0) for spin_box in self.weightings.values()
            )
            valid_sum = (
                abs(total_weighting - 1.0) < 0.001
            )  # Allow slight floating-point tolerance
        except ValueError:
            valid_sum = False

        # In the case that all rows are disabled, the sum is valid
        enabled_rows = [
            row for row in range(self.table.rowCount()) if self.is_checkbox_checked(row)
        ]
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
                spin_box.setStyleSheet(
                    normal_color
                )  # Reset font color to black if valid
            else:
                spin_box.setStyleSheet(
                    "color: red;"
                )  # Set font color to red if invalid

        # Enable or disable the OK button based on validation result
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(valid_sum)

    def accept_changes(self):
        """Handle the OK button by applying changes and closing the dialog."""
        self.saveWeightingsToModel()  # Assign weightings when changes are accepted
        self.save_combo_to_model(
            self.aggregation_combo, self.aggregation_lineedit, "aggregation"
        )
        self.save_combo_to_model(
            self.population_combo, self.population_lineedit, "population"
        )
        self.save_combo_to_model(self.point_combo, self.point_lineedit, "point_mask")
        self.save_combo_to_model(
            self.polygon_combo, self.polygon_lineedit, "polygon_mask"
        )
        self.save_combo_to_model(self.raster_combo, self.raster_lineedit, "raster_mask")
        # Save the radio button state
        if self.point_radio_button.isChecked():
            self.tree_item.setAttribute("mask_mode", "point")
        elif self.polygon_radio_button.isChecked():
            self.tree_item.setAttribute("mask_mode", "polygon")
        elif self.raster_radio_button.isChecked():
            self.tree_item.setAttribute("mask_mode", "raster")

        self.tree_item.setAttribute("buffer_distance_m", self.buffer_distance_m.value())
        # Save the dialog geometry
        self.save_geometry()
        self.accept()

    def save_combo_to_model(
        self, combo: QgsMapLayerComboBox, lineedit: QLineEdit, prefix: str
    ):
        """Save the state of a QgsMapLayerComboBox to the json tree item.

        Args:
            combo (_type_): _description_
        """
        item = self.tree_item
        layer = combo.currentLayer()
        if not layer:
            item.setAttribute(f"{prefix}_layer", None)
        else:
            item.setAttribute(f"{prefix}_layer_name", layer.name())
            item.setAttribute(f"{prefix}_layer_source", layer.source())
            item.setAttribute(f"{prefix}_layer_provider_type", layer.providerType())
            item.setAttribute(f"{prefix}_layer_crs", layer.crs().authid())
            if layer.providerType() != "gdal":
                item.setAttribute(f"{prefix}_layer_wkb_type", layer.wkbType())
            item.setAttribute(f"{prefix}_layer_id", layer.id())
        if lineedit.objectName() == "raster_lineedit":
            item.setAttribute(f"{prefix}_raster", lineedit.text())
        else:
            item.setAttribute(f"{prefix}_shapefile", lineedit.text())

    def load_combo_from_model(
        self, combo: QgsMapLayerComboBox, lineedit: QLineEdit, prefix: str
    ):
        """Load the state of a QgsMapLayerComboBox from the json tree item.

        Args:
            combo (_type_): _description_
        """
        item = self.tree_item
        layer_id = item.attribute(f"{prefix}_layer_id", None)
        if layer_id:
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer:
                combo.setLayer(layer)
        if item.attribute(f"{prefix}_shapefile", False):
            lineedit.setText(item.attribute(f"{prefix}_shapefile"))
            lineedit.setVisible(True)
        if item.attribute(f"{prefix}_raster", False):
            lineedit.setText(item.attribute(f"{prefix}_raster"))
            lineedit.setVisible(True)
