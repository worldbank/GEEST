from qgis.PyQt.QtCore import (
    Qt,
)

# Change to this when implementing in QGIS
# from qgis.PyQt.QtGui import (
from PyQt5.QtGui import QColor, QFont, QIcon
from qgis.core import QgsMessageLog, Qgis
from geest.utilities import resources_path


class JsonTreeItem:
    """A class representing a node in the tree.

    🚩  TAKE NOTE: 🚩

    This class may NOT inherit from QObject, as it has to remain
    thread safe and not be tied to the main thread. Items are passed to
    workflow threads and must be able to be manipulated in the background.

    """

    def __init__(self, data, role, parent=None):
        self.parentItem = parent
        self.itemData = data
        self.childItems = []
        self.role = role  # Stores whether an item is a dimension, factor, or layer
        self.font_color = QColor(Qt.black)  # Default font color

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
        if column == 3:
            QgsMessageLog.logMessage(
                f"JsonTreeItem setData: {value} for column {column} ",
                tag="Geest JsonTreeItem",
                level=Qgis.Info,
            )
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

    def isIndicator(self):
        return self.role == "layer"

    def isFactor(self):
        return self.role == "factor"

    def isDimension(self):
        return self.role == "dimension"

    def isAnalysis(self):
        return self.role == "analysis"

    def getIcon(self):
        """Retrieve the appropriate icon for the item based on its role."""
        if self.isDimension():
            return self.dimension_icon
        elif self.isFactor():
            return self.factor_icon
        elif self.isIndicator():
            return self.indicator_icon
        return None

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
                self.parentItem.parentItem.itemData[3]
                .get("id", "")
                .lower()
                .replace(" ", "_")
            )
            path.append(
                self.parentItem.itemData[3].get("id", "").lower().replace(" ", "_")
            )
            path.append(self.itemData[3].get("id", "").lower().replace(" ", "_"))
        elif self.isFactor():
            path.append(
                self.parentItem.itemData[3].get("id", "").lower().replace(" ", "_")
            )
            path.append(self.itemData[3].get("id", "").lower().replace(" ", "_"))
        if self.isDimension():
            path.append(self.itemData[3].get("id", "").lower().replace(" ", "_"))
        return path

    def getIndicatorAttributes(self):
        """Return the dict of indicators (or layers) under this factor."""
        attributes = {}
        if self.isIndicator():
            attributes["Dimension ID"] = self.parentItem.itemData[3].get("id", "")
            attributes["Factor ID"] = self.data(0)
            attributes["Indicators"] = [
                {
                    "Indicator ID": i,
                    "Indicator Name": child.data(0),
                    "Indicator Weighting": child.data(2),
                    "Indicator Result File": child.data(3).get(
                        "Indicator Result File", ""
                    ),
                }
                for i, child in enumerate(self.childItems)
            ]
        return attributes

    def getFactorAttributes(self):
        """Return the dict of indicators (or layers) under this factor."""
        attributes = {}
        if self.isFactor():
            attributes["Dimension ID"] = self.parentItem.itemData[3].get("id", "")
            attributes["Analysis Mode"] = "Factor Aggregation"
            attributes["Factor ID"] = self.data(0)
            attributes["Indicators"] = [
                {
                    "Indicator ID": i,
                    "Indicator Name": child.data(0),
                    "Indicator Weighting": child.data(2),
                    "Indicator Result File": child.data(3).get(
                        "Indicator Result File", ""
                    ),
                }
                for i, child in enumerate(self.childItems)
            ]
        return attributes

    def getDimensionAttributes(self):
        """Return the dict of factors under this dimension."""
        attributes = {}
        if self.isDimension():
            attributes["Analysis Mode"] = "Dimension Aggregation"
            attributes["Dimension ID"] = self.data(0)
            attributes["Factors"] = [
                {
                    "Factor ID": i,
                    "Factor Name": child.data(0),
                    "Factor Weighting": child.data(2),
                    "Factor Result File": child.data(3).get(f"Factor Result File", ""),
                }
                for i, child in enumerate(self.childItems)
            ]
        return attributes

    def getAnalysisAttributes(self):
        """Return the dict of dimensions under this analysis."""
        attributes = {}
        if self.isAnalysis():
            attributes["Analysis Name"] = self.data(3).get("Analysis Name", "Not Set")
            attributes["Description"] = self.data(3).get(
                "Analysis Description", "Not Set"
            )
            attributes["Working Folder"] = self.data(3).get("Working Folder", "Not Set")

            attributes["Dimensions"] = [
                {
                    "Dimension ID": i,
                    "Dimension Name": child.data(0),
                    "Dimension Weighting": child.data(2),
                    "Dimension Result File": child.data(3).get(
                        f"Dimension Result File", ""
                    ),
                }
                for i, child in enumerate(self.childItems)
            ]
        return attributes

    def updateIndicatorWeighting(self, indicator_name, new_weighting):
        """Update the weighting of a specific indicator by its name."""
        try:
            # Search for the indicator by name
            indicator_item = next(
                (child for child in self.childItems if child.data(0) == indicator_name),
                None,
            )

            # If found, update the weighting
            if indicator_item:
                indicator_item.setData(2, f"{new_weighting:.2f}")
            else:
                # Log if the indicator name is not found
                QgsMessageLog.logMessage(
                    f"Indicator '{indicator_name}' not found.",
                    tag="Geest",
                    level=Qgis.Warning,
                )

        except Exception as e:
            # Handle any exceptions and log the error
            QgsMessageLog.logMessage(
                f"Error updating weighting: {e}", tag="Geest", level=Qgis.Warning
            )
