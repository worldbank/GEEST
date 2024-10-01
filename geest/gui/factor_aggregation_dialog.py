from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
)
from qgis.PyQt.QtCore import Qt


class FactorAggregationDialog(QDialog):
    def __init__(self, factorItem, parent=None):
        super().__init__(parent)
        self.setWindowTitle(
            f"Edit Aggregation Weightings for Factor: {factorItem.data(0)}"
        )

        self.factorItem = factorItem
        self.indicators = (
            factorItem.getIndicators()
        )  # Assuming getIndicators returns a list of dictionaries with indicator details
        self.weightings = {}  # To store the temporary weightings

        # Layout setup
        layout = QVBoxLayout(self)

        # Table setup
        self.table = QTableWidget(self)
        self.table.setRowCount(len(self.indicators))
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Layer", "Weighting"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Populate the table
        for row, indicator in enumerate(self.indicators):
            # Display indicator name (not editable)
            name_item = QTableWidgetItem(indicator.get("name"))
            name_item.setFlags(Qt.ItemIsEnabled)  # Make it non-editable
            self.table.setItem(row, 0, name_item)

            # Display indicator weighting in a QLineEdit for editing
            weighting_item = QLineEdit(str(indicator.get("weighting", 0)))
            self.table.setCellWidget(row, 1, weighting_item)
            self.weightings[indicator.get("id")] = weighting_item

        layout.addWidget(self.table)

        # Buttons for OK and Cancel
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK", self)
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel", self)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def assignWeightings(self):
        """Assign new weightings to the factor's indicators."""
        for indicator_id, line_edit in self.weightings.items():
            try:
                new_weighting = float(line_edit.text())
                # Update the indicator's weighting in the factor item (use your own update logic here)
                self.factorItem.updateIndicatorWeighting(indicator_id, new_weighting)
            except ValueError:
                # Handle invalid input (non-numeric)
                pass
