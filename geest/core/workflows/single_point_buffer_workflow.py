import os
import glob
import shutil
from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsFeedback,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant
import processing  # QGIS processing toolbox
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem
from geest.core.utilities import GridAligner
from geest.core.algorithms import SinglePointBufferProcessor


class SinglePointBufferWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'Use Single Buffer Point' workflow.
    """

    def __init__(self, item: JsonTreeItem, feedback: QgsFeedback):
        """
        Initialize the workflow with attributes and feedback.
        :param item: Item containing workflow parameters.
        :param attributes: Item containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        """
        super().__init__(
            item, feedback
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.workflow_name = "Use Single Buffer Point"
        # Initialize GridAligner with grid size
        self.grid_aligner = GridAligner(grid_size=100)

    def do_execute(self):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """

        QgsMessageLog.logMessage(
            f"Executing {self.workflow_name}", tag="Geest", level=Qgis.Info
        )
        QgsMessageLog.logMessage(
            "----------------------------------", tag="Geest", level=Qgis.Info
        )
        for item in self.attributes.items():
            QgsMessageLog.logMessage(
                f"{item[0]}: {item[1]}", tag="Geest", level=Qgis.Info
            )
        QgsMessageLog.logMessage(
            "----------------------------------", tag="Geest", level=Qgis.Info
        )
        layer_source = self.attributes.get("Single Buffer Point Layer Shapefile", None)
        provider_type = "ogr"
        if not layer_source:
            layer_source = self.attributes.get(
                "Single Buffer Point Layer SourceD", None
            )
            provider_type = self.attributes.get(
                "Single Buffer Point Layer Provider Type", "ogr"
            )
        if not layer_source:
            QgsMessageLog.logMessage(
                "Single Buffer Point Layer Shapefile not found",
                tag="Geest",
                level=Qgis.Critical,
            )

            return False
        input_layer = QgsVectorLayer(layer_source, "points", provider_type)
        if not input_layer.isValid():
            QgsMessageLog.logMessage(
                "Single Buffer Point Layer not valid", tag="Geest", level=Qgis.Critical
            )
            return False

        buffer_distance = self.attributes.get("Single Buffer Distance", 1000)
        processor = SinglePointBufferProcessor(
            output_prefix=self.layer_id,
            buffer_distance=buffer_distance,
            input_layer=input_layer,
            gpkg_path=self.gpkg_path,
            workflow_directory=self.workflow_directory,
        )
        QgsMessageLog.logMessage(
            "Single Point Buffer Impact Processor Created", tag="Geest", level=Qgis.Info
        )

        vrt_path = processor.process_areas()
        self.attributes["Indicator Result File"] = vrt_path
        self.attributes["Indicator Result"] = (
            "Use Single Point Buffer Workflow Completed"
        )
        return True
