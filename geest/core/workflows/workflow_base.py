import os
from abc import ABC, abstractmethod
from qgis.core import QgsFeedback, QgsVectorLayer
from qgis.PyQt.QtCore import QSettings


class WorkflowBase(ABC):
    """
    Abstract base class for all workflows.
    Every workflow must accept an attributes dictionary and a QgsFeedback object.
    """

    def __init__(self, attributes: dict, feedback: QgsFeedback):
        """
        Initialize the workflow with attributes and feedback.
        :param attributes: Dictionary containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        """
        self.attributes = attributes
        self.feedback = feedback
        # This is set in the setup panel
        self.settings = QSettings()
        # This is the top level folder for work files
        self.working_directory = self.settings.value("last_working_directory", "")
        if not self.working_directory:
            raise ValueError("Working directory not set.")
        # This is the lower level directory for this workflow
        self.workflow_directory = self._create_workflow_directory()
        self.gpkg_path: str = os.path.join(self.working_directory, "study_area", "study_area.gpkg")
        if not os.path.exists(self.gpkg_path):
            raise ValueError(f"Study area geopackage not found at {self.gpkg_path}.")
        self.bboxes_layer = QgsVectorLayer(f"{self.gpkg_path}|layername=study_area_bboxes", "study_area_bboxes", "ogr")
        self.areas_layer = QgsVectorLayer(f"{self.gpkg_path}|layername=study_area_polygons", "study_area_polygons", "ogr")
        self.output_crs = self.bboxes_layer.crs()


    @abstractmethod
    def execute(self) -> bool:
        """
        Executes the workflow logic.
        :return: True if the workflow completes successfully, False if canceled or failed.
        """
        pass

    def _create_workflow_directory(self) -> str:
        """
        Creates the directory for this workflow if it doesn't already exist.
        It will be in the scheme of working_dir/dimension/factor/indicator

        :return: The path to the workflow directory
        """
        workflow_dir = os.path.join(
            self.working_directory, "contextual", "workplace_discrimination", "wbl_2024_workplace_index_score")
        if not os.path.exists(workflow_dir):
            try:
                os.makedirs(workflow_dir)
                QgsMessageLog.logMessage(f"Created study area directory: {workflow_dir}", tag="Geest", level=Qgis.Info)
            except Exception as e:
                QgsMessageLog.logMessage(f"Error creating directory: {e}", tag="Geest", level=Qgis.Critical)
        return workflow_dir

