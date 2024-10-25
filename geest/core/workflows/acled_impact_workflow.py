from qgis.core import QgsMessageLog, Qgis, QgsFeedback, QgsProcessingContext
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem
from geest.core.algorithms import AcledImpactRasterProcessor


class AcledImpactWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'Use CSV to Point Layer' workflow.
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
        self.workflow_name = "Use CSV to Point Layer"

    def do_execute(self):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """

        csv_file = self.attributes.get("Use CSV to Point Layer CSV File", "")
        processor = AcledImpactRasterProcessor(
            output_prefix=self.layer_id,
            csv_path=csv_file,
            gpkg_path=self.gpkg_path,
            workflow_directory=self.workflow_directory,
            context=self.context,
        )
        QgsMessageLog.logMessage(
            "Acled Impact Processor Created", tag="Geest", level=Qgis.Info
        )

        vrt_path = processor.process_areas()
        self.attributes["Indicator Result File"] = vrt_path
        self.attributes["Result"] = "Use Acled Impact Workflow Completed"
        return True
