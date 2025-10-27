# -*- coding: utf-8 -*-
import os
from typing import Optional
from urllib.parse import unquote

from qgis.core import (
    Qgis,
    QgsFeedback,
    QgsGeometry,
    QgsProcessingContext,
    QgsVectorLayer,
)

from geest.core import JsonTreeItem
from geest.core.algorithms.features_per_cell_processor import select_grid_cells_and_assign_transport_score
from geest.core.osm_downloaders import OSMDownloadType
from geest.utilities import log_message

from .workflow_base import WorkflowBase


class OsmTransportPolylinePerCellWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'use_osm_transportpolyline_per_cell' workflow.
    """

    def __init__(
        self,
        item: JsonTreeItem,
        cell_size_m: float,
        analysis_scale: str,
        feedback: QgsFeedback,
        context: QgsProcessingContext,
        working_directory: Optional[str],
    ):
        """
        Initialize the workflow with attributes and feedback.

        Args:
            :param item: JsonTreeItem representing the analysis, dimension, or factor to process.
            :param cell_size_m: Cell size in meters
            :param analysis_scale: Scale of the analysis, e.g., 'local', 'national'.
            :param feedback: QgsFeedback object for progress reporting and cancellation.
            :param context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
            :param working_directory: Folder containing study_area.gpkg and where the outputs will be placed. If not set will be taken from QSettings.
        """
        super().__init__(
            item, cell_size_m, analysis_scale, feedback, context, working_directory
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.workflow_name = "use_osm_transport_polyline_per_cell"

        # For now we will use the id attribute to determine if we should
        # use the roads or cycleways lookup table
        # This logic is specific to this workflow
        id = self.attributes.get("id", None)
        if id == "Cycle_Paths_Location":
            self.osm_processing_type = OSMDownloadType.CYCLE
        elif id == "Footpaths_Location":
            self.osm_processing_type = OSMDownloadType.ROAD
        else:
            raise ValueError(f"Unsupported id for OSM Transport Polyline Per Cell Workflow: {id}")

        layer_path = self.attributes.get("osm_transport_polygon_per_cell_shapefile", None)
        if layer_path:
            layer_path = unquote(layer_path)

        if not layer_path:
            log_message(
                "Nothing found in osm_transport_polyline_per_cell_shapefile, trying osm_transport_polyline_per_cell_layer_source.",
                tag="Geest",
                level=Qgis.Warning,
            )
            layer_path = self.attributes.get("osm_transport_polyline_per_cell_layer_source", None)
            if not layer_path:
                log_message(
                    "No points layer found in osm_transport_polyline_per_cell_layer_source.",
                    tag="Geest",
                    level=Qgis.Warning,
                )
                return False

        self.features_layer = QgsVectorLayer(layer_path, "OSM Transport Layer", "ogr")

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
            f"Features layer for area {index + 1} loaded with {area_features_count} features.",
            tag="Geest",
            level=Qgis.Info,
        )
        # Step 1: Select grid cells that intersect with features and assign road scores
        output_path = os.path.join(self.workflow_directory, f"{self.layer_id}_grid_cells.gpkg")
        grid = select_grid_cells_and_assign_transport_score(
            self.osm_processing_type, self.grid_layer, area_features, output_path, self.feedback
        )

        log_message(
            "OSM Transport Polyline per Cell - Selected grid cells and assigned transport scores.",
            tag="Geest",
            level=Qgis.Info,
        )
        log_message(f"Grid cells with transport scores saved to: {output_path}", tag="Geest", level=Qgis.Info)

        # Step 2: Rasterize the grid layer using the assigned values
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
