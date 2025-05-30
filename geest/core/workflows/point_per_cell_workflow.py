import os
from qgis.core import (
    Qgis,
    QgsGeometry,
    QgsFeedback,
    QgsVectorLayer,
    QgsProcessingContext,
)
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem
from geest.core.algorithms.features_per_cell_processor import (
    select_grid_cells,
    assign_values_to_grid,
)
from geest.utilities import log_message


class PointPerCellWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'use_point_per_cell' workflow.
    """

    def __init__(
        self,
        item: JsonTreeItem,
        cell_size_m: float,
        feedback: QgsFeedback,
        context: QgsProcessingContext,
        working_directory: str = None,
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param attributes: Item containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        :working_directory: Folder containing study_area.gpkg and where the outputs will be placed. If not set will be taken from QSettings.
        """
        super().__init__(
            item, cell_size_m, feedback, context, working_directory
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.workflow_name = "use_point_per_cell"
        layer_path = self.attributes.get("point_per_cell_shapefile", None)

        if not layer_path:
            layer_path = self.attributes.get("point_per_cell_layer_source", None)
            if not layer_path:
                error = "No point per cell layer provided."
                self.attributes["error"] = error
                # Raise an exception using our error message
                raise Exception(error)
        try:
            log_message(
                f"Loading point per cell layer: {layer_path}",
                tag="Geest",
                level=Qgis.Info,
            )
            self.features_layer = QgsVectorLayer(
                layer_path, "point_per_cell_layer", "ogr"
            )
            if not self.features_layer.isValid():
                error = f"Point per cell layer is not valid. : {layer_path}"
                self.attributes["error"] = error
                self.attributes["result"] = f"{self.workflow_name} Workflow Failed"
                raise Exception(error)
        except Exception as e:
            log_message(
                f"Error loading point per cell layer: {str(e)}",
                tag="Geest",
                level=Qgis.Critical,
            )
            error = f"Error loading point per cell layer: {str(e)}"
            self.attributes["error"] = error
            self.attributes["result"] = f"{self.workflow_name} Workflow Failed"

            raise Exception(error)
        self.feedback.setProgress(
            1.0
        )  # We just use nominal intervals for progress updates

    def _process_features_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
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
        log_message(
            f"Features layer for area {index+1} loaded with {area_features_count} features.",
            tag="Geest",
            level=Qgis.Info,
        )
        # Step 1: Select grid cells that intersect with features
        output_path = os.path.join(
            self.workflow_directory, f"{self.layer_id}_grid_cells.gpkg"
        )
        area_grid = select_grid_cells(
            self.grid_layer, area_features, output_path, self.feedback
        )

        # Step 2: Assign values to grid cells
        grid = assign_values_to_grid(area_grid, self.feedback)

        # Step 3: Rasterize the grid layer using the assigned values
        # Create a scored boundary layer
        raster_output = self._rasterize(
            grid,
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
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_raster: str,
        index: int,
    ):
        """
        Executes the actual workflow logic for a single area using a raster.

        :current_area: Current polygon from our study area.
        :clip_area: Polygon to clip the raster to which is aligned to cell edges.
        :current_bbox: Bounding box of the above area.
        :area_raster: A raster layer of features to analyse that includes only bbox pixels in the study area.
        :index: Index of the current area.

        :return: Path to the reclassified raster.
        """
        pass

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
    ):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        pass
