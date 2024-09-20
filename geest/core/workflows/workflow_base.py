from abc import ABC, abstractmethod
from qgis.core import QgsFeedback


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

    @abstractmethod
    def execute(self) -> bool:
        """
        Executes the workflow logic.
        :return: True if the workflow completes successfully, False if canceled or failed.
        """
        pass
