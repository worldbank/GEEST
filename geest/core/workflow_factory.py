from qgis.core import (
    Qgis,
    QgsProcessingContext,
    QgsFeedback,
)

from geest.core.workflows import (
    DontUseWorkflow,
    DefaultIndexScoreWorkflow,
    FactorAggregationWorkflow,
    DimensionAggregationWorkflow,
    AnalysisAggregationWorkflow,
    MultiBufferDistancesWorkflow,
    PointPerCellWorkflow,
    PolylinePerCellWorkflow,
    PolygonPerCellWorkflow,
    AcledImpactWorkflow,
    SinglePointBufferWorkflow,
    SafetyPolygonWorkflow,
    SafetyRasterWorkflow,
    RasterReclassificationWorkflow,
    StreetLightsBufferWorkflow,
    ClassifiedPolygonWorkflow,
)

from .json_tree_item import JsonTreeItem
from geest.utilities import log_message


class WorkflowFactory:
    """
    A factory class that creates workflow objects based on the attributes.
    The workflows accept a QgsFeedback object to report progress and handle cancellation.
    """

    def create_workflow(
        self,
        item: JsonTreeItem,
        cell_size_m: float,
        feedback: QgsFeedback,
        context: QgsProcessingContext,
    ):
        """
        Determines the workflow to return based on 'Analysis Mode' in the attributes.
        Passes the feedback object to the workflow for progress reporting.

        :param item: The JsonTreeItem object representing the task.
        :param cell_size_m: The cell size in meters for the analysis.
        :param feedback: The QgsFeedback object for progress reporting.
        :param context: The QgsProcessingContext object for processing. This can be used to
            pass objects to the thread. e.g. the QgsProject Instance

        :return: The workflow object to execute.
        """
        try:
            if not item:
                return DontUseWorkflow({}, feedback)

            attributes = item.attributes()
            log_message(f"Workflow Factory Called")
            log_message(f"-----------------------")
            log_message(f"{item.attributesAsMarkdown()}")
            log_message(f"-----------------------")

            analysis_mode = attributes.get("analysis_mode", "")

            if analysis_mode == "use_index_score":
                return DefaultIndexScoreWorkflow(item, cell_size_m, feedback, context)
            elif analysis_mode == "Do Not Use":
                return DontUseWorkflow(item, cell_size_m, feedback, context)
            elif analysis_mode == "use_multi_buffer_point":
                return MultiBufferDistancesWorkflow(
                    item, cell_size_m, feedback, context
                )
            elif analysis_mode == "use_single_buffer_point":
                return SinglePointBufferWorkflow(item, cell_size_m, feedback, context)
            elif analysis_mode == "use_point_per_cell":
                return PointPerCellWorkflow(item, cell_size_m, feedback, context)
            elif analysis_mode == "use_polyline_per_cell":
                return PolylinePerCellWorkflow(item, cell_size_m, feedback, context)
            elif analysis_mode == "use_polygon_per_cell":
                return PolygonPerCellWorkflow(item, cell_size_m, feedback, context)
            elif analysis_mode == "factor_aggregation":
                return FactorAggregationWorkflow(item, cell_size_m, feedback, context)
            elif analysis_mode == "dimension_aggregation":
                return DimensionAggregationWorkflow(
                    item, cell_size_m, feedback, context
                )
            elif analysis_mode == "analysis_aggregation":
                return AnalysisAggregationWorkflow(item, cell_size_m, feedback, context)
            elif analysis_mode == "use_csv_to_point_layer":
                return AcledImpactWorkflow(item, cell_size_m, feedback, context)
            elif analysis_mode == "use_classify_polygon_into_classes":
                return ClassifiedPolygonWorkflow(item, cell_size_m, feedback, context)
            elif analysis_mode == "use_classify_safety_polygon_into_classes":
                return SafetyPolygonWorkflow(item, cell_size_m, feedback, context)
            elif analysis_mode == "use_nighttime_lights":
                return SafetyRasterWorkflow(item, cell_size_m, feedback, context)
            elif analysis_mode == "use_environmental_hazards":
                return RasterReclassificationWorkflow(
                    item, cell_size_m, feedback, context
                )
            elif analysis_mode == "use_street_lights":
                return StreetLightsBufferWorkflow(item, cell_size_m, feedback, context)
            else:
                raise ValueError(f"Unknown Analysis Mode: {analysis_mode}")

        except Exception as e:
            log_message(f"Error creating workflow: {e}", level=Qgis.Critical)
            import traceback

            log_message(traceback.format_exc(), level=Qgis.Critical)
            return DontUseWorkflow(item, cell_size_m, feedback, context)
