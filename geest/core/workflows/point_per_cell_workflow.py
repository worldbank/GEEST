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
    QgsProcessingContext,
)
from qgis.PyQt.QtCore import QVariant
import processing  # QGIS processing toolbox
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem
from geest.core.utilities import GridAligner
from geest.core.algorithms import FeaturesPerCellProcessor


class PointPerCellWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'Use Point per Cell' workflow.
    """

    def __init__(
        self, item: JsonTreeItem, feedback: QgsFeedback, context: QgsProcessingContext
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
        self.workflow_name = "Use Point per Cell"
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

        layer_name = self.attributes.get("Point per Cell Shapefile", None)

        if not layer_name:
            QgsMessageLog.logMessage(
                "Invalid raster found in Point per Cell Shapefile, trying Point per Cell Layer Source.",
                tag="Geest",
                level=Qgis.Warning,
            )
            layer_name = self.attributes.get("Point per Cell Layer Source", None)
            if not layer_name:
                QgsMessageLog.logMessage(
                    "No points layer found in Point per Cell Layer Source.",
                    tag="Geest",
                    level=Qgis.Warning,
                )
            return False

        points_layer = QgsVectorLayer(layer_name, "Point per Cell Layer", "ogr")
        processor = FeaturesPerCellProcessor(
            output_prefix=self.layer_id,
            features_layer=points_layer,
            gpkg_path=self.gpkg_path,
            workflow_directory=self.workflow_directory,
        )
        QgsMessageLog.logMessage(
            "Point per Cell Processor Created", tag="Geest", level=Qgis.Info
        )

        vrt_path = processor.process_areas()
        self.attributes["Indicator Result File"] = vrt_path
        self.attributes["Indicator Result"] = "Use Point per Cell Workflow Completed"
        return True
