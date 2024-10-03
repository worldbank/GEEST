import os
import shutil
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


class FactorAggregationWorkflow(WorkflowBase):
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
        self.factor_id = self.attributes["id"].lower()
        self.indicators = self.attributes.get("Indicators", [])
        for indicator in self.indicators:
            self.indicator_name = indicator.get("name", None).lower().replace(" ", "_")

        self.project_base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../..")
        )

    def get_layer_weights(self, num_layers: int) -> list:
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
            return [0.33, 0.33, 0.34]
        else:
            return [1.0] * num_layers  # Handle unexpected cases

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
        weights = self.get_layer_weights(len(vrt_files))

        # Build the calculation expression
        expression = " + ".join(
            [f"({weights[i]} * layer_{i+1}@1)" for i in range(len(vrt_files))]
        )

        # Define output path for the aggregated raster
        aggregation_output = os.path.join(
            self.workflow_directory, "contextual", f"{self.indicator_name}.tif"
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
                aggregation_output_8bit, f"{self.indicator_name}"
            )
            if aggregated_layer.isValid():
                # Copy the style (.qml) file to the same directory as the VRT
                style_folder = os.path.join(
                    self.project_base_dir, "resources", "qml"
                )  # assuming 'style' folder path
                qml_src_path = os.path.join(style_folder, "Contextual.qml")

                if os.path.exists(qml_src_path):
                    qml_dest_path = os.path.join(
                        self.workflow_directory,
                        "contextual",
                        os.path.basename(aggregation_output_8bit).replace(
                            ".tif", ".qml"
                        ),
                    )
                    shutil.copy(qml_src_path, qml_dest_path)
                    QgsMessageLog.logMessage(
                        f"Copied QML style file to {qml_dest_path}",
                        tag="Geest",
                        level=Qgis.Info,
                    )
                else:
                    QgsMessageLog.logMessage(
                        f"QML style file not found: {qml_src_path}",
                        tag="Geest",
                        level=Qgis.Warning,
                    )
                if os.path.exists(qml_dest_path):

                    result = aggregated_layer.loadNamedStyle(qml_dest_path)
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

    def execute(self):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        # Log the execution
        QgsMessageLog.logMessage(
            f"Executing Factor Aggregation Workflow", tag="Geest", level=Qgis.Info
        )

        # Get VRT file paths from self.attributes["Result File"]
        vrt_files = []

        # Access the 'Indicators' key in the attributes dictionary
        indicators = self.attributes.get("Indicators", [])

        # Traverse through each indicator and get the 'Result File'
        for indicator in indicators:
            result_file = indicator.get("Result File", None)
            if result_file:
                vrt_files.append(result_file)

            if not vrt_files or not isinstance(vrt_files, list):
                QgsMessageLog.logMessage(
                    f"No valid VRT files found in '{indicators}'. Cannot proceed with aggregation.",
                    tag="Geest",
                    level=Qgis.Warning,
                )
                self.attributes["Result"] = "Factor Aggregation Workflow Failed"
                return False

        QgsMessageLog.logMessage(
            f"Found {len(vrt_files)} VRT files in 'Result File'. Proceeding with aggregation.",
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
