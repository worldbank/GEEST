import sys
import os
import json

# Change to this when implementing in QGIS
# from qgis.PyQt.QtWidgets import (
from qgis.PyQt.QtWidgets import (
    QAbstractItemDelegate,
    QTreeView,
    QMessageBox,
)

# Change to this when implementing in QGIS
# from qgis.PyQt.QtCore import (
from PyQt5.QtCore import (
    QAbstractItemModel,
    QModelIndex,
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

    def isFactor(self):
        return self.role == "factor"

    def getFactorAttributes(self):
        """Return the dict of indicators (or layers) under this factor."""
        attributes = {}
        if self.isFactor():
            attributes["Analysis Mode"] = "Factor Aggregation"
            attributes["id"] = self.data(0)
            attributes["Indicators"] = [
                {
                    "id": i,
                    "name": child.data(0),
                    "weighting": child.data(2),
                    "Result File": child.data(3).get("Result File", ""),
                }
                for i, child in enumerate(self.childItems)
            ]
        return attributes

    def updateIndicatorWeighting(self, indicator_id, new_weighting):
        """Update the weighting of a specific indicator."""
        try:
            indicator_item = self.childItems[indicator_id]
            indicator_item.setData(2, f"{new_weighting:.2f}")
        except IndexError:
            # Handle invalid indicator_id
            pass


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
            dimension_attributes = {}
            dimension_attributes["id"] = dimension.get("id", "")
            dimension_attributes["name"] = dimension.get("name", "")
            dimension_attributes["text"] = dimension.get("text", "")
            dimension_attributes["required"] = dimension.get("required", False)
            dimension_attributes["default_analysis_weighting"] = dimension.get(
                "default_analysis_weighting", 0.0
            )
            # We store the whole dimension object in the last column (excluding factors)
            # so that we can pull out any of the additional properties
            # from it later
            dimension_item = JsonTreeItem(
                [dimension_name, "🔴", "", dimension_attributes],
                "dimension",
                self.rootItem,  # parent
            )
            self.rootItem.appendChild(dimension_item)

            for factor in dimension.get("factors", []):
                # We store the whole factor object in the last column (excluding layers)
                # so that we can pull out any of the additional properties
                # from it later
                factor_attributes = {}
                factor_attributes["id"] = factor.get("id", "")
                factor_attributes["name"] = factor.get("name", "")
                factor_attributes["text"] = factor.get("text", "")
                factor_attributes["required"] = factor.get("required", False)
                factor_attributes["default_dimension_weighting"] = factor.get(
                    "default_analysis_weighting", 0.0
                )
                factor_item = JsonTreeItem(
                    [factor["name"], "🔴", "", factor_attributes],
                    "factor",
                    dimension_item,  # parent
                )
                dimension_item.appendChild(factor_item)

                factor_weighting_sum = 0.0

                for layer in factor.get("layers", []):

                    layer_item = JsonTreeItem(
                        # We store the whole json layer object in the last column
                        # so that we can pull out any of the additional properties
                        # from it later
                        # layer name, status, weighting, attributes
                        [layer["Layer"], "🔴", layer.get("Factor Weighting", 0), layer],
                        "layer",
                        factor_item,
                    )
                    factor_item.appendChild(layer_item)

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

        # Override the flags method to allow specific columns to be editable.

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
                json = {
                    "name": item.data(0).lower(),
                    "factors": [recurse_tree(child) for child in item.childItems],
                    "Analysis Weighting": item.data(2),
                }
                try:
                    json.update(
                        item.data(3)
                    )  # merges in the data stored in the third column
                except:
                    pass
                return json
            elif item.role == "factor":
                json = {
                    "name": item.data(0),
                    "layers": [recurse_tree(child) for child in item.childItems],
                    "Dimension Weighting": item.data(2),
                }
                try:
                    json.update(
                        item.data(3)
                    )  # merges in the data stored in the third column
                except:
                    pass
                return json
            elif item.role == "layer":
                json = item.data(3)
                json["Factor Weighting"] = item.data(2)
                return json

        json_data = {
            "dimensions": [recurse_tree(child) for child in self.rootItem.childItems]
        }
        return json_data

    def clear_factor_weightings(self, dimension_item):
        """Clear all weightings for factors under the given dimension."""
        for i in range(dimension_item.childCount()):
            factor_item = dimension_item.child(i)
            factor_item.setData(2, "0.00")
        # After clearing, update the dimension's total weighting
        dimension_item.setData(2, "0.00")
        self.update_font_color(dimension_item, QColor(Qt.red))
        self.layoutChanged.emit()

    def auto_assign_factor_weightings(self, dimension_item):
        """Auto-assign weightings evenly across all factors under the dimension."""
        num_factors = dimension_item.childCount()
        if num_factors == 0:
            return
        factor_weighting = 1 / num_factors
        for i in range(num_factors):
            factor_item = dimension_item.child(i)
            factor_item.setData(2, f"{factor_weighting:.2f}")
        # Update the dimensions's total weighting
        dimension_item.setData(2, "1.00")
        self.update_font_color(dimension_item, QColor(Qt.green))
        self.layoutChanged.emit()

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
