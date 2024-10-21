import os
import shutil
import glob
from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsFeedback,
    QgsRasterLayer,
    QgsProject,
    QgsProcessingContext,
)
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from .workflow_base import WorkflowBase
from geest.core.convert_to_8bit import RasterConverter
from geest.utilities import resources_path
from geest.core import JsonTreeItem


class AggregationWorkflowBase(WorkflowBase):
    """
    Base class for all aggregation workflows (factor, dimension, analysis)
    """

    def __init__(
        self, item: JsonTreeItem, feedback: QgsFeedback, context: QgsProcessingContext
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param attributes: Item containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        """
        super().__init__(
            item, feedback, context
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.attributes = item.data(3)
        self.aggregation_attributes = None  # This should be set by the child class e.g. item.getIndicatorAttributes()
        self.analysis_mode = self.attributes.get("Analysis Mode", "")
        self.id = None  # This should be set by the child class
        self.layers = None  # This should be set by the child class
        self.weight_key = None  # This should be set by the child class
        self.result_file_tag = (
            None  # This should be set by the child class e.g. "Factor Result File"
        )
        self.raster_path_key = (
            None  # This should be set by the child class e.g. "Indicator Result File"
        )

    def get_weights(self) -> list:
        """
        Retrieve default weights based on the number of layers.
        :return: List of weights for the layers.
        """
        weights = []

        for layer in self.layers:
            weight = layer.get(self.weight_key, 1.0)
            if weight == "" and len(self.layers) == 1:
                weight = 1.0
            weights.append(weight)
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

    def aggregate(self, input_files: list) -> None:
        """
        Perform weighted raster aggregation on the found raster files.

        :param input_files: List of raster file paths to aggregate.

        :return: Path to the aggregated raster file.
        """
        if len(input_files) == 0:
            QgsMessageLog.logMessage(
                f"Error: Found no Input files. Cannot proceed with aggregation.",
                tag="Geest",
                level=Qgis.Warning,
            )
            return None

        # Load the layers
        raster_layers = [
            QgsRasterLayer(vf, f"raster_{i}") for i, vf in enumerate(input_files)
        ]

        # Ensure all raster layers are valid and print filenames of invalid layers
        invalid_layers = [
            layer.source() for layer in raster_layers if not layer.isValid()
        ]
        if invalid_layers:
            QgsMessageLog.logMessage(
                f"Invalid raster layers found: {', '.join(invalid_layers)}",
                tag="Geest",
                level=Qgis.Critical,
            )
            return None

        # Create QgsRasterCalculatorEntries for each raster layer
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

        # Number of raster layers
        layer_count = len(input_files)

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
            f"Aggregating {len(input_files)} raster layers to {aggregation_output}",
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

        self.context.project().addMapLayer(aggregated_layer)
        QgsMessageLog.logMessage(
            "Added raster layer to the map.", tag="Geest", level=Qgis.Info
        )
        return aggregation_output_8bit

    def get_raster_list(self) -> list:
        """
        Get the list of rasters from the attributes that will be aggregated.

        (Factor Aggregation, Dimension Aggregation, Analysis).

        Returns:
            list: List of found raster file paths.
        """
        raster_files = []

        for layer in self.layers:
            path = layer.get(self.raster_path_key, "")
            raster_files.append(path)
            QgsMessageLog.logMessage(
                f"Adding raster: {path}", tag="Geest", level=Qgis.Info
            )
        QgsMessageLog.logMessage(
            f"Total raster files found: {len(raster_files)}",
            tag="Geest",
            level=Qgis.Info,
        )
        return raster_files

    def do_execute(self):
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

        raster_files = self.get_raster_list()

        if not raster_files or not isinstance(raster_files, list):
            QgsMessageLog.logMessage(
                f"No valid raster files found in '{self.layers}'. Cannot proceed with aggregation.",
                tag="Geest",
                level=Qgis.Warning,
            )
            self.attributes["Result"] = (
                f"{self.analysis_mode} Aggregation Workflow Failed"
            )
            return False

        QgsMessageLog.logMessage(
            f"Found {len(raster_files)} raster files in 'Indicator Result File'. Proceeding with aggregation.",
            tag="Geest",
            level=Qgis.Info,
        )

        # Perform aggregation only if raster files are provided
        result_file = self.aggregate(raster_files)
        if result_file:
            QgsMessageLog.logMessage(
                "Aggregation Workflow completed successfully.",
                tag="Geest",
                level=Qgis.Info,
            )
            self.attributes[self.result_file_tag] = result_file
            self.attributes["Result"] = (
                f"{self.analysis_mode} Factor Aggregation Workflow Completed"
            )
            return True
        else:
            QgsMessageLog.logMessage(
                "Aggregation failed due to missing or invalid raster files.",
                tag="Geest",
                level=Qgis.Warning,
            )
            self.attributes[self.result_file_tag] = None
            self.attributes["Result"] = (
                f"{self.analysis_mode} Aggregation Workflow Failed"
            )
            return False
