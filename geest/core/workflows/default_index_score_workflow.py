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
    QgsVectorFileWriter,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant
import processing  # QGIS processing toolbox
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem


class DefaultIndexScoreWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'use_default_index_score' workflow.
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
        self.workflow_name = "use_default_index_score"
        self.index_score = int(
            (self.attributes.get("default_index_score", 0) / 100) * 5
        )
        self.workflow_is_legacy = False
        self.features_layer = True  # Normally we would set this to a QgsVectorLayer but in this workflow it is not needed

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

        :return: Raster file path of the output.
        """
        _ = area_features  # unused
        QgsMessageLog.logMessage(
            f"Processing area {index} score workflow", "Geest", Qgis.Info
        )

        QgsMessageLog.logMessage(
            f"Index score: {self.index_score}",
            "Geest",
            Qgis.Info,
        )

        # Create a scored boundary layer filtered by current_area
        scored_layer = self.create_scored_boundary_layer(
            current_area=current_area,
            index=index,
        )

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

    def create_scored_boundary_layer(
        self, current_area: QgsGeometry, index: int
    ) -> QgsVectorLayer:
        """
        Create a scored boundary layer, filtering features by the current_area.

        :param current_area: The geometry of the current processing area.
        :param index: The index of the current processing area.
        :return: A vector layer with a 'score' attribute.
        """
        output_prefix = f"{self.layer_id}_area_{index}"

        # Create a new memory layer with the target CRS (EPSG:4326)
        subset_layer = QgsVectorLayer(f"Polygon", "subset", "memory")
        subset_layer.setCrs(self.target_crs)
        subset_layer_data = subset_layer.dataProvider()
        field = QgsField("score", QVariant.Double)
        fields = [field]
        # Add attributes (fields) from the point_layer
        subset_layer_data.addAttributes(fields)
        subset_layer.updateFields()

        feature = QgsFeature(subset_layer.fields())
        feature.setGeometry(current_area)
        score_field_index = subset_layer.fields().indexFromName("score")
        feature.setAttribute(score_field_index, self.index_score)
        features = [feature]
        # Add reprojected features to the new subset layer
        subset_layer_data.addFeatures(features)
        subset_layer.commitChanges()

        shapefile_path = os.path.join(self.workflow_directory, f"{output_prefix}.shp")
        # Use QgsVectorFileWriter to save the layer to a shapefile
        QgsVectorFileWriter.writeAsVectorFormat(
            subset_layer,
            shapefile_path,
            "utf-8",
            subset_layer.crs(),
            "ESRI Shapefile",
        )
        layer = QgsVectorLayer(shapefile_path, "area_layer", "ogr")

        return layer

    # TODO remove when all concrete classes are refactored to new base class layout
    def do_execute(self):
        return super().do_execute()

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
