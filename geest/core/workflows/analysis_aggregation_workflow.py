import os
from qgis.core import (
    QgsFeedback,
)
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from .aggregation_workflow_base import AggregationWorkflowBase
from geest.utilities import resources_path
from geest.gui.views import JsonTreeItem


class AnalysisAggregationWorkflow(AggregationWorkflowBase):
    """
    Concrete implementation of an 'Analysis Aggregation' workflow.

    It will aggregate the dimensions within an analysis to create a single raster output.
    """

    def __init__(self, item: JsonTreeItem, feedback: QgsFeedback):
        """
        Initialize the Analysis Aggregation with attributes and feedback.

        ⭐️ Item is a reference - whatever you change in this item will directly update the tree

        :param JsonTreeItem: Treeview item containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        """
        super().__init__(item, feedback)
        self.id = "geest_analysis"
        self.aggregation_attributes = self.item.getAnalysisAttributes()
        self.layers = self.aggregation_attributes.get(f"Dimensions", [])
        self.weight_key = "Dimension Weighting"
        self.result_file_tag = "Analysis Result File"
        self.raster_path_key = "Dimension Result File"

    def output_path(self, extension: str) -> str:
        """
        Define output path for the aggregated raster based on the analysis mode.

        Parameters:
            extension (str): The file extension for the output file.

        Returns:
            str: Path to the aggregated raster file.

        """
        directory = self.workflow_directory
        # Create the directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)

        return os.path.join(
            directory,
            f"aggregate_{self.id}" + f".{extension}",
        )
