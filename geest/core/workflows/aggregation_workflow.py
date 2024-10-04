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
        for layer in self.aggregation_layers:
            self.name = (
                layer.get(f"{self.sub_key_prefix} Name", None).lower().replace(" ", "_")
            )
        self.dimension_id = self.attributes.get("Dimension ID", None).lower()

        self.project_base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../..")
        )

    def get_weights(self, num_layers: int) -> list:
        """
        Retrieve default weights based on the number of layers.
        :param num_layers: Number of raster layers to aggregate.
        :return: List of weights for the layers.
        """
        if num_layers == 1:
            return [1.0]
        elif num_layers == 2:
            return [0.5, 0.5]
        elif num_layers == 3:
            return [0.50, 0.25, 0.25]
        else:
            return [1.0] * num_layers  # Handle unexpected cases

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
                f"aggregate_{self.name}" + f".{extension}",
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
            entry = QgsRasterCalculatorEntry()
            entry.ref = f"layer_{i+1}@1"  # layer_1@1, layer_2@1, etc.
            entry.raster = raster_layer
            entry.bandNumber = 1
            entries.append(entry)

        # Assign default weights (you can modify this as needed)
        weights = self.get_weights(len(vrt_files))

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
                aggregation_output_8bit, f"aggregated_{self.name}"
            )
            if aggregated_layer.isValid():

                qml_src_path = resources_path(
                    "resources", "qml", f"{self.dimension_id}.qml"
                )

                if os.path.exists(qml_src_path):
                    qml_dest_path = self.get_aggregation_output_path("qml")
                    qml_dest_path_8bit = qml_dest_path.replace(".qml", "_8bit.qml")
                    shutil.copy(qml_src_path, qml_dest_path_8bit)
                    QgsMessageLog.logMessage(
                        f"Copied QML style file to {qml_dest_path_8bit}",
                        tag="Geest",
                        level=Qgis.Info,
                    )
                else:
                    QgsMessageLog.logMessage(
                        f"QML style file not found: {qml_src_path}",
                        tag="Geest",
                        level=Qgis.Warning,
                    )
                if os.path.exists(qml_dest_path_8bit):

                    result = aggregated_layer.loadNamedStyle(qml_dest_path_8bit)
                    if result[0]:  # Check if the style was successfully loaded
                        QgsMessageLog.logMessage(
                            "Successfully applied QML style.",
                            tag="Geest",
                            level=Qgis.Info,
                        )
                    else:
                        QgsMessageLog.logMessage(
                            f"Failed to apply QML style: {result[1]}",
                            tag="Geest",
                            level=Qgis.Warning,
                        )

                    QgsProject.instance().addMapLayer(aggregated_layer)
                    QgsMessageLog.logMessage(
                        "Added VRT layer to the map.", tag="Geest", level=Qgis.Info
                    )
                else:
                    QgsMessageLog.logMessage(
                        "QML not in the directory.", tag="Geest", level=Qgis.Critical
                    )
                    QgsProject.instance().addMapLayer(aggregated_layer)
                    return aggregation_output
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

    def get_vrt_files_by_analysis_mode(self, base_paths: list) -> list:
        """
        Scan directories for VRT files based on the analysis mode (Factor Aggregation, Dimension Aggregation, Analysis).

        Parameters:
            base_paths (list): List of base paths to search for VRT files.

        Returns:
            list: List of found VRT file paths.
        """
        vrt_files = []

        # Iterate through each provided base path
        for base_path in base_paths:
            # Construct the search path based on analysis mode
            if self.analysis_mode == "Factor Aggregation":
                search_directory = os.path.join(
                    base_path,
                    self.attributes.get("Dimension ID"),
                )
            elif self.analysis_mode == "Dimension Aggregation":
                search_directory = os.path.join(
                    base_path,
                    self.attributes.get("Dimension ID"),
                )
            else:  # Analysis level
                search_directory = os.path.join(
                    base_path,
                )

            # Debug log to show the directory being searched
            QgsMessageLog.logMessage(
                f"Searching directory: {search_directory} for VRT files.",
                tag="Geest",
                level=Qgis.Info,
            )

            # If the directory exists, look for VRT files recursively
            if os.path.exists(search_directory):
                # Use glob to find all VRT files recursively in the search directory
                search_pattern = os.path.join(search_directory, "**", "*.vrt")
                found_vrts = glob.glob(search_pattern, recursive=True)

                # Debug log for each found VRT file
                for vrt_file in found_vrts:
                    QgsMessageLog.logMessage(
                        f"Found VRT file: {vrt_file}", tag="Geest", level=Qgis.Info
                    )

                vrt_files.extend(found_vrts)
            else:
                # Log if the directory does not exist
                QgsMessageLog.logMessage(
                    f"Directory does not exist: {search_directory}",
                    tag="Geest",
                    level=Qgis.Warning,
                )

        # Debug log to show how many VRT files were found
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

        vrt_files = self.get_vrt_files_by_analysis_mode(
            base_paths=[self.workflow_directory]
        )

        # Access the 'Dimensions/Factors/Indicators' key in the attributes dictionary
        QgsMessageLog.logMessage(str(self.attributes), tag="Geest", level=Qgis.Info)
        QgsMessageLog.logMessage(
            str(self.attributes.get(f"{self.key_prefix}s", [])),
            tag="Geest",
            level=Qgis.Info,
        )

        if self.key_prefix == "Factor":
            layers = self.attributes.get("Indicators", [])
        elif self.key_prefix == "Dimension":
            layers = self.attributes.get("Factors", [])
        elif self.key_prefix == "Analysis":
            layers = self.attributes.get(f"Dimensions", [])

        # Traverse through each resource and get the 'Result File'
        for layer in layers:
            if self.key_prefix == "Factor":
                result_file = layer.get("Indicator Result File")
            elif self.key_prefix == "Dimension":
                result_file = layer.get("Factor Result File")
            elif self.key_prefix == "Analysis":
                result_file = layer.get("Dimension Result File")
            if result_file:
                vrt_files.append(result_file)
                QgsMessageLog.logMessage(
                    f"Found VRT file: {result_file}", tag="Geest", level=Qgis.Info
                )

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
