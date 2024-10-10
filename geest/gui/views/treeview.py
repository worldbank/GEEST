import sys
import os
import json

# Change to this when implementing in QGIS
from qgis.PyQt.QtWidgets import (
    QAbstractItemDelegate,
    QTreeView,
    QMessageBox,
)

# Change to this when implementing in QGIS
from qgis.PyQt.QtCore import (
    QAbstractItemModel,
    QModelIndex,
    Qt,
)

# Change to this when implementing in QGIS
# from qgis.PyQt.QtGui import (
from PyQt5.QtGui import QColor
from qgis.core import QgsMessageLog, Qgis
from geest.utilities import resources_path
from geest.core import JsonTreeItem


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
            dimension_attributes["Analysis Mode"] = dimension.get(
                "Factor Aggregation", ""
            )
            dimension_attributes["Result"] = dimension.get("Result", "")
            dimension_attributes["Execution Start Time"] = dimension.get(
                "Execution Start Time", ""
            )
            dimension_attributes["Dimension Result File"] = dimension.get(
                "Dimension Result File", ""
            )
            dimension_attributes["Execution End Time"] = dimension.get(
                "Execution End Time", ""
            )
            status = "🔴"
            result = dimension.get("Result", "")
            if "Workflow Completed" in result:
                status = "✔️"
            dimension_item = JsonTreeItem(
                [dimension_name, status, "", dimension_attributes],
                "dimension",
                self.rootItem,  # parent
            )
            self.rootItem.appendChild(dimension_item)

            for factor in dimension.get("factors", []):
                factor_attributes = {}
                factor_attributes["id"] = factor.get("id", "")
                factor_attributes["name"] = factor.get("name", "")
                factor_attributes["text"] = factor.get("text", "")
                factor_attributes["required"] = factor.get("required", False)
                factor_attributes["default_dimension_weighting"] = factor.get(
                    "default_analysis_weighting", 0.0
                )
                factor_attributes["Analysis Mode"] = factor.get(
                    "Factor Aggregation", ""
                )
                factor_attributes["Result"] = factor.get("Result", "")
                factor_attributes["Execution Start Time"] = factor.get(
                    "Execution Start Time", ""
                )
                factor_attributes["Factor Result File"] = factor.get(
                    "Factor Result File", ""
                )
                factor_attributes["Execution End Time"] = factor.get(
                    "Execution End Time", ""
                )
                status = "🔴"
                result = factor_attributes.get("Result", "")
                if "Workflow Completed" in result:
                    status = "✔️"
                factor_item = JsonTreeItem(
                    [factor["name"], status, "", factor_attributes],
                    "factor",
                    dimension_item,  # parent
                )
                dimension_item.appendChild(factor_item)

                factor_weighting_sum = 0.0

                for indicator in factor.get("layers", []):

                    status = "🔴"
                    result = indicator.get("Indicator Result", "")
                    if "Workflow Completed" in result:
                        status = "✔️"
                    indicator_item = JsonTreeItem(
                        [
                            indicator["Layer"],
                            status,
                            indicator.get("Factor Weighting", 0),
                            indicator,
                        ],
                        "layer",
                        factor_item,
                    )

                    factor_item.appendChild(indicator_item)

                # Set the factor's total weighting
                factor_item.setData(2, f"{factor_weighting_sum:.2f}")
                self.update_font_color(
                    factor_item,
                    QColor(Qt.green if factor_weighting_sum == 1.0 else Qt.red),
                )

        self.endResetModel()

    def data(self, index, role):
        if not index.isValid():
            return None

        item = index.internalPointer()

        # Set the display text
        if role == Qt.DisplayRole:
            return item.data(index.column())

        # Set the font color for weightings
        elif role == Qt.ForegroundRole and index.column() == 2:
            return item.font_color

        # Set the icon
        elif role == Qt.DecorationRole and index.column() == 0:
            return item.get_icon()

        # Set the font
        elif role == Qt.FontRole:
            return item.get_font()

        return None

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


class JsonTreeView(QTreeView):
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
