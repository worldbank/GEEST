from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsProcessingContext,
    QgsFeedback,
)

from geest.core.workflows import (
    RasterLayerWorkflow,
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
)

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

            attributes = item.data(3)
            QgsMessageLog.logMessage(
                f"Workflow Factory Called", "Geest", level=Qgis.Info
            )
            QgsMessageLog.logMessage(
                f"-----------------------", "Geest", level=Qgis.Info
            )
            for key, value in attributes.items():
                QgsMessageLog.logMessage(f"{key}: {value}", "Geest", level=Qgis.Info)
            QgsMessageLog.logMessage(
                f"-----------------------", "Geest", level=Qgis.Info
            )

            analysis_mode = attributes.get("analysis_mode", "")

            if analysis_mode == "use_default_index_score":
                return DefaultIndexScoreWorkflow(item, cell_size_m, feedback, context)
            elif analysis_mode == "do_not_use":
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
            # TODO fix inconsistent abbreviation below for Poly
            elif analysis_mode == "use_poly_per_cell":
                return PolygonPerCellWorkflow(item, cell_size_m, feedback, context)
            elif analysis_mode == "factor_aggregation":
                return FactorAggregationWorkflow(item, cell_size_m, feedback, context)
            elif analysis_mode == "dimension_aggregation":
                return DimensionAggregationWorkflow(
                    item, cell_size_m, feedback, context
                )
            elif analysis_mode == "analysis_aggregation":
                return AnalysisAggregationWorkflow(
                    item, cell_size_m, cell_size_m, feedback, context
                )
            elif analysis_mode == "use_csv_to_point_layer":
                return AcledImpactWorkflow(item, cell_size_m, feedback, context)
            elif analysis_mode == "use_classify_poly_into_classes":
                return SafetyPolygonWorkflow(item, cell_size_m, feedback, context)
            elif analysis_mode == "use_nighttime_lights":
                return SafetyRasterWorkflow(item, cell_size_m, feedback, context)
            elif analysis_mode == "use_environmental_hazards":
                return RasterReclassificationWorkflow(
                    item, cell_size_m, feedback, context
                )
            else:
                raise ValueError(f"Unknown Analysis Mode: {analysis_mode}")

        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error creating workflow: {e}", "Geest", level=Qgis.Critical
            )
            import traceback

            QgsMessageLog.logMessage(
                traceback.format_exc(), "Geest", level=Qgis.Critical
            )
            return DontUseWorkflow(item, cell_size_m, feedback, context)
