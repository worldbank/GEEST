import os
import traceback
from typing import Optional, Tuple
from qgis.core import (
    QgsTask,
    QgsProcessingContext,
    QgsFeedback,
    QgsCoordinateReferenceSystem,
    QgsRasterLayer,
    QgsRasterDataProvider,
    QgsVectorLayer,
    QgsFeature,
)
import processing
from geest.utilities import log_message
from geest.core.algorithms import AreaIterator


class PopulationRasterProcessingTask(QgsTask):
    """
    A QgsTask subclass for processing population raster layers.

    It iterates over bounding boxes and study areas, clips the population raster
    data to match the study area masks, and reclassifies the clipped rasters into
    three classes based on population values.

    Args:
        name (str): Name of the task.
        population_raster_path (str): Path to the population raster layer.
        study_area_gpkg_path (str): Path to the GeoPackage containing study area masks.
        output_dir (str): Directory to save the output rasters.
        crs (Optional[QgsCoordinateReferenceSystem]): CRS for the output rasters.
        context (Optional[QgsProcessingContext]): QGIS processing context.
        feedback (Optional[QgsFeedback]): QGIS feedback object.
        force_clear (bool): Flag to force clearing of all outputs before processing.
    """

    def __init__(
        self,
        name: str,
        population_raster_path: str,
        study_area_gpkg_path: str,
        output_dir: str,
        crs: Optional[QgsCoordinateReferenceSystem] = None,
        context: Optional[QgsProcessingContext] = None,
        feedback: Optional[QgsFeedback] = None,
        force_clear: bool = False,
    ):
        super().__init__(name, QgsTask.CanCancel)
        self.population_raster_path = population_raster_path
        self.study_area_gpkg_path = study_area_gpkg_path
        self.output_dir = os.path.join(output_dir, "population")
        self.force_clear = force_clear
        if self.force_clear and os.path.exists(self.output_dir):
            for file in os.listdir(self.output_dir):
                os.remove(os.path.join(self.output_dir, file))
        os.makedirs(self.output_dir, exist_ok=True)
        self.crs = crs
        self.context = context
        self.feedback = feedback
        self.global_min = float("inf")
        self.global_max = float("-inf")
        self.clipped_rasters = []
        self.reclassified_rasters = []

    def run(self) -> bool:
        """
        Executes the task to process population rasters.
        """
        try:
            self.process_population_rasters()
            self.reclassify_population_rasters()
            self.generate_vrts()
            return True
        except Exception as e:
            log_message(f"Task failed: {e}")
            log_message(traceback.format_exc())
            return False

    def finished(self, result: bool) -> None:
        """
        Called when the task completes.
        """
        if result:
            log_message("Population raster processing completed successfully.")
        else:
            log_message("Population raster processing failed.")

    def process_population_rasters(self) -> None:
        """
        Clips the population raster using study area masks and records min and max values.
        """
        area_iterator = AreaIterator(self.study_area_gpkg_path)
        for index, (current_area, clip_area, current_bbox, progress) in enumerate(
            area_iterator
        ):
            if self.feedback and self.feedback.isCanceled():
                return
            # create a temporary layer using the clip geometry
            clip_layer = QgsVectorLayer("Polygon", "clip", "memory")
            clip_layer.setCrs(self.crs)
            clip_layer.startEditing()
            feature = QgsFeature()
            feature.setGeometry(clip_area)
            clip_layer.addFeature(feature)
            clip_layer.commitChanges()

            layer_name = f"{index}.tif"
            output_path = os.path.join(self.output_dir, f"clipped_{layer_name}")
            log_message(f"Processing mask {output_path}")

            if not self.force_clear and os.path.exists(output_path):
                log_message(f"Reusing existing clipped raster: {output_path}")
                self.clipped_rasters.append(output_path)
                continue

            # Clip the population raster using the mask
            params = {
                "INPUT": self.population_raster_path,
                "MASK_LAYER": None,
                "MASK": clip_layer,
                "NODATA": -9999,
                "ALPHA_BAND": False,
                "CROP_TO_CUTLINE": True,
                "KEEP_RESOLUTION": True,
                "OPTIONS": "",
                "DATA_TYPE": 5,  # Float32
                "OUTPUT": output_path,
            }

            result = processing.run("gdal:cliprasterbymasklayer", params)

            if not result["OUTPUT"]:
                log_message(f"Failed to clip raster for mask: {layer_name}")
                continue

            clipped_layer = QgsRasterLayer(output_path, f"Clipped {layer_name}")
            if not clipped_layer.isValid():
                log_message(f"Invalid clipped raster layer for mask: {layer_name}")
                continue

            self.clipped_rasters.append(output_path)

            # Calculate min and max values for the clipped raster
            provider: QgsRasterDataProvider = clipped_layer.dataProvider()
            stats = provider.bandStatistics(1)
            self.global_min = min(self.global_min, stats.minimumValue)
            self.global_max = max(self.global_max, stats.maximumValue)

            log_message(
                f"Processed mask {layer_name}: Min={stats.minimumValue}, Max={stats.maximumValue}"
            )

    def reclassify_population_rasters(self) -> None:
        """
        Reclassifies clipped rasters into three classes based on population values.
        """
        area_iterator = AreaIterator(self.study_area_gpkg_path)
        range_third = (self.global_max - self.global_min) / 3

        for index, (current_area, clip_area, current_bbox, progress) in enumerate(
            area_iterator
        ):
            if self.feedback and self.feedback.isCanceled():
                return

            layer_name = f"{index}.tif"
            output_path = os.path.join(self.output_dir, f"reclassified_{layer_name}")

            input_path = os.path.join(self.output_dir, f"clipped_{layer_name}")
            log_message(f"Reclassifying {output_path} from {input_path}")

            if not self.force_clear and os.path.exists(output_path):
                log_message(f"Reusing existing reclassified raster: {output_path}")
                self.reclassified_rasters.append(output_path)
                continue

            params = {
                "INPUT_RASTER": input_path,
                "RASTER_BAND": 1,
                "TABLE": [
                    self.global_min,
                    self.global_min + range_third,
                    1,
                    self.global_min + range_third,
                    self.global_min + 2 * range_third,
                    2,
                    self.global_min + 2 * range_third,
                    self.global_max,
                    3,
                ],
                "NO_DATA": 0,
                "DATA_TYPE": 5,  # Float32
                # "DATA_TYPE": 1,  # Byte
                "OUTPUT": output_path,
            }
            log_message(f"Reclassifying raster: {input_path}")
            result = processing.run("native:reclassifybytable", params)

            if not result["OUTPUT"]:
                log_message(f"Failed to reclassify raster: {output_path}")
                continue

            self.reclassified_rasters.append(output_path)

            log_message(f"Reclassified raster: {output_path}")

    def generate_vrts(self) -> None:
        """
        Generates VRT files combining all clipped and reclassified rasters.
        """
        clipped_vrt_path = os.path.join(self.output_dir, "clipped_population.vrt")
        reclassified_vrt_path = os.path.join(
            self.output_dir, "reclassified_population.vrt"
        )

        # Generate VRT for clipped rasters
        if self.clipped_rasters:
            params = {
                "INPUT": self.clipped_rasters,
                "RESOLUTION": 0,  # Use highest resolution among input files
                "SEPARATE": False,  # Combine into a single band
                "OUTPUT": clipped_vrt_path,
            }
            processing.run("gdal:buildvirtualraster", params)
            log_message(f"Generated VRT for clipped rasters: {clipped_vrt_path}")

        # Generate VRT for reclassified rasters
        if self.reclassified_rasters:
            params = {
                "INPUT": self.reclassified_rasters,
                "RESOLUTION": 0,  # Use highest resolution among input files
                "SEPARATE": False,  # Combine into a single band
                "OUTPUT": reclassified_vrt_path,
            }
            processing.run("gdal:buildvirtualraster", params)
            log_message(
                f"Generated VRT for reclassified rasters: {reclassified_vrt_path}"
            )
