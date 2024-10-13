import os
import glob
import shutil
from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsFeedback,
    QgsFeature,
    QgsVectorLayer,
    QgsField,
    QgsGeometry,
    QgsRasterLayer,
    QgsProject,
)
from qgis.PyQt.QtCore import QVariant
import processing  # QGIS processing toolbox
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem
from geest.core.utilities import GridAligner
from geest.core.algorithms import FeaturesPerCellProcessor


class PolygonPerCellWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'Use Polygon per Cell' workflow.
    """

    def __init__(self, item: JsonTreeItem, feedback: QgsFeedback):
        """
        Initialize the workflow with attributes and feedback.
        :param attributes: Item containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        """
        super().__init__(
            item, feedback
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        # TODO fix inconsistent abbreviation below for Poly
        self.workflow_name = "Use Poly per Cell"
        self.attributes = item.data(3)
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
        features_layer = QgsVectorLayer(
            self.attributes.get("Polygon per Cell Layer Source", "")
        )
        processor = FeaturesPerCellProcessor(
            output_prefix=self.layer_id,
            features_layer=features_layer,
            gpkg_path=self.gpkg_path,
            workflow_directory=self.workflow_directory,
        )
        QgsMessageLog.logMessage(
            "Polygon per Cell Processor Created", tag="Geest", level=Qgis.Info
        )

        vrt_path = processor.process_areas()
        self.attributes["Indicator Result File"] = vrt_path
        self.attributes["Indicator Result"] = "Use Polygon per Cell Workflow Completed"
        return True
