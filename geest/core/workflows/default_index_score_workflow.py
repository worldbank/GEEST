import os
import glob
from qgis.core import (
    Qgis,
    QgsFeature,
    QgsFeedback,
    QgsField,
    QgsGeometry,
    QgsMessageLog,
    QgsProcessingContext,
    QgsProcessingException,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant
import processing  # QGIS processing toolbox
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem


class DefaultIndexScoreWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'Use Default Index Score' workflow.
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
        self.workflow_name = "Use Default Index Score"
        self.index_score = (self.attributes.get("Default Index Score", 0) / 100) * 5
        self.workflow_is_legacy = False
        self.gpkg_path = os.path.join(
            self.working_directory, "study_area", "study_area.gpkg"
        )
        # Initialize features_layer from a layer in the GeoPackage
        self.features_layer = QgsVectorLayer(
            f"{self.gpkg_path}|layername=study_area_polygons",
            "Study Area Polygons",
            "ogr",
        )

    def _process_area(
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

        :return: True if the workflow completes successfully, False if canceled or failed.
        """
        QgsMessageLog.logMessage(
            f"Processing area {index} score workflow", "Geest", Qgis.Info
        )
        output_prefix = f"{self.layer_id}_area_features_{index}"

        QgsMessageLog.logMessage(
            f"Index score: {self.index_score}",
            "Geest",
            Qgis.Info,
        )

        # Create a scored boundary layer filtered by current_area
        scored_layer = self.create_scored_boundary_layer(output_prefix)

        # Create a scored boundary layer
        raster_output = self._rasterize(
            scored_layer,
            current_bbox,
            index,
            value_field="score",
            default_value=255,
        )
        QgsMessageLog.logMessage(f"Raster output: {raster_output}", "Geest", Qgis.Info)
        QgsMessageLog.logMessage(
            f"Worflow completed for area {index}", "Geest", Qgis.Info
        )
        return raster_output

    def create_scored_boundary_layer(self, output_prefix: str) -> QgsVectorLayer:
        """
        Create a scored boundary layer, filtering features by the current_area.

        :param current_area: The geometry of the current processing area.
        :return: A memory vector layer with a 'score' attribute.
        """

        shapefile_path = os.path.join(self.workflow_directory, f"{output_prefix}.shp")
        scored_layer = QgsVectorLayer(
            shapefile_path,
            "scored_boundary_layer",
            "ogr",
        )
        if not scored_layer.isValid():
            raise QgsProcessingException(f"Failed to load shapefile: {shapefile_path}")

        # Start editing mode
        scored_layer.startEditing()

        # Check if the "score" field already exists
        if scored_layer.fields().indexFromName("score") == -1:
            # Add the "score" field if it doesn't exist
            scored_layer.dataProvider().addAttributes(
                [QgsField("score", QVariant.Double)]
            )
            scored_layer.updateFields()  # Make sure the layer is aware of the new field

        # Get the index of the "score" field
        score_field_index = scored_layer.fields().indexFromName("score")

        # Update each feature with the score value
        for feature in scored_layer.getFeatures():
            feature.setAttribute(score_field_index, self.index_score)
            scored_layer.updateFeature(feature)  # Apply changes to the feature

            # Commit changes to save edits
        if not scored_layer.commitChanges():
            QgsMessageLog.logMessage(
                "Failed to commit changes to score layer", "Geest", Qgis.Critical
            )
        else:
            QgsMessageLog.logMessage(
                "Score field added and updated in shapefile.", "Geest", Qgis.Info
            )
        return scored_layer

    def do_execute(self):
        return super().do_execute()
