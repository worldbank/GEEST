from abc import abstractmethod
from qgis.PyQt.QtWidgets import QRadioButton, QVBoxLayout, QWidget, QSizePolicy
from qgis.PyQt.QtCore import pyqtSignal
from qgis.core import Qgis
from geest.utilities import log_message


class BaseConfigurationWidget(QWidget):
    """
    Abstract base class for radio buttons with internal widgets.

    Unlike the combined widgets, this class does not offer the data source selection functionality.
    It is intended to be used from the aggregation dialogs for factors and dimensions.
    """

    data_changed = pyqtSignal(dict)

    def __init__(
        self,
        analysis_mode: str,
        attributes: dict,
        humanised_label: str = None,
        parent: QWidget = None,
    ) -> None:
        """

        Args:
            analysis_mode (str): The analysis mode for the widget.
            attributes (dict): The json tree items attributes for the widget.
            humanised_label (str): Optional custom label for the radio button.
        """
        super().__init__(parent)
        self.analysis_mode = analysis_mode
        if not humanised_label:
            humanised_label = analysis_mode.replace("_", " ").title()

        self.attributes = attributes
        # Main layout
        self.layout: QVBoxLayout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Radio button
        self.radio_button: QRadioButton = QRadioButton(humanised_label, self)
        self.layout.addWidget(self.radio_button)

        # Internal container for the internal widgets
        self.internal_container: QWidget = QWidget(self)
        self.internal_container.setVisible(False)  # Initially hidden
        self.internal_container.setSizePolicy(
            QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        )
        self.internal_layout: QVBoxLayout = QVBoxLayout(self.internal_container)
        self.internal_layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.internal_container)

        # Signal handling
        self.radio_button.toggled.connect(self.on_toggled)

        # Log creation of widget
        log_message(
            f"Creating Indicator Configuration Widget '{analysis_mode}' humanised as '{humanised_label}'"
        )

        try:
            self.add_internal_widgets()
        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", level=Qgis.Critical)
            import traceback

            log_message(traceback.format_exc(), level=Qgis.Critical)

    def isChecked(self) -> bool:
        """
        Return whether the radio button is checked.
        """
        return self.radio_button.isChecked()

    def setChecked(self, checked: bool):
        """
        Set the radio button's checked state.
        """
        self.radio_button.setChecked(checked)

    @abstractmethod
    def add_internal_widgets(self) -> None:
        """
        Add internal widgets; to be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement add_internal_widgets.")

    @abstractmethod
    def get_data(self) -> dict:
        """
        Method to get data from internal widgets.
        To be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement get_data.")

    @abstractmethod
    def update_widgets(self, attributes: dict) -> None:
        """
        Updates the internal widgets with the current attributes.
        To be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement update_widgets.")

    def update_data(self) -> None:
        """
        Gathers data from internal widgets and emits the data_changed signal.
        """
        log_message("Update data called.......checking checked status")
        if self.isChecked():
            try:
                data = self.get_data()
                if not data:
                    # In some edge cases, the widget (e.g. FeaturePerCellConfigurationWidget) may not return data
                    # but we still need to emit the signal to update the attributes
                    # to avoid breaking the datasource widget logic.
                    data = self.attributes
                data["analysis_mode"] = self.analysis_mode
                log_message(f"\nData changed:\n\n********\n {data}\n\n********")
                self.data_changed.emit(data)
            except Exception as e:
                log_message(f"Error in update_data: {e}", level=Qgis.Critical)
                import traceback

                log_message(traceback.format_exc(), level=Qgis.Critical)

    def on_toggled(self, checked: bool) -> None:
        """
        Slot for when the radio button is toggled.
        Enables/disables internal widgets based on the radio button state.
        """
        log_message(f"Radio button toggled: {checked}")
        # self.set_internal_widgets_enabled(checked)
        self.internal_container.setVisible(checked)
        self.updateGeometry()
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
