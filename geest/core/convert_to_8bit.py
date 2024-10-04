import os
import processing
from qgis.core import QgsMessageLog, Qgis, QgsRasterLayer, QgsProject


class RasterConverter:
    """
    A class to handle the conversion of rasters to 8-bit TIFFs.
    """

    def __init__(self, feedback=None):
        """
        Initialize the RasterConverter with optional feedback for progress reporting.
        :param feedback: Optional QgsFeedback object for reporting progress.
        """
        self.feedback = feedback

    def convert_to_8bit(self, input_raster: str, output_raster: str) -> bool:
        """
        Convert the input raster to an 8-bit TIFF using gdal:translate.
        :param input_raster: Path to the input raster file.
        :param output_raster: Path to the output 8-bit TIFF file.
        :return: True if conversion is successful, False otherwise.
        """
        QgsMessageLog.logMessage(
            f"Converting {input_raster} to 8-bit TIFF at {output_raster}.",
            tag="Geest",
            level=Qgis.Info,
        )

        params = {
            "INPUT": input_raster,
            "TARGET_CRS": None,  # Use input CRS
            "NODATA": -9999,
            "COPY_SUBDATASETS": False,
            "OPTIONS": "",
            "EXTRA": "",
            "DATA_TYPE": 1,  # 1 = Byte (8-bit unsigned)
            "OUTPUT": output_raster,
        }

        try:
            # Run the gdal:translate processing algorithm
            processing.run("gdal:translate", params, feedback=self.feedback)
            QgsMessageLog.logMessage(
                f"Successfully converted {input_raster} to 8-bit TIFF.",
                tag="Geest",
                level=Qgis.Info,
            )
            return True
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Failed to convert {input_raster} to 8-bit: {str(e)}",
                tag="Geest",
                level=Qgis.Critical,
            )
            return False
