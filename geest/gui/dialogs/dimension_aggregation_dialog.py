from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtCore import Qt
from geest.utilities import resources_path, log_message


class DimensionAggregationDialog(QDialog):
    def __init__(
        self, dimension_name, dimension_data, dimension_item, editing=False, parent=None
    ):
        super().__init__(parent)

        self.setWindowTitle(dimension_name)
        self.dimension_name = dimension_name
        self.dimension_data = dimension_data
        self.tree_item = dimension_item  # Reference to the QTreeView item to update
        self.editing = editing

        self.setWindowTitle(
            f"Edit Dimension Weightings for Dimension: {self.tree_item.data(0)}"
        )
        # Need to be refactored...
        self.guids = self.tree_item.getDimensionFactorGuids()
        self.weightings = {}  # To store the temporary weightings

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
        In this dialog you can set the weightings for each indicator in the dimension.
        """
        self.text_edit_left = QTextEdit()
        self.text_edit_left.setPlainText(
            self.dimension_data.get("description", default_text)
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

        # Table setup
        self.table = QTableWidget(self)
        self.table.setRowCount(len(self.guids))
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Factor", "Weighting"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Populate the table
        for row, guid in enumerate(self.guids):
            # Get the child indicator item from this factor
            item = self.tree_item.getItemByGuid(guid)
            attributes = item.attributes()
            # Display indicator name (not editable)
            factor_id = attributes.get("name")
            dimension_weighting = attributes.get("dimension_weighting", 0)
            name_item = QTableWidgetItem(factor_id)
            name_item.setFlags(Qt.ItemIsEnabled)  # Make it non-editable
            self.table.setItem(row, 0, name_item)

            # Display indicator weighting in a QLineEdit for editing
            weighting_item = QLineEdit(str(dimension_weighting))
            self.table.setCellWidget(row, 1, weighting_item)
            self.weightings[guid] = weighting_item

        layout.addWidget(self.table)

        # QDialogButtonBox setup for OK and Cancel
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        auto_calculate_button = QPushButton("Balance Weights")
        button_box.addButton(auto_calculate_button, QDialogButtonBox.ActionRole)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        auto_calculate_button.clicked.connect(self.auto_calculate_weightings)

        layout.addWidget(button_box)

        self.setLayout(layout)
        # Initial call to update the preview with existing content
        self.update_preview()

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

    def update_preview(self):
        """Update the right text edit to show a live HTML preview of the Markdown."""
        markdown_text = self.text_edit_left.toPlainText()
        # Set the rendered HTML into the right text edit
        self.text_edit_right.setMarkdown(markdown_text)

    def accept_changes(self):
        """Handle the OK button by applying changes and closing the dialog."""
        self.assignWeightings()  # Ensure this is called when changes are accepted
        if self.editing:
            updated_data = self.factor_data
            updated_data["description"] = self.text_edit_left.toPlainText()
            self.dataUpdated.emit(updated_data)
        self.accept()
