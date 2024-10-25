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
        self.index_score = self.attributes["Default Index Score"]
        self.workflow_is_legacy = False
        self.gpkg_path = os.path.join(
            self.working_directory, "study_area", "study_area.gpkg"
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

        # Create a scored boundary layer
        scored_layer = self.create_scored_boundary_layer()
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

    def create_scored_boundary_layer(self):
        # Load the boundary polygon layer from the GeoPackage
        boundary_layer = QgsVectorLayer(
            f"{self.gpkg_path}|layername=study_area_polygons", "Study Area", "ogr"
        )

        if not boundary_layer.isValid():
            raise QgsProcessingException(
                "Boundary layer could not be loaded from the GeoPackage."
            )

        # Prepare the new layer with the same CRS and geometry type
        scored_layer = QgsVectorLayer(
            "Polygon?crs=" + boundary_layer.crs().authid(),
            "scored_boundary_layer",
            "memory",
        )
        scored_layer_data_provider = scored_layer.dataProvider()

        # Add the original fields + "score" field
        scored_layer_data_provider.addAttributes(
            boundary_layer.fields()
        )  # copy original fields
        scored_layer_data_provider.addAttributes(
            [QgsField("score", QVariant.Int)]
        )  # add score field
        scored_layer.updateFields()

        # Copy each feature and set the score
        features = []
        for feature in boundary_layer.getFeatures():
            new_feature = QgsFeature()
            new_feature.setGeometry(feature.geometry())
            new_feature.setAttributes(feature.attributes())  # copy original attributes
            new_feature.setAttribute("score", self.index_score)  # set score value
            features.append(new_feature)

        # Add all features to the scored layer
        scored_layer_data_provider.addFeatures(features)

        QgsMessageLog.logMessage("Scored boundary layer created.", "Geest", Qgis.Info)
        return scored_layer

    def do_execute(self):
        return super().do_execute()
