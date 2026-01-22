# -*- coding: utf-8 -*-
"""📦 Workflow Factory module.

This module contains functionality for workflow factory.
"""

from qgis.core import Qgis, QgsFeedback, QgsProcessingContext

from geest.core.workflows import (
    AcledImpactWorkflow,
    AnalysisAggregationWorkflow,
    ClassifiedPolygonWorkflow,
    ContextualIndexScoreWorkflow,
    DefaultIndexScoreWorkflow,
    DimensionAggregationWorkflow,
    DontUseWorkflow,
    EPLEXWorkflow,
    FactorAggregationWorkflow,
    IndexScoreWithGHSLWorkflow,
    IndexScoreWithOoklaWorkflow,
    MultiBufferDistancesNativeWorkflow,
    MultiBufferDistancesORSWorkflow,
    OsmTransportPolylinePerCellWorkflow,
    PointPerCellWorkflow,
    PolygonPerCellWorkflow,
    PolylinePerCellWorkflow,
    RasterReclassificationWorkflow,
    SafetyPolygonWorkflow,
    SafetyRasterWorkflow,
    SinglePointBufferWorkflow,
    StreetLightsBufferWorkflow,
)
from geest.utilities import log_message

from .settings import setting
from .json_tree_item import JsonTreeItem


class WorkflowFactory:
    """
    A factory class that creates workflow objects based on the attributes.
    The workflows accept a QgsFeedback object to report progress and handle cancellation.
    """

    def create_workflow(
        self,
        item: JsonTreeItem,
        cell_size_m: float,
        analysis_scale: str,
        feedback: QgsFeedback,
        context: QgsProcessingContext,
    ):
        """
        Determines the workflow to return based on 'Analysis Mode' in the attributes.
        Passes the feedback object to the workflow for progress reporting.

        Args:
            item: The JsonTreeItem object representing the task.
            cell_size_m: The cell size in meters for the analysis.
            analysis_scale: The analysis scale string to determine the workflow e.g. local, national.
            feedback: The QgsFeedback object for progress reporting.
            context: The QgsProcessingContext object for processing. This can be used to
                pass objects to the thread. e.g. the QgsProject Instance

        Returns:
            Workflow: The workflow object to execute.

        Raises:
            ValueError: If an unknown analysis mode is encountered.
        """
        try:
            if not item:
                return DontUseWorkflow({}, feedback)

            attributes = item.attributes()
            log_message("Workflow Factory Called")
            log_message("-----------------------")
            log_message(f"{item.attributesAsMarkdown()}")
            log_message("-----------------------")

            analysis_mode = attributes.get("analysis_mode", "")

            if analysis_mode == "use_index_score":
                return DefaultIndexScoreWorkflow(item, cell_size_m, analysis_scale, feedback, context)
            elif analysis_mode == "use_contextual_index_score":
                return ContextualIndexScoreWorkflow(item, cell_size_m, analysis_scale, feedback, context)
            elif analysis_mode == "use_eplex_score":
                return EPLEXWorkflow(item, cell_size_m, analysis_scale, feedback, context)
            elif analysis_mode == "use_index_score_with_ookla":
                return IndexScoreWithOoklaWorkflow(item, cell_size_m, analysis_scale, feedback, context)
            elif analysis_mode == "use_index_score_with_ghsl":
                return IndexScoreWithGHSLWorkflow(item, cell_size_m, analysis_scale, feedback, context)
            elif analysis_mode == "Do Not Use":
                return DontUseWorkflow(item, cell_size_m, analysis_scale, feedback, context)
            elif analysis_mode == "use_multi_buffer_point":
                use_ors = setting(key="use_ors_for_accessibility", default=False)
                if isinstance(use_ors, str):
                    use_ors = use_ors.lower() in ("1", "true", "yes", "y", "on")
                if use_ors:
                    log_message("Using Multi Buffer Distances ORS Workflow")
                    return MultiBufferDistancesORSWorkflow(item, cell_size_m, analysis_scale, feedback, context)
                log_message("Using Multi Buffer Distances Native Workflow")
                return MultiBufferDistancesNativeWorkflow(item, cell_size_m, analysis_scale, feedback, context)
            elif analysis_mode == "use_single_buffer_point":
                return SinglePointBufferWorkflow(item, cell_size_m, analysis_scale, feedback, context)
            elif analysis_mode == "use_point_per_cell":
                return PointPerCellWorkflow(item, cell_size_m, analysis_scale, feedback, context)
            elif analysis_mode == "use_polyline_per_cell":
                return PolylinePerCellWorkflow(item, cell_size_m, analysis_scale, feedback, context)
            elif analysis_mode == "use_osm_transport_polyline_per_cell":
                return OsmTransportPolylinePerCellWorkflow(item, cell_size_m, analysis_scale, feedback, context)
            elif analysis_mode == "use_polygon_per_cell":
                return PolygonPerCellWorkflow(item, cell_size_m, analysis_scale, feedback, context)
            elif analysis_mode == "factor_aggregation":
                return FactorAggregationWorkflow(item, cell_size_m, analysis_scale, feedback, context)
            elif analysis_mode == "dimension_aggregation":
                return DimensionAggregationWorkflow(item, cell_size_m, analysis_scale, feedback, context)
            elif analysis_mode == "analysis_aggregation":
                return AnalysisAggregationWorkflow(item, cell_size_m, analysis_scale, feedback, context)
            elif analysis_mode == "use_csv_to_point_layer":
                return AcledImpactWorkflow(item, cell_size_m, analysis_scale, feedback, context)
            elif analysis_mode == "use_classify_polygon_into_classes":
                return ClassifiedPolygonWorkflow(item, cell_size_m, analysis_scale, feedback, context)
            elif analysis_mode == "use_classify_safety_polygon_into_classes":
                return SafetyPolygonWorkflow(item, cell_size_m, analysis_scale, feedback, context)
            elif analysis_mode == "use_nighttime_lights":
                return SafetyRasterWorkflow(item, cell_size_m, analysis_scale, feedback, context)
            elif analysis_mode == "use_environmental_hazards":
                return RasterReclassificationWorkflow(item, cell_size_m, analysis_scale, feedback, context)
            elif analysis_mode == "use_street_lights":
                return StreetLightsBufferWorkflow(item, cell_size_m, analysis_scale, feedback, context)
            else:
                raise ValueError(f"Unknown Analysis Mode: {analysis_mode}")

        except Exception as e:
            log_message(f"Error creating workflow: {e}", level=Qgis.Critical)
            import traceback

            log_message(traceback.format_exc(), level=Qgis.Critical)
            return DontUseWorkflow(item, cell_size_m, analysis_scale, feedback, context)
