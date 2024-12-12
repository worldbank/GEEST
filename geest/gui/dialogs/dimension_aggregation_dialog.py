from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QDoubleSpinBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QCheckBox,
    QWidget,
    QHBoxLayout,
    QSpacerItem,
)
from qgis.PyQt.QtGui import QPixmap, QDesktopServices
from qgis.PyQt.QtCore import Qt, QUrl
from qgis.core import Qgis
from geest.utilities import (
    resources_path,
    log_message,
    setting,
    is_qgis_dark_theme_active,
)
from geest.gui.widgets import CustomBannerLabel


class DimensionAggregationDialog(QDialog):
    def __init__(self, dimension_name, dimension_data, dimension_item, parent=None):
        super().__init__(parent)

        self.setWindowTitle(dimension_name)
        self.dimension_name = dimension_name
        self.dimension_data = dimension_data
        self.tree_item = dimension_item  # Reference to the QTreeView item to update

        self.setWindowTitle(
            f"Edit Dimension Weightings for Dimension: {self.tree_item.data(0)}"
        )
        # Need to be refactored...
        self.guids = self.tree_item.getDimensionFactorGuids()
        self.weightings = {}  # To store the temporary weightings

        # Layout setup
        layout = QVBoxLayout(self)
        self.resize(800, 600)  # Set a wider dialog size
        layout.setContentsMargins(20, 20, 20, 20)  # Add padding around the layout

        self.banner_label = CustomBannerLabel(
            "The Gender Enabling Environments Spatial Tool",
            resources_path("resources", "geest-banner.png"),
        )
        layout.addWidget(self.banner_label)

        # Get the parent item
        parent_item = self.tree_item.parent()

        # If both grandparent and parent exist, create the label
        if parent_item:
            hierarchy_label = QLabel(
                f"{parent_item.data(0)} :: {self.tree_item.data(0)}"
            )
            hierarchy_label.setStyleSheet(
                "font-size: 14px; font-weight: bold; color: gray;"
            )
            layout.addWidget(hierarchy_label, alignment=Qt.AlignTop)

        # Description label
        description_label = QLabel()
        description_label.setText(self.dimension_data.get("description", ""))
        description_label.setWordWrap(True)
        layout.addWidget(description_label)

        # Table setup
        self.table = QTableWidget(self)
        self.table.setRowCount(len(self.guids))
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Factor", "Weight 0-1", "Use", "", "Guid"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Adjust column widths
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )  # Factor column expands
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Fixed
        )  # Weight 0-1 column fixed
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Fixed
        )  # Use column fixed
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.Fixed
        )  # Reset column fixed
        self.table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.Fixed
        )  # Guid column fixed

        # Set fixed widths for the last three columns
        self.table.setColumnWidth(1, 100)  # Weight 0-1 column width
        self.table.setColumnWidth(2, 50)  # Use column (checkbox) width
        self.table.setColumnWidth(3, 75)  # Reset button column width
        self.table.setColumnWidth(3, 100)  # GUID button column width

        # Populate the table
        for row, guid in enumerate(self.guids):
            item = self.tree_item.getItemByGuid(guid)
            attributes = item.attributes()
            factor_id = attributes.get("name")
            dimension_weighting = float(attributes.get("dimension_weighting", 0.0))
            default_dimension_weighting = attributes.get(
                "default_dimension_weighting", 0
            )
            name_item = QTableWidgetItem(factor_id)
            name_item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 0, name_item)

            # weightings
            weighting_item = QDoubleSpinBox(self)
            weighting_item.setRange(0.0, 1.0)
            weighting_item.setDecimals(4)
            weighting_item.setValue(dimension_weighting)
            weighting_item.setSingleStep(0.01)
            weighting_item.valueChanged.connect(self.validate_weightings)
            self.table.setCellWidget(row, 1, weighting_item)
            self.weightings[guid] = weighting_item

            # Use checkboxes
            checkbox_widget = self.create_checkbox_widget(row, dimension_weighting)
            self.table.setCellWidget(row, 2, checkbox_widget)

            # Reset button
            reset_button = QPushButton("Reset")
            reset_button.clicked.connect(
                lambda checked, item=weighting_item: item.setValue(
                    default_dimension_weighting
                )
            )
            self.table.setCellWidget(row, 3, reset_button)

            # Guid column
            guid_item = QTableWidgetItem(guid)
            guid_item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 4, guid_item)
            guid_item.setToolTip(str(item.attributes()))

            # disable the table row if the checkbox is unchecked
            # Have to do this last after all widgets are initialized
            # First check if the factor is required
            # and disable the checkbox if it is
            for col in range(4):
                try:
                    item = self.table.item(row, col)
                    item.setEnabled(False)
                    # item.setFlags(Qt.ItemIsEnabled)
                except AttributeError:
                    pass

        layout.addWidget(self.table)

        help_layout = QHBoxLayout()
        help_layout.addItem(
            QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )
        self.help_icon = QPixmap(resources_path("resources", "images", "help.png"))
        self.help_icon = self.help_icon.scaledToWidth(20)
        self.help_label_icon = QLabel()
        self.help_label_icon.setPixmap(self.help_icon)
        self.help_label_icon.setScaledContents(True)
        self.help_label_icon.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.help_label_icon.setMaximumWidth(20)
        self.help_label_icon.setAlignment(Qt.AlignRight)
        help_layout.addWidget(self.help_label_icon)

        self.help_label = QLabel(
            "For detailed instructions on how to use this tool, please refer to the <a href='https://worldbank.github.io/GEEST/docs/user_guide.html'>GEEST User Guide</a>."
        )
        self.help_label.setOpenExternalLinks(True)
        self.help_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.help_label)
        self.help_label.linkActivated.connect(self.open_link_in_browser)
        help_layout.addWidget(self.help_label)
        help_layout.addItem(
            QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )
        layout.addLayout(help_layout)

        # QDialogButtonBox for OK and Cancel
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        auto_calculate_button = QPushButton("Balance Weights")
        self.button_box.addButton(auto_calculate_button, QDialogButtonBox.ActionRole)
        self.button_box.accepted.connect(self.accept_changes)
        self.button_box.rejected.connect(self.reject)
        auto_calculate_button.clicked.connect(self.auto_calculate_weightings)

        toggle_guid_button = QPushButton("Show GUIDs")
        self.button_box.addButton(auto_calculate_button, QDialogButtonBox.ActionRole)
        verbose_mode = setting(key="verbose_mode", default=0)
        if verbose_mode:
            self.button_box.addButton(toggle_guid_button, QDialogButtonBox.ActionRole)
        toggle_guid_button.clicked.connect(self.toggle_guid_column)
        self.guid_column_visible = False  # Track GUID column visibility
        self.table.setColumnHidden(
            4, not self.guid_column_visible
        )  # Hide GUID column by default

        layout.addWidget(self.button_box)

        # Initial validation check
        self.validate_weightings()

    def open_link_in_browser(self, url: str):
        """Open the given URL in the user's default web browser using QDesktopServices."""
        QDesktopServices.openUrl(QUrl(url))

    def toggle_guid_column(self):
        """Toggle the visibility of the GUID column."""
        log_message("Toggling GUID column visibility")
        self.guid_column_visible = not self.guid_column_visible
        self.table.setColumnHidden(4, not self.guid_column_visible)

    def create_checkbox_widget(self, row: int, dimension_weighting: float) -> QWidget:
        """
        Create a QWidget containing a QCheckBox for a specific row and center it.
        """
        checkbox = QCheckBox()
        if dimension_weighting > 0:
            checkbox.setChecked(True)  # Initially checked
        else:
            checkbox.setChecked(False)
        checkbox.stateChanged.connect(
            lambda state, r=row: self.toggle_row_widgets(r, state)
        )

        # Create a container widget with a centered layout
        container = QWidget()
        layout = QHBoxLayout()
        layout.addWidget(checkbox)
        layout.setAlignment(Qt.AlignCenter)  # Center the checkbox
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        container.setLayout(layout)

        return container

    def toggle_row_widgets(self, row: int, state: int):
        """
        Enable or disable widgets in the row based on the checkbox state.
        """
        is_enabled = state == Qt.Checked
        for col in range(self.table.columnCount()):
            # Skip the column containing the checkbox (assumed to be column 2)
            if col == 2:
                continue
            # Disable QTableWidgetItems
            item = self.table.item(row, col)
            if item:
                item.setFlags(Qt.ItemIsEnabled if is_enabled else Qt.NoItemFlags)

            # Disable widgets inside cells
            widget = self.table.cellWidget(row, col)
            if widget:
                if isinstance(widget, QDoubleSpinBox) and not is_enabled:
                    widget.setValue(0)  # Reset weightings to zero
                widget.setEnabled(is_enabled)
        self.validate_weightings()

    def auto_calculate_weightings(self):
        """Calculate and set equal weighting for each enabled indicator."""
        log_message("Auto-calculating weightings")
        # Filter rows where the checkbox is checked
        enabled_rows = [
            row for row in range(self.table.rowCount()) if self.is_checkbox_checked(row)
        ]
        disabled_rows = [
            row
            for row in range(self.table.rowCount())
            if not self.is_checkbox_checked(row)
        ]
        if not enabled_rows:
            log_message("No enabled rows found, skipping auto-calculation")
            return  # No enabled rows, avoid division by zero

        if len(enabled_rows) == 0:
            equal_weighting = 0.0
        else:
            equal_weighting = 1.0 / len(
                enabled_rows
            )  # Divide equally among enabled rows

        # Set the weighting for each enabled row
        for row in enabled_rows:
            log_message(f"Setting equal weighting for row: {row}")
            widget = self.table.cellWidget(row, 1)  # Assuming weight is in column 1
            widget.setValue(equal_weighting)
        # Rest of the rows get assigned zero
        for row in disabled_rows:
            log_message(f"Setting zero weighting for row: {row}")
            widget = self.table.cellWidget(row, 1)  # Assuming weight is in column 1
            widget.setValue(0)
        self.validate_weightings()

    def is_checkbox_checked(self, row: int) -> bool:
        """
        Check if the checkbox in the specified row is checked.
        :param row: The row index to check.
        :return: True if the checkbox is checked, False otherwise.
        """
        log_message(f"Checking checkbox state for row: {row}")
        checkbox = self.get_checkbox_in_row(row)  # Assuming the checkbox is in column 2
        return checkbox.isChecked()

    def get_checkbox_in_row(self, row: int) -> QCheckBox:
        """
        Retrieve the checkbox widget in the specified row.
        :param row: The row index to retrieve the checkbox from.
        :return: The QCheckBox widget, or None if not found.
        """
        container = self.table.cellWidget(
            row, 2
        )  # Assuming the checkbox is in column 2
        if container and isinstance(container, QWidget):
            layout = container.layout()
            if layout and layout.count() > 0:
                checkbox = layout.itemAt(0).widget()
                if isinstance(checkbox, QCheckBox):
                    return checkbox
        return None

    def saveWeightingsToModel(self):
        """Assign new weightings to the dimensions's factors."""
        for factor_guid, spin_box in self.weightings.items():
            try:
                new_weighting = spin_box.value()
                self.tree_item.updateFactorWeighting(factor_guid, new_weighting)
            except ValueError:
                log_message(
                    f"Invalid weighting input for GUID: {factor_guid}",
                    tag="Geest",
                    level=Qgis.Warning,
                )

    def validate_weightings(self):
        """Validate weightings to ensure they sum to 1 and are within range."""
        try:
            total_weighting = sum(
                float(spin_box.value() or 0) for spin_box in self.weightings.values()
            )
            valid_sum = (
                abs(total_weighting - 1.0) < 0.001
            )  # Allow slight floating-point tolerance
        except ValueError:
            valid_sum = False

        # In the case that all rows are disabled, the sum is valid
        enabled_rows = [
            row for row in range(self.table.rowCount()) if self.is_checkbox_checked(row)
        ]
        enabled_rows_count = len(enabled_rows)
        if enabled_rows_count == 0:
            valid_sum = True

        if is_qgis_dark_theme_active():
            normal_color = "color: white;"
        else:
            normal_color = "color: black;"
        # Update button state and cell highlighting
        for spin_box in self.weightings.values():
            if valid_sum:
                spin_box.setStyleSheet(
                    normal_color
                )  # Reset font color to black if valid
            else:
                spin_box.setStyleSheet(
                    "color: red;"
                )  # Set font color to red if invalid

        # Enable or disable the OK button based on validation result
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(valid_sum)

    def accept_changes(self):
        """Handle the OK button by applying changes and closing the dialog."""
        self.saveWeightingsToModel()  # Assign weightings when changes are accepted
        self.accept()
