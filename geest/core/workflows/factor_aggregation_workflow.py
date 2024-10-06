import os
from qgis.core import (
    QgsFeedback,
)
from .aggregation_workflow_base import AggregationWorkflowBase
from geest.utilities import resources_path
from geest.gui.treeview import JsonTreeItem


class FactorAggregationWorkflow(AggregationWorkflowBase):
    """
    Concrete implementation of a 'Factor Aggregation' workflow.

    It will aggregate the indicators within a factor to create a single raster output.
    """

    def __init__(self, item: dict, feedback: QgsFeedback):
        """
        Initialize the Factor Aggregation with attributes and feedback.

        ⭐️ Item is a reference - whatever you change in this item will directly update the tree

        :param item: JsonTreeItem containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        """
        super().__init__(item, feedback)

        self.aggregation_attributes = self.item.getFactorAttributes()
        self.id = self.aggregation_attributes[f"Factor ID"].lower().replace(" ", "_")
        self.layers = self.aggregation_attributes.get(f"Indicators", [])
        self.weight_key = "Indicator Weighting"
        self.result_file_tag = "Factor Result File"
        self.raster_path_key = "Indicator Result File"

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
            self.aggregation_attributes.get("Dimension ID").lower().replace(" ", "_"),
            self.aggregation_attributes.get("Factor ID").lower().replace(" ", "_"),
        )
        # Create the directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)

        return os.path.join(
            directory,
            f"aggregate_{self.id}" + f".{extension}",
        )
