import datetime
import os
import traceback
from abc import ABC, abstractmethod
from qgis.core import (
    QgsFeedback,
    QgsVectorLayer,
    QgsMessageLog,
    Qgis,
    QgsProcessingContext,
)
from qgis.PyQt.QtCore import QSettings, pyqtSignal
from geest.core import JsonTreeItem


class WorkflowBase(ABC):
    """
    Abstract base class for all workflows.
    Every workflow must accept an attributes dictionary and a QgsFeedback object.
    """

    # Signal for progress changes - will be propagated to the task that owns this workflow
    progressChanged = pyqtSignal(int)

    def __init__(
        self, item: JsonTreeItem, feedback: QgsFeedback, context: QgsProcessingContext
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param attributes: Item containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        """
        self.item = item  # ⭐️ This is a reference - whatever you change in this item will directly update the tree
        self.feedback = feedback
        self.context = context  # QgsProcessingContext
        self.workflow_name = None  # This is set in the concrete class
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
        self.attributes = self.item.data(3)
        self.layer_id = self.attributes.get("ID", "").lower().replace(" ", "_")
        self.attributes["Result"] = "Not Run"

    def execute(self) -> bool:
        """
        Executes the workflow logic.
        :return: True if the workflow completes successfully, False if canceled or failed.
        """
        # call the execute method of the concrete class and then add a time stamp to the attributes
        try:
            self.attributes["Execution Start Time"] = (
                datetime.datetime.now().isoformat()
            )
            result = self.do_execute()
            self.attributes["Execution End Time"] = datetime.datetime.now().isoformat()
            # remove error.txt if it exists
            error_file = os.path.join(self.workflow_directory, "error.txt")
            if os.path.exists(error_file):
                os.remove(error_file)
            return result
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Failed to process {self.workflow_name}: {e}",
                tag="Geest",
                level=Qgis.Critical,
            )
            QgsMessageLog.logMessage(
                traceback.format_exc(),
                tag="Geest",
                level=Qgis.Critical,
            )
            self.attributes["Indicator Result"] = f"{self.workflow_name} Workflow Error"
            # Write the traceback to error.txt in the workflow_directory
            with open(os.path.join(self.workflow_directory, "error.txt"), "w") as f:
                f.write(f"Failed to process {self.workflow_name}: {e}\n")
                f.write(traceback.format_exc())
            return False

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
        directory = os.path.join(self.working_directory, *paths)
        # Create the directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)

        return directory
