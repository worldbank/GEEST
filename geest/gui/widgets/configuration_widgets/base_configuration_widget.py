from abc import abstractmethod
from qgis.PyQt.QtWidgets import QRadioButton, QVBoxLayout, QWidget
from qgis.PyQt.QtCore import pyqtSignal
from qgis.core import Qgis
from geest.utilities import log_message


class BaseConfigurationWidget(QRadioButton):
    """
    Abstract base class for radio buttons with internal widgets.

    Unlike the combined widgets, this class does not offer the data source selection functionality.
    It is intended to be used from the aggregation dialogs for factors and dimensions.
    """

    data_changed = pyqtSignal(dict)

    def __init__(
        self, analysis_mode: str, attributes: dict, humanised_label: str = None
    ) -> None:
        """

        Args:
            analysis_mode (str): The analysis mode for the widget.
            attributes (dict): The json tree items attributes for the widget.
            humanised_label (str): Optional custom label for the radio button.
        """
        self.analysis_mode = analysis_mode
        if not humanised_label:
            humanised_label = analysis_mode.replace("_", " ").title()
        super().__init__(humanised_label)
        self.attributes = attributes
        self.container: QWidget = QWidget()
        self.layout: QVBoxLayout = QVBoxLayout(self.container)
        self.layout.addWidget(self)

        # Log creation of widget
        log_message(
            f"Creating Indicator Configuration Widget '{analysis_mode}' humanised as '{humanised_label}'",
            tag="Geest",
            level=Qgis.Info,
        )

        try:
            self.add_internal_widgets()
        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", "Geest")

        # Connect toggled signal to enable/disable internal widgets
        self.toggled.connect(self.on_toggled)

        # Initially disable internal widgets if not checked
        self.set_internal_widgets_enabled(self.isChecked())

    @abstractmethod
    def add_internal_widgets(self) -> None:
        """
        Add internal widgets; to be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement add_internal_widgets.")

    @abstractmethod
    def get_container(self) -> QWidget:
        """
        Returns the container holding the radio button and its internal widgets.
        """
        return self.container

    @abstractmethod
    def get_data(self) -> dict:
        """
        Method to get data from internal widgets.
        To be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement get_data.")

    @abstractmethod
    def update_data(self) -> None:
        """
        Gathers data from internal widgets and emits the data_changed signal.
        """
        if self.isChecked():
            try:
                data = self.get_data()
                if not data:
                    # In some edge cases, the widget (e.g. FeaturePerCellConfigurationWidget) may not return data
                    # but we still need to emit the signal to update the attributes
                    # to avoid breaking the datasource widget logic.
                    data = self.attributes
                data["analysis_mode"] = self.analysis_mode
                log_message(f"Data changed: {data}", "Geest")
                self.data_changed.emit(data)
            except Exception as e:
                log_message(f"Error in update_data: {e}", "Geest")

    def on_toggled(self, checked: bool) -> None:
        """
        Slot for when the radio button is toggled.
        Enables/disables internal widgets based on the radio button state.
        """
        self.set_internal_widgets_enabled(checked)

        # Emit data changed only if the radio button is checked
        if checked:
            self.update_data()

    @abstractmethod
    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets based on the radio button state.
        To be implemented by subclasses to manage their internal widgets.
        """
        raise NotImplementedError(
            "Subclasses must implement set_internal_widgets_enabled."
        )
