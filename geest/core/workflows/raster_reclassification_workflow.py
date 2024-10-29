import os
import glob
import shutil
from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsGeometry,
    QgsFeedback,
    QgsRasterLayer,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant
import processing  # QGIS processing toolbox
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem
from geest.core.algorithms import RasterReclassificationProcessor


class RasterReclassificationWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'Use Classify Poly into Classes' workflow.
    """

    def __init__(
        self,
        item: JsonTreeItem,
        feedback: QgsFeedback,
        context: QgsProcessingContext,
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param attributes: Item containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        """
        super().__init__(
            item, feedback, context
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.workflow_name = "use_environmental_hazards"

        layer_name = self.attributes.get("Use Environmental Hazards Raster", None)

        if not layer_name:
            QgsMessageLog.logMessage(
                "Invalid layer found in Use Environmental Hazards Raster, trying Use Environmental Hazards Layer Source.",
                tag="Geest",
                level=Qgis.Warning,
            )
            layer_name = self.attributes.get(
                "Use Environmental Hazards Layer Source", None
            )
            if not layer_name:
                QgsMessageLog.logMessage(
                    "No layer found in Use Environmental Hazards Layer Source.",
                    tag="Geest",
                    level=Qgis.Warning,
                )
                return False

        self.raster_layer = QgsRasterLayer(
            layer_name, "Environmental Hazards Raster", "gdal"
        )

        if self.layer_id == "fire":
            self.reclassification_rules = [
                "-inf",
                0,
                5.00,  # new value = 5
                0,
                1,
                4.00,  # new value = 4
                1,
                2,
                3.00,  # new value = 3
                2,
                5,
                2.00,  # new value = 2
                5,
                8,
                1.00,  # new value = 1
                8,
                "inf",
                0,  # new value = 0
            ]
        elif self.layer_id == "flood":
            self.reclassification_rules = [
                -1,
                0,
                5.00,  # new value = 5
                0,
                180,
                4.00,  # new value = 4
                180,
                360,
                3.00,  # new value = 3
                360,
                540,
                2.00,  # new value = 2
                540,
                720,
                1.00,  # new value = 1
                720,
                900,
                0,  # new value = 0
            ]
        elif self.layer_id == "landslide":
            self.reclassification_rules = [
                0,
                0,
                5.00,  # new value = 5
                1,
                1,
                4.00,  # new value = 4
                2,
                2,
                3.00,  # new value = 3
                3,
                3,
                2.00,  # new value = 2
                4,
                4,
                1.00,  # new value = 1
                5,
                5,
                0,  # new value = 0
            ]
        elif self.layer_id == "cyclone":
            self.reclassification_rules = [
                0,
                0,
                5.00,  # new value = 5
                0,
                25,
                4.00,  # new value = 4
                25,
                50,
                3.00,  # new value = 3
                50,
                75,
                2.00,  # new value = 2
                75,
                100,
                1.00,  # new value = 1
                100,
                "inf",
                0,  # new value = 0
            ]
        elif self.layer_id == "drought":
            self.reclassification_rules = [
                0,
                0,
                5.00,  # new value = 5
                0,
                1,
                4.00,  # new value = 4
                1,
                2,
                3.00,  # new value = 3
                2,
                3,
                2.00,  # new value = 2
                3,
                4,
                1.00,  # new value = 1
                4,
                5,
                0,  # new value = 0
            ]

        QgsMessageLog.logMessage(
            f"Reclassification Rules for {self.layer_id}: {self.reclassification_rules}",
            tag="Geest",
            level=Qgis.Info,
        )
        self.workflow_is_legacy = False

    def _process_raster_for_area(
        self,
        current_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_raster: str,
        index: int,
    ):
        """
        Executes the actual workflow logic for a single area using a raster.

        :current_area: Current polygon from our study area.
        :current_bbox: Bounding box of the above area.
        :area_raster: A raster layer of features to analyse that includes only bbox pixels in the study area.
        :index: Index of the current area.

        :return: Path to the reclassified raster.
        """
        _ = current_area  # Unused in this analysis

        # Apply the reclassification rules
        reclassified_raster = self._apply_reclassification(
            area_raster,
            index,
            bbox=current_bbox,
        )

        return reclassified_raster

    def _apply_reclassification(
        self,
        input_raster: QgsRasterLayer,
        index: int,
        bbox: QgsGeometry,
    ):
        """
        Apply the reclassification using the raster calculator and save the output.
        """
        bbox = bbox.boundingBox()

        reclassified_raster_path = os.path.join(
            self.workflow_directory, f"{self.layer_id}_reclassified_{index}.tif"
        )

        # Set up the reclassification using reclassifybytable
        params = {
            "INPUT_RASTER": input_raster,
            "RASTER_BAND": 1,  # Band number to apply the reclassification
            "TABLE": self.reclassification_rules,  # Reclassification table
            "RANGE_BOUNDARIES": 0,  # Inclusive lower boundary
            "OUTPUT": "TEMPORARY_OUTPUT",
        }

        # Perform the reclassification using the raster calculator
        reclass = processing.run(
            "native:reclassifybytable", params, feedback=QgsProcessingFeedback()
        )["OUTPUT"]

        clip_params = {
            "INPUT": reclass,
            "MASK": self.areas_layer,
            "CROP_TO_CUTLINE": True,
            "KEEP_RESOLUTION": True,
            "DATA_TYPE": 1,  #  Byte
            "TARGET_EXTENT": f"{bbox.xMinimum()},{bbox.xMaximum()},{bbox.yMinimum()},{bbox.yMaximum()} [{self.target_crs.authid()}]",
            "OUTPUT": reclassified_raster_path,
        }

        processing.run(
            "gdal:cliprasterbymasklayer", clip_params, feedback=QgsProcessingFeedback()
        )
        QgsMessageLog.logMessage(
            f"Reclassification for area {index} complete. Saved to {reclassified_raster_path}",
            "Geest",
            Qgis.Info,
        )

        return reclassified_raster_path

    # TODO Remove when all workflows are refactored
    def do_execute(self):
        """
        Execute the workflow.
        """
        self._execute()

    # Not used in this workflow since we work with rasters
    def _process_features_for_area(
        self,
        current_area: QgsGeometry,
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
        pass

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
    ):
        """
        Executes the actual workflow logic for a single area using an aggregate.

        :current_area: Current polygon from our study area.
        :current_bbox: Bounding box of the above area.
        :index: Index of the current area.

        :return: Path to the reclassified raster.
        """
        pass
