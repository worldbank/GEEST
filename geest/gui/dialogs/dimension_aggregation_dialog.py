from qgis.PyQt.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
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
from geest.utilities import resources_path


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

        self.factors = self.tree_item.getDimensionAttributes()["factors"]
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

        # Create a wordwrapped label for the dimension description
        self.description_label = QLabel(
            self.dimension_data.get("description", ""), self
        )
        self.description_label.setWordWrap(True)
        layout.addWidget(self.description_label)
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
        self.table.setRowCount(len(self.factors))
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Factor", "Weighting"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Populate the table
        for row, factor in enumerate(self.factors):
            # Display indicator name (not editable)
            factor_id = factor.get("factor_name")
            factor_weighting = factor.get("factor_weighting", 0)
            name_item = QTableWidgetItem(factor_id)
            name_item.setFlags(Qt.ItemIsEnabled)  # Make it non-editable
            self.table.setItem(row, 0, name_item)

            # Display indicator weighting in a QLineEdit for editing
            weighting_item = QLineEdit(str(factor_weighting))
            self.table.setCellWidget(row, 1, weighting_item)
            self.weightings[factor_id] = weighting_item

        layout.addWidget(self.table)

        # QDialogButtonBox setup for OK and Cancel
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

        self.setLayout(layout)
        # Initial call to update the preview with existing content
        self.update_preview()

    def assignWeightings(self):
        """Assign new weightings to the dimension's indicators."""
        for factor_id, line_edit in self.weightings.items():
            try:
                new_weighting = float(line_edit.text())
                # Update the indicator's weighting in the dimension item (use your own update logic here)
                self.tree_item.updateFactorWeighting(factor_id, new_weighting)
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
            updated_data = self.layer_data
            # Include the Markdown text from the left text edit
            updated_data["description"] = self.text_edit_left.toPlainText()
            self.dataUpdated.emit(updated_data)  # Emit the updated data as a dictionary
        self.accept()  # Close the dialog
