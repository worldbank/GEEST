import os
from qgis.core import QgsVectorLayer, QgsProcessingFeedback
import processing


class Rasterizer:
    def __init__(
        self,
        vector_layer_path,
        output_dir,
        pixel_size,
        utm_crs,
        field=None,
        dimension="default",
    ):
        """
        Initializes the Rasterizer class with relevant parameters.

        Args:
            vector_layer_path (str): Path to the vector layer to be rasterized.
            output_dir (str): Directory where the rasterized output will be saved.
            pixel_size (int or float): Pixel size for the rasterized output.
            utm_crs (QgsCoordinateReferenceSystem): CRS for rasterization.
            field (str): The field to rasterize by (optional). If None, a burn value can be used.
            dimension (str): Sub-directory within the output directory where results are saved.
        """
        self.vector_layer_path = vector_layer_path
        self.output_dir = os.path.normpath(output_dir)
        self.dimension = dimension
        self.pixel_size = pixel_size
        self.utm_crs = utm_crs
        self.field = field  # Field for rasterization (optional)

        self.current_script_path = os.path.dirname(os.path.abspath(__file__))
        self.temp_dir = os.path.join(self.output_dir, "temp")

        self.raster_output_path = os.path.join(
            self.output_dir, self.dimension, "rasterized_output.tif"
        )

        # Create necessary directories
        self._setup_directories()

        # Load and preprocess the vector layer
        self._load_and_preprocess_vector_layer()

    def _setup_directories(self):
        """Sets up the working and temporary directories."""
        os.makedirs(os.path.join(self.output_dir, self.dimension), exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

    def _load_and_preprocess_vector_layer(self):
        """Loads and preprocesses the vector layer, including reprojecting if necessary."""
        # Load the vector layer
        self.vector_layer = QgsVectorLayer(
            self.vector_layer_path, "vector_layer", "ogr"
        )
        if not self.vector_layer.isValid():
            raise ValueError(f"Invalid vector layer: {self.vector_layer_path}")

        # Reproject the vector layer if necessary
        if self.vector_layer.crs() != self.utm_crs:
            reprojected_result = processing.run(
                "native:reprojectlayer",
                {
                    "INPUT": self.vector_layer,
                    "TARGET_CRS": self.utm_crs,
                    "OUTPUT": "memory:",
                },
                feedback=QgsProcessingFeedback(),
            )
            self.vector_layer = reprojected_result["OUTPUT"]

    def rasterize_vector_layer(self, nodata_value=-9999, data_type=5):
        """
        Rasterizes the vector layer using the gdal:rasterize algorithm.

        Args:
            nodata_value (int/float): NoData value for the output raster.
            data_type (int): Data type for the raster output (default is Float32).
        """
        rasterize_params = {
            "INPUT": self.vector_layer,
            "FIELD": self.field,  # Field to use for rasterization, or None for burn value
            "BURN": None if self.field else 1,  # Burn value if no field is provided
            "UNITS": 1,  # pixel size is set in units of CRS
            "WIDTH": self.pixel_size,
            "HEIGHT": self.pixel_size,
            "EXTENT": self.vector_layer.extent(),
            "NODATA": nodata_value,
            "DATA_TYPE": data_type,  # Data type: Float32 (5) or others
            "OUTPUT": self.raster_output_path,
        }

        # Run the rasterization algorithm
        rasterize_result = processing.run(
            "gdal:rasterize", rasterize_params, feedback=QgsProcessingFeedback()
        )

        self.rasterized_layer = rasterize_result["OUTPUT"]
        if not os.path.exists(self.rasterized_layer):
            raise ValueError("Rasterization failed. Output file not created.")

    def get_rasterized_layer_path(self):
        """
        Returns the path to the rasterized output layer.

        Returns:
            str: Path to the rasterized layer.
        """
        return self.rasterized_layer
