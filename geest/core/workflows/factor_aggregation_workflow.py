import os
import glob
from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsFeedback,
    QgsGeometry,
)
from qgis.PyQt.QtCore import QVariant
import processing  # QGIS processing toolbox
from .workflow_base import WorkflowBase


class FactorAggregationWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'Use Default Index Score' workflow.
    """

    def __init__(self, attributes: dict, feedback: QgsFeedback):
        """
        Initialize the Factor Aggregation with attributes and feedback.
        :param attributes: Dictionary containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        """
        super().__init__(attributes, feedback)
        self.factor_id = self.attributes["id"].lower()

    def execute(self):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """

        QgsMessageLog.logMessage(
            "Executing Use FactorAggregationWorkflow", tag="Geest", level=Qgis.Info
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

        self.workflow_directory = self._create_workflow_directory(
            "contextual",
            self.factor_id,
        )

        # Get the indicators beneath this factor and combine them into a single raster
        # proportional to the weight of each indicator
        QgsMessageLog.logMessage(f"Factor attributes", tag="Geest", level=Qgis.Info)
        QgsMessageLog.logMessage(f"{self.attributes}", tag="Geest", level=Qgis.Info)

        QgsMessageLog.logMessage(
            f"----------------------------", tag="Geest", level=Qgis.Info
        )

        # for key, value in self.attributes:
        #    QgsMessageLog.logMessage(
        #        f"Key: {key}, Value: {value}", tag="Geest", level=Qgis.Info
        #    )
        # QgsMessageLog.logMessage(
        #    f"----------------------------", tag="Geest", level=Qgis.Info
        # )

        self.attributes["Result"] = "Factor Aggregation Workflow Completed"
        QgsMessageLog.logMessage(
            "Factor aggregation workflow completed",
            tag="Geest",
            level=Qgis.Info,
        )
        return True

    def create_raster(
        self,
        geom: QgsGeometry,
        aligned_box: QgsGeometry,
        mask_name: str,
        index_score: float,
    ) -> None:
        """
        Creates a byte raster mask for a single geometry.

        :param geom: Geometry to be rasterized.
        :param aligned_box: Aligned bounding box geometry for the geometry.
        :param mask_name: Name for the output raster file.
        """
        if self.feedback.isCanceled():  # Check for cancellation before starting
            QgsMessageLog.logMessage(
                "Workflow canceled before creating raster.",
                tag="Geest",
                level=Qgis.Warning,
            )
            return

        pass

    def create_raster_vrt(self, output_vrt_name: str = None) -> None:
        """
        Creates a VRT file from all generated raster masks and adds it to the QGIS map.

        :param output_vrt_name: The name of the VRT file to create.
        """
        if self.feedback.isCanceled():  # Check for cancellation before starting
            QgsMessageLog.logMessage(
                "Workflow canceled before creating VRT.",
                tag="Geest",
                level=Qgis.Warning,
            )
            return
        pass
