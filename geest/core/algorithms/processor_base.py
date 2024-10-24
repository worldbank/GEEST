import os
from qgis.core import (
    QgsFeatureRequest,
    QgsGeometry,
    QgsProcessingFeedback,
    QgsProcessingException,
    QgsVectorLayer,
    QgsMessageLog,
    QgsVectorFileWriter,
    QgsWkbTypes,
    Qgis,
    QgsFeedback,
)
from qgis.PyQt.QtCore import pyqtSignal
from .area_iterator import AreaIterator
from .utilities import assign_crs_to_raster_layer
from geest.core import JsonTreeItem


class ProcessorBase:
    """
    Base class for all processors. Provides a common interface for all processors to implement.
    """

    progress = pyqtSignal(int)

    def __init__(self, item: JsonTreeItem, feedback: QgsFeedback):
        """
        Initialize the processor with attributes and feedback.
        :param item: Item containing processor parameters.
        :param feedback: QgsFeedback object for cancellation.
        """
        self.attributes = item.attributes
        self.feedback = feedback
        self.output_prefix = output_prefix
        self.workflow_directory = workflow_directory

    def _process_area(
        self,
        area_geom: QgsGeometry,
        area_bbox: QgsRectangle,
        progress: float,
        target_crs: str,
    ) -> str:
        """
        Process the current area by applying the processor's algorithm to the selected features.

        Args:
            area_geom (QgsGeometry): The geometry of the current area to process.
            area_bbox (QgsRectangle): The bounding box of the current area to process.
            progress (float): The progress of the current area processing.
            target_crs (str): The target CRS for the output raster.

        Returns:
            str: The file path to the output raster vrt.
        """
        raise NotImplementedError
