# -*- coding: utf-8 -*-
"""📦 Opportunities By GeoE3 Score Population Processor module.

This module contains functionality for opportunities by GeoE3 Score population processor.
"""

import os
import shutil
import traceback
from typing import List, Optional

from qgis import processing
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsRasterLayer,
    QgsTask,
    QgsVectorLayer,
)

from geest.core import JsonTreeItem
from geest.core.algorithms import AreaIterator
from geest.utilities import log_message, resources_path


class OpportunitiesByWeeScorePopulationProcessingTask(QgsTask):
    """
    A QgsTask subclass for calculating masked GeoE3 Score x Population using raster algebra.

    It iterates over study areas, gets the GeoE3 Score x Population and applies the Job Opportunities
    mask to it. It then combines the resulting rasters into a VRT, and applies a QML style.

    It takes as input a GeoE3 Score layer (output as the result of Analysis level aggregation
    of GEEST workflow). This GeoE3 Score layer has the following classes:

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

    Additionally a mask layer containing cell values of 1 for included areas is required.
    One sub product is made per study area and then all of the study area outputs are
    combined as a VRT and assigned a QML with the correct legend colours.

    Args:
        study_area_gpkg_path (str): Path to the GeoPackage containing study area masks.
        working_directory (str): Directory to save the output rasters.
        target_crs (Optional[QgsCoordinateReferenceSystem]): CRS for the output rasters.
        force_clear (bool): Flag to force clearing of all outputs before processing.
    """

    def __init__(
        self,
        item: JsonTreeItem,
        study_area_gpkg_path: str,
        working_directory: str,
        target_crs: Optional[QgsCoordinateReferenceSystem] = None,
        force_clear: bool = False,
    ):
        super().__init__("Opportunities GeoE3 Score by Population Processor", QgsTask.CanCancel)
        self.item = item
        self.study_area_gpkg_path = study_area_gpkg_path

        self.output_dir = os.path.join(working_directory, "opportunities_by_geoe3_score_by_population")
        os.makedirs(self.output_dir, exist_ok=True)

        # These folders should already exist from the analysis and opportunities mask processor
        self.opportunity_masks_folder = os.path.join(working_directory, "opportunity_masks")
        self.geoe3_folder = os.path.join(working_directory, "geoe3_by_population_score")

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
        self.result_file_key = "geoe3_by_population_by_opportunities_mask_result_file"
        self.result_key = "geoe3_by_population_by_opportunities_mask_result"
        log_message("Initialized Opportunities Mask by GeoE3 Score by Population Processing Task")

    def run(self) -> bool:
        """
        Executes the Opportunities by GeoE3 Score by Population calculation task.

        Returns:
            bool: True if the task completed successfully, False otherwise.
        """
        try:
            self.calculate_score()
            vrt_path = self.generate_vrt()
            self.item.setAttribute(self.result_file_key, vrt_path)
            self.item.setAttribute(
                self.result_key,
                "GeoE3 Score by Population by Opportunities Mask Created OK",
            )
            return True
        except Exception as e:
            log_message(f"Task failed: {e}")
            log_message(traceback.format_exc())
            self.item.setAttribute(self.result_key, f"Task failed: {e}")
            return False

    def validate_rasters(
        self,
        opportunities_mask_raster: QgsRasterLayer,
        geoe3_score_by_population_raster: QgsRasterLayer,
        dimension_check=False,
    ) -> None:
        """
        Checks if Opportunities Mask and GeoE3 Score by Population
        rasters have the same origin, dimensions, and pixel sizes.

        Args:
            opportunities_mask_raster (QgsRasterLayer): The mask raster layer.
            geoe3_score_by_population_raster (QgsRasterLayer): The GeoE3 Score by Population raster layer.
            dimension_check (bool): Flag to check if the rasters have the same dimensions. Defaults to False.

        Raises:
            ValueError: If one or both input rasters are invalid, or if rasters don't share the same extent or dimensions when dimension_check is True.
        """
        log_message("Validating input rasters")
        log_message(f"opportunities_mask_raster: {opportunities_mask_raster.source()}")  # noqa: E293
        log_message(
            f"geoe3_score_by_population raster : {geoe3_score_by_population_raster.source()}"
        )  # noqa: E293, E203

        if (
            not opportunities_mask_raster.isValid()  # noqa: W503
            or not geoe3_score_by_population_raster.isValid()  # noqa: W503
        ):
            raise ValueError("One or both input rasters are invalid.")

        if not dimension_check:
            return

        mask_provider = opportunities_mask_raster.dataProvider()
        geoe3_score_by_population_provider = geoe3_score_by_population_raster.dataProvider()

        mask_extent = mask_provider.extent()
        geoe3_score_by_population_size = geoe3_score_by_population_provider.extent()
        if mask_extent != geoe3_score_by_population_size:
            raise ValueError("Input rasters do not share the same extent.")

        mask_size = mask_provider.xSize(), mask_provider.ySize()
        geoe3_score_by_population_size = (
            geoe3_score_by_population_provider.xSize(),
            geoe3_score_by_population_provider.ySize(),
        )
        if mask_size != geoe3_score_by_population_size:
            raise ValueError("Input rasters do not share the same dimensions.")

        log_message("Validation successful: rasters are aligned.")

    def calculate_score(self) -> None:
        """
        Calculates Mask x GeoE3 Score by Population using raster
        algebra and saves the result for each area.
        """
        area_iterator = AreaIterator(self.study_area_gpkg_path)
        for index, (_, _, _, _) in enumerate(area_iterator):
            if self.isCanceled():
                return

            mask_path = os.path.join(self.opportunity_masks_folder, f"opportunites_mask_{index}.tif")
            geoe3_score_by_population_path = os.path.join(self.geoe3_folder, f"geoe3_by_population_score_{index}.tif")
            mask_layer = QgsRasterLayer(mask_path, "GeoE3")
            geoe3_score_by_population_layer = QgsRasterLayer(geoe3_score_by_population_path, "POP")
            self.validate_rasters(mask_layer, geoe3_score_by_population_layer, dimension_check=False)

            output_path = os.path.join(self.output_dir, f"geoe3_by_population_by_opportunities_mask_{index}.tif")
            if not self.force_clear and os.path.exists(output_path):
                log_message(f"Reusing existing raster: {output_path}")
                self.output_rasters.append(output_path)
                continue

            log_message(f"Calculating Mask by SCORE by Population for area {index}")

            params = {
                "INPUT_A": mask_layer,
                "BAND_A": 1,
                "INPUT_B": geoe3_score_by_population_layer,
                "BAND_B": 1,
                "FORMULA": "A * B",
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

            log_message(f"Masked GeoE3 Score raster saved to {output_path}")

    def generate_vrt(self) -> str:
        """
        Combines all GeoE3 Score rasters into a single VRT and applies a QML style.

        Returns:
            str: Path to the generated VRT file.
        """
        vrt_path = os.path.join(self.output_dir, "geoe3_by_population_by_opportunities_mask.vrt")
        qml_path = os.path.join(self.output_dir, "geoe3_by_population_by_opportunities_mask.qml")
        source_qml = resources_path("resources", "qml", "geoe3_by_population_score.qml")

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
        return vrt_path

    def finished(self, result: bool) -> None:
        """
        Called when the task completes.

        Args:
            result (bool): The result of the task execution.
        """
        if result:
            log_message("Opportunities mask by GeoE3 Score by Population calculation completed successfully.")
        else:
            log_message("Opportunities mask by GeoE3 Score by Population calculation failed.")
