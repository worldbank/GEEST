import os
import glob
import shutil
from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsFeedback,
    QgsFeature,
    QgsVectorLayer,
    QgsField,
    QgsGeometry,
    QgsRectangle,
    QgsRasterLayer,
    QgsProject,
    QgsMapLayer,
)
from qgis.PyQt.QtCore import QVariant
import processing  # QGIS processing toolbox
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem
from geest.core.multibuffer_point import MultiBufferCreator


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

    def __init__(self, item: JsonTreeItem, feedback: QgsFeedback):
        """
        Initialize the Multi Buffer Distance with attributes and feedback.

        :param attributes: Dictionary containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        """
        super().__init__(
            item, feedback
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.workflow_name = "Multi Buffer Distances"
        self.attributes = item.data(3)
        self.layer_id = self.attributes["Layer"].lower().replace(" ", "_")
        self.project_base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../..")
        )
        # self.buffer_creator = MultiBufferCreator(
        #    distance_list=self.attributes["Default Multi Buffer Distances"],
        #    subset_size=5
        # )  # Initialize the MultiBufferCreator
        self.dummy_distances = [
            250,
            500,
            1000,
            1250,
            2000,
        ]  # Dummy distances for testing
        self.buffer_creator = MultiBufferCreator(
            distance_list=self.dummy_distances,
        )
        layer_name = "points"
        self.dummy_layer = QgsProject.instance().mapLayersByName(layer_name)[0]

    def do_execute(self):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """

        QgsMessageLog.logMessage(
            f"Executing {self.workflow_name}", tag="Geest", level=Qgis.Info
        )
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
        # distance_units = self.attributes[
        #    "Multi Buffer Distances Units"
        # ]  # distance or time
        # travel_mode = self.attributes[
        #    "Multi Buffer Distances Travel Mode"
        # ]  # walking, driving
        # points_layer = self.attributes[
        # "Multi Buffer Distances Points of Interest Layer"
        # ]

        # if not points_layer or not isinstance(points_layer, QgsVectorLayer):
        #    QgsMessageLog.logMessage("Invalid points layer.", tag="Geest", level=Qgis.Warning)
        #    return False

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

            # Call the internal create_multibuffer function
            # self.create_multibuffer(
            #    geom=geom,
            #    aligned_box=aligned_box,
            #    mask_name=f"{self.layer_id}_{area_name}",
            #    distance_units="distance",
            #    travel_mode="foot-walking",
            #    points_layer=self.dummy_layer,
            # )

            mask_name = f"{self.layer_id}_{area_name}"

            QgsMessageLog.logMessage(
                f"Creating buffers for {mask_name}", tag="Geest", level=Qgis.Info
            )

            # Call the create_multibuffers function from MultiBufferCreator
            self.buffer_creator.create_multibuffers(
                point_layer=self.dummy_layer,
                output_path=os.path.join(self.workflow_directory, f"{mask_name}.shp"),
                mode="foot-walking",
                measurement="distance",  # TODO this should be distances
                crs="EPSG:4326",
            )
            QgsMessageLog.logMessage(
                f"Buffers created for {mask_name}", tag="Geest", level=Qgis.Info
            )

        QgsMessageLog.logMessage(
            f"{self.workflow_name} completed successfully.",
            tag="Geest",
            level=Qgis.Info,
        )
        return True

    """def create_multibuffer(
        self,
        geom: QgsGeometry,
        aligned_box: QgsRectangle,
        mask_name: str,
        distance_units: str,
        travel_mode: str,
        points_layer: QgsMapLayer,
    ):
        """
    """Creates buffers for a single geometry using the MultiBufferCreator.

        :param geom: Geometry to be buffered.
        :param aligned_box: Bounding box for raster mask alignment.
        :param mask_name: Name for the output raster file.
        :param distances: List of buffer distances (or times).
        :param distance_units: Units for the buffers ('distance' for meters or 'time' for seconds).
        :param travel_mode: Mode of travel for ORS API (e.g., 'walking', 'driving').
        :param points_layer: Points of interest layer for distance calculation.
        """

    """if self.feedback.isCanceled():  # Check for cancellation before starting
            QgsMessageLog.logMessage(
                "Workflow canceled before creating raster.",
                tag="Geest",
                level=Qgis.Warning,
            )
            return

        QgsMessageLog.logMessage(
            f"Creating buffers for {mask_name}", tag="Geest", level=Qgis.Info
        )

        # Call the create_multibuffers function from MultiBufferCreator
        self.buffer_creator.create_multibuffers(
            point_layer=points_layer,
            output_path=os.path.join(self.workflow_directory, f"{mask_name}.shp"),
            mode=travel_mode,
            measurement=distance_units, # TODO this should be distances
            crs="EPSG:4326",
        )
        QgsMessageLog.logMessage(
            f"Buffers created for {mask_name}", tag="Geest", level=Qgis.Info
        )
        return True"""
