from qgis.PyQt.QtWidgets import (
    QDialog,
    QFrame,
    QHeaderView,
    QLabel,
    QDoubleSpinBox,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QDialogButtonBox,
    QWidget,
    QCheckBox,
    QHBoxLayout,
)
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtCore import Qt
from qgis.core import Qgis
from geest.utilities import resources_path, setting
from ..datasource_widget_factory import DataSourceWidgetFactory
from ..widgets.datasource_widgets.base_datasource_widget import BaseDataSourceWidget
from ..factor_configuration_widget import FactorConfigurationWidget
from geest.utilities import log_message


class FactorAggregationDialog(QDialog):
    def __init__(
        self, factor_name, factor_data, factor_item, editing=False, parent=None
    ):
        super().__init__(parent)

        self.setWindowTitle(factor_name)
        self.factor_name = factor_name
        self.factor_data = factor_data
        self.tree_item = factor_item  # Reference to the QTreeView item to update
        self.editing = editing

        # Initialize dictionaries
        self.guids = self.tree_item.getFactorIndicatorGuids()
        self.weightings = {}  # Temporary weightings
        self.data_sources = {}  # Temporary data sources

        self.weighting_column_visible = len(self.guids) > 1

        # Layout setup
        layout = QVBoxLayout(self)
        self.resize(800, 600)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title label
        self.title_label = QLabel(
            "Geospatial Assessment of Women Employment and Business Opportunities in the Renewable Energy Sector"
        )
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

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

        # Banner label
        self.banner_label = QLabel()
        self.banner_label.setPixmap(
            QPixmap(resources_path("resources", "geest-banner.png"))
        )
        self.banner_label.setScaledContents(True)
        self.banner_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.banner_label)

        # Description label
        description_label = QLabel()
        description_label.setText(self.factor_data.get("description", ""))
        description_label.setWordWrap(True)
        layout.addWidget(description_label)

        # Create the QStackedWidget and pages
        self.stacked_widget = QStackedWidget()

        # Page 1 (default): Configuration widget and table
        page_1_layout = QVBoxLayout()
        configuration_widget = FactorConfigurationWidget(self.tree_item, self.guids)
        page_1_layout.addWidget(configuration_widget)

        configuration_widget.selection_changed.connect(self.populate_table)

        # Add page 1 layout to a container widget and set it in stacked_widget
        page_1_container = QWidget()
        page_1_container.setLayout(page_1_layout)
        self.stacked_widget.addWidget(page_1_container)

        # Page 2: Splitter, text edits, and expanding spacer
        page_2_layout = QVBoxLayout()

        splitter = QSplitter(Qt.Horizontal)
        self.text_edit_left = QTextEdit()
        self.text_edit_left.setPlainText(self.factor_data.get("description", ""))
        self.text_edit_left.setMinimumHeight(100)  # Set at least 5 lines high
        splitter.addWidget(self.text_edit_left)

        self.text_edit_right = QTextEdit()
        self.text_edit_right.setReadOnly(True)
        self.text_edit_right.setFrameStyle(QFrame.NoFrame)
        self.text_edit_right.setStyleSheet("background-color: transparent;")
        splitter.addWidget(self.text_edit_right)

        page_2_layout.addWidget(splitter)

        expanding_spacer = QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        page_2_layout.addSpacerItem(expanding_spacer)

        # Add page 2 layout to a container widget and set it in stacked_widget
        page_2_container = QWidget()
        page_2_container.setLayout(page_2_layout)
        self.stacked_widget.addWidget(page_2_container)

        # Add the stacked widget to the main layout
        layout.addWidget(self.stacked_widget)

        # Table setup
        self.table = QTableWidget(self)
        self.table.setRowCount(len(self.guids))
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Source", "Indicator", "Weight 0-1", "Use", "GUID", ""]
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
        self.table.setColumnHidden(2, not self.weighting_column_visible)
        self.table.setColumnHidden(5, not self.weighting_column_visible)

        layout.addWidget(self.table)

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
        if self.editing:
            self.switch_page_button = QPushButton("Edit Description")
            self.button_box.addButton(
                self.switch_page_button, QDialogButtonBox.ActionRole
            )
            self.switch_page_button.clicked.connect(self.switch_page)

        self.button_box.accepted.connect(self.accept_changes)
        self.button_box.rejected.connect(self.reject)
        auto_calculate_button.clicked.connect(self.auto_calculate_weightings)

        toggle_guid_button.clicked.connect(self.toggle_guid_column)
        self.guid_column_visible = False  # Track GUID column visibility

        layout.addWidget(self.button_box)
        self.populate_table()
        self.validate_weightings()

        # Initial call to update the preview with existing content
        self.update_preview()

        # Connect the Markdown editor to update preview
        self.text_edit_left.textChanged.connect(self.update_preview)
        self.setLayout(layout)
        self.populate_table()  # Populate the table after initializing data_sources and weightings

    def switch_page(self):
        """Switch to the next page in the stacked widget."""
        current_index = self.stacked_widget.currentIndex()
        self.stacked_widget.setCurrentIndex(1 - current_index)  # Toggle between 0 and 1

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
                widget.setEnabled(is_enabled)
        self.validate_weightings()

    def populate_table(self):
        self.table.setRowCount(len(self.guids))
        for row, guid in enumerate(self.guids):
            item = self.tree_item.getItemByGuid(guid)
            attributes = item.attributes()

            # Data Source Widget
            data_source_widget = DataSourceWidgetFactory.create_widget(
                attributes["analysis_mode"], 1, attributes
            )
            default_indicator_factor_weighting = attributes.get(
                "default_indicator_factor_weighting", 0
            )
            self.table.setCellWidget(row, 0, data_source_widget)
            self.data_sources[guid] = data_source_widget

            # Indicator Name
            name_item = QTableWidgetItem(attributes.get("indicator", ""))
            name_item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 1, name_item)

            # Weighting
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
            self.table.setCellWidget(row, 3, checkbox_widget)

            # GUID
            guid_item = QTableWidgetItem(guid)
            guid_item.setFlags(Qt.ItemIsEnabled)
            guid_item.setToolTip(str(item.attributes()))
            self.table.setItem(row, 4, guid_item)

            # Reset Button
            reset_button = QPushButton("Reset")
            reset_button.clicked.connect(
                lambda checked, item=weighting_item, value=default_indicator_factor_weighting: item.setValue(
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

    def saveWeightingsToModel(self):
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
        self.saveWeightingsToModel()
        if self.editing:
            updated_data = self.factor_data
            updated_data["description"] = self.text_edit_left.toPlainText()
            self.dataUpdated.emit(updated_data)
        self.accept()

    def update_preview(self):
        """Update the right text edit to show a live HTML preview of the Markdown."""
        markdown_text = self.text_edit_left.toPlainText()
        self.text_edit_right.setMarkdown(markdown_text)

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

        # Update button state and cell highlighting
        for spin_box in self.weightings.values():
            if valid_sum:
                spin_box.setStyleSheet(
                    "color: black;"
                )  # Reset font color to black if valid
            else:
                spin_box.setStyleSheet(
                    "color: red;"
                )  # Set font color to red if invalid

        # Enable or disable the OK button based on the validity of the sum
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(valid_sum)
