import os
from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsFeedback,
    QgsProcessingContext,
)
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem
from geest.core.algorithms import ORSMultiBufferProcessor
from geest.core import setting


class MultiBufferDistancesWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'Multi Buffer Distances' workflow.

    This uses ORS (OpenRouteService) to calculate the distances between the study area
    and the selected points of interest.

    It will create concentric buffers (isochrones) around the study area and calculate
    the distances to the points of interest.

    The buffers will be calcuated either using travel time or travel distance.

    The results will be stored as a collection of tif files scaled to the likert scale.

    These results will be be combined into a VRT file and added to the QGIS map.

    """

    def __init__(
        self, item: JsonTreeItem, feedback: QgsFeedback, context: QgsProcessingContext
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param attributes: Item containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        """
        super().__init__(
            item, feedback, context
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.workflow_name = "Multi Buffer Distances"
        self.attributes = item.data(3)
        self.layer_id = self.attributes["ID"].lower().replace(" ", "_")
        self.project_base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../..")
        )
        # self.buffer_creator = MultiBufferCreator(
        #    distance_list=self.attributes["Default Multi Buffer Distances"],
        #    subset_size=5
        # )  # Initialize the MultiBufferCreator
        self.distances = item.data(3).get("Multi Buffer Travel Distances", None)
        # split the distances string into a list of floats
        self.distances = [float(x) for x in self.distances.split(",")]
        self.buffer_creator = ORSMultiBufferProcessor(
            distance_list=self.distances,
            subset_size=5,
            context=self.context,  # set in base class
        )
        layer_name = item.data(3).get("Multi Buffer Point Layer Name", None)
        if not layer_name:
            QgsMessageLog.logMessage(
                "Invalid points layer.", tag="Geest", level=Qgis.Warning
            )
            return False
        self.points_layer = self.context.project().mapLayersByName(layer_name)[0]

    def do_execute(self):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        verbose_mode = int(setting(key="verbose_mode", default=0))

        QgsMessageLog.logMessage(
            f"Executing {self.workflow_name}", tag="Geest", level=Qgis.Info
        )
        if verbose_mode:
            QgsMessageLog.logMessage(
                "----------------------------------", tag="Geest", level=Qgis.Info
            )
            for item in self.attributes.items():
                QgsMessageLog.logMessage(
                    f"{item[0]}: {item[1]}", tag="Geest", level=Qgis.Info
                )
            QgsMessageLog.logMessage(
                "----------------------------------", tag="Geest", level=Qgis.Info
            )

        self.workflow_directory = self._create_workflow_directory()

        # loop through self.bboxes_layer and the self.areas_layer  and create a raster mask for each feature
        distances = self.attributes[
            "Default Multi Buffer Distances"
        ]  # in the units specified below

        for feature in self.areas_layer.getFeatures():
            if (
                self.feedback.isCanceled()
            ):  # Check for cancellation before each major step
                QgsMessageLog.logMessage(
                    "Workflow canceled before processing feature.",
                    tag="Geest",
                    level=Qgis.Warning,
                )
                return False
            geom = feature.geometry()  # todo this shoudl come from the areas layer
            aligned_box = geom
            # Set the 'area_name' from layer
            area_name = feature.attribute("area_name")

            mask_name = f"{self.layer_id}_{area_name}"

            QgsMessageLog.logMessage(
                f"Creating buffers for {mask_name}", tag="Geest", level=Qgis.Info
            )

            # Call the create_multibuffers function from MultiBufferCreator
            vector_output_path = os.path.join(
                self.workflow_directory, f"{mask_name}.shp"
            )

            result = self.buffer_creator.create_multibuffers(
                point_layer=self.points_layer,
                output_path=vector_output_path,
                mode="foot-walking",
                measurement="distance",  # TODO this should be distances
            )
            if not result:
                QgsMessageLog.logMessage(
                    f"Error creating buffers for {mask_name}",
                    tag="Geest",
                    level=Qgis.Warning,
                )
                return False
            QgsMessageLog.logMessage(
                f"Buffers created for {mask_name}", tag="Geest", level=Qgis.Info
            )
            raster_output_path = os.path.join(
                self.workflow_directory, f"{mask_name}.tif"
            )
            # Call the rasterize function from MultiBufferCreator
            QgsMessageLog.logMessage(
                f"Rasterizing buffers for {mask_name} with input_path {vector_output_path}",
                tag="Geest",
                level=Qgis.Info,
            )
            result = self.buffer_creator.rasterize(
                input_path=vector_output_path,
                output_path=raster_output_path,
                distance_field="distance",
                distance_values=self.distances,
                cell_size=100,
            )

        QgsMessageLog.logMessage(
            f"{self.workflow_name} completed successfully.",
            tag="Geest",
            level=Qgis.Info,
        )
        self.attributes["Indicator Result File"] = result
        self.attributes["Indicator Result"] = (
            "Use Multi Buffer Point Workflow Completed"
        )
        return True
