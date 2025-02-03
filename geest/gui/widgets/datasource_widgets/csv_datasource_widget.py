import os
from qgis.PyQt.QtWidgets import (
    QLineEdit,
    QToolButton,
    QFileDialog,
    QMessageBox,
)
from qgis.core import Qgis
from .base_datasource_widget import BaseDataSourceWidget
from geest.utilities import log_message


class CsvDataSourceWidget(BaseDataSourceWidget):
    """
    A widget for selecting a generic CSV file and verifying its format.

    This widget allows the user to select a CSV file, checks if it's in the expected format
    by verifying the presence of 'latitude', 'longitude' , and provides feedback
    on the validity of the selected file.

    Attributes:
        widget_key (str): The key identifier for this widget.
        csv_file_line_edit (QLineEdit): Line edit for entering/selecting a CSV file.
    """

    def add_internal_widgets(self) -> None:
        """
        Adds the internal widgets required for selecting the CSV firadiole and validating its format.
        This method is called during the widget initialization and sets up the layout for the UI components.
        """
        log_message("Adding internal widgets for ACLED CSV Layer Widget")
        try:
            self.widget_key = "use_csv_to_point_layer"

            # CSV File Section
            self._add_csv_file_widgets()

            # Connect signals to update the data when user changes selections
            self.csv_file_line_edit.textChanged.connect(self.update_attributes)

        except Exception as e:
            log_message(f"Error in add_internal_widgets: {e}", level=Qgis.Critical)
            import traceback

            log_message(traceback.format_exc(), level=Qgis.Critical)

    def _add_csv_file_widgets(self) -> None:
        """
        Adds the widgets for selecting the CSV file, including a `QLineEdit` and a `QToolButton` to browse for files.
        If the attribute set contains 'Use CSV to Point Layer CSV File', the line edit will be pre-filled.
        """
        # CSV File Input and Selection Button
        self.csv_file_line_edit = QLineEdit()
        self.csv_file_button = QToolButton()
        self.csv_file_button.setText("...")
        self.csv_file_button.clicked.connect(self.select_csv_file)
        self.layout.addWidget(self.csv_file_line_edit)
        self.layout.addWidget(self.csv_file_button)

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
                self, "Select CSV File", last_dir, "CSV Files (*.csv)"
            )
            if file_path:
                self.csv_file_line_edit.setText(file_path)
                self.validate_csv_file(file_path)
                os.environ["GEEST_LAST_CSV_DIR"] = os.path.dirname(file_path)

        except Exception as e:
            log_message(f"Error selecting CSV file: {e}", level=Qgis.Critical)

    def validate_csv_file(self, file_path: str) -> None:
        """
        Validates the selected CSV file to ensure it contains the required columns:
        'latitude', 'longitude'.

        :param file_path: The path to the selected CSV file.
        """
        try:
            required_columns = ["latitude", "longitude"]
            missing_columns = []

            with open(file_path, "r", encoding="utf-8") as file:
                header = file.readline().strip().split(",")

                for column in required_columns:
                    if column not in header:
                        missing_columns.append(column)

            if missing_columns:
                error_message = f"Missing columns: {', '.join(missing_columns)}"
                log_message(error_message, tag="Geest", level=Qgis.Critical)
                QMessageBox.critical(self, "Invalid CSV", error_message)
            else:
                log_message("CSV file validation successful.")
                QMessageBox.information(
                    self, "Valid CSV", "The selected CSV file is valid."
                )

        except Exception as e:
            log_message(f"Error validating CSV file: {e}", level=Qgis.Critical)
            QMessageBox.critical(
                self, "CSV Validation Error", f"An error occurred: {e}"
            )

    def update_attributes(self):
        """
        Updates the attributes dict to match the current state of the widget.

        The attributes dict is a reference so any tree item attributes will be updated directly.

        Returns:
            None
        """
        # Collect data for the CSV file
        self.attributes[f"{self.widget_key}_csv_file"] = self.csv_file_line_edit.text()
