import os
from qgis.core import (
    QgsFeedback,
)
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from .aggregation_workflow_base import AggregationWorkflowBase
from geest.utilities import resources_path


class DimensionAggregationWorkflow(AggregationWorkflowBase):
    """
    Concrete implementation of a 'Dimension Aggregation' workflow.

    It will aggregate the factors within a dimension to create a single raster output.

    """

    def __init__(self, attributes: dict, feedback: QgsFeedback):
        """
        Initialize the Dimension Aggregation with attributes and feedback.
        :param attributes: Dictionary containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        """
        super().__init__(attributes, feedback)
        self.id = self.attributes[f"Dimension ID"].lower().replace(" ", "_")
        self.layers = self.attributes.get(f"Factors", [])
        self.weight_key = "Factor Weighting"
        self.result_file_tag = "Dimension Result File"
        self.vrt_path_key = "Factor Result File"

    def output_path(self, extension: str) -> str:
        """
        Define output path for the aggregated raster based on the analysis mode.

        Parameters:
            extension (str): The file extension for the output file.

        Returns:
            str: Path to the aggregated raster file.

        """
        directory = os.path.join(
            self.workflow_directory,
            self.attributes.get("Dimension ID").lower().replace(" ", "_"),
        )
        # Create the directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)

        return os.path.join(
            directory,
            f"aggregate_{self.id}" + f".{extension}",
        )
