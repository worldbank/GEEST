from qgis.PyQt.QtWidgets import QRadioButton, QHBoxLayout, QWidget
from qgis.PyQt.QtCore import pyqtSignal
from qgis.core import QgsMessageLog, Qgis


class BaseDataSourceWidget(QWidget):
    """
    Abstract base class for data source selectors with internal widgets.
    """

    data_changed = pyqtSignal(dict)

    def __init__(self, attributes: dict) -> None:
        """Constructor

        Args:
            attributes (dict): A reference to the attribute set for a JSONTreeItem (stored in data(3))
        """
        super().__init__()
        self.attributes = attributes
        self.layout: QHBoxLayout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        # Log creation of widget
        QgsMessageLog.logMessage(
            "Creating DataSource Configuration Widget", tag="Geest", level=Qgis.Info
        )
        QgsMessageLog.logMessage(
            "----------------------------------", tag="Geest", level=Qgis.Info
        )
        for item in self.attributes.items():
            QgsMessageLog.logMessage(
                f"{item[0]}: {item[1]}", tag="Geest", level=Qgis.Info
            )
        QgsMessageLog.logMessage(
            "----------------------------------", tag="Geest", level=Qgis.Info
        )

        try:
            self.add_internal_widgets()  # implemented in subclasses
        except Exception as e:
            QgsMessageLog.logMessage(f"Error in add_internal_widgets: {e}", "Geest")

    def add_internal_widgets(self) -> None:
        """
        Add internal widgets; to be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement add_internal_widgets.")

    def get_data(self) -> dict:
        """
        Method to get data from internal widgets.
        To be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement get_data.")

    def update_data(self) -> None:
        """
        Gathers data from internal widgets and emits the data_changed signal.
        """
        try:
            data = self.get_data()
            self.data_changed.emit(data)
        except Exception as e:
            QgsMessageLog.logMessage(f"Error in update_data: {e}", "Geest")
