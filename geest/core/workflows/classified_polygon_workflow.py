import os
from qgis.core import (
    Qgis,
    QgsFeedback,
    QgsGeometry,
    QgsVectorLayer,
    QgsProcessingContext,
    edit,
    QgsField,
)
from qgis.PyQt.QtCore import QVariant
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem
from geest.utilities import log_message


class ClassifiedPolygonWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'use_classify_polygon_into_classes' workflow.
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
        self.workflow_name = "use_classify_polygon_into_classes"
        layer_path = self.attributes.get(
            "classify_polygon_into_classes_shapefile", None
        )

        if not layer_path:
            log_message(
                "Invalid layer found in use_classify_polygon_into_classes_shapefile, trying use_classify_polygon_into_classes_source.",
                tag="Geest",
                level=Qgis.Warning,
            )
            layer_path = self.attributes.get(
                "classify_polygon_into_classes_layer_source", None
            )
            if not layer_path:
                log_message(
                    "No layer found in use_classify_polygon_into_classes_layer_source.",
                    tag="Geest",
                    level=Qgis.Warning,
                )
                return False

        self.features_layer = QgsVectorLayer(layer_path, "features_layer", "ogr")

        self.selected_field = self.attributes.get(
            "classify_polygon_into_classes_selected_field", ""
        )

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
        # Step 1: Assign reclassification values based on perceived safety
        reclassified_layer = self._assign_reclassification_to_safety(area_features)

        # Step 2: Rasterize the data
        raster_output = self._rasterize(
            reclassified_layer,
            current_bbox,
            index,
            value_field="value",
            default_value=255,
        )
        return raster_output

    def _assign_reclassification_to_safety(
        self, layer: QgsVectorLayer
    ) -> QgsVectorLayer:
        """
        Assign reclassification values to polygons based on thresholds.
        """
        with edit(layer):
            # Remove all other columns except the selected field and the new 'value' field
            fields_to_keep = {self.selected_field, "value"}
            fields_to_remove = [
                field.name()
                for field in layer.fields()
                if field.name() not in fields_to_keep
            ]
            layer.dataProvider().deleteAttributes(
                [layer.fields().indexFromName(field) for field in fields_to_remove]
            )
            layer.updateFields()
            if layer.fields().indexFromName("value") == -1:
                layer.dataProvider().addAttributes([QgsField("value", QVariant.Int)])
                layer.updateFields()

            for feature in layer.getFeatures():
                score = feature[self.selected_field]
                # Scale values between 0 and 5
                reclass_val = self._scale_value(score, 0, 100, 0, 5)
                log_message(f"Scaled {score} to: {reclass_val}")
                feature.setAttribute("value", reclass_val)
                layer.updateFeature(feature)
        return layer

    def _scale_value(self, value, min_in, max_in, min_out, max_out):
        """
        Scale value from input range (min_in, max_in) to output range (min_out, max_out).
        """
        try:
            result = (value - min_in) / (max_in - min_in) * (
                max_out - min_out
            ) + min_out
            return result
        except:
            log_message(f"Invalid value, returning 0: {value}")
            return 0

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
