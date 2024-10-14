from qgis.core import QgsMessageLog, Qgis
from qgis.core import QgsFeedback
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
)
from .json_tree_item import JsonTreeItem


class WorkflowFactory:
    """
    A factory class that creates workflow objects based on the attributes.
    The workflows accept a QgsFeedback object to report progress and handle cancellation.
    """

    def create_workflow(self, item: JsonTreeItem, feedback: QgsFeedback):
        """
        Determines the workflow to return based on 'Analysis Mode' in the attributes.
        Passes the feedback object to the workflow for progress reporting.
        """
        if not item:
            return DontUseWorkflow({}, feedback)
        attributes = item.data(3)
        QgsMessageLog.logMessage(f"Workflow Factory Called", "Geest", level=Qgis.Info)
        QgsMessageLog.logMessage(f"-----------------------", "Geest", level=Qgis.Info)
        for key, value in attributes.items():
            QgsMessageLog.logMessage(f"{key}: {value}", "Geest", level=Qgis.Info)
        QgsMessageLog.logMessage(f"-----------------------", "Geest", level=Qgis.Info)

        analysis_mode = attributes.get("Analysis Mode", "")

        if analysis_mode == "Spatial Analysis":
            return RasterLayerWorkflow(item, feedback)
        elif analysis_mode == "Use Default Index Score":
            return DefaultIndexScoreWorkflow(item, feedback)
        elif analysis_mode == "Don’t Use":
            return DontUseWorkflow(item, feedback)
        elif analysis_mode == "Use Multi Buffer Point":
            return MultiBufferDistancesWorkflow(item, feedback)
        elif analysis_mode == "Use Point per Cell":
            return PointPerCellWorkflow(item, feedback)
        elif analysis_mode == "Use Polyline per Cell":
            return PolylinePerCellWorkflow(item, feedback)
        # TODO fix inconsistent abbreviation below for Poly
        elif analysis_mode == "Use Poly per Cell":
            return PolygonPerCellWorkflow(item, feedback)
        elif analysis_mode == "Factor Aggregation":
            return FactorAggregationWorkflow(item, feedback)
        elif analysis_mode == "Dimension Aggregation":
            return DimensionAggregationWorkflow(item, feedback)
        elif analysis_mode == "Analysis Aggregation":
            return AnalysisAggregationWorkflow(item, feedback)
        else:
            raise ValueError(f"Unknown Analysis Mode: {analysis_mode}")
