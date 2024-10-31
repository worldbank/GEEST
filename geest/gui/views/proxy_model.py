#!/usr/bin/env python

from qgis.PyQt.QtCore import QAbstractProxyModel, QModelIndex, QObject
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
        self.flattened_structure: List[QModelIndex] = []
        self.parent_mapping: Dict[int, int] = {}

    def setSourceModel(self, source_model: QAbstractProxyModel) -> None:
        if source_model is None:
            raise ValueError("source_model cannot be None")
        self.source_model = source_model
        super().setSourceModel(source_model)
        self._buildFlattenedStructure()

    def _buildFlattenedStructure(self):
        """Build a flattened representation of the source model."""
        self.flattened_structure.clear()
        self.parent_mapping.clear()

        def _traverse(parent: QModelIndex, parent_flat_index: int):
            row_count = self.source_model.rowCount(parent)
            if row_count == 1:
                # Promote single child to parent level
                child = self.source_model.index(0, 0, parent)
                self.flattened_structure.append(child)
                current_index = len(self.flattened_structure) - 1
                self.parent_mapping[current_index] = parent_flat_index
                _traverse(child, current_index)
            else:
                for row in range(row_count):
                    child = self.source_model.index(row, 0, parent)
                    self.flattened_structure.append(child)
                    current_index = len(self.flattened_structure) - 1
                    self.parent_mapping[current_index] = parent_flat_index
                    _traverse(child, current_index)

        # Start with the root items
        _traverse(QModelIndex(), -1)

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

        if not parent.isValid():
            # Root level index
            if row < len(self.flattened_structure):
                source_index = self.flattened_structure[row]
                return self.createIndex(row, column, source_index.internalPointer())
            return QModelIndex()

        # Non-root level index, find it using flattened structure
        parent_flat_index = self.parent_mapping.get(parent.row(), -1)
        for idx, flat_parent in self.parent_mapping.items():
            if flat_parent == parent_flat_index and row == idx:
                source_index = self.flattened_structure[idx]
                return self.createIndex(row, column, source_index.internalPointer())
        return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid() or self.source_model is None:
            return QModelIndex()

        flat_index = index.row()
        parent_flat_index = self.parent_mapping.get(flat_index, -1)

        if parent_flat_index == -1:
            return QModelIndex()  # No parent (root level)

        source_index = self.flattened_structure[parent_flat_index]
        return self.createIndex(parent_flat_index, 0, source_index.internalPointer())

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

        flat_index = proxy_index.row()
        if flat_index < len(self.flattened_structure):
            return self.flattened_structure[flat_index]
        return QModelIndex()

    def mapFromSource(self, source_index: QModelIndex) -> QModelIndex:
        if not source_index.isValid():
            return QModelIndex()

        try:
            flat_index = self.flattened_structure.index(source_index)
            return self.createIndex(flat_index, 0, source_index.internalPointer())
        except ValueError:
            return QModelIndex()
