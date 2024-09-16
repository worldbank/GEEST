import sys
import os
import json

# Change to this when implementing in QGIS
# from qgis.PyQt.QtWidgets import (
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
# from qgis.PyQt.QtCore import (
from PyQt5.QtCore import (
    QAbstractItemModel,
    QModelIndex,
    Qt,
    QFileSystemWatcher,
    QPoint,
    QEvent,
    QTimer,
    pyqtSignal,
    Qt,
)

# Change to this when implementing in QGIS
# from qgis.PyQt.QtGui import (
from PyQt5.QtGui import QColor, QColor, QMovie


class JsonTreeItem:
    """A class representing a node in the tree."""

    def __init__(self, data, role, parent=None):
        self.parentItem = parent
        self.itemData = data
        self.childItems = []
        self.role = role  # Stores whether an item is a dimension, factor, or layer
        self.font_color = QColor(Qt.black)  # Default font color

    def appendChild(self, item):
        self.childItems.append(item)

    def child(self, row):
        return self.childItems[row]

    def childCount(self):
        return len(self.childItems)

    def columnCount(self):
        return len(self.itemData)

    def data(self, column):
        if column < len(self.itemData):
            return self.itemData[column]
        return None

    def setData(self, column, value):
        if column < len(self.itemData):
            self.itemData[column] = value
            return True
        return False

    def parent(self):
        return self.parentItem

    def row(self):
        if self.parentItem:
            return self.parentItem.childItems.index(self)
        return 0


class JsonTreeModel(QAbstractItemModel):
    """Custom QAbstractItemModel to manage JSON data."""

    def __init__(self, json_data, parent=None):
        super().__init__(parent)
        self.rootItem = JsonTreeItem(["GEEST2", "Status", "Weight"], "root")
        self.loadJsonData(json_data)
        self.original_value = None  # To store the original value before editing

    def loadJsonData(self, json_data):
        """Load JSON data into the model, showing dimensions, factors, layers, and weightings."""
        self.beginResetModel()
        self.rootItem = JsonTreeItem(["GEEST2", "Status", "Weight"], "root")

        # Process dimensions, factors, and layers
        for dimension in json_data.get("dimensions", []):
            dimension_name = dimension["name"].title()  # Show dimensions in title case
            dimension_item = JsonTreeItem(
                [dimension_name, "🔴", ""], "dimension", self.rootItem
            )
            self.rootItem.appendChild(dimension_item)

            for factor in dimension.get("factors", []):
                factor_item = JsonTreeItem(
                    [factor["name"], "🔴", ""], "factor", dimension_item
                )
                dimension_item.appendChild(factor_item)

                num_layers = len(factor.get("layers", []))
                if num_layers == 0:
                    continue

                layer_weighting = 1 / num_layers
                factor_weighting_sum = 0.0

                for layer in factor.get("layers", []):
                    try:
                        weight = layer.get("weighting", "")
                    except:
                        weight = 0.0
                    layer_item = JsonTreeItem(
                        # We store the whole json layer object in the last column
                        # so that we can pull out any of the additional properties
                        # from it later
                        [layer["layer"], "🔴", f"{layer_weighting:.2f}", weight, layer],
                        "layer",
                        factor_item,
                    )
                    factor_item.appendChild(layer_item)
                    factor_weighting_sum += layer_weighting

                # Set the factor's total weighting
                factor_item.setData(2, f"{factor_weighting_sum:.2f}")
                self.update_font_color(
                    factor_item,
                    QColor(Qt.green if factor_weighting_sum == 1.0 else Qt.red),
                )

        self.endResetModel()

    def setData(self, index, value, role=Qt.EditRole):
        """Handle editing of values in the tree."""
        if role == Qt.EditRole:
            item = index.internalPointer()
            column = index.column()

            # Allow editing for the weighting column (index 2)
            if column == 2:
                try:
                    # Ensure the value is a valid floating-point number
                    value = float(value)
                    # Update the weighting value
                    return item.setData(column, f"{value:.2f}")
                except ValueError:
                    # Show an error if the value is not valid
                    QMessageBox.critical(
                        None,
                        "Invalid Value",
                        "Please enter a valid number for the weighting.",
                    )
                    return False

            # For other columns (like the name), we allow regular editing
            return item.setData(column, value)
        return False

    def flags(self, index):
        """Allow editing of the name and weighting columns."""
       
        #Override the flags method to allow specific columns to be editable.
        
        if not index.isValid():
            return Qt.NoItemFlags
        
        item = index.internalPointer()
        # For example, only allow editing for the first and second columns
        if index.column() == 0 or index.column() == 1:
            return Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled

        return Qt.ItemIsSelectable | Qt.ItemIsEnabled        
        
    def update_font_color(self, item, color):
        """Update the font color of an item."""
        item.font_color = color
        self.layoutChanged.emit()

    def to_json(self):
        """Convert the tree structure back into a JSON document."""

        def recurse_tree(item):
            if item.role == "dimension":
                return {
                    "name": item.data(0).lower(),
                    "factors": [recurse_tree(child) for child in item.childItems],
                }
            elif item.role == "factor":
                return {
                    "name": item.data(0),
                    "layers": [recurse_tree(child) for child in item.childItems],
                }
            elif item.role == "layer":
                # TODO: Add more layer details here
                # like weighting etc.
                return {
                    "layer": item.data(0),
                    "Text": item.data(4)["Text"],
                    "Default Weighting": item.data(4)["Default Weighting"],
                    "Use Aggregate": item.data(4)["Use Aggregate"],
                    "Default Index Score": item.data(4)["Default Index Score"],
                    "Index Score": item.data(4)["Index Score"],
                    "Use default Idex Score": item.data(4)["Use default Idex Score"],
                    "Rasterise Raster": item.data(4)["Rasterise Raster"],
                    "Rasterise Polygon": item.data(4)["Rasterise Polygon"],
                    "Rasterise Polyline": item.data(4)["Rasterise Polyline"],
                    "Rasterise Point": item.data(4)["Rasterise Point"],
                    "Default Buffer Distances": item.data(4)[
                        "Default Buffer Distances"
                    ],
                    "Use Buffer point": item.data(4)["Use Buffer point"],
                    "Default pixel": item.data(4)["Default pixel"],
                    "Use Create Grid": item.data(4)["Use Create Grid"],
                    "Default Mode": item.data(4)["Default Mode"],
                    "Default Measurement": item.data(4)["Default Measurement"],
                    "Default Increments": item.data(4)["Default Increments"],
                    "Use Mode of Travel": item.data(4)["Use Mode of Travel"],
                    "source": item.data(4)["source"],
                    "indicator": item.data(4)["indicator"],
                    "query": item.data(4)["query"],
                }

        json_data = {
            "dimensions": [recurse_tree(child) for child in self.rootItem.childItems]
        }
        return json_data

    def clear_layer_weightings(self, factor_item):
        """Clear all weightings for layers under the given factor."""
        for i in range(factor_item.childCount()):
            layer_item = factor_item.child(i)
            layer_item.setData(2, "0.00")
        # After clearing, update the factor's total weighting
        factor_item.setData(2, "0.00")
        self.update_font_color(factor_item, QColor(Qt.red))
        self.layoutChanged.emit()

    def auto_assign_layer_weightings(self, factor_item):
        """Auto-assign weightings evenly across all layers under the factor."""
        num_layers = factor_item.childCount()
        if num_layers == 0:
            return
        layer_weighting = 1 / num_layers
        for i in range(num_layers):
            layer_item = factor_item.child(i)
            layer_item.setData(2, f"{layer_weighting:.2f}")
        # Update the factor's total weighting
        factor_item.setData(2, "1.00")
        self.update_font_color(factor_item, QColor(Qt.green))
        self.layoutChanged.emit()

    def add_factor(self, dimension_item):
        """Add a new factor under the given dimension."""
        new_factor = JsonTreeItem(["New Factor", "🔴", ""], "factor", dimension_item)
        dimension_item.appendChild(new_factor)
        self.layoutChanged.emit()

    def add_layer(self, factor_item):
        """Add a new layer under the given factor."""
        new_layer = JsonTreeItem(["New Layer", "🔴", "1.00"], "layer", factor_item)
        factor_item.appendChild(new_layer)
        self.layoutChanged.emit()

    def remove_item(self, item):
        """Remove the given item from its parent."""
        parent = item.parent()
        if parent:
            parent.childItems.remove(item)
        self.layoutChanged.emit()

    def rowCount(self, parent=QModelIndex()):
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()
        return parentItem.childCount()

    def columnCount(self, parent=QModelIndex()):
        return self.rootItem.columnCount()

    def data(self, index, role):
        if not index.isValid():
            return None

        item = index.internalPointer()

        if role == Qt.DisplayRole:
            return item.data(index.column())
        elif role == Qt.ForegroundRole and index.column() == 2:
            return item.font_color  # Return the custom font color

        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            item = index.internalPointer()
            return item.setData(index.column(), value)
        return False

    def flags(self, index):
        """Allow editing and drag/drop reordering of dimensions."""
        item = index.internalPointer()

        if index.column() == 0:
            if item.parentItem is None:  # Top-level dimensions
                return (
                    Qt.ItemIsSelectable
                    | Qt.ItemIsEditable
                    | Qt.ItemIsEnabled
                    | Qt.ItemIsDragEnabled
                    | Qt.ItemIsDropEnabled
                )
            else:  # Factors and layers
                return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def index(self, row, column, parent=QModelIndex()):
        """Create a QModelIndex for the specified row and column."""
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        return QModelIndex()

    def parent(self, index):
        """Return the parent of the QModelIndex."""
        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.rootItem.data(section)
        return None

    def add_dimension(self, name="New Dimension"):
        """Add a new dimension to the root and allow editing."""
        new_dimension = JsonTreeItem([name, "🔴", ""], "dimension", self.rootItem)
        self.rootItem.appendChild(new_dimension)
        self.layoutChanged.emit()

    def removeRow(self, row, parent=QModelIndex()):
        """Allow removing dimensions."""
        parentItem = self.rootItem if not parent.isValid() else parent.internalPointer()
        parentItem.childItems.pop(row)
        self.layoutChanged.emit()


class CustomTreeView(QTreeView):
    """Custom QTreeView to handle editing and reverting on Escape or focus loss."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_editing_index = None

    def edit(self, index, trigger, event):
        """Start editing the item at the given index."""
        self.current_editing_index = index
        model = self.model()
        self.original_value = model.data(
            index, Qt.DisplayRole
        )  # Store original value before editing
        return super().edit(index, trigger, event)

    def keyPressEvent(self, event):
        """Handle Escape key to cancel editing."""
        if event.key() == Qt.Key_Escape and self.current_editing_index:
            self.model().setData(
                self.current_editing_index, self.original_value, Qt.EditRole
            )
            if self.hasCurrentEditor():
                self.closeEditor(
                    self.current_editor(), QAbstractItemDelegate.RevertModelCache
                )
        else:
            super().keyPressEvent(event)

    def commitData(self, editor):
        """Handle commit data, reverting if needed."""
        if self.current_editing_index:
            super().commitData(editor)
            self.current_editing_index = None
            self.original_value = None

    def closeEditor(self, editor, hint):
        """Handle closing the editor and reverting the value on Escape or clicking elsewhere."""
        if (
            hint == QAbstractItemDelegate.RevertModelCache
            and self.current_editing_index
        ):
            self.model().setData(
                self.current_editing_index, self.original_value, Qt.EditRole
            )
        self.current_editing_index = None
        self.original_value = None
        super().closeEditor(editor, hint)
