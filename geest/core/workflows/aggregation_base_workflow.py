import os
import shutil
import glob
from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsFeedback,
    QgsRasterLayer,
    QgsProject,
)
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from .workflow_base import WorkflowBase
from geest.core.convert_to_8bit import RasterConverter
from geest.utilities import resources_path


class AggregationBaseWorkflow(WorkflowBase):
    """
    Base class for all aggregation workflows (factor, dimension, analysis)
    """

    def __init__(self, attributes: dict, feedback: QgsFeedback):
        """
        Initialize the Factor Aggregation with attributes and feedback.
        :param attributes: Dictionary containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        """
        super().__init__(attributes, feedback)
        self.analysis_mode = self.attributes.get("Analysis Mode", "")
        self.id = None  # This should be set by the child class
        self.layers = None  # This should be set by the child class
        self.weight_key = None  # This should be set by the child class
        self.result_file_tag = (
            None  # This should be set by the child class e.g. "Factor Result File"
        )
        self.vrt_path_key = (
            None  # This should be set by the child class e.g. "Indicator Result File"
        )

    def get_weights(self) -> list:
        """
        Retrieve default weights based on the number of layers.
        :return: List of weights for the layers.
        """
        weights = []

        for layer in self.layers:
            weights.append(float(layer.get(self.weight_key, 1.0)))
        return weights

    def output_path(self, extension: str) -> str:
        """
        Define output path for the aggregated raster based on the analysis mode.

        Parameters:
            extension (str): The file extension for the output file.

        Returns:
            str: Path to the aggregated raster file.

        """
        pass

    def aggregate(self, vrt_files: list) -> None:
        """
        Perform weighted raster aggregation on the found VRT files.

        :param vrt_files: List of VRT file paths to aggregate.

        :return: Path to the aggregated raster file.
        """
        if len(vrt_files) == 0:
            QgsMessageLog.logMessage(
                f"Error: Found no VRT files. Cannot proceed with aggregation.",
                tag="Geest",
                level=Qgis.Warning,
            )
            return None

        # Load the VRT layers
        raster_layers = [
            QgsRasterLayer(vf, f"VRT_{i}") for i, vf in enumerate(vrt_files)
        ]

        # Ensure all VRT layers are valid
        if not all(layer.isValid() for layer in raster_layers):
            QgsMessageLog.logMessage(
                "One or more VRT layers are invalid, cannot proceed with aggregation.",
                tag="Geest",
                level=Qgis.Critical,
            )
            return None

        # Create QgsRasterCalculatorEntries for each VRT layer
        entries = []
        for i, raster_layer in enumerate(raster_layers):
            QgsMessageLog.logMessage(
                f"Adding raster layer {i+1} to the raster calculator. {raster_layer.source()}",
                tag="Geest",
                level=Qgis.Info,
            )
            entry = QgsRasterCalculatorEntry()
            entry.ref = f"layer_{i+1}@1"  # layer_1@1, layer_2@1, etc.
            entry.raster = raster_layer
            entry.bandNumber = 1
            entries.append(entry)

        # Assign default weights (you can modify this as needed)
        weights = self.get_weights()

        # Number of VRT layers
        layer_count = len(vrt_files)

        # Ensure that the sum of weights is calculated
        sum_weights = sum(weights)

        # Build the calculation expression for weighted average
        expression = " + ".join(
            [f"({weights[i]} * layer_{i+1}@1)" for i in range(layer_count)]
        )

        # Wrap the weighted sum and divide by the sum of weights
        expression = f"({expression}) / {sum_weights}"

        aggregation_output = self.output_path("tif")
        QgsMessageLog.logMessage(
            f"Aggregating {len(vrt_files)} raster layers to {aggregation_output}",
            tag="Geest",
            level=Qgis.Info,
        )
        QgsMessageLog.logMessage(
            f"Aggregation Expression: {expression}", tag="Geest", level=Qgis.Info
        )
        # Set up the raster calculator
        calc = QgsRasterCalculator(
            expression,
            aggregation_output,
            "GTiff",  # Output format
            raster_layers[0].extent(),  # Assuming all layers have the same extent
            raster_layers[0].width(),
            raster_layers[0].height(),
            entries,
        )

        # Run the calculation
        result = calc.processCalculation()
        QgsMessageLog.logMessage(
            f"Calculator errors: {calc.lastError()}", tag="Geest", level=Qgis.Info
        )
        if result != 0:
            QgsMessageLog.logMessage(
                "Raster aggregation completed successfully.",
                tag="Geest",
                level=Qgis.Info,
            )
            return None

        converter = RasterConverter()
        aggregation_output_8bit = aggregation_output.replace(".tif", "_8bit.tif")
        # Convert the aggregated raster to 8-bit
        converter.convert_to_8bit(aggregation_output, aggregation_output_8bit)
        if os.path.exists(aggregation_output_8bit):
            # TODO We should check if developer mode is set and keep the 32-bit raster if it is
            os.remove(aggregation_output)

        QgsMessageLog.logMessage(
            "Raster aggregation completed successfully.",
            tag="Geest",
            level=Qgis.Info,
        )
        # Add the aggregated raster to the map
        aggregated_layer = QgsRasterLayer(
            aggregation_output_8bit, f"aggregated_{self.id}.tif"
        )
        if not aggregated_layer.isValid():
            QgsMessageLog.logMessage(
                "Aggregate layer is not valid.",
                tag="Geest",
                level=Qgis.Critical,
            )
            return None
        # WRite the output path to the attributes
        # That will get passed back to the json model
        self.attributes[self.result_file_tag] = aggregation_output_8bit

        # Fallback sequence to copy QML style
        # qml with same name as factor
        # qml with generic name of factor.qml
        qml_paths = []
        qml_paths.append(
            resources_path(
                "resources",
                "qml",
                f"{self.id}.qml",
            )
        )
        qml_paths.append(
            resources_path(
                "resources",
                "qml",
                f"{self.analysis_mode}.qml",  # e.g. factor.qml
            )
        )
        qml_dest_path = self.output_path("qml")
        for qml_src_path in qml_paths:
            if os.path.exists(qml_src_path):
                qml_dest_path_8bit = qml_dest_path.replace(".qml", "_8bit.qml")
                shutil.copy(qml_src_path, qml_dest_path_8bit)
                QgsMessageLog.logMessage(
                    f"Copied QML style file to {qml_dest_path_8bit}",
                    tag="Geest",
                    level=Qgis.Info,
                )
                result = aggregated_layer.loadNamedStyle(qml_dest_path_8bit)
                if result[0]:  # Check if the style was successfully loaded
                    QgsMessageLog.logMessage(
                        "Successfully applied QML style.",
                        tag="Geest",
                        level=Qgis.Info,
                    )
                    break

        QgsProject.instance().addMapLayer(aggregated_layer)
        QgsMessageLog.logMessage(
            "Added VRT layer to the map.", tag="Geest", level=Qgis.Info
        )
        return aggregation_output_8bit

    def get_vrt_list(self) -> list:
        """
        Get the list of vrts from the attributes that will be aggregated.

        (Factor Aggregation, Dimension Aggregation, Analysis).

        Returns:
            list: List of found VRT file paths.
        """
        vrt_files = []

        for layer in self.layers:
            path = layer.get(self.vrt_path_key, "")
            vrt_files.append(path)
            QgsMessageLog.logMessage(
                f"Adding VRT: {path}", tag="Geest", level=Qgis.Info
            )
        QgsMessageLog.logMessage(
            f"Total VRT files found: {len(vrt_files)}", tag="Geest", level=Qgis.Info
        )
        return vrt_files

    def execute(self):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        # Log the execution
        QgsMessageLog.logMessage(
            f"Executing {self.analysis_mode} Aggregation Workflow",
            tag="Geest",
            level=Qgis.Info,
        )
        QgsMessageLog.logMessage(f"ID: {self.id}", tag="Geest", level=Qgis.Info)
        QgsMessageLog.logMessage(
            f"Aggregation Layers: {self.layers}",
            tag="Geest",
            level=Qgis.Info,
        )

        vrt_files = self.get_vrt_list()

        if not vrt_files or not isinstance(vrt_files, list):
            QgsMessageLog.logMessage(
                f"No valid VRT files found in '{self.layers}'. Cannot proceed with aggregation.",
                tag="Geest",
                level=Qgis.Warning,
            )
            self.attributes["Result"] = (
                f"{self.analysis_mode} Aggregation Workflow Failed"
            )
            return False

        QgsMessageLog.logMessage(
            f"Found {len(vrt_files)} VRT files in 'Indicator Result File'. Proceeding with aggregation.",
            tag="Geest",
            level=Qgis.Info,
        )

        # Perform aggregation only if VRT files are provided
        result_file = self.aggregate(vrt_files)
        if result_file:
            QgsMessageLog.logMessage(
                "Aggregation Workflow completed successfully.",
                tag="Geest",
                level=Qgis.Info,
            )
            self.attributes["Result File"] = result_file
            self.attributes["Result"] = (
                f"{self.analysis_mode} Factor Aggregation Workflow Completed"
            )
            return True
        else:
            QgsMessageLog.logMessage(
                "Aggregation failed due to missing or invalid VRT files.",
                tag="Geest",
                level=Qgis.Warning,
            )
            self.attributes["Result File"] = None
            self.attributes["Result"] = (
                f"{self.analysis_mode} Aggregation Workflow Failed"
            )
            return False
