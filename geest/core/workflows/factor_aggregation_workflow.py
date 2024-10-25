import os
from qgis.core import QgsFeedback, QgsProcessingContext
from .aggregation_workflow_base import AggregationWorkflowBase
from geest.utilities import resources_path
from geest.core import JsonTreeItem


class FactorAggregationWorkflow(AggregationWorkflowBase):
    """
    Concrete implementation of a 'Factor Aggregation' workflow.

    It will aggregate the indicators within a factor to create a single raster output.
    """

    def __init__(
        self, item: dict, feedback: QgsFeedback, context: QgsProcessingContext
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

    def _process_area(self):
        pass
