import os
from qgis.core import QgsFeedback, QgsProcessingContext
from .aggregation_workflow_base import AggregationWorkflowBase
from geest.core.algorithms import (
    PopulationRasterProcessingTask,
    WEEByPopulationScoreProcessingTask,
    SubnationalAggregationProcessingTask,
    OpportunitiesPolygonMaskProcessingTask,
)
from geest.utilities import resources_path
from geest.core import JsonTreeItem


class AnalysisAggregationWorkflow(AggregationWorkflowBase):
    """
    Concrete implementation of an 'Analysis Aggregation' workflow.

    It will aggregate the dimensions within an analysis to create a single raster output.
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
        self.guids = (
            self.item.getAnalysisDimensionGuids()
        )  # get a list of the items to aggregate
        self.id = (
            self.item.attribute("analysis_name")
            .lower()
            .replace(" ", "_")
            .replace("'", "")
        )  # should not be needed any more
        self.layer_id = "wee"
        self.weight_key = "dimension_weighting"
        self.workflow_name = "analysis_aggregation"
        # Prepare the population data if provided
        self.population_data = self.item.attribute("population_layer_source", None)
        population_processor = PopulationRasterProcessingTask(
            population_raster_path=self.population_data,
            working_directory=self.working_directory,
            study_area_gpkg_path=self.gpkg_path,
            cell_size_m=self.cell_size_m,
            target_crs=self.target_crs,
            feedback=self.feedback,
        )
        population_processor.run()
        wee_processor = WEEByPopulationScoreProcessingTask(
            study_area_gpkg_path=self.gpkg_path,
            working_directory=self.working_directory,
            force_clear=False,
        )
        wee_processor.run()
        # Shamelessly hard coded for now, needs to move to the wee processor class
        output = os.path.join(
            self.working_directory, "wee_score", "wee_by_population_score.vrt"
        )
        item.setAttribute("wee_by_population", output)

        # Prepare the polygon mask data if provided
        self.polygon_mask = self.item.attribute("population_layer_source", None)
        opportunites_mask_processor = OpportunitiesPolygonMaskProcessingTask(
            self.studyarea_gpkg_path,
            self.gpkg_path,
            self.working_directory,
            self.target_crs,
            self.feedback,
        )
        opportunites_mask_processor.run()

        aggregation_layer = self.item.attribute("aggregation_layer_source")
        subnational_processor = SubnationalAggregationProcessingTask(
            study_area_gpkg_path=self.gpkg_path,
            aggregation_areas_path=aggregation_layer,
            working_directory=self.working_directory,
            force_clear=False,
        )
        subnational_processor.run()
        # Shamelessly hard coded for now, needs to move to the aggregation processor class
        output = os.path.join(
            self.working_directory,
            "subnational_aggregation",
            "subnational_aggregation.gpkg",
        )
        item.setAttribute(
            "subnational_aggregation", f"{output}|layername=subnational_aggregation"
        )
