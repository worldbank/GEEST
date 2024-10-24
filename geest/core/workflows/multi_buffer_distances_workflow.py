import os
from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsFeedback,
    QgsProcessingContext,
    QgsVectorLayer,
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
        self.workflow_name = "Use Multi Buffer Point"

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

        self.distances = self.attributes.get("Multi Buffer Travel Distances", None)
        if not self.distances:
            QgsMessageLog.logMessage(
                "Invalid travel distances, using default.",
                tag="Geest",
                level=Qgis.Warning,
            )
            distances = self.attributes.get("Default Multi Buffer Distances", None)
            if not distances:
                QgsMessageLog.logMessage(
                    "Invalid default travel distances and no default specified.",
                    tag="Geest",
                    level=Qgis.Warning,
                )
                return False
        try:
            self.distances = [float(x) for x in self.distances.split(",")]
        except Exception as e:
            QgsMessageLog.logMessage(
                "Invalid travel distances provided. Distances should be a comma separated list of up to 5 numbers.",
                tag="Geest",
                level=Qgis.Warning,
            )
            return False

        layer_name = self.attributes.get("Multi Buffer Shapefile", None)

        if not layer_name:
            QgsMessageLog.logMessage(
                "Invalid points layer found in Multi Buffer Shapefile, trying Multi Buffer Point Layer Name.",
                tag="Geest",
                level=Qgis.Warning,
            )
            layer_name = self.attributes.get("Multi Buffer Point Layer Source", None)
            if not layer_name:
                QgsMessageLog.logMessage(
                    "No points layer found in Multi Buffer Point Layer Name.",
                    tag="Geest",
                    level=Qgis.Warning,
                )
            return False
        points_layer = QgsVectorLayer(layer_name, "points", "ogr")
        try:

            processor = ORSMultiBufferProcessor(
                output_prefix=self.layer_id,
                distance_list=self.distances,
                points_layer=points_layer,
                gpkg_path=self.gpkg_path,
                workflow_directory=self.workflow_directory,
                context=self.context,
            )
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Failed to initialize {self.workflow_name} processor: {e}",
                tag="Geest",
                level=Qgis.Critical,
            )
            return False
        QgsMessageLog.logMessage(
            f"{self.workflow_name} created", tag="Geest", level=Qgis.Info
        )

        mode = self.attributes.get("Multi Buffer Travel Mode", "Walking")
        if mode == "Walking":
            mode = "foot-walking"
        else:
            mode = "driving-car"
        measurement = self.attributes.get("Multi Buffer Travel Units", "Distance")
        if measurement == "Distance":
            measurement = "distance"
        else:
            measurement = "time"
        QgsMessageLog.logMessage(
            f"Processing areas for {self.workflow_name} with mode {mode} and measurement {measurement}",
            tag="Geest",
            level=Qgis.Info,
        )
        vrt_path = processor.process_areas(mode=mode, measurement=measurement)

        QgsMessageLog.logMessage(
            f"{self.workflow_name} completed successfully.",
            tag="Geest",
            level=Qgis.Info,
        )
        self.attributes["Indicator Result File"] = vrt_path
        return True
