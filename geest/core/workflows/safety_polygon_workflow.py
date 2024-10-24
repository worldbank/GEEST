from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsFeedback,
    QgsVectorLayer,
    QgsProcessingContext,
)
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem
from geest.core.algorithms import SafetyPerCellProcessor


class SafetyPolygonWorkflow(WorkflowBase):
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
        self.workflow_name = "Use Classify Poly into Classes"

    def do_execute(self):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        features_layer = QgsVectorLayer(
            self.attributes.get("Classify Poly into Classes Layer Source", "")
        )
        selected_field = self.attributes.get(
            "Classify Poly into Classes Selected Field", ""
        )
        processor = SafetyPerCellProcessor(
            output_prefix=self.layer_id,
            safety_layer=features_layer,
            safety_field=selected_field,
            workflow_directory=self.workflow_directory,
            gpkg_path=self.gpkg_path,
            context=self.context,
        )
        QgsMessageLog.logMessage(
            "Safety Per Cell Processor Created", tag="Geest", level=Qgis.Info
        )

        vrt_path = processor.process_areas()
        self.attributes["Indicator Result File"] = vrt_path
        self.attributes["Indicator Result"] = "Use Safety Per Cell Workflow Completed"
        return True
