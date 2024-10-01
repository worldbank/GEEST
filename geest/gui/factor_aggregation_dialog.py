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
)
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtCore import Qt
from geest.utilities import resources_path


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

        self.indicators = (
            self.tree_item.getIndicators()
        )  # Assuming getIndicators returns a list of dictionaries with indicator details
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

        # Get the  parent item
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
        self.text_edit_left.setPlainText(self.factor_data.get("Text", default_text))
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
        self.table.setRowCount(len(self.indicators))
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Layer", "Weighting"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Populate the table
        for row, indicator in enumerate(self.indicators):
            # Display indicator name (not editable)
            name_item = QTableWidgetItem(indicator.get("name"))
            name_item.setFlags(Qt.ItemIsEnabled)  # Make it non-editable
            self.table.setItem(row, 0, name_item)

            # Display indicator weighting in a QLineEdit for editing
            weighting_item = QLineEdit(str(indicator.get("weighting", 0)))
            self.table.setCellWidget(row, 1, weighting_item)
            self.weightings[indicator.get("id")] = weighting_item

        layout.addWidget(self.table)

        # Buttons for OK and Cancel
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK", self)
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel", self)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)
        # Initial call to update the preview with existing content
        self.update_preview()

    def assignWeightings(self):
        """Assign new weightings to the factor's indicators."""
        for indicator_id, line_edit in self.weightings.items():
            try:
                new_weighting = float(line_edit.text())
                # Update the indicator's weighting in the factor item (use your own update logic here)
                self.tree_item.updateIndicatorWeighting(indicator_id, new_weighting)
            except ValueError:
                # Handle invalid input (non-numeric)
                pass

    def update_preview(self):
        """Update the right text edit to show a live HTML preview of the Markdown."""
        markdown_text = self.text_edit_left.toPlainText()
        # Set the rendered HTML into the right text edit
        self.text_edit_right.setMarkdown(markdown_text)
