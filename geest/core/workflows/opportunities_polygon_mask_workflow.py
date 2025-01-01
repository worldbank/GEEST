import os
from qgis.core import (
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
from geest.utilities import log_message


class OpportunitiesPolygonMaskWorkflow(WorkflowBase):
    """
    Concrete implementation of a geest insight for masking by job opportunities.

    It will create a raster layer where all cells outside the masked areas (defined
    by the input polygons layer) are set to a no data value.

    This is used when you want to represent the WEE Score and WEE x Population Score
    only in areas where there are job opportunities / job creation initiatives.

    The input layer should be a polygon layer with the job opportunities. Its attributes
    are completely ignored, only the geometry is used to create a mask.

    The output raster will have the same extent and cell size as the study area.

    The output raster will have either 5 classes (WEE Score) or 15 classes (WEE x Population Score).

    The output raster will be a vrt which is a composite of all the individual area rasters.

    The output raster will be saved in the working directory under a subfolder called 'opportunity_masks'.

    Preconditions:

    This workflow expects that the user has configured the root analysis node dialog with
    the population, aggregation and polygon mask settings, and that the WEE Score and WEE x Population
    scores have been calculated.

    WEE x Population Score is optional. If it is not present, only a masked copy of the WEE Score
    will be generated.
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
        :param attributes: Item containing workflow parameters (should be node type: analysis).
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        :working_directory: Folder containing study_area.gpkg and where the outputs will be placed. If not set will be taken from QSettings.
        """
        super().__init__(
            item, cell_size_m, feedback, context, working_directory
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.workflow_name = "opportunities_polygon_mask"
        # There are two ways a user can specify the polygon mask layer
        # either as a shapefile path added in a line edit or as a layer source
        # using a QgsMapLayerComboBox. We prioritize the shapefile path, so check that first.
        layer_source = self.attributes.get("polygon_mask_shapefile", None)
        provider_type = "ogr"
        if not layer_source:
            # Fall back to the QgsMapLayerComboBox source
            layer_source = self.attributes.get("polygon_mask_layer_source", None)
            provider_type = self.attributes.get(
                "polygon_mask_layer_provider_type", "ogr"
            )
        if not layer_source:
            log_message(
                "polygon_mask_shapefile not found",
                tag="Geest",
                level=Qgis.Critical,
            )
            return False
        self.features_layer = QgsVectorLayer(layer_source, "polygons", provider_type)
        if not self.features_layer.isValid():
            log_message("polygon_mask_shapefile not valid", level=Qgis.Critical)
            log_message(f"Layer Source: {layer_source}", level=Qgis.Critical)
            return False

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
            This is created by the base class using the features_layer and the current_area to subset the features.
        :index: Iteration / number of area being processed.

        :return: A raster layer file path if processing completes successfully, False if canceled or failed.
        """
        log_message(f"{self.workflow_name}  Processing Started")

        # Step 1: clip the selected features to the current area's clip area
        clipped_layer = self._clip_features(
            area_features, f"polygon_masks_clipped_{index}", clip_area
        )

        # Step 2: Assign values to the buffered polygons
        scored_layer = self._assign_scores(clipped_layer)

        # Step 3: Rasterize the scored buffer layer
        raster_output = self._rasterize(scored_layer, current_bbox, index)

        return raster_output

    def _clip_features(
        self, layer: QgsVectorLayer, output_name: str, clip_area: QgsGeometry
    ) -> QgsVectorLayer:
        """
        Clip the input features by the clip area.

        Args:
            layer (QgsVectorLayer): The input feature layer.
            output_name (str): A name for the output buffered layer.
            clip_area (QgsGeometry): The geometry to clip the features by.

        Returns:
            QgsVectorLayer: The buffered features layer.
        """
        clip_layer = self.geometry_to_memory_layer(clip_area, "clip_area")
        output_path = os.path.join(self.workflow_directory, f"{output_name}.shp")
        params = {"INPUT": layer, "OVERLAY": clip_layer, "OUTPUT": output_path}
        output = processing.run("native:clip", params)["OUTPUT"]
        clipped_layer = QgsVectorLayer(output_path, output_name, "ogr")
        return clipped_layer

    def _assign_scores(self, layer: QgsVectorLayer) -> QgsVectorLayer:
        """
        Assign values to buffered polygons based 5 for presence of a polygon.

        Args:
            layer QgsVectorLayer: The buffered features layer.

        Returns:
            QgsVectorLayer: A new layer with a "value" field containing the assigned scores.
        """

        log_message(f"Assigning scores to {layer.name()}")
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
