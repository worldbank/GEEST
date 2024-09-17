import re
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHeaderView,
    QLineEdit,
    QCheckBox,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QHBoxLayout,
    QTextEdit,
    QWidget,
    QSplitter,
    QFrame,
    QRadioButton,
    QButtonGroup,
)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from .toggle_switch import ToggleSwitch


class LayerDetailDialog(QDialog):
    """Dialog to show layer properties, with a Markdown editor and preview for the 'indicator' field."""

    # Signal to emit the updated data as a dictionary
    dataUpdated = pyqtSignal(dict)

    def __init__(self, layer_name, layer_data, tree_item, editing=False, parent=None):
        super().__init__(parent)

        self.setWindowTitle(layer_name)
        self.layer_data = layer_data
        self.tree_item = tree_item  # Reference to the QTreeView item to update
        self.editing = editing
        self.radio_buttons = []  # To keep track of the radio buttons for later
        self.button_group = QButtonGroup()  # To group radio buttons
        layout = QVBoxLayout()

        # Heading for the dialog
        heading_label = QLabel(layer_name)
        layout.addWidget(heading_label)

        # Create a horizontal splitter to hold both the Markdown editor and the preview
        splitter = QSplitter(Qt.Horizontal)

        # Create the QTextEdit for Markdown editing (left side)
        self.text_edit_left = QTextEdit()
        self.text_edit_left.setPlainText(layer_data.get("Text", ""))
        self.text_edit_left.setMinimumHeight(100)  # Set at least 5 lines high
        if self.editing:
            splitter.addWidget(self.text_edit_left)

        # Create the QTextEdit for HTML preview (right side)
        self.text_edit_right = QTextEdit()
        self.text_edit_right.setReadOnly(True)  # Set as read-only for preview
        splitter.addWidget(self.text_edit_right)

        layout.addWidget(splitter)

        # Connect the Markdown editor (left) to update the preview (right) in real-time
        self.text_edit_left.textChanged.connect(self.update_preview)

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

        # Add the table to the layout
        if self.editing:
            layout.addWidget(self.table)

        # Add the configuration frame with radio buttons
        self.add_config_widgets(layout)

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.on_close)  # Connect close button to custom close handler
        layout.addWidget(close_button)

        self.setLayout(layout)

        # Initial call to update the preview with existing content
        self.update_preview()

    def populate_table(self):
        """Populate the table with all key-value pairs except 'indicator'."""
        filtered_data = {k: v for k, v in self.layer_data.items() if k != "indicator"}
        self.table.setRowCount(len(filtered_data))
        
        for row, (key, value) in enumerate(filtered_data.items()):
            # Column 1: Key (Property name, read-only)
            key_item = QTableWidgetItem(str(key))
            key_item.setFlags(key_item.flags() & ~Qt.ItemIsEditable)  # Make it read-only
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
        if "Use" in key or "Rasterise" in key:
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
        """
        Add a frame widget containing radio buttons for 'Use' attributes that are True.
        """
        frame = QFrame()
        frame_layout = QVBoxLayout()

        # Find all keys that start with 'Use' and have a value of True
        use_keys = {k: v for k, v in self.layer_data.items() if k.startswith("Use") and v}

        if use_keys:
            for i, key in enumerate(use_keys):
                radio_button = QRadioButton(key)
                self.radio_buttons.append(radio_button)
                frame_layout.addWidget(radio_button)

                # Check the first radio button by default
                if i == 0:
                    radio_button.setChecked(True)

                # Add the radio button to the button group
                self.button_group.addButton(radio_button)

                # Add a label next to the radio button with the key's name
                label = QLabel(key)
                frame_layout.addWidget(label)

        frame.setLayout(frame_layout)
        layout.addWidget(frame)

    def on_close(self):
        """Handle the dialog close event by writing the edited data back to the TreeView item."""
        updated_data = self.get_updated_data_from_table()

        # Set 'Analysis Mode' based on the selected radio button
        selected_button = self.button_group.checkedButton()
        if selected_button:
            updated_data["Analysis Mode"] = selected_button.text()

        self.dataUpdated.emit(updated_data)  # Emit the updated data as a dictionary
        self.close()

    def get_updated_data_from_table(self):
        """Convert the table back into a dictionary with any changes made, including the Markdown text."""
        updated_data = {}

        # Include the Markdown text from the left text edit
        updated_data["text"] = self.text_edit_left.toPlainText()

        # Loop through the table and collect other data
        for row in range(self.table.rowCount()):
            key = self.table.item(row, 0).text()  # Get the key (read-only)
            value_widget = self.table.cellWidget(row, 1)  # Get the widget from the second column

            if isinstance(value_widget, ToggleSwitch):
                updated_value = value_widget.isChecked()
            elif isinstance(value_widget, QCheckBox):
                updated_value = value_widget.isChecked()
            elif isinstance(value_widget, QSpinBox) or isinstance(value_widget, QDoubleSpinBox):
                updated_value = value_widget.value()
            elif isinstance(value_widget, QComboBox):
                updated_value = value_widget.currentText()
            else:
                updated_value = value_widget.text()  # Default to text value

            updated_data[key] = updated_value  # Update the dictionary with the key-value pair

        return updated_data
