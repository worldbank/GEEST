import json
import os
from qgis.PyQt.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFrame,
    QHeaderView,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QTabWidget,  # Added for tabs
    QWidget,  # Added for tab contents
)
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.core import QgsMessageLog, Qgis
from ..toggle_switch import ToggleSwitch
from geest.utilities import resources_path
from ..indicator_config_widget import IndicatorConfigWidget


class IndicatorDetailDialog(QDialog):
    """Dialog to show layer properties, with a Markdown editor and preview for the 'indicator' field."""

    # Signal to emit the updated data as a dictionary
    dataUpdated = pyqtSignal()

    def __init__(self, item, editing=False, parent=None):
        """
        Initializes the dialog with the given item and optional editing mode.

        :param item: The QTreeView item to show the properties for.
        :param editing: Whether the dialog is in editing mode (default: False).
        :param parent: The parent widget (default: None).

        Note: The item is a reference to the QTreeView item, so any changes will update the tree.

        """
        super().__init__(parent)

        self.setWindowTitle(item.name())
        # Note this is a reference to the tree item
        # any changes you make will update the tree
        self.item = item  # Reference to the QTreeView item to update
        self.attributes = self.item.data(3)  # Reference to the attributes dictionary
        self.editing = editing
        self.config_widget = None  # To hold the configuration from widget factory
        self.radio_buttons = []  # To keep track of the radio buttons for later
        self.button_group = QButtonGroup()  # To group radio buttons
        layout = QVBoxLayout()

        # Make the dialog wider and add padding
        self.resize(800, 600)  # Set a wider dialog size
        layout.setContentsMargins(20, 20, 20, 20)  # Add padding around the layout

        # Main widget with tabs
        self.tab_widget = QTabWidget()

        # Left-hand tab for Markdown editor and preview
        self.markdown_tab = QWidget()
        self.setup_markdown_tab()

        # Right-hand tab for editing properties (table)
        self.edit_tab = QWidget()
        self.setup_edit_tab()

        # Add tabs to the QTabWidget
        self.tab_widget.addTab(self.markdown_tab, "Preview")
        self.tab_widget.addTab(self.edit_tab, "Edit")

        # Show or hide the "Edit" tab based on `editing`
        self.tab_widget.setTabVisible(1, self.editing)

        # Add the tab widget to the main layout
        layout.addWidget(self.tab_widget)

        # Create a QDialogButtonBox for OK/Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_changes)  # Connect OK to accept_changes
        button_box.rejected.connect(self.reject)  # Connect Cancel to reject the dialog
        layout.addWidget(button_box, alignment=Qt.AlignBottom)  # Place at the bottom

        self.setLayout(layout)

        # Initial call to update the preview with existing content
        self.update_preview()

    def setup_markdown_tab(self):
        """Sets up the left-hand tab for the Markdown editor and preview."""
        markdown_layout = QVBoxLayout(self.markdown_tab)

        self.title_label = QLabel(
            "Geospatial Assessment of Women Employment and Business Opportunities in the Renewable Energy Sector",
            self,
        )
        self.title_label.setWordWrap(True)
        markdown_layout.addWidget(self.title_label)

        # Get the grandparent and parent items
        grandparent_item = self.item.parent().parent() if self.item.parent() else None
        parent_item = self.item.parent()

        # If both grandparent and parent exist, create the label
        if grandparent_item and parent_item:
            hierarchy_label = QLabel(
                f"{grandparent_item.data(0)} :: {parent_item.data(0)}"
            )
            hierarchy_label.setStyleSheet(
                "font-size: 14px; font-weight: bold; color: gray;"
            )
            markdown_layout.addWidget(
                hierarchy_label, alignment=Qt.AlignTop
            )  # Add the label above the heading

        # Heading for the dialog
        heading_label = QLabel(self.item.name())
        heading_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )  # Bold heading
        markdown_layout.addWidget(
            heading_label, alignment=Qt.AlignTop
        )  # Align heading at the top

        self.banner_label = QLabel()
        self.banner_label.setPixmap(
            QPixmap(resources_path("resources", "geest-banner.png"))
        )
        self.banner_label.setScaledContents(True)  # Allow image scaling
        self.banner_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )  # Stretch horizontally, fixed vertically

        markdown_layout.addWidget(self.banner_label)

        # Create a horizontal splitter to hold both the Markdown editor and the preview
        splitter = QSplitter(Qt.Horizontal)

        # Create the QTextEdit for Markdown editing (left side)
        self.text_edit_left = QTextEdit()
        self.text_edit_left.setPlainText(self.attributes.get("description", ""))
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

        markdown_layout.addWidget(splitter)

        # Connect the Markdown editor (left) to update the preview (right) in real-time
        self.text_edit_left.textChanged.connect(self.update_preview)

        # Add an expanding spacer to push content above it upwards and below it downwards
        expanding_spacer = QSpacerItem(
            20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        markdown_layout.addSpacerItem(expanding_spacer)

        # Add the configuration frame with radio buttons
        # If you are in edit mode you will not be preparing analysis
        # but rather editing the json model document
        if not self.editing:
            self.add_config_widgets(markdown_layout)

    def setup_edit_tab(self):
        """Sets up the right-hand tab for editing layer properties (table)."""
        edit_layout = QVBoxLayout(self.edit_tab)

        # Create the QTableWidget for other properties
        self.table = QTableWidget()
        self.table.setColumnCount(2)  # Two columns (Key and Value)
        self.table.setHorizontalHeaderLabels(["Property", "Value"])

        # Set the number of rows equal to the number of key-value pairs, excluding 'indicator'
        self.populate_table()

        # Set column resize mode to stretch to fill the layout
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Key column
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Value column

        edit_layout.addWidget(self.table)

    def populate_table(self):
        """Populate the table with all key-value pairs except 'indicator'."""
        filtered_data = {k: v for k, v in self.attributes.items() if k != "indicator"}
        self.table.setRowCount(len(filtered_data))

        for row, (key, value) in enumerate(filtered_data.items()):
            # Column 1: Key (Property name, read-only)
            key_item = QTableWidgetItem(str(key))
            key_item.setFlags(
                key_item.flags() & ~Qt.ItemIsEditable
            )  # Make it read-only
            self.table.setItem(row, 0, key_item)

            # Column 2: Value (use appropriate widgets based on data type)
            value_widget = self.get_widget_for_value(key, value)
            self.table.setCellWidget(row, 1, value_widget)

    def update_preview(self):
        """Update the right text edit to show a live HTML preview of the Markdown."""
        markdown_text = self.text_edit_left.toPlainText()
        # Set the rendered HTML into the right text edit
        self.text_edit_right.setMarkdown(markdown_text)

    def get_widget_for_value(self, key, value):
        """
        Returns an appropriate widget for the table based on the data type or key.
        """
        if "use" in key or "rasterise" in key:
            toggle_widget = ToggleSwitch(initial_value=bool(value))
            return toggle_widget
        elif isinstance(value, bool):
            checkbox = QCheckBox()
            checkbox.setChecked(value)
            return checkbox
        elif isinstance(value, int):
            spin_box = QSpinBox()
            spin_box.setValue(value)
            spin_box.setMaximum(99999)  # Set an arbitrary maximum value
            return spin_box
        elif isinstance(value, float):
            spin_box = QDoubleSpinBox()
            spin_box.setDecimals(3)  # Allow up to 3 decimal points
            spin_box.setValue(value)
            return spin_box
        elif isinstance(value, list) and key == "options":
            combo_box = QComboBox()
            combo_box.addItems(value)
            return combo_box
        else:
            # Use QLineEdit for other data types (default to string)
            line_edit = QLineEdit(str(value))
            return line_edit

    def add_config_widgets(self, layout):
        if not self.editing:

            self.config_widget = IndicatorConfigWidget(self.attributes)
            if self.config_widget:
                layout.addWidget(self.config_widget)
                # connect to the stateChanged signal
                # config_widget.stateChanged.connect(self.handle_config_change)
            else:
                QgsMessageLog.logMessage(
                    "No configuration widgets were created for this layer.",
                    tag="Geest",
                    level=Qgis.CRITICAL,
                )

    def handle_config_change(self, new_config):
        """Optionally handle configuration changes."""
        self.attributes = new_config
        QgsMessageLog.logMessage(
            f"LayerDetailDialog config set to: {new_config}",
            tag="Geest",
            level=Qgis.Critical,
        )

    def accept_changes(self):
        """Handle the OK button by applying changes and closing the dialog."""
        if self.editing:
            # In editing mode, the edit table is canonical
            updated_data = self.get_updated_data_from_table()
            # Update the layer data with the new data
            # This directly updates the tree item
            self.attributes = updated_data
        else:
            # Otherwise, the custom widget is canonical
            pass

        self.dataUpdated.emit()  # Emit the updated data as a dictionary
        self.accept()  # Close the dialog

    def get_updated_data_from_table(self):
        """Convert the table back into a dictionary with any changes made, including the Markdown text."""
        updated_data = self.attributes

        # Loop through the table and collect other data
        for row in range(self.table.rowCount()):
            key = self.table.item(row, 0).text()  # Get the key (read-only)
            value_widget = self.table.cellWidget(
                row, 1
            )  # Get the widget from the second column

            if isinstance(value_widget, ToggleSwitch):
                updated_value = value_widget.isChecked()
            elif isinstance(value_widget, QCheckBox):
                updated_value = value_widget.isChecked()
            elif isinstance(value_widget, QSpinBox) or isinstance(
                value_widget, QDoubleSpinBox
            ):
                updated_value = value_widget.value()
            elif isinstance(value_widget, QComboBox):
                updated_value = value_widget.currentText()
            else:
                updated_value = value_widget.text()  # Default to text value

            updated_data[key] = (
                updated_value  # Update the dictionary with the key-value pair
            )

        # Include the Markdown text from the left text edit
        updated_data["description"] = self.text_edit_left.toPlainText()

        return updated_data
