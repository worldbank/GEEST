import os
import shutil
import glob
from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsFeedback,
    QgsRasterLayer,
    QgsProcessingContext,
    QgsGeometry,
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
        self.aggregation_attributes = None  # This should be set by the child class e.g. item.getIndicatorAttributes()
        self.analysis_mode = self.attributes.get("analysis_mode", "")
        self.id = None  # This should be set by the child class
        self.layers = None  # This should be set by the child class
        self.weight_key = None  # This should be set by the child class
        self.raster_path_key = (
            None  # This should be set by the child class e.g. "result_file"
        )
        self.aggregation = True
        self.workflow_is_legacy = False

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
            # Ensure the weight is numeric, cast to float if necessary
            try:
                weight = float(weight)
            except (ValueError, TypeError):
                weight = 1.0  # Default fallback to 1.0 if weight is invalid
            weights.append(weight)
        return weights

    def aggregate(self, input_files: list, index: int) -> str:
        """
        Perform weighted raster aggregation on the found raster files.

        :param input_files: List of raster file paths to aggregate.
        :param index: The index of the area being processed.

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
        ref_names = []
        for i, raster_layer in enumerate(raster_layers):
            QgsMessageLog.logMessage(
                f"Adding raster layer {i+1} to the raster calculator. {raster_layer.source()}",
                tag="Geest",
                level=Qgis.Info,
            )
            entry = QgsRasterCalculatorEntry()
            ref_name = os.path.basename(raster_layer.source()).split(".")[0]
            entry.ref = f"{ref_name}_{i+1}@1"  # Reference the first band
            # entry.ref = f"layer_{i+1}@1"  # layer_1@1, layer_2@1, etc.
            entry.raster = raster_layer
            entry.bandNumber = 1
            entries.append(entry)
            ref_names.append(f"{ref_name}_{i+1}")

        # Assign default weights (you can modify this as needed)
        weights = self.get_weights()

        # Number of raster layers
        layer_count = len(input_files)

        # Ensure that the sum of weights is calculated
        sum_weights = sum(weights)

        # Build the calculation expression for weighted average
        expression = " + ".join(
            [f"({weights[i]} * {ref_names[i]}@1)" for i in range(layer_count)]
        )

        # Wrap the weighted sum and divide by the sum of weights
        expression = f"({expression}) / {layer_count}"

        if self.weight_key == "indicator_weighting":
            aggregation_output = os.path.join(
                self.workflow_directory, f"{self.layer_id}_aggregated_{index}.tif"
            )
        elif self.weight_key == "factor_weighting":
            aggregation_output = os.path.join(
                self.workflow_directory, f"{self.id}_aggregated_{index}.tif"
            )
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

        # Write the output path to the attributes
        # That will get passed back to the json model
        self.attributes["result_file"] = aggregation_output

        return aggregation_output

    def get_raster_list(self, index) -> list:
        """
        Get the list of rasters from the attributes that will be aggregated.

        (Factor Aggregation, Dimension Aggregation, Analysis).

        Parameters:
            index (int): The index of the area being processed.

        Returns:
            list: List of found raster file paths.
        """
        raster_files = []

        if self.weight_key == "indicator_weighting":
            for layer in self.layers:
                id = layer.get("indicator_id", "").lower()
                layer_folder = os.path.dirname(layer.get("result_file", ""))
                path = os.path.join(
                    self.workflow_directory, layer_folder, f"{id}_masked_{index}.tif"
                )
                if path:
                    raster_files.append(path)
                    QgsMessageLog.logMessage(
                        f"Adding raster: {path}", tag="Geest", level=Qgis.Info
                    )
        elif self.weight_key == "factor_weighting":
            for layer in self.layers:
                id = layer.get("factor_name", "").lower().replace(" ", "_")
                layer_folder = os.path.dirname(layer.get("result_file", ""))
                path = os.path.join(
                    self.workflow_directory,
                    layer_folder,
                    f"{id}_aggregated_{index}.tif",
                )
                if path:
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

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
    ):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        _ = current_area  # Unused in this analysis
        _ = current_bbox  # Unused in this analysis

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

        raster_files = self.get_raster_list(index)

        if not raster_files or not isinstance(raster_files, list):
            QgsMessageLog.logMessage(
                f"No valid raster files found in '{self.layers}'. Cannot proceed with aggregation.",
                tag="Geest",
                level=Qgis.Warning,
            )
            self.attributes["result"] = (
                f"{self.analysis_mode} Aggregation Workflow Failed"
            )
            return False

        QgsMessageLog.logMessage(
            f"Found {len(raster_files)} raster files in 'Result File'. Proceeding with aggregation.",
            tag="Geest",
            level=Qgis.Info,
        )

        # Perform aggregation only if raster files are provided
        result_file = self.aggregate(raster_files, index)

        return result_file

    def _process_features_for_area(self):
        pass

    def _process_raster_for_area(self):
        pass

    def do_execute(self):
        pass
