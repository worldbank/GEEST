from qgis.PyQt.QtWidgets import (
    QDialog,
    QFrame,
    QHeaderView,
    QLabel,
    QLineEdit,
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
)
from qgis.PyQt.QtGui import QPixmap, QPalette, QColor, QDoubleValidator
from qgis.PyQt.QtCore import Qt
from qgis.core import Qgis
from geest.utilities import resources_path
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

        # Initialize these dictionaries before calling populate_table
        self.guids = self.tree_item.getFactorIndicatorGuids()
        self.weightings = {}  # To store the temporary weightings
        self.data_sources = {}  # To store the temporary data sources

        # Layout setup
        layout = QVBoxLayout(self)
        self.resize(800, 600)  # Set a wider dialog size
        layout.setContentsMargins(20, 20, 20, 20)  # Add padding around the layout

        # Title label
        self.title_label = QLabel(
            "Geospatial Assessment of Women Employment and Business Opportunities in the Renewable Energy Sector",
            self,
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

        self.table = QTableWidget(self)
        configuration_widget.selection_changed.connect(self.populate_table)
        page_1_layout.addWidget(self.table)

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

        # QDialogButtonBox setup for OK, Cancel, and Switch Page
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        auto_calculate_button = QPushButton("Balance Weights")
        if len(self.guids) > 1:
            self.button_box.addButton(
                auto_calculate_button, QDialogButtonBox.ActionRole
            )

        toggle_guid_button = QPushButton("Show GUIDs")
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

        layout.addWidget(self.button_box)

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

    def populate_table(self):
        """Populate the table with data source widgets, indicator names, weightings, and GUIDs."""
        self.table.clear()
        self.table.setRowCount(len(self.guids))
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["Data Source", "Indicator", "Weight 0-1", "GUID"]
        )
        self.table.setColumnWidth(2, 80)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)

        self.guid_column_visible = False
        self.table.setColumnHidden(3, not self.guid_column_visible)
        self.weighting_column_visible = len(self.guids) > 1
        self.table.setColumnHidden(2, not self.weighting_column_visible)

        for row, guid in enumerate(self.guids):
            item = self.tree_item.getItemByGuid(guid)
            attributes = item.attributes()
            data_source_widget = DataSourceWidgetFactory.create_widget(
                attributes["analysis_mode"], 1, attributes
            )
            if data_source_widget:
                data_source_widget.setSizePolicy(
                    QSizePolicy.Expanding, QSizePolicy.Preferred
                )
                data_source_widget.setMinimumWidth(150)
                data_source_widget.setMinimumHeight(30)
                data_source_widget.setParent(self.table)
                self.table.setCellWidget(row, 0, data_source_widget)
            self.data_sources["indicator_guid"] = data_source_widget

            name_item = QTableWidgetItem(item.attribute("indicator"))
            name_item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 1, name_item)

            # Add QLineEdit for weightings with initial validation
            weighting_value = item.attribute(
                "factor_weighting", 1.0 if len(self.guids) == 1 else 0.0
            )
            weighting_item = QLineEdit(str(weighting_value))
            weighting_item.setValidator(QDoubleValidator(0.0, 1.0, 4, self))
            weighting_item.textChanged.connect(
                self.validate_weightings
            )  # Connect for real-time validation
            self.table.setCellWidget(row, 2, weighting_item)
            self.weightings[guid] = weighting_item

            guid_item = QTableWidgetItem(guid)
            guid_item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 3, guid_item)

        self.validate_weightings()  # Initial validation check

    def toggle_guid_column(self):
        """Toggle the visibility of the GUID column."""
        self.guid_column_visible = not self.guid_column_visible
        self.table.setColumnHidden(3, not self.guid_column_visible)

    def auto_calculate_weightings(self):
        """Calculate and set equal weighting for each indicator."""
        equal_weighting = 1.0 / len(self.guids)
        for guid, line_edit in self.weightings.items():
            line_edit.setText(f"{equal_weighting:.4f}")

    def assignWeightings(self):
        """Assign new weightings to the factor's indicators."""
        for indicator_guid, line_edit in self.weightings.items():
            try:
                new_weighting = float(line_edit.text())
                self.tree_item.updateIndicatorWeighting(indicator_guid, new_weighting)
            except ValueError:
                log_message(
                    f"Invalid weighting input for GUID: {indicator_guid}",
                    tag="Geest",
                    level=Qgis.Warning,
                )

    def accept_changes(self):
        """Handle the OK button by applying changes and closing the dialog."""
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
        total_weighting = sum(
            float(line_edit.text() or 0) for line_edit in self.weightings.values()
        )
        valid_sum = (
            abs(total_weighting - 1.0) < 0.001
        )  # Allow slight floating-point tolerance

        # Update button state and cell highlighting
        for line_edit in self.weightings.values():
            if valid_sum:
                line_edit.setStyleSheet(
                    "color: black;"
                )  # Reset font color to black if valid
            else:
                line_edit.setStyleSheet(
                    "color: red;"
                )  # Set font color to red if invalid

        # Enable or disable the OK button based on the validity of the sum
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(valid_sum)
