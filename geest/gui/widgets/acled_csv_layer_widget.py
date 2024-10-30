from qgis.PyQt.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QToolButton,
    QFileDialog,
    QMessageBox,
)
from qgis.core import QgsMessageLog, Qgis
import os

from .base_indicator_widget import BaseIndicatorWidget


class AcledCsvLayerWidget(BaseIndicatorWidget):
    """
    A widget for selecting an ACLED CSV file and verifying its format.

    This widget allows the user to select a CSV file, checks if it's in the expected format
    by verifying the presence of 'latitude', 'longitude', and 'event_type', and provides feedback
    on the validity of the selected file.

    Attributes:
        widget_key (str): The key identifier for this widget.
        csv_file_line_edit (QLineEdit): Line edit for entering/selecting a CSV file.
    """

    def add_internal_widgets(self) -> None:
        """
        Adds the internal widgets required for selecting the CSV file and validating its format.
        This method is called during the widget initialization and sets up the layout for the UI components.
        """
        try:
            self.main_layout = QVBoxLayout()
            self.widget_key = "use_csv_to_point_layer"

            # CSV File Section
            self._add_csv_file_widgets()

            # Add the main layout to the widget's layout
            self.layout.addLayout(self.main_layout)

            # Connect signals to update the data when user changes selections
            self.csv_file_line_edit.textChanged.connect(self.update_data)

        except Exception as e:
            QgsMessageLog.logMessage(f"Error in add_internal_widgets: {e}", "Geest")
            import traceback

            QgsMessageLog.logMessage(traceback.format_exc(), "Geest")

    def _add_csv_file_widgets(self) -> None:
        """
        Adds the widgets for selecting the CSV file, including a `QLineEdit` and a `QToolButton` to browse for files.
        If the attribute set contains 'Use CSV to Point Layer CSV File', the line edit will be pre-filled.
        """
        self.csv_file_label = QLabel("Select ACLED CSV File")
        self.main_layout.addWidget(self.csv_file_label)

        # CSV File Input and Selection Button
        self.csv_file_layout = QHBoxLayout()
        self.csv_file_line_edit = QLineEdit()
        self.csv_file_button = QToolButton()
        self.csv_file_button.setText("...")
        self.csv_file_button.clicked.connect(self.select_csv_file)
        self.csv_file_layout.addWidget(self.csv_file_line_edit)
        self.csv_file_layout.addWidget(self.csv_file_button)
        self.main_layout.addLayout(self.csv_file_layout)

        # If there is a pre-existing file path in the attributes, set it in the line edit
        csv_file_path = self.attributes.get(f"{self.widget_key}_csv_file", None)
        if csv_file_path:
            self.csv_file_line_edit.setText(csv_file_path)

    def select_csv_file(self) -> None:
        """
        Opens a file dialog to select a CSV file and updates the QLineEdit with the file path.
        Also validates the selected file to check for required columns.
        """
        try:
            last_dir = os.getenv("GEEST_LAST_CSV_DIR", "")

            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select ACLED CSV File", last_dir, "CSV Files (*.csv)"
            )
            if file_path:
                self.csv_file_line_edit.setText(file_path)
                self.validate_csv_file(file_path)
                os.environ["GEEST_LAST_CSV_DIR"] = os.path.dirname(file_path)

        except Exception as e:
            QgsMessageLog.logMessage(f"Error selecting CSV file: {e}", "Geest")

    def validate_csv_file(self, file_path: str) -> None:
        """
        Validates the selected CSV file to ensure it contains the required columns:
        'latitude', 'longitude', and 'event_type'.

        :param file_path: The path to the selected CSV file.
        """
        try:
            required_columns = ["latitude", "longitude", "event_type"]
            missing_columns = []

            with open(file_path, "r", encoding="utf-8") as file:
                header = file.readline().strip().split(",")

                for column in required_columns:
                    if column not in header:
                        missing_columns.append(column)

            if missing_columns:
                error_message = f"Missing columns: {', '.join(missing_columns)}"
                QgsMessageLog.logMessage(error_message, "Geest", Qgis.Critical)
                QMessageBox.critical(self, "Invalid CSV", error_message)
            else:
                QgsMessageLog.logMessage(
                    "CSV file validation successful.", "Geest", Qgis.Info
                )
                QMessageBox.information(
                    self, "Valid CSV", "The selected CSV file is valid."
                )

        except Exception as e:
            QgsMessageLog.logMessage(f"Error validating CSV file: {e}", "Geest")
            QMessageBox.critical(
                self, "CSV Validation Error", f"An error occurred: {e}"
            )

    def get_data(self) -> dict:
        """
        Retrieves and returns the current state of the widget, including the selected CSV file path.

        Returns:
            dict: A dictionary containing the current attributes of the widget.
        """
        if not self.isChecked():
            return None

        # Collect data for the CSV file
        self.attributes[f"{self.widget_key}_csv_file"] = self.csv_file_line_edit.text()

        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets (CSV file input) based on the state of the radio button.

        Args:
            enabled (bool): Whether to enable or disable the internal widgets.
        """
        try:
            self.csv_file_line_edit.setEnabled(enabled)
            self.csv_file_button.setEnabled(enabled)
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error in set_internal_widgets_enabled: {e}", "Geest"
            )
