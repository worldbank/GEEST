import os
from qgis.core import (
    QgsFeedback,
)
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from .aggregation_base_workflow import AggregationBaseWorkflow
from geest.utilities import resources_path


class FactorAggregationWorkflow(AggregationBaseWorkflow):
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
        self.id = self.attributes[f"Factor ID"].lower().replace(" ", "_")
        self.layers = self.attributes.get(f"Indicators", [])
        self.weight_key = "Indicator Weighting"
        self.result_file_tag = "Factor Result File"  # This should be set by the child class e.g. "Factor Result File"
        self.vrt_path_key = "Indicator Result File"  # This should be set by the child class e.g. "Indicator Result File"

    def output_path(self, extension: str) -> str:
        """
        Define output path for the aggregated raster based on the analysis mode.

        Parameters:
            extension (str): The file extension for the output file.

        Returns:
            str: Path to the aggregated raster file.

        """
        return os.path.join(
            self.workflow_directory,
            self.attributes.get("Dimension ID").lower().replace(" ", "_"),
            self.attributes.get("Factor ID").lower().replace(" ", "_"),
            +f"aggregate_{self.id}" + f".{extension}",
        )
