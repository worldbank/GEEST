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


class AggregationWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'Use Default Index Score' workflow.
    """

    def __init__(self, attributes: dict, feedback: QgsFeedback):
        """
        Initialize the Factor Aggregation with attributes and feedback.
        :param attributes: Dictionary containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        """
        super().__init__(attributes, feedback)
        self.analysis_mode = self.attributes.get("Analysis Mode", "")
        self.key_prefix = self.analysis_mode.split(" ")[0]

        if self.key_prefix == "Factor":
            self.sub_key_prefix = "Indicator"
        elif self.key_prefix == "Dimension":
            self.sub_key_prefix = "Factor"
        elif self.key_prefix == "Analysis":
            self.sub_key_prefix = "Dimension"

        self.id = self.attributes[f"{self.key_prefix} ID"].lower()
        self.aggregation_layers = self.attributes.get(f"{self.sub_key_prefix}s", [])

    def get_weights(self) -> list:
        """
        Retrieve default weights based on the number of layers.
        :return: List of weights for the layers.
        """
        weights = []
        weight_key = f"{self.sub_key_prefix} Weight"
        for layer in self.aggregation_layers:
            weights.append(float(layer.get(weight_key, 1.0)))
        return weights

    def get_aggregation_output_path(self, extension: str) -> str:
        """
        Define output path for the aggregated raster based on the analysis mode.

        Parameters:
            extension (str): The file extension for the output file.

        Returns:
            str: Path to the aggregated raster file.

        """
        if self.analysis_mode == "Factor Aggregation":
            return os.path.join(
                self.workflow_directory,
                self.attributes.get("Dimension ID"),
                # self.attributes.get("Factor ID").lower().replace(" ", "_") +
                f"aggregate_{self.id}" + f".{extension}",
            )
        elif self.analysis_mode == "Dimension Aggregation":
            return os.path.join(
                self.workflow_directory,
                self.attributes.get("Dimension ID"),
                self.attributes.get("Factor ID").lower().replace(" ", "_")
                + f".{extension}",
            )
        else:  # Analysis level
            return os.path.join(
                self.workflow_directory,
                self.attributes.get("Dimension ID") + f".{extension}",
            )

    def aggregate_vrt_files(self, vrt_files: list) -> None:
        """
        Perform weighted raster aggregation on the found VRT files.

        :param vrt_files: List of VRT file paths to aggregate.

        :return: Path to the aggregated raster file.
        """
        if len(vrt_files) == 0:
            QgsMessageLog.logMessage(
                f"Not all required VRT files found. Found {len(vrt_files)} VRT files. Cannot proceed with aggregation.",
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
        num_layers = len(vrt_files)

        # Ensure that the sum of weights is calculated
        sum_weights = sum(weights)

        # Build the calculation expression for weighted average
        expression = " + ".join(
            [f"({weights[i]} * layer_{i+1}@1)" for i in range(num_layers)]
        )

        # Wrap the weighted sum and divide by the sum of weights
        expression = f"({expression}) / {sum_weights}"

        aggregation_output = self.get_aggregation_output_path("tif")
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
        converter = RasterConverter()

        aggregation_output_8bit = aggregation_output.replace(".tif", "_8bit.tif")

        # Convert the aggregated raster to 8-bit
        converter.convert_to_8bit(aggregation_output, aggregation_output_8bit)

        if os.path.exists(aggregation_output_8bit):
            os.remove(aggregation_output)

        if result == 0:
            QgsMessageLog.logMessage(
                "Raster aggregation completed successfully.",
                tag="Geest",
                level=Qgis.Info,
            )
            # Add the aggregated raster to the map
            aggregated_layer = QgsRasterLayer(
                aggregation_output_8bit, f"aggregated_{self.id}.tif"
            )
            if aggregated_layer.isValid():
                self.attributes["Factor Result File"] = aggregation_output_8bit

                #    qml_src_path = resources_path(
                #        # TODO I think this should be factor, dimension, or analysis
                #        "resources",
                #        "qml",
                #        f"{self.dimension_id}.qml",
                #    )

                #    if os.path.exists(qml_src_path):
                #        qml_dest_path = self.get_aggregation_output_path("qml")
                #        qml_dest_path_8bit = qml_dest_path.replace(".qml", "_8bit.qml")
                #        shutil.copy(qml_src_path, qml_dest_path_8bit)
                #        QgsMessageLog.logMessage(
                #            f"Copied QML style file to {qml_dest_path_8bit}",
                #            tag="Geest",
                #            level=Qgis.Info,
                #        )
                #    else:
                #        QgsMessageLog.logMessage(
                #            f"QML style file not found: {qml_src_path}",
                #            tag="Geest",
                #            level=Qgis.Warning,
                #        )
                #    if os.path.exists(qml_dest_path_8bit):
                #
                #        result = aggregated_layer.loadNamedStyle(qml_dest_path_8bit)
                #        if result[0]:  # Check if the style was successfully loaded
                #            QgsMessageLog.logMessage(
                #                "Successfully applied QML style.",
                #                tag="Geest",
                #                level=Qgis.Info,
                #            )
                #        else:
                #            QgsMessageLog.logMessage(
                #                f"Failed to apply QML style: {result[1]}",
                #                tag="Geest",
                #                level=Qgis.Warning,
                #            )

                QgsProject.instance().addMapLayer(aggregated_layer)
                QgsMessageLog.logMessage(
                    "Added VRT layer to the map.", tag="Geest", level=Qgis.Info
                )
                return aggregation_output_8bit
            #    else:
            #        QgsMessageLog.logMessage(
            #            "QML not in the directory.", tag="Geest", level=Qgis.Critical
            #        )
            #        QgsProject.instance().addMapLayer(aggregated_layer)
            #        return aggregation_output
            else:
                QgsMessageLog.logMessage(
                    "Failed to add the aggregated raster to the map.",
                    tag="Geest",
                    level=Qgis.Critical,
                )
                return None
        else:
            QgsMessageLog.logMessage(
                "Error occurred during raster aggregation.",
                tag="Geest",
                level=Qgis.Critical,
            )
            return None

    def get_vrt_list(self) -> list:
        """
        Scan directories for VRT files based on the analysis mode (Factor Aggregation, Dimension Aggregation, Analysis).

        Returns:
            list: List of found VRT file paths.
        """
        vrt_files = []
        path_key = f"{self.sub_key_prefix} Result File"
        for layer in self.aggregation_layers:
            path = layer.get(path_key, "")
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
            f"Executing Factor Aggregation Workflow", tag="Geest", level=Qgis.Info
        )
        QgsMessageLog.logMessage(f"ID: {self.id}", tag="Geest", level=Qgis.Info)
        QgsMessageLog.logMessage(
            f"Key Prefix: {self.key_prefix}", tag="Geest", level=Qgis.Info
        )
        QgsMessageLog.logMessage(
            f"Aggregation Layers: {self.aggregation_layers}",
            tag="Geest",
            level=Qgis.Info,
        )

        vrt_files = self.get_vrt_list()

        if not vrt_files or not isinstance(vrt_files, list):
            QgsMessageLog.logMessage(
                f"No valid VRT files found in '{layers}'. Cannot proceed with aggregation.",
                tag="Geest",
                level=Qgis.Warning,
            )
            self.attributes["Result"] = "Factor Aggregation Workflow Failed"
            return False

        QgsMessageLog.logMessage(
            f"Found {len(vrt_files)} VRT files in '{self.key_prefix} Result File'. Proceeding with aggregation.",
            tag="Geest",
            level=Qgis.Info,
        )

        # Perform aggregation only if VRT files are provided
        result_file = self.aggregate_vrt_files(vrt_files)
        if result_file:
            QgsMessageLog.logMessage(
                "Aggregation Workflow completed successfully.",
                tag="Geest",
                level=Qgis.Info,
            )
            self.attributes["Result File"] = result_file
            self.attributes["Result"] = "Factor Aggregation Workflow Completed"
            return True
        else:
            QgsMessageLog.logMessage(
                "Aggregation failed due to missing or invalid VRT files.",
                tag="Geest",
                level=Qgis.Warning,
            )
            self.attributes["Result File"] = None
            self.attributes["Result"] = "Factor Aggregation Workflow Failed"
            return False
