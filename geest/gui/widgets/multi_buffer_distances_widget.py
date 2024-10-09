from qgis.PyQt.QtWidgets import (
    QLabel,
    QGroupBox,
    QRadioButton,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QToolButton,
    QFileDialog,
)
from qgis.gui import QgsMapLayerComboBox

from .base_indicator_widget import BaseIndicatorWidget
from qgis.core import QgsMessageLog, Qgis, QgsMapLayerProxyModel
from qgis.PyQt.QtCore import QSettings


class MultiBufferDistancesWidget(BaseIndicatorWidget):
    """
    A specialized radio button with additional widgetQDoubleSpinBoxs for IndexScore.
    """

    def add_internal_widgets(self) -> None:
        """
        Adds internal widgets specific to self.set_internal_widgets_visible(self.isChecked()) - in this case there are none.
        """
        try:
            self.main_layout = QVBoxLayout()

            # Point Layer Combobox - Filtered to point layers
            self.point_layer_label = QLabel(
                "Point Layer - shapefile will have preference"
            )
            self.main_layout.addWidget(self.point_layer_label)

            self.layer_combo = QgsMapLayerComboBox()
            self.layer_combo.setFilters(QgsMapLayerProxyModel.PointLayer)
            self.main_layout.addWidget(self.layer_combo)

            # Add shapefile selection (QLineEdit and QToolButton)
            self.shapefile_layout = QHBoxLayout()
            self.shapefile_line_edit = QLineEdit()
            self.shapefile_button = QToolButton()
            self.shapefile_button.setText("...")
            self.shapefile_button.clicked.connect(self.select_shapefile)
            if self.attributes.get("Multi Buffer Shapefile", False):
                self.shapefile_line_edit.setText(
                    self.attributes["Multi Buffer Shapefile"]
                )
            self.shapefile_layout.addWidget(self.shapefile_line_edit)
            self.shapefile_layout.addWidget(self.shapefile_button)
            self.main_layout.addLayout(self.shapefile_layout)

            # Travel Mode group
            self.travel_mode_group = QGroupBox("Travel Mode:")
            self.travel_mode_layout = QHBoxLayout()
            self.walking_radio = QRadioButton("Walking")
            self.driving_radio = QRadioButton("Driving")
            if self.attributes.get("Multi Buffer Travel Mode", "") == "Walking":
                self.walking_radio.setChecked(True)
            else:
                self.driving_radio.setChecked(True)  # Default selection
            self.travel_mode_layout.addWidget(self.walking_radio)
            self.travel_mode_layout.addWidget(self.driving_radio)
            self.travel_mode_group.setLayout(self.travel_mode_layout)

            # Measurement group
            self.measurement_group = QGroupBox("Measurement:")
            self.measurement_layout = QHBoxLayout()
            self.distance_radio = QRadioButton("Distance")
            self.time_radio = QRadioButton("Time")
            if self.attributes.get("Multi Buffer Travel Units", "") == "Distance":
                self.distance_radio.setChecked(True)
            else:
                self.time_radio.setChecked(True)  # Default selection
            self.measurement_layout.addWidget(self.distance_radio)
            self.measurement_layout.addWidget(self.time_radio)
            self.measurement_group.setLayout(self.measurement_layout)

            # Travel Increments input
            self.travel_increments_layout = QHBoxLayout()
            self.increments_label = QLabel("Travel Increments:")
            self.increments_input = QLineEdit("")
            self.travel_increments_layout.addWidget(self.increments_label)
            self.travel_increments_layout.addWidget(self.increments_input)
            if self.attributes.get("Multi Buffer Travel Distances", False):
                self.increments_input.setText(
                    self.attributes["Multi Buffer Travel Distances"]
                )
            else:
                self.increments_input.setText(
                    self.attributes.get("Default Multi Buffer Travel Distances", "")
                )

            # Add all layouts to the main layout
            self.main_layout.addWidget(self.travel_mode_group)
            self.main_layout.addWidget(self.measurement_group)
            self.main_layout.addLayout(self.travel_increments_layout)
            self.layout.addLayout(self.main_layout)

            # Emit the data_changed signal when any widget is changed
            self.layer_combo.currentIndexChanged.connect(self.update_data)
            self.time_radio.toggled.connect(self.update_data)
            self.distance_radio.toggled.connect(self.update_data)
            self.walking_radio.toggled.connect(self.update_data)
            self.driving_radio.toggled.connect(self.update_data)
            self.increments_input.textChanged.connect(self.update_data)
            self.shapefile_line_edit.textChanged.connect(self.update_data)

        except Exception as e:
            QgsMessageLog.logMessage(f"Error in add_internal_widgets: {e}", "Geest")
            import traceback

            QgsMessageLog.logMessage(traceback.format_exc(), "Geest")

    def select_shapefile(self):
        """
        Opens a file dialog to select a shapefile and stores the last directory in QSettings.
        """
        try:
            settings = QSettings()
            last_dir = settings.value("Geest/lastShapefileDir", "")

            # Open file dialog to select a shapefile
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Shapefile", last_dir, "Shapefiles (*.shp)"
            )

            if file_path:
                # Update the line edit with the selected file path
                self.shapefile_line_edit.setText(file_path)

                # Save the directory of the selected file to QSettings
                settings.setValue("Geest/lastShapefileDir", os.path.dirname(file_path))

        except Exception as e:
            QgsMessageLog.logMessage(f"Error selecting shapefile: {e}", "Geest")

    def get_data(self) -> dict:
        """
        Return the data as a dictionary, updating attributes with current value.
        """
        if not self.isChecked():
            return None

        layer = self.layer_combo.currentLayer()
        if not layer:
            self.attributes["Multi Buffer Point Layer"] = None
        else:
            self.attributes["Multi Buffer Point Layer"] = layer

        if self.walking_radio.isChecked():
            self.attributes["Multi Buffer Travel Mode"] = "Walking"
        else:
            self.attributes["Multi Buffer Travel Mode"] = "Driving"

        if self.distance_radio.isChecked():
            self.attributes["Multi Buffer Travel Units"] = "Distance"
        else:
            self.attributes["Multi Buffer Travel Units"] = "Time"

        self.attributes["Multi Buffer Travel Distances"] = self.increments_input.text()
        self.attributes["Multi Buffer Shapefile"] = self.shapefile_line_edit.text()

        return self.attributes

    def set_internal_widgets_enabled(self, enabled: bool) -> None:
        """
        Enables or disables the internal widgets based on the state of the radio button.
        """
        try:
            self.layer_combo.setEnabled(enabled)
            self.distance_radio.setEnabled(enabled)
            self.time_radio.setEnabled(enabled)
            self.walking_radio.setEnabled(enabled)
            self.driving_radio.setEnabled(enabled)
            self.increments_input.setEnabled(enabled)
            self.increments_label.setEnabled(enabled)
            self.point_layer_label.setEnabled(enabled)
            self.travel_mode_group.setEnabled(enabled)
            self.measurement_group.setEnabled(enabled)
            self.travel_increments_layout.setEnabled(enabled)
            self.shapefile_line_edit.setEnabled(enabled)
            self.shapefile_button.setEnabled(enabled)
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error in set_internal_widgets_enabled: {e}", "Geest"
            )
