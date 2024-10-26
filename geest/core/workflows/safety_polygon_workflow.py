from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsFeedback,
    QgsGeometry,
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

        layer_name = self.attributes.get("Classify Poly into Classes Shapefile", None)

        if not layer_name:
            QgsMessageLog.logMessage(
                "Invalid raster found in Classify Poly into Classes Shapefile, trying Classify Poly into Classes Layer Source.",
                tag="Geest",
                level=Qgis.Warning,
            )
            layer_name = self.attributes.get(
                "Classify Poly into Classes Layer Source", None
            )
            if not layer_name:
                QgsMessageLog.logMessage(
                    "No points layer found in Classify Poly into Classes Layer Source.",
                    tag="Geest",
                    level=Qgis.Warning,
                )
            return False

        features_layer = QgsVectorLayer(layer_name, "features_layer", "ogr")

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
        self.attributes["Result"] = "Use Safety Per Cell Workflow Completed"
        return True

    def _process_features_for_area(self):
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
