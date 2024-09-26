from qgis.core import QgsCoordinateTransform, QgsCoordinateReferenceSystem, QgsProcessingFeedback, QgsVectorLayer
from qgis import processing

class CRSConverter:
    def __init__(self, layer):
        """
        Initialize the CRSConverter class with a given layer.
        :param layer: The input layer for CRS conversion (QgsVectorLayer or QgsRasterLayer)
        """
        self.layer = layer

    def convert_to_crs(self, target_crs_epsg):
        """
        Converts the layer's CRS to the target CRS based on the EPSG code.
        :param target_crs_epsg: EPSG code of the target CRS
        """
        # Get the current CRS of the layer
        current_crs = self.layer.crs()

        # Create the target CRS using the EPSG code
        target_crs = QgsCoordinateReferenceSystem(f"EPSG:{target_crs_epsg}")

        # Check if the current CRS is the same as the target CRS
        if current_crs != target_crs:
            print(f"Converting layer from {current_crs.authid()} to {target_crs.authid()}")

            layer = processing.run(
                "native:reprojectlayer",
                {
                    "INPUT": self.layer,
                    "TARGET_CRS": target_crs,
                    "OUTPUT": "memory:",
                },
                feedback=QgsProcessingFeedback(),
            )["OUTPUT"]
            print(f"Layer successfully converted to {target_crs.authid()}")
            return layer
        else:
            print(f"Layer is already in the target CRS: {target_crs.authid()}")
            return self.layer
