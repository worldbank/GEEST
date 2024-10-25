import os
import glob
from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsFeedback,
    QgsFeature,
    QgsVectorLayer,
    QgsField,
    QgsGeometry,
    QgsRasterLayer,
    QgsProcessingContext,
)
from qgis.PyQt.QtCore import QVariant
import processing  # QGIS processing toolbox
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem
from geest.core.utilities import GridAligner


class DefaultIndexScoreWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'Use Default Index Score' workflow.
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
        self.workflow_name = "Use Default Index Score"

    def do_execute(self):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        # loop through self.bboxes_layer and the self.areas_layer  and create a raster for each feature
        index_score = self.attributes["Default Index Score"]
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

            raster_name = f"{self.layer_id}_{area_name}"
            self.create_raster(
                geom=geom,
                aligned_box=aligned_box,
                raster_name=raster_name,
                index_score=index_score,
            )
        # TODO Jeff copy create_raster_vrt from study_area.py
        # Create and add the VRT of all generated raster if in raster mode
        vrt_filepath = self.create_raster_vrt(
            output_vrt_name=os.path.join(
                self.workflow_directory, f"{self.layer_id}.vrt"
            )
        )
        self.attributes["Indicator Result File"] = vrt_filepath
        self.attributes["Result"] = "Use Default Index Score Workflow Completed"
        QgsMessageLog.logMessage(
            f"self.attributes after Use Default Index Score workflow\n\n {self.attributes}",
            tag="Geest",
            level=Qgis.Info,
        )
        QgsMessageLog.logMessage(
            "Use Default Index Score workflow workflow completed",
            tag="Geest",
            level=Qgis.Info,
        )
        return True

    def create_raster(
        self,
        geom: QgsGeometry,
        aligned_box: QgsGeometry,
        raster_name: str,
        index_score: float,
    ) -> None:
        """
        Creates a byte raster for a single geometry.

        :param geom: Geometry to be rasterized.
        :param aligned_box: Aligned bounding box geometry for the geometry.
        :param raster_name: Name for the output raster file.
        """
        if self.feedback.isCanceled():  # Check for cancellation before starting
            QgsMessageLog.logMessage(
                "Workflow canceled before creating raster.",
                tag="Geest",
                level=Qgis.Warning,
            )
            return

        raster_filepath = os.path.join(self.workflow_directory, f"{raster_name}.tif")
        index_score = (self.attributes["Default Index Score"] / 100) * 5

        # Create a memory layer to hold the geometry
        temp_layer = QgsVectorLayer(
            f"Polygon?crs={self.target_crs.authid()}", "temp_raster_layer", "memory"
        )
        temp_layer_data_provider = temp_layer.dataProvider()

        # Define a field to store the raster value
        temp_layer_data_provider.addAttributes([QgsField("area_name", QVariant.String)])
        temp_layer.updateFields()

        # Add the geometry to the memory layer
        temp_feature = QgsFeature()
        temp_feature.setGeometry(geom)
        temp_feature.setAttributes(["1"])  # Setting an arbitrary value for the raster
        temp_layer_data_provider.addFeature(temp_feature)

        # Ensure resolution parameters are properly formatted as float values
        x_res = 100.0  # 100m pixel size in X direction
        y_res = 100.0  # 100m pixel size in Y direction
        aligned_box = aligned_box.boundingBox()
        # Define rasterization parameters for the temporary layer
        params = {
            "INPUT": temp_layer,
            "FIELD": None,
            "BURN": index_score,  # todo Jeff put on likert scale properly
            "USE_Z": False,
            "UNITS": 1,
            "WIDTH": x_res,
            "HEIGHT": y_res,
            "EXTENT": f"{aligned_box.xMinimum()},{aligned_box.xMaximum()},"
            f"{aligned_box.yMinimum()},{aligned_box.yMaximum()} [{self.target_crs.authid()}]",  # Extent of the aligned bbox
            "NODATA": None,
            "OPTIONS": "",
            "DATA_TYPE": 0,  # byte
            "INIT": None,
            "INVERT": False,
            "EXTRA": "",
            "OUTPUT": "TEMPORARY_OUTPUT",
        }
        # Run the rasterize algorithm
        raster = processing.run("gdal:rasterize", params)["OUTPUT"]
        QgsMessageLog.logMessage(
            f"Created raster: {raster}", tag="Geest", level=Qgis.Info
        )

        # Clip the raster to the study area boundary
        clipped_raster_filepath = os.path.join(
            self.workflow_directory, f"{raster_filepath}"
        )

        processing.run(
            "gdal:cliprasterbymasklayer",
            {
                "INPUT": raster,
                "MASK": self.areas_layer,
                "NODATA": 255,
                "CROP_TO_CUTLINE": True,
                "OUTPUT": raster_filepath,
            },
        )
        QgsMessageLog.logMessage(
            f"Created raster: {raster_filepath}", tag="Geest", level=Qgis.Info
        )

    def create_raster_vrt(self, output_vrt_name: str = None) -> None:
        """
        Creates a VRT file from all generated rasters and adds it to the QGIS map.

        :param output_vrt_name: The name of the VRT file to create.

        :return: The path to the created VRT file.
        """
        if self.feedback.isCanceled():  # Check for cancellation before starting
            QgsMessageLog.logMessage(
                "Workflow canceled before creating VRT.",
                tag="Geest",
                level=Qgis.Warning,
            )
            return

        if output_vrt_name is None:
            output_vrt_name = f"{self.layer_id}.vrt"

        QgsMessageLog.logMessage(
            f"Creating VRT of rasters '{output_vrt_name}' layer to the map.",
            tag="Geest",
            level=Qgis.Info,
        )
        # Directory containing rasters
        raster_dir = os.path.dirname(output_vrt_name)
        raster_files = glob.glob(os.path.join(raster_dir, "*.tif"))

        if not raster_files:
            QgsMessageLog.logMessage(
                "No rasters found to combine into VRT.",
                tag="Geest",
                level=Qgis.Warning,
            )
            return

        vrt_filepath = os.path.join(raster_dir, output_vrt_name)

        # Define the VRT parameters
        params = {
            "INPUT": raster_files,
            "RESOLUTION": 0,  # Use highest resolution among input files
            "SEPARATE": False,  # Combine all input rasters as a single band
            "OUTPUT": vrt_filepath,
            "PROJ_DIFFERENCE": False,
            "ADD_ALPHA": False,
            "ASSIGN_CRS": None,
            "RESAMPLING": 0,
            "SRC_NODATA": "255",
            "EXTRA": "",
        }

        # Run the gdal:buildvrt processing algorithm to create the VRT
        processing.run("gdal:buildvirtualraster", params)
        QgsMessageLog.logMessage(
            f"Created VRT: {vrt_filepath}", tag="Geest", level=Qgis.Info
        )

        # Add the VRT to the QGIS map
        vrt_layer = QgsRasterLayer(vrt_filepath, f"{self.layer_id}")

        if not vrt_layer.isValid():
            QgsMessageLog.logMessage(
                f"VRT Is not valid", tag="Geest", level=Qgis.Critical
            )
            return None
        return vrt_filepath

    def _process_area(self):
        pass
