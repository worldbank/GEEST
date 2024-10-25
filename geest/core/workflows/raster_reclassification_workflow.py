import os
import glob
import shutil
from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsFeedback,
    QgsRasterLayer,
    QgsProcessingContext,
)
from qgis.PyQt.QtCore import QVariant
import processing  # QGIS processing toolbox
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem
from geest.core.algorithms import RasterReclassificationProcessor


class RasterReclassificationWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'Use Classify Poly into Classes' workflow.
    """

    def __init__(
        self,
        item: JsonTreeItem,
        feedback: QgsFeedback,
        context: QgsProcessingContext,
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param attributes: Item containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        """
        super().__init__(
            item, feedback, context
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.workflow_name = "Use Environmental Hazards"

    def do_execute(self):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """

        layer_name = self.attributes.get("Use Environmental Hazards Raster", None)

        if not layer_name:
            QgsMessageLog.logMessage(
                "Invalid points layer found in Use Environmental Hazards Raster, trying Use Environmental Hazards Layer Source.",
                tag="Geest",
                level=Qgis.Warning,
            )
            layer_name = self.attributes.get(
                "Use Environmental Hazards Layer Source", None
            )
            if not layer_name:
                QgsMessageLog.logMessage(
                    "No points layer found in Use Environmental Hazards Layer Source.",
                    tag="Geest",
                    level=Qgis.Warning,
                )
            return False

        features_layer = QgsRasterLayer(
            layer_name, "Environmental Hazards Raster", "gdal"
        )

        if self.layer_id == "fire":
            reclassification_rules = [
                "-inf",
                0,
                5.00,  # new value = 5
                0,
                1,
                4.00,  # new value = 4
                1,
                2,
                3.00,  # new value = 3
                2,
                5,
                2.00,  # new value = 2
                5,
                8,
                1.00,  # new value = 1
                8,
                "inf",
                0,  # new value = 0
            ]
        elif self.layer_id == "flood":
            reclassification_rules = [
                -1,
                0,
                5.00,  # new value = 5
                0,
                180,
                4.00,  # new value = 4
                180,
                360,
                3.00,  # new value = 3
                360,
                540,
                2.00,  # new value = 2
                540,
                720,
                1.00,  # new value = 1
                720,
                900,
                0,  # new value = 0
            ]
        elif self.layer_id == "landslide":
            reclassification_rules = [
                0,
                0,
                5.00,  # new value = 5
                1,
                1,
                4.00,  # new value = 4
                2,
                2,
                3.00,  # new value = 3
                3,
                3,
                2.00,  # new value = 2
                4,
                4,
                1.00,  # new value = 1
                5,
                5,
                0,  # new value = 0
            ]
        elif self.layer_id == "cyclone":
            reclassification_rules = [
                0,
                0,
                5.00,  # new value = 5
                0,
                25,
                4.00,  # new value = 4
                25,
                50,
                3.00,  # new value = 3
                50,
                75,
                2.00,  # new value = 2
                75,
                100,
                1.00,  # new value = 1
                100,
                "inf",
                0,  # new value = 0
            ]
        elif self.layer_id == "drought":
            reclassification_rules = [
                -3.4e38,
                -3.4e38,
                5.00,  # new value = 5
                0,
                1,
                4.00,  # new value = 4
                1,
                2,
                3.00,  # new value = 3
                2,
                3,
                2.00,  # new value = 2
                3,
                4,
                1.00,  # new value = 1
                4,
                5,
                0,  # new value = 0
            ]
        QgsMessageLog.logMessage(
            f"Reclassification Rules for {self.layer_id}: {reclassification_rules}",
            tag="Geest",
            level=Qgis.Info,
        )

        processor = RasterReclassificationProcessor(
            input_raster=features_layer,
            output_prefix=self.layer_id,
            reclassification_table=reclassification_rules,
            pixel_size=100,
            gpkg_path=self.gpkg_path,
            workflow_directory=self.workflow_directory,
            context=self.context,
        )

        QgsMessageLog.logMessage(
            "Use Environmental Hazards Processor Created", tag="Geest", level=Qgis.Info
        )

        vrt_path = processor.reclassify()
        self.attributes["Indicator Result File"] = vrt_path
        self.attributes["Result"] = "Use Environmental Hazards Workflow Completed"
        return True

    def _process_area(self):
        pass
