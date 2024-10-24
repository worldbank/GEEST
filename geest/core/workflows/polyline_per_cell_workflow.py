from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsFeedback,
    QgsVectorLayer,
    QgsProcessingContext,
)
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem
from geest.core.algorithms import FeaturesPerCellProcessor


class PolylinePerCellWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'Use Polyline per Cell' workflow.
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
        self.workflow_name = "Use Polyline per Cell"

    def do_execute(self):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """

        layer_name = self.attributes.get("Polyline per Cell Shapefile", None)

        if not layer_name:
            QgsMessageLog.logMessage(
                "Invalid raster found in Polyline per Cell Shapefile, trying Polyline per Cell Layer Source.",
                tag="Geest",
                level=Qgis.Warning,
            )
            layer_name = self.attributes.get("Polyline per Cell Layer Source", None)
            if not layer_name:
                QgsMessageLog.logMessage(
                    "No points layer found in Polyline per Cell Layer Source.",
                    tag="Geest",
                    level=Qgis.Warning,
                )
            return False

        features_layer = QgsVectorLayer(layer_name, "Polyline per Cell", "ogr")

        processor = FeaturesPerCellProcessor(
            output_prefix=self.layer_id,
            features_layer=features_layer,
            gpkg_path=self.gpkg_path,
            workflow_directory=self.workflow_directory,
        )
        QgsMessageLog.logMessage(
            "Polyline per Cell Processor Created", tag="Geest", level=Qgis.Info
        )

        vrt_path = processor.process_areas()
        self.attributes["Indicator Result File"] = vrt_path
        self.attributes["Indicator Result"] = "Use Polyline per Cell Workflow Completed"
        return True
