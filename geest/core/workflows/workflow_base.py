import datetime
import os
from abc import ABC, abstractmethod
from qgis.core import QgsFeedback, QgsVectorLayer, QgsMessageLog, Qgis
from qgis.PyQt.QtCore import QSettings
from geest.gui.treeview import JsonTreeItem


class WorkflowBase(ABC):
    """
    Abstract base class for all workflows.
    Every workflow must accept an attributes dictionary and a QgsFeedback object.
    """

    def __init__(self, item: JsonTreeItem, feedback: QgsFeedback):
        """
        Initialize the workflow with attributes and feedback.
        :param attributes: Dictionary containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        """
        self.item = item  # ⭐️ This is a reference - whatever you change in this item will directly update the tree
        self.feedback = feedback
        # This is set in the setup panel
        self.settings = QSettings()
        # This is the top level folder for work files
        self.working_directory = self.settings.value("last_working_directory", "")
        if not self.working_directory:
            raise ValueError("Working directory not set.")
        # This is the lower level directory for this workflow
        self.workflow_directory = self._create_workflow_directory()
        self.gpkg_path: str = os.path.join(
            self.working_directory, "study_area", "study_area.gpkg"
        )
        if not os.path.exists(self.gpkg_path):
            raise ValueError(f"Study area geopackage not found at {self.gpkg_path}.")
        self.bboxes_layer = QgsVectorLayer(
            f"{self.gpkg_path}|layername=study_area_bboxes", "study_area_bboxes", "ogr"
        )
        self.areas_layer = QgsVectorLayer(
            f"{self.gpkg_path}|layername=study_area_polygons",
            "study_area_polygons",
            "ogr",
        )
        self.output_crs = self.bboxes_layer.crs()
        # Will be populated by the workflow
        attributes = self.item.data(3)
        attributes["Result"] = "Not Run"

    def execute(self) -> bool:
        """
        Executes the workflow logic.
        :return: True if the workflow completes successfully, False if canceled or failed.
        """
        # call the execute method of the concrete class and then add a time stamp to the attributes
        attributes = self.item.data(3)
        attributes["Execution Start Time"] = datetime.datetime.now().isoformat()
        result = self.do_execute()
        attributes["Execution End Time"] = datetime.datetime.now().isoformat()
        return result

    @abstractmethod
    def do_execute(self) -> bool:
        """
        Executes the actual workflow logic.
        Must be implemented by subclasses.
        :return: True if the workflow completes successfully, False if canceled or failed.
        """
        pass

    def _create_workflow_directory(self, *subdirs: str) -> str:
        """
        Creates the directory for this workflow if it doesn't already exist.
        It will be in the scheme of working_dir/dimension/factor/indicator

        :return: The path to the workflow directory
        """
        paths = self.item.getPaths()
        directory = os.path.join(self.workflow_directory, *paths)
        # Create the directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)

        return directory
