# -*- coding: utf-8 -*-
import os
from typing import Optional

from qgis import processing  # noqa: F401 # QGIS processing toolbox
from qgis.core import (  # noqa: F401
    QgsFeature,
    QgsFeedback,
    QgsField,
    QgsGeometry,
    QgsProcessingContext,
    QgsVectorDataProvider,
    QgsVectorFileWriter,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant

from geest.core import JsonTreeItem
from geest.utilities import log_message

from .workflow_base import WorkflowBase


class IndexScoreWithGHSLException(Exception):
    """Custom exception for IndexScoreWithGHSLWorkflow errors."""

    pass


class IndexScoreWithGHSLWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'use_index_score_with_ghsl' workflow.

    This follows the same logic as the index score workflow but additionally
    masks the result using the GHSL coverage layer to ensure that only areas
    that have GHSL data are included in the final output.
    """

    def __init__(
        self,
        item: JsonTreeItem,
        cell_size_m: float,
        analysis_scale: str,
        feedback: QgsFeedback,
        context: QgsProcessingContext,
        working_directory: Optional[str] = None,
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param item: JsonTreeItem representing the analysis, dimension, or factor to process.
        :param cell_size_m: Cell size in meters for rasterization.
        :param analysis_scale: Scale of the analysis, e.g., 'local', 'national'
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :param context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        :param working_directory: Folder containing study_area.gpkg and where the outputs will be placed. If not set will be taken from QSettings.
        """
        log_message("\n\n\n\n")
        log_message("--------------------------------------------")
        log_message("Initializing Index Score with GHSL Workflow")
        log_message("--------------------------------------------")
        super().__init__(
            item, cell_size_m, analysis_scale, feedback, context, working_directory
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        index_score = self.attributes.get("index_score", 0)
        log_message(f"Index score before rescaling to likert scale: {index_score}")
        self.index_score = (float(index_score) / 100) * 5
        log_message(f"Index score after rescaling to likert scale: {self.index_score}")
        self.features_layer = (
            True  # Normally we would set this to a QgsVectorLayer but in this workflow it is not needed
        )
        self.workflow_name = "index_score"
        # Get the analysis extents
        self.study_area_bbox = self._study_area_bbox_4326()

        # Prepare GHSL coverage layer - adds a minute or two to the workflow
        # and requires internet access
        ghsl_layer_path = os.path.join(self.working_directory, "study_area")
        self.ghsl_layer_path = os.path.join(ghsl_layer_path, "ghsl_settlements_layer.parquet")
        # Raise an error if the GHSL layer does not exist
        if not os.path.exists(self.ghsl_layer_path):
            log_message("ERROR: GHSL coverage layer not found ...")
            raise IndexScoreWithGHSLException("GHSL coverage layer not found.")

        # Ensure the GHSL layer is in the target CRS
        ghsl_layer = QgsVectorLayer(self.ghsl_layer_path, "ghsl_layer", "ogr")
        if ghsl_layer.crs() != self.target_crs:
            log_message("Reprojecting GHSL layer to target CRS ...")
            reprojected_ghsl_path = os.path.join(ghsl_layer_path, "ghsl_settlements_layer_4326.parquet")
            if os.path.exists(reprojected_ghsl_path):
                os.remove(reprojected_ghsl_path)

            processing.run(
                "native:reprojectlayer",
                {
                    "INPUT": ghsl_layer,
                    "TARGET_CRS": self.target_crs,
                    "OUTPUT": reprojected_ghsl_path,
                },
                context=self.context,
            )
            self.ghsl_layer_path = reprojected_ghsl_path
            log_message("GHSL layer reprojected.")

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
        Must be implemented by sub classes.

        :current_area: Current polygon from our study area.
        :current_bbox: Bounding box of the above area.
        :area_features: A vector layer of features to analyse that includes only features in the study area.
        :index: Iteration / number of area being processed.

        :return: Raster file path of the output.
        """
        _ = area_features  # unused
        log_message(f"Processing area {index} score workflow")

        log_message(f"Index score: {self.index_score}")
        self.progressChanged.emit(10.0)  # We just use nominal intervals for progress updates

        # Create a scored boundary layer filtered by current_area
        scored_layer = self.create_scored_boundary_layer(
            clip_area=clip_area,
            index=index,
        )
        self.progressChanged.emit(30.0)  # We just use nominal intervals for progress updates
        # Now mask with GHSL coverage layer
        # First select the features from the GHSL layer that intersect our current area
        ghsl_layer = QgsVectorLayer(self.ghsl_layer_path, "ghsl_layer", "ogr")

        # Select features in ghsl_layer that intersect current_area
        expr = f"intersects($geometry, geom_from_wkt('{current_area.asWkt()}'))"
        ghsl_layer.selectByExpression(expr, QgsVectorLayer.SetSelection)
        # Now only keep the parts of the geometry of the current area that intersect with the ghsl_layer
        ghsl_features = ghsl_layer.selectedFeatures()
        final_geom: QgsGeometry = None
        if ghsl_features:
            ghsl_union_geom = QgsGeometry.unaryUnion([feat.geometry() for feat in ghsl_features])
            # Intersect with the clip_area to get the final geometry to use
            final_geom = clip_area.intersection(ghsl_union_geom)
        else:
            log_message(f"No GHSL coverage in area {index}, skipping ghsl masking.")

        if final_geom.isEmpty():
            log_message(f"No GHSL coverage in area {index} after intersection, skipping rasterization.")
        else:
            scored_layer = self.create_scored_boundary_layer(
                clip_area=final_geom,
                index=index,
            )
        self.progressChanged.emit(60.0)  # We just use nominal intervals for progress

        # Create a scored boundary layer
        raster_output = self._rasterize(
            scored_layer,
            current_bbox,
            index,
            value_field="score",
            default_value=255,
        )
        self.progressChanged.emit(100.0)  # We just use nominal intervals for progress updates

        log_message(f"Raster output: {raster_output}")
        log_message(f"Workflow completed for area {index}")
        return raster_output

    def create_scored_boundary_layer(self, clip_area: QgsGeometry, index: int) -> QgsVectorLayer:
        """
        Create a scored boundary layer, filtering features by the current_area.

        :param index: The index of the current processing area.
        :return: A vector layer with a 'score' attribute.
        """
        output_prefix = f"{self.layer_id}_area_{index}"

        self.progressChanged.emit(20.0)  # We just use nominal intervals for progress updates
        # Create a new memory layer with the target CRS (EPSG:4326)
        subset_layer = QgsVectorLayer("Polygon", "subset", "memory")
        subset_layer.setCrs(self.target_crs)
        subset_layer_data: QgsVectorDataProvider = subset_layer.dataProvider()
        field = QgsField("score", QVariant.Double)
        fields = [field]
        # Add attributes (fields) from the point_layer
        subset_layer_data.addAttributes(fields)
        subset_layer.updateFields()
        self.progressChanged.emit(40.0)  # We just use nominal intervals for progress updates

        feature = QgsFeature(subset_layer.fields())
        feature.setGeometry(clip_area)
        score_field_index = subset_layer.fields().indexFromName("score")
        feature.setAttribute(score_field_index, self.index_score)
        features = [feature]
        # Add reprojected features to the new subset layer
        subset_layer_data.addFeatures(features)
        subset_layer.commitChanges()
        self.progressChanged.emit(60.0)  # We just use nominal intervals for progress updates

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
        self.progressChanged.emit(80.0)  # We just use nominal intervals for progress updates

        return layer

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
