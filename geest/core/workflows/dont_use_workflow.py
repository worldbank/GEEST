import time
from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsFeedback,
    QgsProcessingContext,
    QgsGeometry,
)
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem


class DontUseWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'dont use' workflow.
    """

    def __init__(
        self,
        item: JsonTreeItem,
        cell_size_m: float,
        feedback: QgsFeedback,
        context: QgsProcessingContext,
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param item: Item containing workflow parameters.
        :param cell_size_m: Cell size in meters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        """
        super().__init__(
            item, cell_size_m, feedback, context
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.workflow_name = "do_not_use"
        self.attributes["result_file"] = ""
        self.attributes["result"] = ""
        self.attributes["result"] = "Don't Use Completed"

    def _process_features_for_area(self):
        pass

    def do_execute(self):
        pass

    # Default implementation of the abstract method - not used in this workflow
    def _process_raster_for_area(
        self,
        current_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_raster: str,
        index: int,
    ):
        """
        Executes the actual workflow logic for a single area using a raster.

        :current_area: Current polygon from our study area.
        :current_bbox: Bounding box of the above area.
        :area_raster: A raster layer of features to analyse that includes only bbox pixels in the study area.
        :index: Index of the current area.

        :return: Path to the reclassified raster.
        """
        pass

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
    ):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        pass
