from qgis.PyQt.QtWidgets import QRadioButton, QHBoxLayout, QWidget
from qgis.PyQt.QtCore import pyqtSignal
from qgis.core import QgsMessageLog, Qgis


class BaseIndicatorWidget(QRadioButton):
    """
    Abstract base class for radio buttons with internal widgets.
    """
    data_changed = pyqtSignal(dict)

    def __init__(self, label_text: str, attributes: dict) -> None:
        super().__init__(label_text)
        self.label_text = label_text
        self.attributes = attributes
        self.container: QWidget = QWidget()
        self.layout: QHBoxLayout = QHBoxLayout(self.container)
        self.layout.addWidget(self)
        QgsMessageLog.logMessage(
            "Creating Indicator Configuration Widget", tag="Geest", level=Qgis.Info
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
            self.add_internal_widgets()
        except Exception as e:
            QgsMessageLog.logMessage(f"Error in add_internal_widgets: {e}", "Geest")

    def add_internal_widgets(self) -> None:
        """
        Add internal widgets; to be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement add_internal_widgets.")

    def get_container(self) -> QWidget:
        """
        Returns the container holding the radio button and its internal widgets.
        """
        return self.container

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
