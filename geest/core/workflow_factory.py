from .workflows import RasterLayerWorkflow, DontUseWorkflow, DefaultIndexScoreWorkflow
from qgis.core import QgsFeedback


class WorkflowFactory:
    """
    A factory class that creates workflow objects based on the attributes.
    The workflows accept a QgsFeedback object to report progress and handle cancellation.
    """

    def create_workflow(self, attributes, feedback: QgsFeedback):
        """
        Determines the workflow to return based on 'Analysis Mode' in the attributes.
        Passes the feedback object to the workflow for progress reporting.
        """
        analysis_mode = attributes.get("Analysis Mode")

        if analysis_mode == "Spatial Analysis":
            return RasterLayerWorkflow(attributes, feedback)
        elif analysis_mode == "Use Default Index Score":
            return DefaultIndexScoreWorkflow(attributes, feedback)
        elif analysis_mode == "Don’t Use":
            return DontUseWorkflow(attributes, feedback)
        elif analysis_mode == "Temporal Analysis":
            return RasterLayerWorkflow(attributes, feedback)
        else:
            raise ValueError(f"Unknown Analysis Mode: {analysis_mode}")
