from qgis.PyQt.QtWidgets import (
    QDialog,
    QHeaderView,
    QLabel,
    QDoubleSpinBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QDialogButtonBox,
    QWidget,
    QCheckBox,
    QHBoxLayout,
    QSpacerItem,
)
from qgis.PyQt.QtGui import QPixmap, QDesktopServices
from qgis.PyQt.QtCore import Qt, QUrl
from qgis.core import Qgis
from geest.utilities import resources_path, setting
from ..datasource_widget_factory import DataSourceWidgetFactory
from ..factor_configuration_widget import FactorConfigurationWidget
from geest.utilities import log_message, is_qgis_dark_theme_active
from geest.gui.widgets import CustomBannerLabel


class FactorAggregationDialog(QDialog):

    def __init__(self, factor_name, factor_data, factor_item, parent=None):
        super().__init__(parent)

        self.setWindowTitle(factor_name)
        self.factor_name = factor_name
        self.factor_data = factor_data
        self.tree_item = factor_item  # Reference to the QTreeView item to update

        # Initialize dictionaries
        self.guids = self.tree_item.getFactorIndicatorGuids()
        # If the indicators do not have a usable analysis mode set, iterate through them
        # and set it to the first available usable mode
        for guid in self.guids:
            item = self.tree_item.getItemByGuid(guid)
            item.ensureValidAnalysisMode()

        self.weightings = {}  # Temporary weightings
        self.data_sources = {}  # Temporary data sources

        self.weighting_column_visible = len(self.guids) > 1

        # Layout setup
        layout = QVBoxLayout(self)
        self.resize(800, 600)
        layout.setContentsMargins(20, 20, 20, 20)  # Add padding around the layout

        self.banner_label = CustomBannerLabel(
            "The Gender Enabling Environments Spatial Tool",
            resources_path("resources", "geest-banner.png"),
        )
        layout.addWidget(self.banner_label)
        # Title label
        self.title_label = QLabel(
            "The Gender Enabling Environments Spatial Tool", self.banner_label
        )
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet(
            "color: white; font-size: 16px; background-color: rgba(0, 0, 0, 0.5); padding: 5px;"
        )
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)

        # Positioning the title label with a 10px offset from the left and bottom of the banner
        self.title_label.setGeometry(
            10, self.banner_label.height() - 30, self.banner_label.width() - 20, 20
        )
        self.title_label.setMargin(10)

        # Update layout
        layout.addWidget(self.banner_label)
        # Hierarchy label
        parent_item = self.tree_item.parent()
        if parent_item:
            hierarchy_label = QLabel(
                f"{parent_item.data(0)} :: {self.tree_item.data(0)}"
            )
            hierarchy_label.setStyleSheet(
                "font-size: 14px; font-weight: bold; color: gray;"
            )
            layout.addWidget(hierarchy_label, alignment=Qt.AlignTop)

        # Description label
        description_label = QLabel()
        description_label.setText(self.factor_data.get("description", ""))
        description_label.setWordWrap(True)
        layout.addWidget(description_label)

        # Configuration widget and table
        self.configuration_widget = FactorConfigurationWidget(
            self.tree_item, self.guids
        )

        self.configuration_widget.selection_changed.connect(self.populate_table)
        layout.addWidget(self.configuration_widget)

        # Table setup
        self.table = QTableWidget(self)
        self.table.setRowCount(len(self.guids))
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Input", "Indicator", "Weight 0-1", "Use", "GUID", ""]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 100)  # Weight column
        self.table.setColumnWidth(3, 50)  # Use column (checkbox)
        self.table.setColumnWidth(5, 75)  # Reset column
        # hide weight and reset column if only one indicator
        if not self.weighting_column_visible:
            self.hide_widgets_in_column(2)
            self.hide_widgets_in_column(5)
            self.table.setColumnHidden(2, True)
            self.table.setColumnHidden(5, True)

        layout.addWidget(self.table)

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
        layout.addWidget(self.help_label)
        self.help_label.linkActivated.connect(self.open_link_in_browser)
        help_layout.addWidget(self.help_label)
        help_layout.addItem(
            QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )
        layout.addLayout(help_layout)

        # Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        auto_calculate_button = QPushButton("Balance Weights")
        toggle_guid_button = QPushButton("Show GUIDs")
        if self.weighting_column_visible:
            self.button_box.addButton(
                auto_calculate_button, QDialogButtonBox.ActionRole
            )
        verbose_mode = setting(key="verbose_mode", default=0)
        if verbose_mode:
            self.button_box.addButton(toggle_guid_button, QDialogButtonBox.ActionRole)

        self.button_box.accepted.connect(self.accept_changes)
        self.button_box.rejected.connect(self.reject)
        auto_calculate_button.clicked.connect(self.auto_calculate_weightings)

        toggle_guid_button.clicked.connect(self.toggle_guid_column)
        self.guid_column_visible = False  # Track GUID column visibility

        layout.addWidget(self.button_box)
        self.populate_table()
        self.validate_weightings()
        self.setLayout(layout)
        self.populate_table()  # Populate the table after initializing data_sources and weightings

    def open_link_in_browser(self, url: str):
        """Open the given URL in the user's default web browser using QDesktopServices."""
        QDesktopServices.openUrl(QUrl(url))

    def refresh_configuration(self, attributes: dict):
        """Refresh the configuration widget and table.

        We call this when any data source widget changes to ensure the data source
        and the configuration are conistent with each other.

        """
        log_message("data_changed signal received, refreshing configuration")
        self.configuration_widget.refresh_radio_buttons(attributes)

    def create_checkbox_widget(self, row: int, weighting_value: float) -> QWidget:
        checkbox = QCheckBox()
        if weighting_value > 0:
            checkbox.setChecked(True)
        else:
            checkbox.setChecked(False)
        checkbox.stateChanged.connect(
            lambda state, r=row: self.toggle_row_widgets(r, state)
        )

        container = QWidget()
        layout = QHBoxLayout()
        layout.addWidget(checkbox)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        container.setLayout(layout)
        return container

    def toggle_row_widgets(self, row: int, state: int):
        is_enabled = state == Qt.Checked
        for col in range(self.table.columnCount()):
            if col in (3, 5):  # Skip Use (checkbox) and Reset columns
                continue
            widget = self.table.cellWidget(row, col)
            if widget:
                if isinstance(widget, QDoubleSpinBox) and not is_enabled:
                    widget.setValue(0)
                if isinstance(widget, QDoubleSpinBox) and is_enabled:
                    widget.setValue(1.0)
                widget.setEnabled(is_enabled)
        self.validate_weightings()

    def populate_table(self):
        self.table.setRowCount(len(self.guids))
        for row, guid in enumerate(self.guids):
            item = self.tree_item.getItemByGuid(guid)
            attributes = item.attributes()
            log_message(f"Populating table for GUID: {guid}")
            log_message(f"Attributes: {item.attributesAsMarkdown()}")
            # Data Source Widget
            data_source_widget = DataSourceWidgetFactory.create_widget(
                attributes["analysis_mode"], 1, attributes
            )
            # Expand the widget to fill the available horizontal space
            data_source_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            if not data_source_widget:
                continue
            data_source_widget.data_changed.connect(self.refresh_configuration)
            default_factor_weighting = attributes.get("default_factor_weighting", 0)
            self.table.setCellWidget(row, 0, data_source_widget)
            self.data_sources[guid] = data_source_widget

            # Indicator Name
            name_item = QTableWidgetItem(attributes.get("indicator", ""))
            name_item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 1, name_item)

            # Weighting
            if self.weighting_column_visible:
                weighting_value = float(attributes.get("factor_weighting", 0.0))
                weighting_item = QDoubleSpinBox()
                weighting_item.setRange(0.0, 1.0)
                weighting_item.setDecimals(4)
                weighting_item.setSingleStep(0.01)
                weighting_item.setValue(weighting_value)
                weighting_item.valueChanged.connect(self.validate_weightings)
                self.table.setCellWidget(row, 2, weighting_item)
                self.weightings[guid] = weighting_item
                # Use (Checkbox)
                checkbox_widget = self.create_checkbox_widget(row, weighting_value)
            else:
                checkbox_widget = self.create_checkbox_widget(row, 1)
            self.table.setCellWidget(row, 3, checkbox_widget)

            # GUID
            guid_item = QTableWidgetItem(guid)
            guid_item.setFlags(Qt.ItemIsEnabled)
            guid_item.setToolTip(str(item.attributes()))
            self.table.setItem(row, 4, guid_item)

            # Reset Button
            if self.weighting_column_visible:
                reset_button = QPushButton("Reset")
                reset_button.clicked.connect(
                    lambda checked, item=weighting_item, value=default_factor_weighting: item.setValue(
                        value
                    )
                )
                self.table.setCellWidget(row, 5, reset_button)

        self.table.setColumnHidden(
            4, not self.guid_column_visible
        )  # Hide GUID column by default
        self.validate_weightings()  # Initial validation check
        # If we dont have the weightings column, we can enable the OK button
        if not self.weighting_column_visible:
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(True)

    def toggle_guid_column(self):
        """Toggle the visibility of the GUID column."""
        self.guid_column_visible = not self.guid_column_visible
        self.table.setColumnHidden(4, not self.guid_column_visible)

    def hide_widgets_in_column(self, column: int):
        """Hide all widgets in the specified column."""
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, column)
            if widget:
                widget.setVisible(False)  # Explicitly hide the widget

    def show_widgets_in_column(self, column: int):
        """Show all widgets in the specified column."""
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, column)
            if widget:
                widget.setVisible(True)  # Explicitly show the widget

    def auto_calculate_weightings(self):
        enabled_rows = [
            row for row in range(self.table.rowCount()) if self.is_checkbox_checked(row)
        ]
        if not enabled_rows:
            equal_weighting = 0.0
        else:
            equal_weighting = 1.0 / len(enabled_rows)

        for row in enabled_rows:
            widget = self.table.cellWidget(row, 2)  # Weight column
            widget.setValue(equal_weighting)
        for row in range(self.table.rowCount()):
            if row not in enabled_rows:
                widget = self.table.cellWidget(row, 2)
                widget.setValue(0)
        self.validate_weightings()

    def is_checkbox_checked(self, row: int) -> bool:
        checkbox = self.get_checkbox_in_row(row)
        return checkbox.isChecked() if checkbox else False

    def get_checkbox_in_row(self, row: int) -> QCheckBox:
        container = self.table.cellWidget(row, 3)  # Use (Checkbox) column
        if container and isinstance(container, QWidget):
            layout = container.layout()
            if layout and layout.count() > 0:
                checkbox = layout.itemAt(0).widget()
                if isinstance(checkbox, QCheckBox):
                    return checkbox
        return None

    def save_weightings_to_model(self):
        """Assign new weightings to the factor's indicators."""
        for indicator_guid, spin_box in self.weightings.items():
            try:
                new_weighting = spin_box.value()
                self.tree_item.updateIndicatorWeighting(indicator_guid, new_weighting)
            except ValueError:
                log_message(
                    f"Invalid weighting input for GUID: {indicator_guid}",
                    tag="Geest",
                    level=Qgis.Warning,
                )
                import traceback

                log_message(traceback.format_exc(), tag="Geest", level=Qgis.Warning)

    def accept_changes(self):
        """Handle the OK button by applying changes and closing the dialog."""
        self.save_weightings_to_model()
        self.accept()

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

        # Enable or disable the OK button based on the validity of the sum
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(valid_sum)
