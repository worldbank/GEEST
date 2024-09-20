import os
from qgis.core import QgsVectorLayer, QgsProcessingFeedback
import processing


class Extents:
    def __init__(self, workingDir, countryLayerPath, pixelSize, UTM_crs):
        """
        Initializes the Extents class with relevant parameters.

        Args:
            workingDir (str): The working directory path.
            countryLayerPath (str): The file path of the country layer.
            pixelSize (float): The pixel size for raster operations.
            UTM_crs (QgsCoordinateReferenceSystem): The CRS to reproject the country layer to.
        """
        # Set up paths and directories
        self.current_script_path = os.path.dirname(os.path.abspath(__file__))
        self.workingDir = os.path.normpath(workingDir)
        self.Dimension = "Place Characterization"
        self.tempDir = os.path.join(self.workingDir, "temp")

        # Create necessary directories
        self._setup_directories()

        # Input parameters
        self.countryLayerPath = countryLayerPath
        self.pixelSize = pixelSize
        self.UTM_crs = UTM_crs

        # Preprocess the country layer
        self._load_and_preprocess_country_layer()

    def _setup_directories(self):
        """Sets up the working and temporary directories."""
        os.makedirs(os.path.join(self.workingDir, self.Dimension), exist_ok=True)
        os.makedirs(self.tempDir, exist_ok=True)
        os.chdir(self.workingDir)

    def _load_and_preprocess_country_layer(self):
        """Loads and preprocesses the country layer, including reprojecting if necessary."""
        # Load the country layer
        self.countryLayer = QgsVectorLayer(
            self.countryLayerPath, "country_layer", "ogr"
        )
        if not self.countryLayer.isValid():
            raise ValueError("Invalid country layer")

        # Reproject the country layer if necessary
        if self.countryLayer.crs() != self.UTM_crs:
            self.countryLayer = processing.run(
                "native:reprojectlayer",
                {
                    "INPUT": self.countryLayer,
                    "TARGET_CRS": self.UTM_crs,
                    "OUTPUT": "memory:",
                },
                feedback=QgsProcessingFeedback(),
            )["OUTPUT"]

        # Get the extent of the country layer
        self.country_extent = self.countryLayer.extent()

    def get_country_extent(self):
        """
        Returns the extent of the country layer.

        Returns:
            QgsRectangle: Extent of the country layer.
        """
        return self.country_extent

    def get_processed_layers(self):
        """
        Returns a dictionary containing the processed layers and paths.

        Returns:
            dict: Contains processed layers and paths.
        """
        return {
            "current_script_path": self.current_script_path,
            "workingDir": self.workingDir,
            "Dimension": self.Dimension,
            "tempDir": self.tempDir,
            "countryLayer": self.countryLayer,
            "country_extent": self.country_extent,
            "pixelSize": self.pixelSize,
            "UTM_crs": self.UTM_crs,
        }
