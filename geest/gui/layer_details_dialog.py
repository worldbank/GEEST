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
)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from .toggle_switch import ToggleSwitch

class LayerDetailDialog(QDialog):
    """Dialog to show layer properties, with a Markdown editor for the 'indicator' field."""

    # Signal to emit the updated data as a dictionary
    dataUpdated = pyqtSignal(dict)

    def __init__(self, layer_name, layer_data, tree_item, parent=None):
        super().__init__(parent)

        self.setWindowTitle(layer_name)
        self.layer_data = layer_data
        self.tree_item = tree_item  # Reference to the QTreeView item to update

        layout = QVBoxLayout()

        # Heading for the dialog
        heading_label = QLabel(layer_name)
        layout.addWidget(heading_label)

        # Create the QTextEdit for Markdown editing
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(layer_data.get("indicator", ""))
        self.text_edit.setMinimumHeight(100)  # Set at least 5 lines high
        layout.addWidget(self.text_edit)

        # Create a layout for the toggle and label at the bottom-right of the text edit
        toggle_layout = QHBoxLayout()
        toggle_layout.addStretch()  # Push to the right

        # Add the toggle switch and "Edit" label
        self.edit_mode_toggle = ToggleSwitch(initial_value=True)
        self.edit_mode_toggle.toggled.connect(self.toggle_edit_mode)
        toggle_layout.addWidget(QLabel("Edit"))
        toggle_layout.addWidget(self.edit_mode_toggle)

        layout.addLayout(toggle_layout)

        # Set the initial mode to edit mode
        self.is_edit_mode = True

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
        layout.addWidget(self.table)

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.on_close)  # Connect close button to custom close handler
        layout.addWidget(close_button)

        self.setLayout(layout)

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

    def toggle_edit_mode(self, checked):
        """Switch between edit mode (plain text) and display mode (render as HTML)."""
        if checked:
            # In Edit Mode: Show plain text to allow Markdown writing
            self.is_edit_mode = True
            self.text_edit.setReadOnly(False)
            self.text_edit.setPlainText(self.text_edit.toPlainText())  # Reset to plain text
        else:
            # In Display Mode: Render Markdown as HTML
            self.is_edit_mode = False
            self.text_edit.setReadOnly(True)
            markdown_text = self.text_edit.toPlainText()

            # Render basic Markdown elements as HTML
            rendered_html = markdown_text.replace("# ", "<h1>").replace("\n", "<br>")
            rendered_html = rendered_html.replace("**", "<b>").replace("_", "<i>")
            self.text_edit.setHtml(rendered_html)  # Render as HTML

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

    def on_close(self):
        """Handle the dialog close event by writing the edited data back to the TreeView item."""
        updated_data = self.get_updated_data_from_table()
        self.dataUpdated.emit(updated_data)  # Emit the updated data as a dictionary

        # Write the Markdown or plain text back to the TreeView column 4
        if self.is_edit_mode:
            updated_text = self.text_edit.toPlainText()
        else:
            updated_text = self.text_edit.toHtml()
        self.tree_item.setText(4, updated_text)  # Update the TreeView item's 4th column

        self.close()

    def get_updated_data_from_table(self):
        """Convert the table back into a dictionary with any changes made."""
        updated_data = {}
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

            updated_data[key] = updated_value  # Update the dictionary
        return updated_data
