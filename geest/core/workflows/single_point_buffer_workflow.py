import os
from qgis.core import (
    QgsMessageLog,
    QgsField,
    Qgis,
    QgsFeedback,
    QgsGeometry,
    QgsVectorLayer,
    QgsProcessingContext,
    QgsVectorLayer,
    QgsGeometry,
)
from qgis.PyQt.QtCore import QVariant
import processing
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem


class SinglePointBufferWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'Use Single Buffer Point' workflow.
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
        self.workflow_name = "use_single_buffer_point"

        layer_source = self.attributes.get("Single Buffer Point Layer Shapefile", None)
        provider_type = "ogr"
        if not layer_source:
            layer_source = self.attributes.get("Single Buffer Point Layer Source", None)
            provider_type = self.attributes.get(
                "Single Buffer Point Layer Provider Type", "ogr"
            )
        if not layer_source:
            QgsMessageLog.logMessage(
                "Single Buffer Point Layer Shapefile not found",
                tag="Geest",
                level=Qgis.Critical,
            )
            return False
        self.features_layer = QgsVectorLayer(layer_source, "points", provider_type)
        if not self.features_layer.isValid():
            QgsMessageLog.logMessage(
                "Single Buffer Point Layer not valid", tag="Geest", level=Qgis.Critical
            )
            QgsMessageLog.logMessage(
                f"Layer Source: {layer_source}", tag="Geest", level=Qgis.Critical
            )
            return False

        self.buffer_distance = int(
            self.attributes.get("Single Buffer Point Layer Distance", "5000")
        )
        self.workflow_is_legacy = False  # This is a new workflow, not a legacy one

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
        QgsMessageLog.logMessage(
            f"{self.workflow_name}  Processing Started", tag="Geest", level=Qgis.Info
        )

        # Step 1: Buffer the selected features
        buffered_layer = self._buffer_features(
            area_features, f"{self.layer_id}_buffered_{index}"
        )

        # Step 2: Assign values to the buffered polygons
        scored_layer = self._assign_scores(buffered_layer)

        # Step 3: Rasterize the scored buffer layer
        raster_output = self._rasterize(scored_layer, current_bbox, index)

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
                "DISTANCE": self.buffer_distance,  # 5 km buffer
                "SEGMENTS": 15,
                "DISSOLVE": True,
                "OUTPUT": output_path,
            },
        )["OUTPUT"]

        buffered_layer = QgsVectorLayer(output_path, output_name, "ogr")
        return buffered_layer

    def _assign_scores(self, layer: QgsVectorLayer) -> QgsVectorLayer:
        """
        Assign values to buffered polygons based 5 for presence of a polygon.

        Args:
            layer QgsVectorLayer: The buffered features layer.

        Returns:
            QgsVectorLayer: A new layer with a "value" field containing the assigned scores.
        """

        QgsMessageLog.logMessage(
            f"Assigning scores to {layer.name()}", tag="Geest", level=Qgis.Info
        )
        # Create a new field in the layer for the scores
        layer.startEditing()
        layer.dataProvider().addAttributes([QgsField("value", QVariant.Int)])
        layer.updateFields()

        # Assign scores to the buffered polygons
        score = 5
        for feature in layer.getFeatures():
            feature.setAttribute("value", score)
            layer.updateFeature(feature)

        layer.commitChanges()

        return layer

    # Remove once all workflows are updated
    def do_execute(self):
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
