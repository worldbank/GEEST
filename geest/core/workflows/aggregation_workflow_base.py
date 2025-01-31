import os
from qgis.core import (
    Qgis,
    QgsFeedback,
    QgsRasterLayer,
    QgsProcessingContext,
    QgsGeometry,
)
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem
from geest.utilities import log_message


class AggregationWorkflowBase(WorkflowBase):
    """
    Base class for all aggregation workflows (factor, dimension, analysis)
    """

    def __init__(
        self,
        item: JsonTreeItem,
        cell_size_m: float,
        feedback: QgsFeedback,
        context: QgsProcessingContext,
        working_directory: str = None,
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param attributes: Item containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        :working_directory: Folder containing study_area.gpkg and where the outputs will be placed. If not set will be taken from QSettings.
        """
        super().__init__(
            item, cell_size_m, feedback, context, working_directory
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.guids = None  # This should be set by the child class - a list of guids of JSONTreeItems to aggregate
        self.id = None  # This should be set by the child class
        self.weight_key = None  # This should be set by the child class
        self.aggregation = True

    def aggregate(self, input_files: list, index: int) -> str:
        """
        Perform weighted raster aggregation on the found raster files.

        :param input_files: dict of raster file paths to aggregate and their weights.
        :param index: The index of the area being processed.

        :return: Path to the aggregated raster file.
        """
        if len(input_files) == 0:
            log_message(
                f"Error: Found no Input files. Cannot proceed with aggregation.",
                tag="Geest",
                level=Qgis.Warning,
            )
            return None

        # Load the layers
        raster_layers = [
            QgsRasterLayer(vf, f"raster_{i}") for i, vf in enumerate(input_files.keys())
        ]

        # Ensure all raster layers are valid and print filenames of invalid layers
        invalid_layers = [
            layer.source() for layer in raster_layers if not layer.isValid()
        ]
        if invalid_layers:
            log_message(
                f"Invalid raster layers found: {', '.join(invalid_layers)}",
                tag="Geest",
                level=Qgis.Critical,
            )

        # Create QgsRasterCalculatorEntries for each raster layer
        entries = []
        ref_names = []
        expression = ""
        sum_of_weights = 0
        for i, raster_layer in enumerate(raster_layers):
            if raster_layer.source() in invalid_layers:
                continue
            log_message(
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
            # input_files[raster_layer.source() returns the weight for the given layer
            weight = input_files[raster_layer.source()]
            if i == 0:
                expression = f"({weight} * {ref_names[i]}@1)"
            else:
                expression += f"+ ({weight} * {ref_names[i]}@1)"
            sum_of_weights += weight

        # I believe these are wrong and should be removed since the total weight
        # of the aggregate layers should already be 1.0 - Tim
        # Number of raster layers
        # layer_count = len(input_files) - len(invalid_layers)

        # Wrap the weighted sum and divide by the sum of weights
        # expression = f"({expression}) / {layer_count}"

        aggregation_output = os.path.join(
            self.workflow_directory, f"{self.id}_aggregated_{index}.tif"
        )

        log_message(
            f"Aggregating {len(input_files)} raster layers to {aggregation_output}",
            tag="Geest",
            level=Qgis.Info,
        )
        log_message(f"Aggregation Expression: {expression}")
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
        log_message(f"Calculator errors: {calc.lastError()}")
        if result != 0:
            log_message(
                "Raster aggregation completed successfully.",
                tag="Geest",
                level=Qgis.Info,
            )
            return None

        # Write the output path to the attributes
        # That will get passed back to the json model
        self.attributes[self.result_file_key] = aggregation_output

        return aggregation_output

    def get_raster_dict(self, index) -> list:
        """
        Get the list of rasters from the attributes that will be aggregated.

        (Factor Aggregation, Dimension Aggregation, Analysis).

        Parameters:
            index (int): The index of the area being processed.

        Returns:
            dict: dict of found raster file paths and their weights.
        """
        raster_files = {}
        if self.guids is None:
            raise ValueError("No GUIDs provided for aggregation")

        for guid in self.guids:

            item = self.item.getItemByGuid(guid)
            status = item.getStatus() == "Completed successfully"
            mode = item.attributes().get("analysis_mode", "Do Not Use") == "Do Not Use"
            excluded = item.getStatus() == "Excluded from analysis"
            id = item.attribute("id").lower()
            if not status and not mode and not excluded:
                raise ValueError(
                    f"{id} is not completed successfully and is not set to 'Do Not Use' or 'Excluded from analysis'"
                )

            if mode:
                log_message(
                    f"Skipping {item.attribute('id')} as it is set to 'Do Not Use'",
                    tag="Geest",
                    level=Qgis.Info,
                )
                continue
            if excluded:
                log_message(
                    f"Skipping {item.attribute('id')} as it is excluded from analysis",
                    tag="Geest",
                    level=Qgis.Info,
                )
                continue
            if not item.attribute(self.result_file_key, ""):
                log_message(
                    f"Skipping {id} as it has no result file",
                    tag="Geest",
                    level=Qgis.Info,
                )
                raise ValueError(f"{id} has no result file")

            layer_folder = os.path.dirname(item.attribute(self.result_file_key, ""))
            path = os.path.join(
                self.workflow_directory, layer_folder, f"{id}_masked_{index}.tif"
            )
            if os.path.exists(path):

                weight = item.attribute(self.weight_key, "")
                try:
                    weight = float(weight)
                except (ValueError, TypeError):
                    weight = 1.0  # Default fallback to 1.0 if weight is invalid

                raster_files[path] = weight

                log_message(f"Adding raster: {path} with weight: {weight}")

        log_message(
            f"Total raster files found: {len(raster_files)}",
            tag="Geest",
            level=Qgis.Info,
        )
        return raster_files

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
    ):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        _ = current_area  # Unused in this analysis
        _ = clip_area  # Unused in this analysis
        _ = current_bbox  # Unused in this analysis

        # Log the execution
        log_message(
            f"Executing {self.analysis_mode} Aggregation Workflow",
            tag="Geest",
            level=Qgis.Info,
        )
        raster_files = self.get_raster_dict(index)

        if not raster_files or not isinstance(raster_files, dict):
            error = f"No valid raster files found in '{self.guids}'. Cannot proceed with aggregation."
            log_message(
                error,
                tag="Geest",
                level=Qgis.Warning,
            )
            self.attributes[self.result_key] = (
                f"{self.analysis_mode} Aggregation Workflow Failed"
            )
            self.attributes["error"] = error

        log_message(
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
