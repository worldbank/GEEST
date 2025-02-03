import os
from qgis.core import (
    Qgis,
    QgsFeedback,
    QgsField,
    QgsGeometry,
    QgsProcessingContext,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant
import processing
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem
from geest.core.algorithms.features_per_cell_processor import (
    select_grid_cells,
)
from geest.utilities import log_message


class StreetLightsBufferWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'use_street_lights' workflow.
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
        self.workflow_name = "use_street_lights"

        layer_path = self.attributes.get("street_lights_shapefile", None)

        if not layer_path:
            log_message(
                "Invalid raster found in street_lights_shapefile, trying street_lights_point_layer_source.",
                tag="Geest",
                level=Qgis.Warning,
            )
            layer_path = self.attributes.get("street_lights_layer_source", None)
            if not layer_path:
                log_message(
                    "No points layer found in street_lights_layer_source.",
                    tag="Geest",
                    level=Qgis.Warning,
                )
                error = f"Streetlights point layer is not set correctly: Shapefile: {self.street_lights_shapefile} "
                error += f"Shapefile: {self.street_lights_shapefile} "
                error += f"Layer Source: {self.street_lights_layer_source} "
                self.attributes["error"] = error
                raise Exception(error)

        self.features_layer = QgsVectorLayer(layer_path, "points", "ogr")
        if not self.features_layer.isValid():
            log_message("street lights source file not valid", level=Qgis.Critical)
            log_message(f"Layer Source: {layer_path}", level=Qgis.Critical)
            error += f"Shapefile: {self.street_lights_shapefile} "
            error += f"Layer Source: {self.street_lights_layer_source} "
            self.attributes["error"] = error
            raise Exception(error)

        self.buffer_distance = 20  # 20m buffer

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
        log_message(f"{self.workflow_name}  Processing Started")

        # Step 1: Buffer the selected features
        buffered_layer = self._buffer_features(
            area_features, f"{self.layer_id}_buffered_{index}"
        )
        # Step 2: Select grid cells that intersect with features
        output_path = os.path.join(
            self.workflow_directory, f"{self.layer_id}_grid_cells.gpkg"
        )
        area_grid = select_grid_cells(self.grid_layer, area_features, output_path)

        # Step 3: Assign scores to the grid layer
        grid_layer = self._score_grid(area_grid, buffered_layer)

        # Step 4: Rasterize the grid layer using the assigned scores
        raster_output = self._rasterize(
            grid_layer,
            current_bbox,
            index,
            value_field="score",
            default_value=0,
        )

        return raster_output

    def _buffer_features(
        self, layer: QgsVectorLayer, output_name: str
    ) -> QgsVectorLayer:
        """
        Buffer the input features by the buffer_distance km.

        Args:
            layer (QgsVectorLayer): The input feature layer.
            output_name (str): A name for the output buffered layer.

        Returns:
            QgsVectorLayer: The buffered features layer.
        """
        output_path = os.path.join(self.workflow_directory, f"{output_name}.shp")
        buffered_layer = processing.run(
            "native:buffer",
            {
                "INPUT": layer,
                "DISTANCE": self.buffer_distance,  # 20m buffer
                "SEGMENTS": 15,
                "DISSOLVE": True,
                "OUTPUT": output_path,
            },
        )["OUTPUT"]

        buffered_layer = QgsVectorLayer(output_path, output_name, "ogr")
        return buffered_layer

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

    def _score_grid(
        self, grid_layer: QgsVectorLayer, buffered_layer: QgsVectorLayer
    ) -> QgsVectorLayer:
        """
        Assign scores to a grid layer and rasterize it.

        Args:
            grid_layer (QgsVectorLayer): The grid layer representing the study area.
            buffered_layer (QgsVectorLayer): Buffered layer to evaluate intersections.
            index (int): Index for output file naming.

        Returns:
            str: Path to the output raster file.
        """
        log_message(
            "Assigning scores to grid layer based on intersection with buffered layer",
            tag="Geest",
            level=Qgis.Info,
        )

        # Add a new attribute to the grid layer for storing the score
        grid_layer.startEditing()
        if not grid_layer.fields().indexFromName("score") >= 0:
            grid_layer.dataProvider().addAttributes([QgsField("score", QVariant.Int)])
            grid_layer.updateFields()

        # Assign scores based on intersection with the buffered layer
        for grid_feature in grid_layer.getFeatures():
            grid_geom = grid_feature.geometry()
            max_score = 0

            for buffered_feature in buffered_layer.getFeatures():
                buffered_geom = buffered_feature.geometry()
                intersection = grid_geom.intersection(buffered_geom)
                if intersection.isEmpty():
                    continue

                overlap_percent = (intersection.area() / grid_geom.area()) * 100

                log_message(
                    f"Overlap percentage: {overlap_percent}",
                    tag="Geest",
                    level=Qgis.Info,
                )

                # Determine score based on overlap percentage
                if 80 <= overlap_percent <= 100:
                    max_score = max(max_score, 5)
                elif 60 <= overlap_percent < 80:
                    max_score = max(max_score, 4)
                elif 40 <= overlap_percent < 60:
                    max_score = max(max_score, 3)
                elif 20 <= overlap_percent < 40:
                    max_score = max(max_score, 2)
                elif 1 <= overlap_percent < 20:
                    max_score = max(max_score, 1)

            # Update the "score" attribute for the feature
            grid_feature.setAttribute("score", max_score)
            grid_layer.updateFeature(grid_feature)

        grid_layer.commitChanges()
        return grid_layer
