import os
import glob
from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsFeedback,
    QgsRasterLayer,
    QgsProject,
)
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from qgis.PyQt.QtCore import QVariant
import processing  # QGIS processing toolbox
from .workflow_base import WorkflowBase


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
        # self.layer_id = self.attributes["ID"].lower()

    def scan_working_directory_for_vrt(self, working_directory: str) -> list:
        """
        Scans the provided working directory and its subdirectories recursively for VRT files and returns a list of found VRT file paths.

        :param working_directory: The base directory to scan for VRT files.
        :return: List of found VRT file paths.
        """
        vrt_files = []
        required_vrt_types = [
            "workplace_index_score",
            "pay_parenthood_index_score",
            "entrepeneurship_index _score",
        ]  # Example: we expect these VRT types

        # Recursively scan for VRT files in the working directory
        found_files = glob.glob(
            os.path.join(working_directory, "**", "*.vrt"), recursive=True
        )

        # Filter and collect VRT files based on their type (e.g., WD, RF, FIN)
        for vrt_file in found_files:
            for vrt_type in required_vrt_types:
                if vrt_type in os.path.basename(vrt_file):
                    vrt_files.append(vrt_file)
                    QgsMessageLog.logMessage(
                        f"Found VRT file: {vrt_file}", tag="Geest", level=Qgis.Info
                    )

        return vrt_files

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
        if len(vrt_files) == 0:  # Expecting 3 VRTs: WD, RF, FIN
            QgsMessageLog.logMessage(
                f"Not all required VRT files found. Found {len(vrt_files)} VRT files. Cannot proceed with aggregation.",
                tag="Geest",
                level=Qgis.Warning,
            )
            return

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
            return

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
            self.workflow_directory, f"contextual_aggregated_score.tif"
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

        if result == 0:
            QgsMessageLog.logMessage(
                "Raster aggregation completed successfully.",
                tag="Geest",
                level=Qgis.Info,
            )
            # Add the aggregated raster to the map
            aggregated_layer = QgsRasterLayer(
                aggregation_output, f"contextual_aggregated_score"
            )
            if aggregated_layer.isValid():
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
        # Get the indicators beneath this factor and combine them into a single raster
        # proportional to the weight of each indicator
        QgsMessageLog.logMessage(f"Factor attributes", tag="Geest", level=Qgis.Info)
        QgsMessageLog.logMessage(f"{self.attributes}", tag="Geest", level=Qgis.Info)

        QgsMessageLog.logMessage(
            f"----------------------------", tag="Geest", level=Qgis.Info
        )
        # Directories where the VRTs are expected to be found

        # for key, value in self.attributes:
        #    QgsMessageLog.logMessage(
        #        f"Key: {key}, Value: {value}", tag="Geest", level=Qgis.Info
        #    )
        # QgsMessageLog.logMessage(
        #    f"----------------------------", tag="Geest", level=Qgis.Info
        # )

        # Directory where the VRTs are expected to be found
        self.workflow_directory = self._create_workflow_directory(
            "contextual",
            self.factor_id,
        )

        # Scan the working directory for VRT files
        vrt_files = self.scan_working_directory_for_vrt(self.workflow_directory)

        # Perform aggregation only if all necessary VRTs are found
        if len(vrt_files) > 0:  # Ensure we have all three VRT files
            result_file = self.aggregate_vrt_files(vrt_files)
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
                "Aggregation could not proceed. Missing VRT files.",
                tag="Geest",
                level=Qgis.Warning,
            )
            self.attributes["Result File"] = None
            self.attributes["Result"] = "Factor Aggregation Workflow Failed"

            return False
