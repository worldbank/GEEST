import os
from qgis.core import (
    QgsMessageLog, 
    Qgis, 
    QgsFeedback, 
    QgsFeature, 
    QgsVectorLayer, 
    QgsField, 
    QgsGeometry, 
    QgsRectangle)
from qgis.PyQt.QtCore import QVariant
import processing  # QGIS processing toolbox
from .workflow_base import WorkflowBase


class DefaultIndexScoreWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'Use Default Index Score' workflow.
    """

    def __init__(self, attributes: dict, feedback: QgsFeedback):
        """
        Initialize the TemporalAnalysisWorkflow with attributes and feedback.
        :param attributes: Dictionary containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        """
        super().__init__(attributes, feedback)

    def execute(self):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """

        QgsMessageLog.logMessage("Executing Use Default Index Score", tag="Geest", level=Qgis.Info)
        QgsMessageLog.logMessage("----------------------------------", tag="Geest", level=Qgis.Info)
        for item in self.attributes.items():
            QgsMessageLog.logMessage(f"{item[0]}: {item[1]}", tag="Geest", level=Qgis.Info)
        QgsMessageLog.logMessage("----------------------------------", tag="Geest", level=Qgis.Info)

        # loop through self.bboxes_layer and the self.areas_layer  and create a raster mask for each feature
        index_score = self.attributes["Default Index Score"]
        for feature in self.bboxes_layer.getFeatures():
            geom = feature.geometry() # todo this shoudl come from the areas layer
            aligned_box = geom
            mask_name = f"bbox_{feature.id()}"
            self.create_raster(
                geom=geom, 
                aligned_box=aligned_box, 
                mask_name=mask_name,
                index_score=index_score)
        # TODO Jeff copy create_raster_vrt from study_area.py

        steps = 10
        for i in range(steps):
            if self.feedback.isCanceled():
                QgsMessageLog.logMessage(
                    "Dont use workflow canceled.", tag="Geest", level=Qgis.Warning
                )
                return False

            # Simulate progress and work
            self.attributes["progress"] = f"Dont use workflow Step {i + 1} completed"
            self.feedback.setProgress(
                (i + 1) / steps * 100
            )  # Report progress in percentage
            QgsMessageLog.logMessage(
                f"Assigning index score: {self.attributes['Default Index Score']}", 
                tag="Geest", level=Qgis.Info)

        self.attributes["result"] = "Use Default Index Score Workflow Completed"
        QgsMessageLog.logMessage(
            "Use Default Index Score workflow workflow completed", tag="Geest", level=Qgis.Info
        )
        return True


    def create_raster(
            self, 
            geom: QgsGeometry, 
            aligned_box: QgsGeometry, 
            mask_name: str,
            index_score: float) -> None:
        """
        Creates a byte raster mask for a single geometry.

        :param geom: Geometry to be rasterized.
        :param aligned_box: Aligned bounding box geometry for the geometry.
        :param mask_name: Name for the output raster file.
        """    
        aligned_box = QgsRectangle(aligned_box.boundingBox())
        mask_filepath = os.path.join(self.workflow_directory, f"{mask_name}.tif")

        # Create a memory layer to hold the geometry
        temp_layer = QgsVectorLayer(
            f"Polygon?crs={self.output_crs.authid()}", "temp_mask_layer", "memory"
        )
        temp_layer_data_provider = temp_layer.dataProvider()

        # Define a field to store the mask value
        temp_layer_data_provider.addAttributes([QgsField("area_name", QVariant.String)])
        temp_layer.updateFields()

        # Add the geometry to the memory layer
        temp_feature = QgsFeature()
        temp_feature.setGeometry(geom)
        temp_feature.setAttributes(["1"])  # Setting an arbitrary value for the mask
        temp_layer_data_provider.addFeature(temp_feature)

        # Ensure resolution parameters are properly formatted as float values
        x_res = 100.0  # 100m pixel size in X direction
        y_res = 100.0  # 100m pixel size in Y direction

        # Define rasterization parameters for the temporary layer
        params = {
            "INPUT": temp_layer,
            "FIELD": None,
            "BURN": 78, # todo Jeff put on likert scale properly
            "USE_Z": False,
            "UNITS": 1,
            "WIDTH": x_res,
            "HEIGHT": y_res,
            "EXTENT": f"{aligned_box.xMinimum()},{aligned_box.xMaximum()},"
                    f"{aligned_box.yMinimum()},{aligned_box.yMaximum()}",  # Extent of the aligned bbox
            "NODATA": 0,
            "OPTIONS": "",
            "DATA_TYPE": 0, # byte
            "INIT": None,
            "INVERT": False,
            "EXTRA": "",
            "OUTPUT": mask_filepath,
        }
        # Run the rasterize algorithm
        processing.run("gdal:rasterize", params)
        QgsMessageLog.logMessage(f"Created raster mask: {mask_filepath}", tag="Geest", level=Qgis.Info)

