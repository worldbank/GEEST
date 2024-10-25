from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsFeedback,
    QgsRasterLayer,
    QgsProcessingContext,
)
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem
from geest.core.algorithms import SafetyRasterReclassificationProcessor


class SafetyRasterWorkflow(WorkflowBase):
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
        self.workflow_name = "Use Nighttime Lights"

    def do_execute(self):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """

        layer_name = self.attributes.get("Use Nighttime Lights Raster", None)

        if not layer_name:
            QgsMessageLog.logMessage(
                "Invalid raster found in Use Nighttime Lights Raster, trying Use Nighttime Lights Layer Source.",
                tag="Geest",
                level=Qgis.Warning,
            )
            layer_name = self.attributes.get("Use Nighttime Lights Layer Source", None)
            if not layer_name:
                QgsMessageLog.logMessage(
                    "No points layer found in Use Nighttime Lights Layer Source.",
                    tag="Geest",
                    level=Qgis.Warning,
                )
            return False

        features_layer = QgsRasterLayer(layer_name, "Nighttime Lights Raster", "gdal")

        processor = SafetyRasterReclassificationProcessor(
            output_prefix=self.layer_id,
            input_raster=features_layer,
            pixel_size=100,
            gpkg_path=self.gpkg_path,
            grid_layer=self.bboxes_layer,
            workflow_directory=self.workflow_directory,
            context=self.context,
        )

        QgsMessageLog.logMessage(
            "Use Nighttime Lights Processor Created", tag="Geest", level=Qgis.Info
        )

        vrt_path = processor.process_areas()
        self.attributes["Indicator Result File"] = vrt_path
        self.attributes["Result"] = "Use Nighttime Lights Workflow Completed"
        return True
