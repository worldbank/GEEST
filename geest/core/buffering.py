import os
from qgis.core import (
    QgsVectorLayer,
    QgsProcessingFeedback,
    QgsMessageLog,
    Qgis,
)
import processing


class SinglePointBuffer:
    def __init__(self, input_layer, buffer_distance, output_path, crs):
        """
        Initializes the SinglePointBuffer class.

        Args:
            input_layer (QgsVectorLayer): The input polygon or line layer to buffer.
            buffer_distance (float): The distance of the buffer in CRS units.
            output_path (str): The path to save the buffered layer.
            crs (QgsCoordinateReferenceSystem): The expected CRS for the input layer.
        """
        self.input_layer = input_layer
        self.buffer_distance = buffer_distance
        self.output_path = output_path
        self.crs = crs

        # Check if the input layer CRS matches the expected CRS, and reproject if necessary
        self.processed_layer = self._check_and_reproject_layer()

    def _check_and_reproject_layer(self):
        """
        Checks if the input layer has the expected CRS. If not, it reprojects the layer.

        Returns:
            QgsVectorLayer: The input layer, either reprojected or unchanged.
        """
        if self.input_layer.crs() != self.crs:
            QgsMessageLog.logMessage(
                f"Reprojecting layer from {self.input_layer.crs().authid()} to {self.crs.authid()}",
                'Geest',
                level=Qgis.Info
            )
            reproject_result = processing.run(
                "native:reprojectlayer",
                {
                    "INPUT": self.input_layer,
                    "TARGET_CRS": self.crs,
                    "OUTPUT": "memory:",  # Reproject in memory
                },
                feedback=QgsProcessingFeedback(),
            )
            reprojected_layer = reproject_result["OUTPUT"]
            return reprojected_layer

        # If CRS matches, return the original layer
        return self.input_layer

    def create_buffer(self):
        """
        Creates a buffer around the input layer's geometries.

        Returns:
            QgsVectorLayer: The resulting buffered layer.
        """
        # Check if the output file already exists and delete it if necessary
        if os.path.exists(self.output_path):
            QgsMessageLog.logMessage(
                f"Warning: {self.output_path} already exists. It will be overwritten.",
                'Geest',
                level=Qgis.Warning
            )
            os.remove(self.output_path)

        # Run the buffer operation using QGIS processing
        buffer_result = processing.run(
            "native:buffer",
            {
                "INPUT": self.processed_layer,
                "DISTANCE": self.buffer_distance,
                "SEGMENTS": 5,  # The number of segments used to approximate curves
                "END_CAP_STYLE": 0,  # Round cap
                "JOIN_STYLE": 0,  # Round joins
                "MITER_LIMIT": 2,
                "DISSOLVE": False,  # Whether to dissolve the output or keep it separate for each feature
                "OUTPUT": self.output_path,
            },
            feedback=QgsProcessingFeedback(),
        )

        # Load the buffered layer as QgsVectorLayer
        buffered_layer = QgsVectorLayer(self.output_path, "buffered_layer", "ogr")

        if not buffered_layer.isValid():
            raise ValueError("Buffered layer creation failed.")

        return buffered_layer
