import sys
import os
import json
# Change to this when implementing in QGIS
#from qgis.PyQt.QtWidgets import (
from qgis.PyQt.QtWidgets import (
    QAbstractItemDelegate,
    QApplication,
    QTreeView,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QMessageBox,
    QHeaderView,
    QPushButton,
    QHBoxLayout,
    QTableWidget, 
    QTableWidgetItem,
    QMenu,
    QAction,
    QDialog,
    QLabel,
    QTextEdit,
)
# Change to this when implementing in QGIS
#from qgis.PyQt.QtCore import (
from qgis.PyQt.QtCore import (
    QAbstractItemModel,
    QModelIndex,
    Qt,
    QFileSystemWatcher,
    QPoint,
    QEvent,
    QTimer,
    pyqtSignal, 
    Qt
)
# Change to this when implementing in QGIS
#from qgis.PyQt.QtGui import (
from qgis.PyQt.QtGui import QColor, QColor, QMovie

class LayerDetailDialog(QDialog):
    """Dialog to show layer properties."""
    
    # Signal to emit the updated data as a dictionary
    dataUpdated = pyqtSignal(dict)
    
    def __init__(self, layer_name, layer_data, parent=None):
        super().__init__(parent)

        self.setWindowTitle(layer_name)

        layout = QVBoxLayout()

        # Heading for the dialog
        heading_label = QLabel(layer_name)
        layout.addWidget(heading_label)

        # Description for the dialog
        description_text = QTextEdit(
            layer_data["indicator"] if "indicator" in layer_data else "")
        description_text.setReadOnly(True)
        layout.addWidget(description_text)

        # Create the QTableWidget
        self.table = QTableWidget()
        self.table.setColumnCount(2)  # Two columns (Key and Value)
        self.table.setHorizontalHeaderLabels(["Key", "Value"])

        # Set the number of rows equal to the number of key-value pairs
        self.table.setRowCount(len(layer_data))

        # Populate the table with key-value pairs
        for row, (key, value) in enumerate(layer_data.items()):
            # Column 1: Key (read-only)
            key_item = QTableWidgetItem(str(key))
            key_item.setFlags(key_item.flags() & ~Qt.ItemIsEditable)  # Make it read-only
            self.table.setItem(row, 0, key_item)
            
            # Column 2: Value (editable)
            value_item = QTableWidgetItem(str(value))
            self.table.setItem(row, 1, value_item)

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

    def on_close(self):
        """Handle the dialog close event by emitting the updated data."""
        updated_data = self.get_updated_data_from_table()
        self.dataUpdated.emit(updated_data)  # Emit the updated data as a dictionary
        self.close()

    def get_updated_data_from_table(self):
        """Convert the table back into a dictionary with any changes made."""
        updated_data = {}
        for row in range(self.table.rowCount()):
            key = self.table.item(row, 0).text()  # Get the key (read-only)
            value = self.table.item(row, 1).text()  # Get the updated value
            updated_data[key] = value  # Update the dictionary
        return updated_data