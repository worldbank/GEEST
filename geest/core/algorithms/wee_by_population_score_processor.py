import os
import traceback
from typing import Optional, List
import shutil

from qgis.core import (
    QgsTask,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
)
import processing
from geest.utilities import log_message, resources_path
from geest.core.algorithms import AreaIterator


class WEEByPopulationScoreProcessingTask(QgsTask):
    """
    A QgsTask subclass for calculating WEE x Population SCORE using raster algebra.

    It iterates over study areas, calculates the WEE SCORE using aligned input rasters
    (WEE and POP), combines the resulting rasters into a VRT, and applies a QML style.

    It takes as input a WEE Score layer (output as the result of Analysis level aggregation
    of GEEST workflow). This WEE Score layer has the following classes:

    | Range  | Description               | Color      |
    |--------|---------------------------|------------|
    | 0 - 1  | Very Low Enablement       | ![#FF0000](#) `#FF0000` |
    | 1 - 2  | Low Enablement            | ![#FFA500](#) `#FFA500` |
    | 2 - 3  | Moderately Enabling       | ![#FFFF00](#) `#FFFF00` |
    | 3 - 4  | Enabling                  | ![#90EE90](#) `#90EE90` |
    | 4 - 5  | Highly Enabling           | ![#0000FF](#) `#0000FF` |

    Additionally a population layer containing counts per cell is required. The population
    data is masked to only include pixels contained within study areas and then reclassified into
    three classes:

    | Color      | Description         |
    |------------|---------------------|
    | ![#FFFF00](#) `#FFFF00` | Low Population      |
    | ![#FFA500](#) `#FFA500` | Medium Population   |
    | ![#800000](#) `#800000` | High Population     |


    The output WEE x Population Score can be one of 15 classes calculated as

    ((A - 1) * 3) + B

    Where A is WEE Score and B is Population class. The output classes are as follows:

    | Color      | Description                                 |
    |------------|---------------------------------------------|
    | ![#FF0000](#) `#FF0000` | Very low enablement, low population       |
    | ![#FF0000](#) `#FF0000` | Very low enablement, medium population    |
    | ![#FF0000](#) `#FF0000` | Very low enablement, high population      |
    | ![#FFA500](#) `#FFA500` | Low enablement, low population            |
    | ![#FFA500](#) `#FFA500` | Low enablement, medium population         |
    | ![#FFA500](#) `#FFA500` | Low enablement, high population           |
    | ![#FFFF00](#) `#FFFF00` | Moderately enabling, low population       |
    | ![#FFFF00](#) `#FFFF00` | Moderately enabling, medium population    |
    | ![#FFFF00](#) `#FFFF00` | Moderately enabling, high population      |
    | ![#90EE90](#) `#90EE90` | Enabling, low population                  |
    | ![#90EE90](#) `#90EE90` | Enabling, medium population               |
    | ![#90EE90](#) `#90EE90` | Enabling, high population                 |
    | ![#0000FF](#) `#0000FF` | Highly enabling, low population           |
    | ![#0000FF](#) `#0000FF` | Highly enabling, medium population        |
    | ![#0000FF](#) `#0000FF` | Highly enabling, high population          |

    One sub product is made per study area and then all of the study area outputs are
    combined as a VRT and assigned a QML with the correct legend colours.

    📒 The population processing phases resamples the population into a grid aligned
        raster with the same output pixel dimensions as the study area. The resampling
        process uses the gdalwarp -r sum flag which is not currently available in QGIS
        processing framework, so we manually call gdalwarp to perform this operation.

        I tried to implement a generic way to discover the location of gdalwarp but this
        may not work well on all systems.

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

        self.output_dir = os.path.join(working_directory, "wee_by_population_score")
        os.makedirs(self.output_dir, exist_ok=True)

        # These folders should already exist from the aggregation analysis and population raster processing
        self.population_folder = os.path.join(working_directory, "population")
        self.wee_folder = os.path.join(working_directory, "wee_score")

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
            self.calculate_score()
            self.generate_vrt()
            return True
        except Exception as e:
            log_message(f"Task failed: {e}")
            log_message(traceback.format_exc())
            return False

    def validate_rasters(
        self,
        geest_raster: QgsRasterLayer,
        pop_raster: QgsRasterLayer,
        dimension_check=False,
    ) -> None:
        """
        Checks if GEEST and POP rasters have the same origin, dimensions, and pixel sizes.

        Raises an exception if the check fails.

        Args:
            geest_raster_path (QgsRasterLayer): Path to the GEEST raster.
            pop_raster_path (QgsRasterLayer): Path to the POP raster.
            dimension_check (bool): Flag to check if the rasters have the same dimensions.
        returns:
            None
        """
        log_message("Validating input rasters")
        log_message(f"GEEST Raster: {geest_raster.source()}")
        log_message(f"POP Raster  : {pop_raster.source()}")

        if not geest_raster.isValid() or not pop_raster.isValid():
            raise ValueError("One or both input rasters are invalid.")

        if not dimension_check:
            return

        geest_provider = geest_raster.dataProvider()
        pop_provider = pop_raster.dataProvider()

        geest_extent = geest_provider.extent()
        pop_extent = pop_provider.extent()
        if geest_extent != pop_extent:
            raise ValueError("Input rasters do not share the same extent.")

        geest_size = geest_provider.xSize(), geest_provider.ySize()
        pop_size = pop_provider.xSize(), pop_provider.ySize()
        if geest_size != pop_size:
            raise ValueError("Input rasters do not share the same dimensions.")

        log_message("Validation successful: rasters are aligned.")

    def calculate_score(self) -> None:
        """
        Calculates WEE by POP SCORE using raster algebra and saves the result for each area.
        """
        area_iterator = AreaIterator(self.study_area_gpkg_path)
        for index, (_, _, _, _) in enumerate(area_iterator):
            if self.isCanceled():
                return

            wee_path = os.path.join(self.wee_folder, f"wee_masked_{index}.tif")
            population_path = os.path.join(
                self.population_folder, f"reclassified_{index}.tif"
            )
            wee_layer = QgsRasterLayer(wee_path, "WEE")
            pop_layer = QgsRasterLayer(population_path, "POP")
            self.validate_rasters(wee_layer, pop_layer, dimension_check=False)

            output_path = os.path.join(
                self.output_dir, f"wee_by_population_score_{index}.tif"
            )
            if not self.force_clear and os.path.exists(output_path):
                log_message(f"Reusing existing raster: {output_path}")
                self.output_rasters.append(output_path)
                continue

            log_message(f"Calculating WEE by POP SCORE for area {index}")

            params = {
                "INPUT_A": wee_layer,
                "BAND_A": 1,
                "INPUT_B": pop_layer,
                "BAND_B": 1,
                "FORMULA": "((A - 1) * 3) + B",
                "NO_DATA": None,
                "EXTENT_OPT": 3,
                "PROJWIN": None,
                "RTYPE": 0,
                "OPTIONS": "",
                "EXTRA": "",
                "OUTPUT": output_path,
            }

            processing.run("gdal:rastercalculator", params)
            self.output_rasters.append(output_path)

            log_message(f"WEE SCORE raster saved to {output_path}")

    def generate_vrt(self) -> None:
        """
        Combines all WEE SCORE rasters into a single VRT and ap plies a QML style.
        """
        vrt_path = os.path.join(self.output_dir, "wee_by_population_score.vrt")
        qml_path = os.path.join(self.output_dir, "wee_by_population_score.qml")
        source_qml = resources_path("resources", "qml", "wee_by_population_score.qml")

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
