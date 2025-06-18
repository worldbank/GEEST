import os
from qgis.core import QgsFeedback, QgsProcessingContext
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from .aggregation_workflow_base import AggregationWorkflowBase
from geest.utilities import resources_path
from geest.core import JsonTreeItem


class DimensionAggregationWorkflow(AggregationWorkflowBase):
    """
    Concrete implementation of a 'Dimension Aggregation' workflow.

    It will aggregate the factors within a dimension to create a single raster output.
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

        # Thread-safe initialization of attributes
        self.thread_safe_execute(self._initialize_attributes)

    def _initialize_attributes(self):
        """
        Initialize attributes in a thread-safe manner.
        """
        self.guids = (
            self.item.getDimensionFactorGuids()
        )  # Get a list of the items to aggregate
        self.id = (
            self.item.attribute("id").lower().replace(" ", "_")
        )  # Should not be needed anymore
        self.weight_key = "dimension_weighting"
        self.workflow_name = "dimension_aggregation"
        self.workflow_directory = os.path.join(
            self.working_directory, "dimension_aggregation"
        )
        if not os.path.exists(self.workflow_directory):
            os.makedirs(self.workflow_directory, exist_ok=True)

    def aggregate(self, input_files: list, index: int) -> str:
        """
        Perform weighted raster aggregation on the found raster files.

        :param input_files: dict of raster file paths to aggregate and their weights.
        :param index: The index of the area being processed.

        :return: Path to the aggregated raster file.
        """
        # Use the thread-safe aggregate method from the base class
        return self.thread_safe_execute(super().aggregate, input_files, index)

    def get_raster_dict(self, index: int) -> dict:
        """
        Get the list of rasters from the attributes that will be aggregated.

        :param index: The index of the area being processed.

        :return: dict of found raster file paths and their weights.
        """
        # Use the thread-safe get_raster_dict method from the base class
        return self.thread_safe_execute(super().get_raster_dict, index)

    def _process_aggregate_for_area(
        self,
        current_area,
        clip_area,
        current_bbox,
        index: int,
    ):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.

        :param current_area: Current area geometry.
        :param clip_area: Clip area geometry.
        :param current_bbox: Current bounding box geometry.
        :param index: The index of the area being processed.

        :return: Path to the aggregated raster file.
        """
        # Use the thread-safe _process_aggregate_for_area method from the base class
        return self.thread_safe_execute(
            super()._process_aggregate_for_area,
            current_area,
            clip_area,
            current_bbox,
            index,
        )
