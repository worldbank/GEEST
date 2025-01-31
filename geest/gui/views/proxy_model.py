#!/usr/bin/env python

from qgis.PyQt.QtCore import QAbstractProxyModel, QModelIndex, QObject, Qt

from geest.core import JsonTreeItem
from typing import Optional, Dict, List

"""
This proxy model provides an alternate representation of the data model
where indicators with no siblings are promoted to factor level.

Version added: 1.2
Date added: 2024-10-31
"""


class PromotionProxyModel(QAbstractProxyModel):
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.source_model: Optional[QAbstractProxyModel] = None
        self.flattened_structure: List[str] = []  # Store guids instead of QModelIndex
        self.parent_mapping: Dict[str, Optional[str]] = {}  # Map guid to parent guid
        self.guid_item_mapping: Dict[str, "JsonTreeItem"] = (
            {}
        )  # Map guid to JsonTreeItem
        self.guid_index_mapping: Dict[str, QModelIndex] = (
            {}
        )  # Map guid to QModelIndex for easy lookups
        self.promoted_mapping: Dict[str, str] = (
            {}
        )  # Map promoted child guid to its original parent's guid

    def setSourceModel(self, source_model: QAbstractProxyModel) -> None:
        if source_model is None:
            raise ValueError("source_model cannot be None")
        self.source_model = source_model
        super().setSourceModel(source_model)
        self._buildFlattenedStructure()

    def _buildFlattenedStructure(self, parent_item=None):
        if parent_item is None:
            self.flattened_structure.clear()
            self.parent_mapping.clear()
            self.guid_item_mapping.clear()
            self.guid_index_mapping.clear()
            self.promoted_mapping.clear()
            parent_item = self.source_model.rootItem
            self._buildFlattenedStructure(parent_item)

        for i in range(parent_item.childCount()):
            child_item = parent_item.child(i)
            child_guid = child_item.guid

            # Promote child if parent has only one child
            if (
                parent_item.childCount() == 1
                and parent_item is not self.source_model.rootItem
                and parent_item.role is not "analysis"
            ):
                # log_message(
                #    f"Found node with only one child {parent_item.data(0)}",
                #    "Geest",
                #    Qgis.Info,
                # )
                # Replace parent with the child
                if parent_item.role in ["factor"] and child_item.role in ["indicator"]:
                    self.flattened_structure.append(child_guid)
                    self.promoted_mapping[child_guid] = parent_item.guid
                    self.guid_item_mapping[child_guid] = child_item
                    # Create a QModelIndex for each promoted child item and store it in guid_index_mapping
                    index = self.source_model.index(
                        i,
                        0,
                        self.guid_index_mapping.get(parent_item.guid, QModelIndex()),
                    )
                    if index.isValid():
                        self.guid_index_mapping[child_guid] = index
                    # Recursively traverse all child nodes
                    self._buildFlattenedStructure(child_item)
            else:
                # Normal addition to the flattened structure
                self.flattened_structure.append(child_guid)
                self.parent_mapping[child_guid] = (
                    parent_item.guid if parent_item is not None else None
                )
                self.guid_item_mapping[child_guid] = child_item
                # Create a QModelIndex for each child item and store it in guid_index_mapping
                index = self.source_model.index(
                    i, 0, self.guid_index_mapping.get(parent_item.guid, QModelIndex())
                )
                if index.isValid():
                    self.guid_index_mapping[child_guid] = index
                # Recursively traverse all child nodes
                self._buildFlattenedStructure(child_item)

    def index(
        self, row: int, column: int, parent: QModelIndex = QModelIndex()
    ) -> QModelIndex:
        if (
            self.source_model is None
            or row < 0
            or column < 0
            or row >= len(self.flattened_structure)
        ):
            return QModelIndex()

        # Retrieve guid from the flattened structure
        guid = self.flattened_structure[row]
        item = self.guid_item_mapping[guid]
        return self.createIndex(row, column, item)

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid() or self.source_model is None:
            return QModelIndex()

        # Retrieve the item and find its parent guid
        item = index.internalPointer()
        if not hasattr(item, "guid"):
            return QModelIndex()

        # Check if this item was promoted
        parent_guid = self.promoted_mapping.get(item.guid)
        if parent_guid is None:
            parent_guid = self.parent_mapping.get(item.guid, None)

        if parent_guid is None:
            return QModelIndex()

        # Retrieve the parent QModelIndex
        parent_item = self.guid_item_mapping.get(parent_guid, None)
        if parent_item is None:
            return QModelIndex()

        parent_row = self.flattened_structure.index(parent_guid)
        return self.createIndex(parent_row, 0, parent_item)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if not parent.isValid():
            return len(self.flattened_structure)
        return 0

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if self.source_model is None:
            return 0
        # Assuming the column count is uniform across all rows
        return self.source_model.columnCount(QModelIndex())

    def mapToSource(self, proxy_index: QModelIndex) -> QModelIndex:
        if not proxy_index.isValid() or self.source_model is None:
            return QModelIndex()

        # Use the internal pointer to locate the actual JsonTreeItem
        item = proxy_index.internalPointer()
        if isinstance(item, JsonTreeItem):
            guid = item.guid
            return self.guid_index_mapping.get(guid, QModelIndex())
        return QModelIndex()

    def mapFromSource(self, source_index: QModelIndex) -> QModelIndex:
        if not source_index.isValid():
            return QModelIndex()

        item = source_index.internalPointer()
        if isinstance(item, JsonTreeItem):
            try:
                row = self.flattened_structure.index(item.guid)
                return self.createIndex(row, 0, item)
            except ValueError:
                return QModelIndex()
        return QModelIndex()

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or self.source_model is None:
            return None

        # Get the source model index using mapToSource
        source_index = self.mapToSource(index)

        if role == Qt.DisplayRole and index.column() == 0:
            # Return the data from the source model for the requested column
            return self.source_model.data(source_index, role)
        elif role == Qt.DecorationRole and index.column() == 0:
            # Return the data from the source model for the requested column
            item = index.internalPointer()
            if isinstance(item, JsonTreeItem):
                return item.getIcon()
        elif role == Qt.DisplayRole and index.column() == 1:
            return None  # We only show the icon in column 1
        elif role == Qt.DecorationRole and index.column() == 1:
            # Assuming column 1 is supposed to have an icon
            item = index.internalPointer()
            if isinstance(item, JsonTreeItem):
                return item.getStatusIcon()  # Assuming item has `status_icon_path`

        return None
