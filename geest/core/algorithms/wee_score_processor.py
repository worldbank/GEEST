import os
import traceback
from typing import Optional, List
import shutil

from qgis.core import (
    QgsTask,
    QgsProcessingContext,
    QgsFeedback,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
)
import processing
from geest.utilities import log_message, resources_path
from geest.core.algorithms import AreaIterator


class WEEScoreProcessingTask(QgsTask):
    """
    A QgsTask subclass for calculating WEE SCORE using raster algebra.

    It iterates over study areas, calculates the WEE SCORE using aligned input rasters
    (GEEST and POP), combines the resulting rasters into a VRT, and applies a QML style.

    Args:
        study_area_gpkg_path (str): Path to the GeoPackage containing study area masks.
        working_directory (str): Directory to save the output rasters.
        target_crs (Optional[QgsCoordinateReferenceSystem]): CRS for the output rasters.
        force_clear (bool): Flag to force clearing of all outputs before processing.
    """

    def __init__(
        self,
        study_area_gpkg_path: str,
        working_directory: str,
        target_crs: Optional[QgsCoordinateReferenceSystem] = None,
        force_clear: bool = False,
    ):
        super().__init__("WEE Score Processor", QgsTask.CanCancel)
        self.study_area_gpkg_path = study_area_gpkg_path

        self.output_dir = os.path.join(working_directory, "wee_score")
        os.makedirs(self.output_dir, exist_ok=True)

        # These folders should already exist from the aggregation analysis and population raster processing
        self.population_folder = os.path.join(self.output_dir, "population")
        self.wee_folder = os.path.join(self.output_dir)

        self.force_clear = force_clear
        if self.force_clear and os.path.exists(self.output_dir):
            for file in os.listdir(self.output_dir):
                os.remove(os.path.join(self.output_dir, file))

        self.target_crs = target_crs
        if not self.target_crs:
            layer: QgsVectorLayer = QgsVectorLayer(
                f"{self.study_area_gpkg_path}|layername=study_area_clip_polygons",
                "study_area_clip_polygons",
                "ogr",
            )
            self.target_crs = layer.crs()
            del layer
        self.output_rasters: List[str] = []

        log_message("Initialized WEE SCORE Processing Task")

    def run(self) -> bool:
        """
        Executes the WEE SCORE calculation task.
        """
        try:
            self.calculate_wee_score()
            self.generate_vrt()
            return True
        except Exception as e:
            log_message(f"Task failed: {e}")
            log_message(traceback.format_exc())
            return False

    def validate_rasters(self, geest_raster_path, pop_raster_path) -> None:
        """
        Checks if GEEST and POP rasters have the same origin, dimensions, and pixel sizes.
        """
        log_message("Validating input rasters")
        log_message(f"GEEST Raster: {geest_raster_path}")
        log_message(f"POP Raster  : {pop_raster_path}")
        geest_layer = QgsRasterLayer(geest_raster_path, "GEEST")
        pop_layer = QgsRasterLayer(pop_raster_path, "POP")

        if not geest_layer.isValid() or not pop_layer.isValid():
            raise ValueError("One or both input rasters are invalid.")

        geest_provider = geest_layer.dataProvider()
        pop_provider = pop_layer.dataProvider()

        geest_extent = geest_provider.extent()
        pop_extent = pop_provider.extent()
        if geest_extent != pop_extent:
            raise ValueError("Input rasters do not share the same extent.")

        geest_size = geest_provider.xSize(), geest_provider.ySize()
        pop_size = pop_provider.xSize(), pop_provider.ySize()
        if geest_size != pop_size:
            raise ValueError("Input rasters do not share the same dimensions.")

        log_message("Validation successful: rasters are aligned.")

    def calculate_wee_score(self) -> None:
        """
        Calculates WEE SCORE using raster algebra and saves the result for each area.
        """
        area_iterator = AreaIterator(self.study_area_gpkg_path)
        for index, (_, _, _, _) in enumerate(area_iterator):
            if self.isCanceled():
                return

            wee_path = os.path.join(self.wee_folder, f"wee_masked_{index}.tif")
            population_path = os.path.join(
                self.population_folder, f"reclassified_{index}.tif"
            )
            self.validate_rasters(wee_path, population_path)

            output_path = os.path.join(self.output_dir, f"wee_score_{index}.tif")
            if not self.force_clear and os.path.exists(output_path):
                log_message(f"Reusing existing raster: {output_path}")
                self.output_rasters.append(output_path)
                continue

            log_message(f"Calculating WEE SCORE for area {index}")

            # Raster algebra formula: ((GEEST - 1) * 3) + POP
            params = {
                "EXPRESSION": f"((A@1 - 1) * 3) + B@1",
                "LAYERS": [wee_path, population_path],
                "OUTPUT": output_path,
            }
            processing.run("gdal:rastercalculator", params)
            self.output_rasters.append(output_path)

            log_message(f"WEE SCORE raster saved to {output_path}")

    def generate_vrt(self) -> None:
        """
        Combines all WEE SCORE rasters into a single VRT and applies a QML style.
        """
        vrt_path = os.path.join(self.output_dir, "wee_score.vrt")
        qml_path = os.path.join(self.output_dir, "wee_score.qml")
        source_qml = resources_path("resources", "qml", "wee_score_style.qml")

        params = {
            "INPUT": self.output_rasters,
            "RESOLUTION": 0,  # Use highest resolution
            "SEPARATE": False,  # Combine into a single band
            "OUTPUT": vrt_path,
        }

        processing.run("gdal:buildvirtualraster", params)
        log_message(f"Generated VRT at {vrt_path}")

        # Apply QML Style
        if os.path.exists(source_qml):
            shutil.copy(source_qml, qml_path)
            log_message(f"Copied QML style from {source_qml} to {qml_path}")
        else:
            log_message("QML style file not found. Skipping QML copy.")

    def finished(self, result: bool) -> None:
        """
        Called when the task completes.
        """
        if result:
            log_message("WEE SCORE calculation completed successfully.")
        else:
            log_message("WEE SCORE calculation failed.")
