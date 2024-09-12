"""
GEEST Plugin

Author: Your Name
Copyright: 2024, Your Organization
License: GPL-3.0-only

This file is part of the GEEST QGIS Plugin. It is available under the terms of the GNU General PublicHere is the continuation of `GEEST/tree_view_model.py`:

GEEST Plugin

Author: Your Name
Copyright: 2024, Your Organization
License: GPL-3.0-only

This file is part of the GEEST QGIS Plugin. It is available under the terms of the GNU General Public License v3.0 only.
See the LICENSE file in the project root for more information.
"""

from PyQt5.QtCore import (
    QAbstractItemModel,
    Qt,
    QModelIndex,
    QVariant,
    QFileSystemWatcher,
)
from PyQt5.QtGui import QIcon
import json
from jsonschema import validate, ValidationError, SchemaError


class TreeNode:
    """
    Represents a node in the tree.
    """

    def __init__(self, name, node_type, status="orange"):
        self.name = name
        self.node_type = node_type
        self.status = status
        self.children = []
        self.parent = None
        self.task_status = "idle"  # 'idle', 'running', 'success', 'error'

    def append_child(self, child):
        child.parent = self
        self.children.append(child)

    def child(self, row):
        return self.children[row]

    def child_count(self):
        return len(self.children)

    def row(self):
        if self.parent:
            return self.parent.children.index(self)
        return 0

    def column_count(self):
        return 1


class TreeViewModel(QAbstractItemModel):
    """
    Custom model for a tree view, loaded from a JSON file.
    """

    def __init__(self, json_file, schema_files, parent=None):
        super(TreeViewModel, self).__init__(parent)
        self.root_node = TreeNode("Root", "root")
        self.json_file = json_file
        self.schema_files = schema_files
        self.load_json(json_file)

        self.file_watcher = QFileSystemWatcher([json_file], self)
        self.file_watcher.fileChanged.connect(self.reload_json)

    def validate_json(self, data):
        for node in data:
            self._validate_node(node, "group")

    def _validate_node(self, node, node_type):
        try:
            schema_path = self.schema_files[node_type]
            with open(schema_path, "r") as schema_file:
                schema = json.load(schema_file)
            validate(instance=node, schema=schema)
        except (ValidationError, SchemaError) as e:
            raise ValidationError(f"Invalid {node_type} node: {e.message}")

        if "children" in node:
            child_type = "factor" if node_type == "group" else "sub-factor"
            for child in node["children"]:
                self._validate_node(child, child_type)

    def load_json(self, json_file):
        with open(json_file, "r") as f:
            data = json.load(f)
        self.validate_json(data)
        self.setup_model_data(data, self.root_node)

    def setup_model_data(self, data, parent_node):
        parent_node.children.clear()
        for item in data:
            node = TreeNode(item["name"], item["type"], item.get("status", "orange"))
            parent_node.append_child(node)
            if "children" in item:
                self.setup_model_data(item["children"], node)
        self.layoutChanged.emit()

    def reload_json(self):
        self.load_json(self.json_file)

    def is_valid(self):
        try:
            with open(self.json_file, "r") as f:
                data = json.load(f)
            self.validate_json(data)
            return True
        except ValidationError:
            return False

    def update_node_status(self, node, status):
        node.task_status = status
        self.layoutChanged.emit()

    def data(self, index, role):
        if not index.isValid():
            return QVariant()

        node = index.internalPointer()

        if role == Qt.DisplayRole:
            return node.name
        elif role == Qt.DecorationRole:
            icons = {
                "running": QIcon("path/to/running_icon.png"),
                "success": QIcon("path/to/success_icon.png"),
                "error": QIcon("path/to/error_icon.png"),
                "idle": QIcon(f"resources/icons/{node.status}.png"),
            }
            return icons[node.task_status]
        return QVariant()

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return "Name"
        return QVariant()

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parent_node = self.root_node
        else:
            parent_node = parent.internalPointer()

        child_node = parent_node.child(row)
        if child_node:
            return self.createIndex(row, column, child_node)
        return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        child_node = index.internalPointer()
        parent_node = child_node.parent
