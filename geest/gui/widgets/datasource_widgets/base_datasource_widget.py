from abc import abstractmethod
from qgis.PyQt.QtWidgets import QHBoxLayout, QWidget
from qgis.PyQt.QtCore import pyqtSignal
from qgis.core import Qgis
from geest.utilities import log_message


class BaseDataSourceWidget(QWidget):
    """
    Abstract base class for data source selectors with internal widgets.
    """

    data_changed = pyqtSignal(dict)

    def __init__(self, widget_key: str, attributes: dict) -> None:
        """Constructor

        Args:
            widget_key (str): The key identifier for this widgets analysis_mode.
            attributes (dict): A reference to the attribute set for a JSONTreeItem (stored in attributes)
        """
        super().__init__()
        self.widget_key = widget_key
        self.attributes = attributes
        self.layout: QHBoxLayout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        # Log creation of widget
        log_message(f"Creating DataSource Configuration Widget {widget_key}")

        try:
            self.add_internal_widgets()  # implemented in subclasses
        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", level=Qgis.Critical)

    @abstractmethod
    def add_internal_widgets(self) -> None:
        """
        Add internal widgets; to be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement add_internal_widgets.")

    @abstractmethod
    def update_attributes(self):
        """
        Method to get data from internal widgets.
        To be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement get_data.")
