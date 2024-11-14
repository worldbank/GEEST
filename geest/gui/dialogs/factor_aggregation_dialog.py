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
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QDialogButtonBox,  # Import the QDialogButtonBox
)
from qgis.PyQt.QtGui import QPixmap
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

        self.setWindowTitle(
            f"Edit Aggregation Weightings for Factor: {self.tree_item.data(0)}"
        )

        self.guids = self.tree_item.getFactorIndicatorGuids()
        log_message(
            f"Creating configs and datasources for these Guids: {self.guids}",
            tag="Geest",
            level=Qgis.Info,
        )
        self.weightings = {}  # To store the temporary weightings
        self.data_sources = {}  # To store the temporary data sources
        # Layout setup
        layout = QVBoxLayout(self)
        # Make the dialog wider and add padding
        self.resize(800, 600)  # Set a wider dialog size
        layout.setContentsMargins(20, 20, 20, 20)  # Add padding around the layout

        self.title_label = QLabel(
            "Geospatial Assessment of Women Employment and Business Opportunities in the Renewable Energy Sector",
            self,
        )
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        # Get the parent item
        parent_item = self.tree_item.parent()

        # If both grandparent and parent exist, create the label
        if parent_item:
            hierarchy_label = QLabel(
                f"{parent_item.data(0)} :: {self.tree_item.data(0)}"
            )
            hierarchy_label.setStyleSheet(
                "font-size: 14px; font-weight: bold; color: gray;"
            )
            layout.addWidget(
                hierarchy_label, alignment=Qt.AlignTop
            )  # Add the label above the heading

        self.banner_label = QLabel()
        self.banner_label.setPixmap(
            QPixmap(resources_path("resources", "geest-banner.png"))
        )
        self.banner_label.setScaledContents(True)  # Allow image scaling
        self.banner_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )  # Stretch horizontally, fixed vertically

        layout.addWidget(self.banner_label)

        # Create a horizontal splitter to hold both the Markdown editor and the preview
        splitter = QSplitter(Qt.Horizontal)

        # Create the QTextEdit for Markdown editing (left side)
        default_text = """
        In this dialog you can set the weightings for each indicator in the factor.
        """
        self.text_edit_left = QTextEdit()
        self.text_edit_left.setPlainText(
            self.factor_data.get("description", default_text)
        )
        self.text_edit_left.setMinimumHeight(100)  # Set at least 5 lines high
        if self.editing:
            splitter.addWidget(self.text_edit_left)

        # Create the QTextEdit for HTML preview (right side, styled to look like a label)
        self.text_edit_right = QTextEdit()
        self.text_edit_right.setReadOnly(True)  # Set as read-only for preview
        self.text_edit_right.setFrameStyle(QFrame.NoFrame)  # Remove the frame
        self.text_edit_right.setStyleSheet(
            "background-color: transparent;"
        )  # Match form background
        splitter.addWidget(self.text_edit_right)

        layout.addWidget(splitter)

        # Connect the Markdown editor (left) to update the preview (right) in real-time
        self.text_edit_left.textChanged.connect(self.update_preview)

        # Add an expanding spacer to push content above it upwards and below it downwards
        expanding_spacer = QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        layout.addSpacerItem(expanding_spacer)

        configuration_widget = FactorConfigurationWidget(self.tree_item, self.guids)
        layout.addWidget(configuration_widget)

        # Table setup
        self.table = QTableWidget(self)
        self.populate_table()

        configuration_widget.data_changed.connect(self.populate_table)

        layout.addWidget(self.table)

        # QDialogButtonBox setup for OK and Cancel
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        auto_calculate_button = QPushButton("Balance Weights")
        if len(self.guids) > 1:
            button_box.addButton(auto_calculate_button, QDialogButtonBox.ActionRole)

        toggle_guid_button = QPushButton("Show GUIDs")
        button_box.addButton(toggle_guid_button, QDialogButtonBox.ActionRole)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        auto_calculate_button.clicked.connect(self.auto_calculate_weightings)
        toggle_guid_button.clicked.connect(self.toggle_guid_column)

        layout.addWidget(button_box)

        self.setLayout(layout)
        # Initial call to update the preview with existing content
        self.update_preview()

    def populate_table(self):
        """Populate the table with data source widgets, indicator names, weightings, and GUIDs."""
        # first clear the table of any existing widgets
        self.table.clear()
        self.table.setRowCount(len(self.guids))
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["Data Source", "Indicator", "Weighting", "GUID"]
        )
        # Set column widths: narrow weighting column and auto-resize others
        self.table.setColumnWidth(2, 80)  # Narrower "Weighting" column
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )  # Data Source
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )  # Indicator
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.Stretch
        )  # GUID column

        # GUID column visibility flag
        self.guid_column_visible = False
        self.table.setColumnHidden(3, not self.guid_column_visible)
        # Hide the weighting column if there is only one indicator
        self.weighting_column_visible = False
        if len(self.guids) > 1:
            self.weighting_column_visible = True
        self.table.setColumnHidden(2, not self.weighting_column_visible)

        for row, guid in enumerate(self.guids):
            # Get the child indicator item from this factor
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
                data_source_widget.setParent(self.table)  # Set the table as the parent

                self.table.setCellWidget(
                    row, 0, data_source_widget
                )  # Set widget in leftmost column
            else:
                log_message(
                    "Failed to create data source widget",
                    tag="Geest",
                    level=Qgis.Critical,
                )
            self.data_sources["indicator_guid"] = data_source_widget

            # Display indicator name (not editable)
            name = item.attribute("indicator")
            name_item = QTableWidgetItem(name)
            name_item.setFlags(Qt.ItemIsEnabled)  # Make it non-editable
            self.table.setItem(row, 1, name_item)

            # Display indicator weighting in a QLineEdit for editing
            # If there is only one indicator, its weighting is fixed to 1.0
            if len(self.guids) > 1:
                indicator_weighting = item.attribute("factor_weighting", 1.0)
            else:
                indicator_weighting = 1.0
            weighting_item = QLineEdit(str(indicator_weighting))
            self.table.setCellWidget(row, 2, weighting_item)
            self.weightings[guid] = weighting_item

            guid_item = QTableWidgetItem(guid)
            guid_item.setFlags(Qt.ItemIsEnabled)  # Make it non-editable
            self.table.setItem(row, 3, guid_item)

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
                # Update the indicator's weighting in the factor item (use your own update logic here)
                self.tree_item.updateIndicatorWeighting(indicator_guid, new_weighting)
            except ValueError:
                # Handle invalid input (non-numeric)
                pass

    def update_preview(self):
        """Update the right text edit to show a live HTML preview of the Markdown."""
        markdown_text = self.text_edit_left.toPlainText()
        # Set the rendered HTML into the right text edit
        self.text_edit_right.setMarkdown(markdown_text)

    def accept_changes(self):
        """Handle the OK button by applying changes and closing the dialog."""

        if self.editing:
            updated_data = self.factor_data
            # Include the Markdown text from the left text edit
            updated_data["description"] = self.text_edit_left.toPlainText()
            self.dataUpdated.emit(updated_data)  # Emit the updated data as a dictionary
        self.accept()  # Close the dialog
