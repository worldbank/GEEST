import os
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
from geest.core.algorithms.polygon_per_cell_processor import (
    assign_reclassification_to_polygons,
)


class PolygonPerCellWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'Use Polygon per Cell' workflow.
    """

    def __init__(
        self,
        item: JsonTreeItem,
        cell_size_m: float,
        feedback: QgsFeedback,
        context: QgsProcessingContext,
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param item: Item containing workflow parameters.
        :param cell_size_m: Cell size in meters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        """
        super().__init__(
            item, cell_size_m, feedback, context
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        # TODO fix inconsistent abbreviation below for Poly
        self.workflow_name = "use_poly_per_cell"

        layer_path = self.attributes.get("Polygon per Cell Shapefile", None)

        if not layer_path:
            QgsMessageLog.logMessage(
                "Invalid raster found in Polygon per Cell Shapefile, trying Polygon per Cell Layer Source.",
                tag="Geest",
                level=Qgis.Warning,
            )
            layer_path = self.attributes.get("Polygon per Cell Layer Source", None)
            if not layer_path:
                QgsMessageLog.logMessage(
                    "No points layer found in Polygon per Cell Layer Source.",
                    tag="Geest",
                    level=Qgis.Warning,
                )
                return False

        self.features_layer = QgsVectorLayer(
            layer_path, "Polygon per Cell Layer", "ogr"
        )
        self.workflow_is_legacy = False

    def _process_features_for_area(
        self,
        current_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
    ) -> str:
        """
        Executes the actual workflow logic for a single area
        Must be implemented by subclasses.

        :current_area: Current polygon from our study area.
        :current_bbox: Bounding box of the above area.
        :area_features: A vector layer of features to analyse that includes only features in the study area.
        :index: Iteration / number of area being processed.

        :return: A raster layer file path if processing completes successfully, False if canceled or failed.
        """
        area_features_count = area_features.featureCount()
        QgsMessageLog.logMessage(
            f"Features layer for area {index+1} loaded with {area_features_count} features.",
            tag="Geest",
            level=Qgis.Info,
        )
        # Step 1: Select grid cells that intersect with features
        output_path = os.path.join(
            self.workflow_directory, f"{self.layer_id}_grid_cells.gpkg"
        )
        # Step 2: Assign reclassification values to polygons based on their perimeter
        polygon_areas = assign_reclassification_to_polygons(area_features)
        raster_output = self._rasterize(
            polygon_areas,
            current_bbox,
            index,
            value_field="value",
            default_value=0,
        )
        return raster_output

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

    # TODO Remove when all workflows are refactored
    def do_execute(self):
        """
        Execute the workflow.
        """
        self._execute()

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
    ):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        pass
