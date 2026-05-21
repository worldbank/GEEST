# -*- coding: utf-8 -*-
"""📦 Classified Polygon Workflow module.

This module contains functionality for classified polygon workflow.

Supports grid-first mode where polygon classification scores are written
directly to the study_area_grid column, then rasterized.
"""

import os
from typing import Optional
from urllib.parse import unquote

from qgis.core import (
    Qgis,
    QgsFeedback,
    QgsField,
    QgsGeometry,
    QgsProcessingContext,
    QgsVectorLayer,
    edit,
)
from qgis.PyQt.QtCore import QVariant

from geest.core import JsonTreeItem
from geest.core.grid_column_utils import (
    clear_grid_column,
    rasterize_grid_column,
    write_buffer_values_to_grid,
)
from geest.utilities import log_message

from .workflow_base import WorkflowBase


class ClassifiedPolygonWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'use_classify_polygon_into_classes' workflow.
    """

    def __init__(
        self,
        item: JsonTreeItem,
        cell_size_m: float,
        analysis_scale: str,  # national or local
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
            item, cell_size_m, analysis_scale, feedback, context, working_directory
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.workflow_name = "use_classify_polygon_into_classes"
        layer_path = self.attributes.get("classify_polygon_into_classes_shapefile", None)
        if layer_path:
            layer_path = unquote(layer_path)
        if not layer_path:
            log_message(
                "Invalid layer found in use_classify_polygon_into_classes_shapefile, trying use_classify_polygon_into_classes_source.",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            layer_path = self.attributes.get("classify_polygon_into_classes_layer_source", None)
            if not layer_path:
                log_message(
                    "No layer found in use_classify_polygon_into_classes_layer_source.",
                    tag="GeoE3",
                    level=Qgis.Warning,
                )
                return False
        self.features_layer = QgsVectorLayer(layer_path, "features_layer", "ogr")
        self.selected_field = self.attributes.get("classify_polygon_into_classes_selected_field", "")
        self.workflow_name = "classified_polygon"
        # Grid-first mode: write results to grid columns first, then rasterize
        self.use_grid_first = True
        # Track if we've cleared the column (only do once, not per area)
        self._column_cleared = False

    def _process_features_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
        area_name: Optional[str] = None,
    ) -> str:
        """
        Executes the actual workflow logic for a single area.

        Supports grid-first mode where classification scores are written
        directly to study_area_grid.

        :current_area: Current polygon from our study area.
        :current_bbox: Bounding box of the above area.
        :area_features: A vector layer of features to analyse that includes only features in the study area.
        :index: Iteration / number of area being processed.
        :area_name: Name of the area being processed.

        :return: A raster layer file path if processing completes successfully.
        """
        area_features_count = area_features.featureCount()
        log_message(
            f"Features layer for area {index + 1} loaded with {area_features_count} features.",
            tag="GeoE3",
            level=Qgis.Info,
        )

        if self.use_grid_first:
            return self._process_grid_first(
                current_bbox=current_bbox,
                area_features=area_features,
                index=index,
                area_name=area_name,
            )
        else:
            return self._process_raster_first(
                current_bbox=current_bbox,
                area_features=area_features,
                index=index,
            )

    def _process_raster_first(
        self,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
    ) -> str:
        """Legacy raster-first processing."""
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

    def _process_grid_first(
        self,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
        area_name: str,
    ) -> str:
        """Grid-first processing - writes classification scores directly to study_area_grid."""
        # Clear column once at the start (not per area)
        if not self._column_cleared:
            log_message(f"Clearing column {self.layer_id} before processing")
            clear_grid_column(self.gpkg_path, self.layer_id)
            self._column_cleared = True

        self.progressChanged.emit(10.0)

        # Step 1: Assign reclassification values (scale 0-100 to 0-5)
        log_message(f"Scaling classification values for {area_features.featureCount()} polygons")
        reclassified_layer = self._assign_reclassification_to_safety(area_features)

        self.progressChanged.emit(40.0)

        # Step 2: Write polygon scores to grid cells
        log_message(f"Writing classification scores to grid column {self.layer_id}")
        write_buffer_values_to_grid(
            gpkg_path=self.gpkg_path,
            column_name=self.layer_id,
            buffer_layer=reclassified_layer,
            value_field="value",
            aggregation_method="MAX",
            feedback=self.feedback,
        )

        self.progressChanged.emit(70.0)

        # Step 3: Rasterize from grid column
        output_path = os.path.join(
            self.workflow_directory,
            f"{self.layer_id}_{index}.tif",
        )

        rect = current_bbox.boundingBox()
        extent = (rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum())

        rasterize_grid_column(
            gpkg_path=self.gpkg_path,
            column_name=self.layer_id,
            output_raster_path=output_path,
            cell_size=self.cell_size_m,
            extent=extent,
            nodata=-9999.0,
            area_name=area_name,
        )

        self.progressChanged.emit(100.0)
        log_message(f"Rasterized grid column to {output_path}")
        return output_path

    def _assign_reclassification_to_safety(self, layer: QgsVectorLayer) -> QgsVectorLayer:
        """
        Assign reclassification values to polygons based on thresholds.
        """
        with edit(layer):
            # Remove all other columns except the selected field and the new 'value' field
            fields_to_keep = {self.selected_field, "value"}
            fields_to_remove = [field.name() for field in layer.fields() if field.name() not in fields_to_keep]
            layer.dataProvider().deleteAttributes([layer.fields().indexFromName(field) for field in fields_to_remove])
            layer.updateFields()
            if layer.fields().indexFromName("value") == -1:
                layer.dataProvider().addAttributes([QgsField("value", QVariant.Int)])
                layer.updateFields()
            count = layer.featureCount()
            counter = 0
            for feature in layer.getFeatures():
                score = feature[self.selected_field]
                # Scale values between 0 and 5
                reclass_val = self._scale_value(score, 0, 100, 0, 5)
                log_message(f"Scaled {score} to: {reclass_val}")
                feature.setAttribute("value", reclass_val)
                layer.updateFeature(feature)
                counter += 1
                if self.feedback.isCanceled():
                    log_message("Feedback cancelled, stopping processing.")
                    return layer
                self.feedback.setProgress(int((counter / count) * 100))
        return layer

    def _scale_value(self, value, min_in, max_in, min_out, max_out):
        """
        Scale value from input range (min_in, max_in) to output range (min_out, max_out).
        """
        try:
            result = (value - min_in) / (max_in - min_in) * (max_out - min_out) + min_out
            return result
        except Exception as e:
            del e
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
        area_name: str = None,
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
        area_name: str = None,
    ):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        pass
