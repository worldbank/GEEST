import uuid
import traceback

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont, QIcon
from qgis.core import Qgis
from geest.utilities import resources_path
from geest.core import setting
from geest.utilities import log_message


class JsonTreeItem:
    """A class representing a node in the tree.

    🚩  TAKE NOTE: 🚩

    This class may NOT inherit from QObject, as it has to remain
    thread safe and not be tied to the main thread. Items are passed to
    workflow threads and must be able to be manipulated in the background.

    """

    def __init__(self, data, role, guid=None, parent=None):
        self.parentItem = parent
        self.itemData = data  # name, status, weighting, attributes(dict)
        self.childItems = []
        self.role = role  # Stores whether an item is a dimension, factor, or layer
        self.font_color = QColor(Qt.black)  # Default font color
        # Add a unique guid for each item
        if guid:
            self.guid = guid
        else:
            self.guid = str(uuid.uuid4())  # Generate a unique identifier for this item

        # Define icons for each role
        self.dimension_icon = QIcon(
            resources_path("resources", "icons", "dimension.svg")
        )
        self.factor_icon = QIcon(resources_path("resources", "icons", "factor.svg"))
        self.indicator_icon = QIcon(
            resources_path("resources", "icons", "indicator.svg")
        )

        # Define fonts for each role
        self.dimension_font = QFont()
        self.dimension_font.setBold(True)

        self.factor_font = QFont()
        self.factor_font.setItalic(True)

        self._visible = True

    def set_visibility(self, visible: bool):
        """Sets the visibility of this item."""
        self._visible = visible

    def is_visible(self) -> bool:
        """Returns the visibility status of this item."""
        return self._visible

    def is_only_child(self) -> bool:
        """Returns the only child status of this item."""
        siblings_count = len(self.parentItem.childItems)
        if siblings_count == 1:
            return True

    def internalPointer(self):
        """Returns a reference to itself, or any unique identifier for the item."""
        return self.guid

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

    def name(self):
        return self.data(0)

    def isIndicator(self):
        return self.role == "indicator"

    def isFactor(self):
        return self.role == "factor"

    def isDimension(self):
        return self.role == "dimension"

    def isAnalysis(self):
        return self.role == "analysis"

    def clear(self):
        """
        Mark the item as not run, keeping any configurations made
        """
        data = self.attributes()
        data["result"] = "Not Run"
        data["result_file"] = ""
        data["error"] = ""
        data["error_file"] = ""
        data["execution_start_time"] = ""
        data["execution_end_time"] = ""

    def disable(self):
        """
        Mark the item as disabled, which is essentially just setting its weight to zero.
        """
        data = self.attributes()
        data["analysis_mode"] = "Do Not Use"

        if self.isDimension():
            data["analysis_weighting"] = 0.0
        if self.isFactor():
            data["dimension_weighting"] = 0.0
        if self.isIndicator():
            data["factor_weighting"] = 0.0

    def enable(self):
        """
        Mark the item as enabled, which is essentially just setting its weight to its default.
        """
        data = self.attributes()
        data["analysis_mode"] = ""
        if self.isDimension():
            data["analysis_weighting"] = data["default_analysis_weighting"]
        if self.isFactor():
            data["dimension_weighting"] = data["default_dimension_weighting"]
            if self.parent().getStatus() == "Excluded from analysis":
                self.parent().attributes()[
                    "analysis_weighting"
                ] = self.parent().attribute("default_analysis_weighting")
        if self.isIndicator():
            data["factor_weighting"] = data["default_factor_weighting"]
            if self.parent().getStatus() == "Excluded from analysis":
                self.parent().attributes()[
                    "dimension_weighting"
                ] = self.parent().attribute("default_dimension_weighting")
                if self.parent().parent().getStatus() == "Excluded from analysis":
                    self.parent().parent().attributes()["analysis_weighting"] = (
                        self.parent().parent().attribute("default_analysis_weighting")
                    )

    def getIcon(self):
        """Retrieve the appropriate icon for the item based on its role."""
        if self.isDimension():
            return self.dimension_icon
        elif self.isFactor():
            return self.factor_icon
        elif self.isIndicator():
            return self.indicator_icon
        return None

    def getItemTooltip(self):
        """Retrieve the appropriate tooltip for the item based on its role."""
        data = self.attributes()
        if self.isDimension():
            description = data.get("description", "")
            if description:
                return f"{description}"
            else:
                return "Dimension"
        elif self.isFactor():
            description = data.get("description", "")
            if description:
                return f"{description}"
            else:
                return "Factor"
        elif self.isIndicator():
            error = data.get("error", None)
            if error:
                return f"Error: {data.get('error')}"
            description = data.get("description", "")
            if description:
                return f"{description}"
            else:
                return "Indicator"
        return ""

    def getStatusIcon(self):
        """Retrieve the appropriate icon for the item based on its role."""
        status = self.getStatus()

        if status == "Excluded from analysis":
            return QIcon(resources_path("resources", "icons", "excluded.svg"))
        if status == "Completed successfully":
            return QIcon(resources_path("resources", "icons", "completed-success.svg"))
        elif status == "Required and not configured":
            return QIcon(
                resources_path("resources", "icons", "required-not-configured.svg")
            )
        elif status == "Not configured (optional)":
            return QIcon(resources_path("resources", "icons", "not-configured.svg"))
        elif status == "Configured, not run":
            return QIcon(resources_path("resources", "icons", "not-run.svg"))
        elif status == "Workflow failed":
            return QIcon(resources_path("resources", "icons", "failed.svg"))
        elif status == "WRITE TOOL TIP":
            return QIcon(resources_path("resources", "icons", ".svg"))
        else:
            return QIcon(resources_path("resources", "icons", ".svg"))

    def getStatus(self):
        """Return the status of the item as single character."""
        try:
            if not type(self.itemData) == list:
                return ""
            if len(self.itemData) < 4:
                return ""

            data = self.attributes()
            # log_message(f"Data: {data}")
            status = ""

            # First check if the item weighting is 0, or its parent factor is zero
            # If so, return "Excluded from analysis"
            if self.isIndicator():
                required_by_parent = float(
                    self.parentItem.attributes().get("dimension_weighting", 0.0)
                )
                required_by_self = float(data.get("factor_weighting", 0.0))
                # log_message(
                #    f"{data.get('id')} Required by indicator: {required_by_self:.10f} and required by parent: {required_by_parent:.10f}"
                # )
                if not required_by_parent or not required_by_self:
                    # log_message(f"Excluded from analysis: {data.get('id')}")
                    return "Excluded from analysis"
                #
                # Note we avoid infinite recursion by NOT doing the checks below using the getStatus
                # method of the parent.
                #
                # if the parents dimension weighting is zero, return "Excluded from analysis"
                if not float(self.parentItem.attribute("dimension_weighting", 0.0)):
                    return "Excluded from analysis"
                # if the grand parent's analysis weighting is zero, return "Excluded from analysis"
                if not float(
                    self.parentItem.parentItem.attribute("analysis_weighting", 0.0)
                ):
                    return "Excluded from analysis"
            if self.isFactor():
                # If the dimension weighting is zero, return "Excluded from analysis"
                if not float(data.get("dimension_weighting", 0.0)):
                    return "Excluded from analysis"
                # If the sum of the indicator weightings is zero, return "Excluded from analysis"
                weight_sum = 0
                for child in self.childItems:
                    weight_sum += float(child.attribute("factor_weighting", 0.0))
                if not weight_sum:
                    return "Excluded from analysis"
                #
                # Note we avoid infinite recursion by NOT doing the checks below using the getStatus
                # method of the parent.
                #
                # if the parent's analysis weighting is zero, return "Excluded from analysis"
                if not float(self.parentItem.attribute("analysis_weighting", 0.0)):
                    return "Excluded from analysis"
            if self.isDimension():
                # If the analysis weighting is zero, return "Excluded from analysis"
                if not float(data.get("analysis_weighting", 0.0)):
                    return "Excluded from analysis"
                # If the sum of the factor weightings is zero, return "Excluded from analysis"
                weight_sum = 0
                for child in self.childItems:
                    weight_sum += float(child.attribute("dimension_weighting", 0.0))
                if not weight_sum:
                    return "Excluded from analysis"
            if self.isAnalysis():
                # If the sum of the dimension weightings is zero, return "Excluded from analysis"
                weight_sum = 0
                for child in self.childItems:
                    weight_sum += float(child.attribute("analysis_weighting", 0.0))
                if not weight_sum:
                    return "Excluded from analysis"

            if "Error" in data.get("result", ""):
                return "Workflow failed"
            if "Failed" in data.get("result", ""):
                return "Workflow failed"
            # Item required and not configured
            if "Do Not Use" in data.get("analysis_mode", "") and data.get(
                "indicator_required", False
            ):
                return "Required and not configured"
            # Item not required but not configured
            if "Do Not Use" in data.get("analysis_mode", "") and not data.get(
                "indicator_required", False
            ):
                return "Not configured (optional)"
            # Item required and not configured
            if (
                self.isIndicator()
                and (data.get("analysis_mode", "") == "")
                and data.get("indicator_required", False)
            ):
                return "Required and not configured"
            # Item not required but not configured
            if (
                self.isIndicator()
                and (data.get("analysis_mode", "") == "")
                and not data.get("indicator_required", False)
            ):
                return "Not configured (optional)"
            if "Not Run" in data.get("result", "") and not data.get("result_file", ""):
                return "Configured, not run"
            if not data.get("result", False):
                return "Configured, not run"
            if "Workflow Completed" not in data.get("result", ""):
                return "Workflow failed"
            if "Workflow Completed" in data.get("result", "") and not data.get(
                "result_file", ""
            ):
                return "Workflow failed"
            if "Workflow Completed" in data.get("result", ""):
                return "Completed successfully"
            return "WRITE TOOL TIP"

        except Exception as e:
            verbose_mode = setting("verbose_mode", False)
            if verbose_mode:
                log_message(f"Error getting status: {e}", level=Qgis.Warning)
                log_message(traceback.format_exc(), level=Qgis.Warning)
                return "WRITE TOOL TIP"

    def getFont(self):
        """Retrieve the appropriate font for the item based on its role."""
        if self.isDimension():
            return self.dimension_font
        elif self.isFactor():
            return self.factor_font
        return QFont()

    def getPaths(self) -> []:
        """Return the path of the item in the tree in the form dimension/factor/indicator.

        :return: A list of strings representing the path of the item in the tree.
        """
        path = []
        if self.isIndicator():
            path.append(
                self.parentItem.parentItem.attributes()
                .get("id", "")
                .lower()
                .replace(" ", "_")
            )
            path.append(self.parentItem.attribute("id", "").lower().replace(" ", "_"))
            path.append(self.attribute("id", "").lower().replace(" ", "_"))
        elif self.isFactor():
            path.append(self.parentItem.attribute("id", "").lower().replace(" ", "_"))
            path.append(self.attribute("id", "").lower().replace(" ", "_"))
        if self.isDimension():
            path.append(self.attribute("id", "").lower().replace(" ", "_"))
        return path

    def attributes(self):
        """Return a reference to the dict of attributes for this item.

        🚨 Beware of Side Effects! Any changes you make to the dict will be propogated
           back to the tree model.🚨
        """
        if len(self.itemData) > 3:
            return self.itemData[3]
        else:
            return {}

    def attribute(self, key, default=None):
        """Return the value of the attribute with the specified key."""
        return self.attributes().get(key, default)

    def setAttributes(self, attributes):
        """Set the attributes of the item."""
        self.itemData[3] = attributes

    def setAnalysisMode(self, mode):
        """Set the analysis mode of the item."""
        self.attributes()["analysis_mode"] = mode

    def getFactorIndicatorGuids(self):
        """Return the list of indicators under this factor."""
        guids = []
        if self.isFactor():
            guids = [child.guid for i, child in enumerate(self.childItems)]
        return guids

    def getDimensionFactorGuids(self):
        """Return the list of factors under this dimension."""
        guids = []
        if self.isDimension():
            guids = [child.guid for i, child in enumerate(self.childItems)]
        return guids
        # attributes["analysis_mode"] = "dimension_aggregation"

    def getAnalysisDimensionGuids(self):
        """Return the list of factors under this dimension."""
        guids = []
        if self.isAnalysis():
            guids = [child.guid for i, child in enumerate(self.childItems)]
        return guids
        # attributes["analysis_mode"] = "dimension_aggregation"

    def getItemByGuid(self, guid):
        """Return the item with the specified guid."""
        if self.guid == guid:
            return self
        for child in self.childItems:
            item = child.getItemByGuid(guid)
            if item:
                return item
        return None

    def updateIndicatorWeighting(self, indicator_guid, new_weighting):
        """Update the weighting of a specific indicator by its name."""
        try:
            # Search for the indicator by name
            indicator_item = self.getItemByGuid(indicator_guid)

            # If found, update the weighting
            if indicator_item:
                log_message(
                    f"Updating weighting for {indicator_guid} to {new_weighting}"
                )
                indicator_item.setData(2, f"{new_weighting:.2f}")
                # weighting references the level above (i.e. factor)
                indicator_item.attributes()["factor_weighting"] = new_weighting
            else:
                # Log if the indicator name is not found
                log_message(
                    f"Indicator '{indicator_guid}' not found.",
                    tag="Geest",
                    level=Qgis.Warning,
                )

        except Exception as e:
            # Handle any exceptions and log the error
            log_message(f"Error updating weighting: {e}", level=Qgis.Warning)

    def updateFactorWeighting(self, factor_guid, new_weighting):
        """Update the weighting of a specific factor by its guid."""
        try:
            # Search for the factor by name
            factor_item = self.getItemByGuid(factor_guid)
            # If found, update the weighting
            if factor_item:
                factor_item.setData(2, f"{new_weighting:.2f}")
                # weighting references the level above (i.e. dimension)
                factor_item.attributes()["dimension_weighting"] = new_weighting

            else:
                # Log if the factor name is not found
                log_message(
                    f"Factor '{factor_guid}' not found.",
                    tag="Geest",
                    level=Qgis.Warning,
                )

        except Exception as e:
            # Handle any exceptions and log the error
            log_message(f"Error updating weighting: {e}", level=Qgis.Warning)

    def updateDimensionWeighting(self, dimension_guid, new_weighting):
        """Update the weighting of a specific dimension by its guid."""
        try:
            # Search for the factor by name
            dimension_item = self.getItemByGuid(dimension_guid)
            # If found, update the weighting
            if dimension_item:
                dimension_item.setData(2, f"{new_weighting:.2f}")
                # weighting references the level above (i.e. analysis)
                dimension_item.attributes()["analysis_weighting"] = new_weighting

            else:
                # Log if the factor name is not found
                log_message(
                    f"Factor '{dimension_guid}' not found.",
                    tag="Geest",
                    level=Qgis.Warning,
                )

        except Exception as e:
            # Handle any exceptions and log the error
            log_message(f"Error updating weighting: {e}", level=Qgis.Warning)
