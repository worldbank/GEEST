import uuid

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
    pyqtSignal,
)
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QAbstractItemDelegate, QTreeView, QMessageBox
from qgis.PyQt.QtCore import QAbstractItemModel, QModelIndex, Qt
from qgis.core import Qgis
from geest.utilities import log_message
from geest.core import JsonTreeItem


class JsonTreeModel(QAbstractItemModel):
    collapseNodeRequested = pyqtSignal(
        object
    )  # Signal to notify the view to collapse a node

    """
    A custom tree model for managing hierarchical JSON data in a QTreeView, including an "Analysis" root item
    under which Dimensions, Factors, and Indicators are stored. Each tree item has attributes that store custom
    properties such as analysis name, description, and working folder.

    The model allows serialization back to JSON.

    Attributes:
        rootItem (JsonTreeItem): The root item of the tree model, which holds the "Analysis" item as a child.
        original_value (str or float): Stores the original value of an item before it is edited.
    """

    def __init__(self, json_data, parent=None):
        """
        Initializes the JsonTreeModel with a given JSON structure and sets up the tree hierarchy.

        Args:
            json_data (dict): The input JSON structure containing the analysis, dimensions, factors, and indicators.
            parent (QObject): Optional parent object for the model.
        """
        super().__init__(parent)
        guid = str(uuid.uuid4())
        self.rootItem = JsonTreeItem(
            ["GEEST", "Status", "Weight"], role="root", guid=guid
        )
        self.original_value = None  # To store the original value before editing
        self.loadJsonData(json_data)

    def loadJsonData(self, json_data):
        """
        Loads the JSON data into the tree model, creating a hierarchical structure with the "Analysis" node
        as the parent. Dimensions, Factors, and Indicators are nested accordingly, including deserializing UUIDs.

        The "Analysis" node contains custom attributes for the analysis name, description, and working folder.

        Args:
            json_data (dict): The JSON data representing the analysis and its hierarchical structure.
        """
        self.beginResetModel()
        self.rootItem = JsonTreeItem(["GEEST", "Status", "Weight"], "root")

        # Create the 'Analysis' parent item
        analysis_name = json_data.get("analysis_name", "Analysis")
        analysis_description = json_data.get("description", "No Description")
        analysis_cell_size_m = json_data.get("analysis_cell_size_m", 100.0)
        working_folder = json_data.get("working_folder", "Not Set")
        guid = json_data.get("guid", str(uuid.uuid4()))  # Deserialize UUID
        analysis_result = json_data.get("result", "")
        analysis_execution_start_time = json_data.get("execution_start_time", "")
        analysis_result_file = json_data.get("result_file", "")
        analysis_execution_end_time = json_data.get("execution_end_time", "")
        analysis_error = json_data.get("error", "")
        analysis_error_file = json_data.get("error_file", "")
        analysis_output_filename = json_data.get("output_filename", "WEE_Score")
        mask_mode = json_data.get("mask_mode", "None")
        buffer_distance_m = json_data.get("buffer_distance_m", 0.0)
        opportunities_mask_result_file = json_data.get(
            "opportunities_mask_result_file", ""
        )
        opportunities_mask_result = json_data.get("opportunities_mask_result", "")
        wee_by_opportunities_mask_result = json_data.get(
            "wee_by_opportunities_mask_result", ""
        )
        wee_by_opportunities_mask_result_file = json_data.get(
            "wee_by_opportunities_mask_result_file", ""
        )
        wee_by_population = json_data.get("wee_by_population", "")
        wee_by_population_subnational_aggregation = json_data.get(
            "wee_by_population_subnational_aggregation", ""
        )
        wee_score_subnational_aggregation = json_data.get(
            "wee_score_subnational_aggregation", ""
        )
        opportunities_by_wee_score_by_population_subnational_aggregation = (
            json_data.get(
                "opportunities_by_wee_score_by_population_subnational_aggregation", ""
            )
        )
        opportunities_by_wee_score_subnational_aggregation = json_data.get(
            "opportunities_by_wee_score_subnational_aggregation", ""
        )
        wee_by_population_by_opportunities_mask_result_file = json_data.get(
            "wee_by_population_by_opportunities_mask_result_file", ""
        )
        wee_by_population_by_opportunities_mask_result = json_data.get(
            "wee_by_population_by_opportunities_mask_result", ""
        )
        # Store special properties in the attributes dictionary
        analysis_attributes = {
            "analysis_name": analysis_name,
            "description": analysis_description,
            "working_folder": working_folder,
            "analysis_cell_size_m": analysis_cell_size_m,
            "result": analysis_result,
            "result_file": analysis_result_file,
            "execution_start_time": analysis_execution_start_time,
            "execution_end_time": analysis_execution_end_time,
            "error": analysis_error,
            "error_file": analysis_error_file,
            "output_filename": analysis_output_filename,
            "mask_mode": mask_mode,
            "buffer_distance_m": buffer_distance_m,
            "opportunities_mask_result_file": opportunities_mask_result_file,
            "opportunities_mask_result": opportunities_mask_result,
            "wee_by_opportunities_mask_result": wee_by_opportunities_mask_result,
            "wee_by_opportunities_mask_result_file": wee_by_opportunities_mask_result_file,
            "wee_by_population": wee_by_population,
            "wee_by_population_subnational_aggregation": wee_by_population_subnational_aggregation,
            "wee_score_subnational_aggregation": wee_score_subnational_aggregation,
            "opportunities_by_wee_score_by_population_subnational_aggregation": opportunities_by_wee_score_by_population_subnational_aggregation,
            "opportunities_by_wee_score_subnational_aggregation": opportunities_by_wee_score_subnational_aggregation,
            "wee_by_population_by_opportunities_mask_result_file": wee_by_population_by_opportunities_mask_result_file,
            "wee_by_population_by_opportunities_mask_result": wee_by_population_by_opportunities_mask_result,
        }
        for prefix in [
            "aggregation",
            "population",
            "point_mask",
            "polygon_mask",
            "raster_mask",
        ]:
            analysis_attributes[f"{prefix}_layer"] = json_data.get(
                f"{prefix}_layer", ""
            )
            analysis_attributes[f"{prefix}_layer_name"] = json_data.get(
                f"{prefix}_layer_name", ""
            )
            analysis_attributes[f"{prefix}_layer_source"] = json_data.get(
                f"{prefix}_layer_source", ""
            )
            analysis_attributes[f"{prefix}_layer_provider_type"] = json_data.get(
                f"{prefix}_layer_provider_type", ""
            )
            analysis_attributes[f"{prefix}_layer_crs"] = json_data.get(
                f"{prefix}_layer_crs", ""
            )
            analysis_attributes[f"{prefix}_layer_wkb_type"] = json_data.get(
                f"{prefix}_layer_wkb_type", ""
            )
            analysis_attributes[f"{prefix}_layer_id"] = json_data.get(
                f"{prefix}_layer_id", ""
            )
            if prefix == "raster_mask":
                analysis_attributes[f"{prefix}_raster"] = json_data.get(
                    f"{prefix}_raster", ""
                )
            else:
                analysis_attributes[f"{prefix}_shapefile"] = json_data.get(
                    f"{prefix}_shapefile", ""
                )

        # Create the "Analysis" item
        status = ""
        weighting = ""
        role = "analysis"
        analysis_item = JsonTreeItem(
            [
                "WEE Score",
                status,
                weighting,
                analysis_attributes,
            ],
            role=role,
            guid=guid,
            parent=self.rootItem,
        )
        self.rootItem.appendChild(analysis_item)

        # Process dimensions, factors, and layers under the 'Analysis' parent item
        for dimension in json_data.get("dimensions", []):
            dimension_item = self._create_dimension_item(dimension, analysis_item)

            # Process factors under each dimension
            for factor in dimension.get("factors", []):
                factor_item = self._create_factor_item(factor, dimension_item)

                # Process indicators (layers) under each factor
                for indicator in factor.get("indicators", []):
                    self._create_indicator_item(indicator, factor_item)

        self.endResetModel()

    def get_analysis_item(self):
        """
        Returns the 'Analysis' item from the tree model.

        Returns:
            JsonTreeItem: The 'Analysis' item.
        """
        return self.rootItem.child(0)

    def _create_dimension_item(self, dimension, parent_item):
        """
        Creates a new Dimension item under the specified parent item (Analysis) and populates it with custom attributes.

        Args:
            dimension (dict): The dimension data to be added to the tree.
            parent_item (JsonTreeItem): The parent item (Analysis) under which the dimension is added.

        Returns:
            JsonTreeItem: The created dimension item.
        """
        dimension_name = dimension["name"].title()  # Title case for dimensions
        dimension_attributes = {
            "id": dimension.get("id", ""),
            "output_filename": dimension.get("output_filename", ""),
            "name": dimension.get("name", ""),
            "description": dimension.get("description", ""),
            "default_analysis_weighting": dimension.get(
                "default_analysis_weighting", 0.0
            ),
            "analysis_weighting": dimension.get("analysis_weighting", 0.0),
            "analysis_mode": dimension.get("factor_aggregation", ""),
            "result": dimension.get("result", ""),
            "execution_start_time": dimension.get("execution_start_time", ""),
            "result_file": dimension.get("result_file", ""),
            "execution_end_time": dimension.get("execution_end_time", ""),
        }
        guid = dimension.get("guid", str(uuid.uuid4()))  # Deserialize UUID

        status = ""  # Will be set in the item ctor
        dimension_item = JsonTreeItem(
            [
                dimension_name,
                status,
                dimension.get("analysis_weighting", 0),
                dimension_attributes,
            ],
            role="dimension",
            guid=guid,
            parent=parent_item,
        )
        parent_item.appendChild(dimension_item)

        return dimension_item

    def _create_factor_item(self, factor, parent_item):
        """
        Creates a new Factor item under the specified Dimension item and populates it with custom attributes.

        Args:
            factor (dict): The factor data to be added to the tree.
            parent_item (JsonTreeItem): The parent item (Dimension) under which the factor is added.

        Returns:
            JsonTreeItem: The created factor item.
        """
        factor_attributes = {
            "id": factor.get("id", ""),
            "output_filename": factor.get("output_filename", ""),
            "name": factor.get("name", ""),
            "description": factor.get("description", ""),
            "default_dimension_weighting": factor.get(
                "default_dimension_weighting", 0.0
            ),
            "dimension_weighting": factor.get("dimension_weighting", 0.0),
            "analysis_mode": factor.get("factor_aggregation", ""),
            "result": factor.get("result", ""),
            "execution_start_time": factor.get("execution_start_time", ""),
            "result_file": factor.get("result_file", ""),
            "execution_end_time": factor.get("execution_end_time", ""),
        }
        status = ""  # Use item.getStatus to get after constructing the item
        guid = factor.get("guid", str(uuid.uuid4()))  # Deserialize UUID
        factor_item = JsonTreeItem(
            [
                factor["name"],
                status,
                factor.get("dimension_weighting", 0),
                factor_attributes,
            ],
            role="factor",
            guid=guid,
            parent=parent_item,
        )
        parent_item.appendChild(factor_item)

        return factor_item

    def _create_indicator_item(self, indicator, parent_item):
        """
        Creates a new Indicator (layer) item under the specified Factor item and populates it with custom attributes.

        Args:
            indicator (dict): The indicator (layer) data to be added to the tree.
            parent_item (JsonTreeItem): The parent item (Factor) under which the indicator is added.

        Returns:
            None
        """
        status = ""  # Use item.getStatus to get after constructing the item
        guid = indicator.get("guid", str(uuid.uuid4()))  # Deserialize UUID
        indicator_item = JsonTreeItem(
            [
                indicator["indicator"],
                status,
                indicator.get("factor_weighting", 0),
                indicator,
            ],
            role="indicator",
            guid=guid,
            parent=parent_item,
        )
        parent_item.appendChild(indicator_item)

    def toggle_indicator_visibility(self, visible: bool, parent_item=None):
        """
        Toggles the visibility of all indicator nodes in the tree.

        Args:
            visible (bool): Whether to show or hide the indicator nodes.
            parent_item (JsonTreeItem): Optional parent item to start from. If None, start from root.
        """

        parent_item = parent_item if parent_item else self.rootItem
        for i in range(parent_item.childCount()):
            child_item = parent_item.child(i)
            if child_item.role == "indicator":
                child_item.set_visibility(visible)
            else:
                # Recursively process children (dimensions, factors)
                self.toggle_indicator_visibility(visible, child_item)

        # Notify view about layout changes
        self.layoutChanged.emit()

    def data(self, index, role):
        """
        Provides data for the given index and role, including displaying custom attributes such as the font color,
        icons, and font style.

        Args:
            index (QModelIndex): The index for which data is requested.
            role (int): The role (e.g., Qt.DisplayRole, Qt.ForegroundRole, etc.).

        Returns:
            QVariant: The data for the given index and role.
        """
        if not index.isValid():
            return None

        item = index.internalPointer()

        # Skip rendering hidden indicators
        if not item.is_visible():
            return None

        # Existing data handling code
        if role == Qt.DisplayRole:
            return item.data(index.column())

        if role == Qt.DisplayRole:
            return item.data(index.column())
        elif role == Qt.ForegroundRole and index.column() == 2:
            return item.font_color
        elif (
            role == Qt.DecorationRole and index.column() == 0
        ):  # Icon for the name column
            return item.getIcon()
        elif (
            role == Qt.DecorationRole and index.column() == 1
        ):  # Icon for the status column
            return item.getStatusIcon()
        elif role == Qt.ToolTipRole and index.column() == 1:
            return item.getStatus()
        elif role == Qt.ToolTipRole and index.column() == 0:
            # if the item role is "indicator" then use the
            # description from its parent for the tooltip
            if item.role == "indicator":
                parent = item.parent()
                if parent and parent.role == "factor":
                    # Force it to rich text so it doen't get cut off
                    return f"<p>{parent.getItemTooltip()}</p>"
            # Analysis, dimension and factor items use their own tooltip
            # Force it to rich text so it doen't get cut off
            return f"<p>{item.getItemTooltip()}</p>"

        elif role == Qt.FontRole:
            return item.getFont()

        return None

    def setData(self, index, value, role=Qt.EditRole):
        """
        Sets the data for the specified index and role, handling value validation (e.g., ensuring weightings are numbers).

        Args:
            index (QModelIndex): The index of the item being edited.
            value (any): The new value to set.
            role (int): The role in which the value is being set (usually Qt.EditRole).

        Returns:
            bool: True if the value was successfully set, False otherwise.
        """
        if role == Qt.EditRole:
            item = index.internalPointer()
            column = index.column()

            if column == 2:  # tree_view column
                try:
                    value = float(value)
                    return item.setData(column, f"{value:.2f}")
                except ValueError:
                    QMessageBox.critical(
                        None,
                        "Invalid Value",
                        "Please enter a valid number for the weighting.",
                    )
                    return False

            return item.setData(column, value)
        return False

    def flags(self, index):
        """
        Specifies the flags for the items in the model, controlling which items can be selected and edited.

        Args:
            index (QModelIndex): The index of the item.

        Returns:
            Qt.ItemFlags: The flags that determine the properties of the item (editable, selectable, etc.).
        """
        if not index.isValid():
            return Qt.NoItemFlags

        item = index.internalPointer()
        if index.column() == 0 or index.column() == 1:
            return Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled

        return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def to_json(self):
        """
        Converts the tree structure back into a JSON document, recursively traversing the tree and including
        the custom attributes stored in `attributes` for each item. UUIDs are serialized for all items.

        Returns:
            dict: The JSON representation of the tree structure.
        """

        def recurse_tree(item):
            # Serialize each item, including UUID
            if item.role == "analysis":
                json_data = {
                    "analysis_name": item.attribute("analysis_name"),
                    "description": item.attribute("description"),
                    "working_folder": item.attribute("working_folder"),
                    "analysis_cell_size_m": item.attribute("analysis_cell_size_m"),
                    "guid": item.guid,  # Serialize UUID
                    "dimensions": [recurse_tree(child) for child in item.childItems],
                }
                json_data.update(item.attributes())
                return json_data
            elif item.role == "dimension":
                json_data = {
                    "name": item.data(0).lower(),
                    "guid": item.guid,  # Serialize UUID
                    "factors": [recurse_tree(child) for child in item.childItems],
                    "analysis_weighting": item.data(2),
                    "description": item.attribute("description"),
                }
                json_data.update(item.attributes())
                return json_data
            elif item.role == "factor":
                json_data = {
                    "name": item.data(0),
                    "guid": item.guid,  # Serialize UUID
                    "indicators": [recurse_tree(child) for child in item.childItems],
                    "dimension_weighting": item.data(2),
                }
                json_data.update(item.attributes())
                return json_data
            elif item.role == "indicator":
                json_data = item.attributes()
                json_data["factor_weighting"] = item.data(2)
                json_data["guid"] = item.guid  # Serialize UUID
                return json_data

        try:
            return recurse_tree(self.rootItem.child(0))  # Start from the root item
        except Exception as e:
            import traceback

            log_message(
                f"Error converting tree to JSON: {e}",
                tag="Geest",
                level=Qgis.Critical,
            )
            # Show the traceback tpp
            log_message(f"{traceback.format_exc()}", level=Qgis.Critical)
            raise e

    def clear_factor_weightings(self, dimension_item):
        """
        Clears all weightings for factors under the given dimension item, setting them to "0.00".
        Also updates the dimension's total weighting and font color to red.

        Args:
            dimension_item (JsonTreeItem): The dimension item whose factors will have their weightings cleared.

        Returns:
            None
        """
        for i in range(dimension_item.childCount()):
            factor_item = dimension_item.child(i)
            factor_item.setData(2, "0.00")
        # Update the dimension's total weighting
        dimension_item.setData(2, "0.00")
        self.update_font_color(dimension_item, QColor(Qt.red))
        self.layoutChanged.emit()

    def auto_assign_factor_weightings(self, dimension_item):
        """
        Automatically assigns weightings evenly across all factors under the given dimension.
        The total weighting will be divided evenly among the factors.

        Args:
            dimension_item (JsonTreeItem): The dimension item whose factors will receive auto-assigned weightings.

        Returns:
            None
        """
        num_factors = dimension_item.childCount()
        if num_factors == 0:
            return
        factor_weighting = 1 / num_factors
        for i in range(num_factors):
            factor_item = dimension_item.child(i)
            factor_item.setData(2, f"{factor_weighting:.2f}")
        # Update the dimension's total weighting
        dimension_item.setData(2, "1.00")
        # self.update_font_color(dimension_item, QColor(Qt.green))
        self.layoutChanged.emit()

    def clear_layer_weightings(self, factor_item):
        """
        Clears all weightings for layers (indicators) under the given factor item, setting them to "0.00".
        Also updates the factor's total weighting and font color to red.

        Args:
            factor_item (JsonTreeItem): The factor item whose layers will have their weightings cleared.

        Returns:
            None
        """
        for i in range(factor_item.childCount()):
            layer_item = factor_item.child(i)
            layer_item.setData(2, "0.00")
        # Update the factor's total weighting
        factor_item.setData(2, "0.00")
        self.update_font_color(factor_item, QColor(Qt.red))
        self.layoutChanged.emit()

    def auto_assign_layer_weightings(self, factor_item):
        """
        Automatically assigns weightings evenly across all layers under the given factor.
        The total weighting will be divided evenly among the layers.

        Args:
            factor_item (JsonTreeItem): The factor item whose layers will receive auto-assigned weightings.

        Returns:
            None
        """
        num_layers = factor_item.childCount()
        if num_layers == 0:
            return
        layer_weighting = 1 / num_layers
        for i in range(num_layers):
            layer_item = factor_item.child(i)
            layer_item.setData(2, f"{layer_weighting:.2f}")
        # Update the factor's total weighting
        factor_item.setData(2, "1.00")
        # self.update_font_color(factor_item, QColor(Qt.green))
        self.layoutChanged.emit()

    def add_factor(self, dimension_item):
        """
        Adds a new Factor item under the given Dimension item, allowing the user to define a new factor.

        Args:
            dimension_item (JsonTreeItem): The dimension item to which the new factor will be added.

        Returns:
            None
        """
        new_factor = JsonTreeItem(["New Factor", "x", ""], "factor", dimension_item)
        dimension_item.appendChild(new_factor)
        self.layoutChanged.emit()

    def add_indicator(self, factor_item):
        """
        Adds a new Indicator item under the given Factor item, allowing the user to define a new item.

        Args:
            factor_item (JsonTreeItem): The factor item to which the new layer will be added.

        Returns:
            None
        """
        indicator = JsonTreeItem(["New Layer", "x", "1.00"], "indicator", factor_item)
        factor_item.appendChild(indicator)
        self.layoutChanged.emit()

    def remove_item(self, item):
        """
        Removes the given item from its parent. If the item has children, they are also removed.

        Args:
            item (JsonTreeItem): The item to be removed from the tree.

        Returns:
            None
        """
        parent = item.parent()
        if parent:
            parent.childItems.remove(item)
        self.layoutChanged.emit()

    def rowCount(self, parent=QModelIndex()):
        """
        Returns the number of child items for the given parent, excluding hidden items if visibility is off.

        Args:
            parent (QModelIndex): The parent index.

        Returns:
            int: The number of visible child items under the parent.
        """
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        # Count only visible items
        return len([child for child in parentItem.childItems if child.is_visible()])

    def columnCount(self, parent=QModelIndex()):
        """
        Returns the number of columns in the model. The number of columns is fixed to match the root item.

        Args:
            parent (QModelIndex): The parent index.

        Returns:
            int: The number of columns in the model.
        """
        return self.rootItem.columnCount()

    def itemIndex(self, item: JsonTreeItem):
        """
        Searches for the item and returns its QModelIndex.

        Args:
            item (JsonTreeItem): The JsonTreeItem to search for.

        Returns:
            QModelIndex: The QModelIndex of the item with the given UUID, or an invalid QModelIndex if not found.
        """
        return self._findIndexByGuid(self.rootItem, item.guid)

    def guidIndex(self, guid):
        """
        Searches for the item with the given guid and returns its QModelIndex.

        Args:
            guid (str): The guid of the item to search for.

        Returns:
            QModelIndex: The QModelIndex of the item with the given guid, or an invalid QModelIndex if not found.
        """
        return self._findIndexByGuid(self.rootItem, guid)

    def _findIndexByGuid(self, parent_item, target_guid, parent_index=QModelIndex()):
        """
        Recursively searches for the target guid within the children of the given parent item.

        Args:
            parent_item (JsonTreeItem): The parent item to start searching from.
            target_guid (str): The GUID of the item to search for.
            parent_index (QModelIndex): The QModelIndex of the parent item.

        Returns:
            QModelIndex: The QModelIndex of the target item, or an invalid QModelIndex if not found.
        """
        for row in range(parent_item.childCount()):
            child_item = parent_item.child(row)

            # If the item's UUID matches, return its QModelIndex
            if child_item.guid == target_guid:
                return self.createIndex(row, 0, child_item)

            # Recursively search children
            child_index = self._findIndexByGuid(
                child_item, target_guid, self.createIndex(row, 0, parent_item)
            )
            if child_index.isValid():
                return child_index

        return QModelIndex()  # Return invalid QModelIndex if not found

    def index(self, row, column, parent=QModelIndex()):
        """
        Creates a QModelIndex for the specified row and column under the given parent.

        Args:
            row (int): The row of the child item.
            column (int): The column of the child item.
            parent (QModelIndex): The parent index.

        Returns:
            QModelIndex: The created index.
        """
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
        """
        Returns the parent index of the specified index.

        Args:
            index (QModelIndex): The child index.

        Returns:
            QModelIndex: The parent index.
        """
        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """
        Provides the data for the header at the given section and orientation.

        Args:
            section (int): The section (column) for which header data is requested.
            orientation (Qt.Orientation): The orientation of the header (horizontal or vertical).
            role (int): The role for which header data is requested.

        Returns:
            QVariant: The data for the header.
        """
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.rootItem.data(section)
        return None

    def add_dimension(self, name="New Dimension"):
        """
        Adds a new Dimension item to the root (under "Analysis") and allows the user to define a new dimension.

        Args:
            name (str): The name of the new dimension.

        Returns:
            None
        """
        new_dimension = JsonTreeItem([name, "x", ""], "dimension", self.rootItem)
        self.rootItem.appendChild(new_dimension)
        self.layoutChanged.emit()

    def removeRow(self, row, parent=QModelIndex()):
        """
        Removes the specified row from the model. This is primarily used for removing dimensions.

        Args:
            row (int): The row to be removed.
            parent (QModelIndex): The parent index.

        Returns:
            bool: True if the row was successfully removed, False otherwise.
        """
        parentItem = self.rootItem if not parent.isValid() else parent.internalPointer()
        parentItem.childItems.pop(row)
        self.layoutChanged.emit()


class JsonTreeView(QTreeView):
    """Custom QTreeView for Geest."""

    def __init__(self, parent=None):
        super().__init__(parent)

    def setModel(self, model: QAbstractItemModel):
        """
        Override setModel to connect signals after setting the model.

        Args:
            model (QAbstractItemModel): The model to set for the tree view.
        """
        super().setModel(model)
        # Connect the collapseNodeRequested signal after setting the model
        model.collapseNodeRequested.connect(self.collapse_node_in_view)

    def collapse_single_nodes(self, parent_item=None):
        """
        Collapses nodes with only one child, streamlining the view by hiding extra details.

        Args:
            parent_item (JsonTreeItem): The starting item for collapsing; defaults to the root.
        """
        model = self.model()
        parent_item = parent_item if parent_item else model.get_analysis_item()
        for i in range(parent_item.childCount()):
            child_item = parent_item.child(i)
            # Collapse factor nodes with only one child
            if child_item.role == "factor" and child_item.childCount() == 1:
                index = model.itemIndex(child_item)
                if index.isValid():
                    self.setExpanded(index, False)
            else:
                # Recursively handle other nodes
                self.collapse_single_nodes(child_item)

    def collapse_node_in_view(self, item):
        index = self.treeView.model().indexFromItem(item)
        self.treeView.setExpanded(index, False)

    def toggle_only_child_indicator_nodes(self):
        """Toggles visibility of indicator nodes if it has no siblings."""
        indicators_visible = self._indicators_only_child()
        self.model().toggle_indicator_visibility(not indicators_visible)

    def _indicators_only_child(self):
        """Checks if indicators are currently the only one under the parent."""
        model = self.model()
        analysis_item = model.get_analysis_item()
        for dimension in analysis_item.childItems:
            for factor in dimension.childItems:
                for indicator in factor.childItems:
                    return indicator.is_only_child()
        return True
