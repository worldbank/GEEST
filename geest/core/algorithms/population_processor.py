import os
import traceback
import shutil
from typing import Optional
import subprocess
import platform

from qgis.core import (
    QgsApplication,
    QgsTask,
    QgsProcessingContext,
    QgsFeedback,
    QgsRasterLayer,
    QgsRasterDataProvider,
    QgsVectorLayer,
    QgsFeature,
)
import processing
from geest.utilities import log_message, resources_path
from geest.core.algorithms import AreaIterator
from .utilities import geometry_to_memory_layer


class PopulationRasterProcessingTask(QgsTask):
    """
    A QgsTask subclass for processing population raster layers.

    It iterates over bounding boxes and study areas, clips the population raster
    data to match the study area masks, and reclassifies the clipped rasters into
    three classes based on population values.

    Args:
        population_raster_path (str): Path to the population raster layer.
        study_area_gpkg_path (str): Path to the GeoPackage containing study area masks.
        output_dir (str): Directory to save the output rasters.
        cell_size_m (float): Cell size for the output rasters.
        context (Optional[QgsProcessingContext]): QGIS processing context.
        feedback (Optional[QgsFeedback]): QGIS feedback object.
        force_clear (bool): Flag to force clearing of all outputs before processing.
    """

    def __init__(
        self,
        population_raster_path: str,
        study_area_gpkg_path: str,
        working_directory: str,
        cell_size_m: float,
        context: Optional[QgsProcessingContext] = None,
        feedback: Optional[QgsFeedback] = None,
        force_clear: bool = False,
    ):
        super().__init__("Population Processor", QgsTask.CanCancel)
        self.population_raster_path = population_raster_path
        self.study_area_gpkg_path = study_area_gpkg_path
        self.output_dir = os.path.join(working_directory, "population")
        self.force_clear = force_clear
        if self.force_clear and os.path.exists(self.output_dir):
            for file in os.listdir(self.output_dir):
                os.remove(os.path.join(self.output_dir, file))
        self.cell_size_m = cell_size_m
        os.makedirs(self.output_dir, exist_ok=True)

        layer: QgsVectorLayer = QgsVectorLayer(
            f"{self.study_area_gpkg_path}|layername=study_area_clip_polygons",
            "study_area_clip_polygons",
            "ogr",
        )
        self.target_crs = layer.crs()
        del layer
        self.context = context
        self.feedback = feedback
        self.global_min = float("inf")
        self.global_max = float("-inf")
        self.clipped_rasters = []
        self.reclassified_rasters = []
        self.resampled_rasters = []
        log_message(f"---------------------------------------------")
        log_message(f"Population raster processing task initialized")
        log_message(f"---------------------------------------------")
        log_message(f"Population raster path: {self.population_raster_path}")
        log_message(f"Study area GeoPackage path: {self.study_area_gpkg_path}")
        log_message(f"Output directory: {self.output_dir}")
        log_message(f"Cell size: {self.cell_size_m}")
        log_message(f"CRS: {self.target_crs.authid() if self.target_crs else 'None'}")
        log_message(f"Force clear: {self.force_clear}")
        log_message(f"---------------------------------------------")

    def run(self) -> bool:
        """
        Executes the task to process population rasters.
        """
        try:
            self.clip_population_rasters()
            self.resample_population_rasters()
            self.reclassify_resampled_rasters()
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

    def clip_population_rasters(self) -> None:
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
            clip_layer = geometry_to_memory_layer(clip_area, self.target_crs, "clip")
            layer_name = f"{index}.tif"
            phase1_output = os.path.join(
                self.output_dir, f"clipped_phase1_{layer_name}"
            )
            log_message(f"Processing mask {phase1_output}")

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
                "OUTPUT": phase1_output,
            }

            if not self.force_clear and os.path.exists(phase1_output):
                log_message(f"Reusing existing clip phase 1 raster: {phase1_output}")
            else:
                result = processing.run("gdal:cliprasterbymasklayer", params)
                if not result["OUTPUT"]:
                    log_message(
                        f"Failed to do phase1 clip raster for mask: {layer_name}"
                    )
                    continue

            del clip_layer

            clipped_layer = QgsRasterLayer(
                phase1_output, f"Phase1 Clipped {layer_name}"
            )
            if not clipped_layer.isValid():
                log_message(f"Invalid clipped raster layer for phase1: {layer_name}")
                continue
            del clipped_layer

            log_message("Expanding clip layer to area bbox now ....")
            # Now we need to expand the raster to the area_bbox so that it alighns
            # with the clipped products produced by workflows
            phase2_output = os.path.join(
                self.output_dir, f"clipped_phase2_{layer_name}"
            )

            if not self.force_clear and os.path.exists(phase2_output):
                log_message(f"Reusing existing phase2 clipped raster: {phase2_output}")
                self.clipped_rasters.append(phase2_output)
                continue
            clip_layer = geometry_to_memory_layer(current_bbox, self.target_crs, "clip")
            bbox = current_bbox.boundingBox()
            params = {
                "INPUT": phase1_output,
                "MASK": clip_layer,
                "SOURCE_CRS": None,
                "TARGET_CRS": self.target_crs,
                "TARGET_EXTENT": f"{bbox.xMinimum()},{bbox.xMaximum()},{bbox.yMinimum()},{bbox.yMaximum()} [{self.target_crs.authid()}]",
                "NODATA": None,
                "ALPHA_BAND": False,
                "CROP_TO_CUTLINE": False,
                "KEEP_RESOLUTION": False,
                "SET_RESOLUTION": True,
                "X_RESOLUTION": self.cell_size_m,
                "Y_RESOLUTION": self.cell_size_m,
                "MULTITHREADING": False,
                "OPTIONS": "",
                "DATA_TYPE": 5,  # Float32
                "EXTRA": "",
                "OUTPUT": phase2_output,
            }

            result = processing.run("gdal:cliprasterbymasklayer", params)
            del clip_layer

            if not result["OUTPUT"]:
                log_message(f"Failed to do phase2 clip raster for mask: {layer_name}")
                continue

            clipped_layer = QgsRasterLayer(
                phase2_output, f"Phase2 Clipped {layer_name}"
            )
            if not clipped_layer.isValid():
                log_message(f"Invalid clipped raster layer for phase2: {layer_name}")
                continue
            del clipped_layer

            self.clipped_rasters.append(phase2_output)

            log_message(f"Processed mask {layer_name}")

    def find_gdalwarp(self) -> str:
        """
        Finds the gdalwarp executable using 'which' command on Unix-based systems
        and QGIS installation path on Windows.
        """
        if platform.system() == "Windows":
            gdal_path = os.path.join(QgsApplication.prefixPath(), "bin", "gdalwarp.exe")
            if os.path.exists(gdal_path):
                return gdal_path
            else:
                raise FileNotFoundError(
                    "gdalwarp.exe not found in QGIS installation path."
                )
        else:
            result = subprocess.run(
                ["which", "gdalwarp"], capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            else:
                raise FileNotFoundError("gdalwarp not found in system path.")

    def resample_population_rasters(self) -> None:
        """
        Resamples the reclassified rasters to the target CRS and resolution.

        Uses the sum method to aggregate values when resampling via gdalwarp.

        From gdalwarp docs: sum: compute the weighted sum of all non-NODATA contributing pixels (since GDAL 3.1)

        Note: gdal:warpreproject does not expose the -r sum option, so this method
        uses a direct gdalwarp shell call instead.
        """
        try:
            gdal_path = self.find_gdalwarp()
        except FileNotFoundError as e:
            log_message(f"Error: {str(e)}")
            return

        area_iterator = AreaIterator(self.study_area_gpkg_path)

        for index, (current_area, clip_area, current_bbox, progress) in enumerate(
            area_iterator
        ):
            if self.feedback and self.feedback.isCanceled():
                return

            layer_name = f"{index}.tif"
            input_path = os.path.join(self.output_dir, f"clipped_phase2_{layer_name}")
            output_path = os.path.join(self.output_dir, f"resampled_{layer_name}")

            log_message(f"Resampling {output_path} from {input_path}")

            if not self.force_clear and os.path.exists(output_path):
                log_message(f"Reusing existing resampled raster: {output_path}")
                self.resampled_rasters.append(output_path)
                continue

            bbox = current_bbox.boundingBox()

            # Define gdalwarp command arguments
            gdalwarp_cmd = [
                gdal_path,
                "-t_srs",
                self.target_crs.authid(),
                "-tr",
                str(self.cell_size_m),
                str(self.cell_size_m),
                "-te",
                str(bbox.xMinimum()),
                str(bbox.yMinimum()),
                str(bbox.xMaximum()),
                str(bbox.yMaximum()),
                "-r",
                "sum",
                "-of",
                "GTiff",
                input_path,
                output_path,
            ]

            try:
                # Run the gdalwarp command
                log_message(f"Running gdalwarp with command: {' '.join(gdalwarp_cmd)}")
                subprocess.run(
                    gdalwarp_cmd,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

            except subprocess.CalledProcessError as e:
                log_message(
                    f"Failed to resample raster: {output_path}\nError: {e.stderr.decode()}"
                )
                continue

            # Load the resampled raster
            resampled_layer = QgsRasterLayer(output_path, f"Resampled {layer_name}")

            if not resampled_layer.isValid():
                log_message(f"Invalid resampled raster layer for: {layer_name}")
                continue

            self.resampled_rasters.append(output_path)

            # Calculate min and max values for the resampled raster
            provider: QgsRasterDataProvider = resampled_layer.dataProvider()
            stats = provider.bandStatistics(1)
            self.global_min = min(self.global_min, stats.minimumValue)
            self.global_max = max(self.global_max, stats.maximumValue)

            log_message(
                f"Processed resample {layer_name}: Min={stats.minimumValue}, Max={stats.maximumValue}"
            )
            log_message(f"Resampled raster: {output_path}")

    def reclassify_resampled_rasters(self) -> None:
        """
        Reclassifies the resampled rasters into three classes based on population values.
        """
        area_iterator = AreaIterator(self.study_area_gpkg_path)
        range_third = (self.global_max - self.global_min) / 3

        for index, (current_area, clip_area, current_bbox, progress) in enumerate(
            area_iterator
        ):
            if self.feedback and self.feedback.isCanceled():
                return

            layer_name = f"{index}.tif"
            input_path = os.path.join(self.output_dir, f"resampled_{layer_name}")
            output_path = os.path.join(self.output_dir, f"reclassified_{layer_name}")

            log_message(f"Reclassifying {output_path} from {input_path}")

            if not self.force_clear and os.path.exists(output_path):
                log_message(f"Reusing existing reclassified raster: {output_path}")
                self.reclassified_rasters.append(output_path)
                continue
            params = {
                "INPUT_RASTER": input_path,
                "RASTER_BAND": 1,
                "TABLE": [  # ['0','52','1','52','95','2','95','140','3'],
                    0,
                    self.global_min + range_third,
                    1,
                    self.global_min + range_third,
                    self.global_min + 2 * range_third,
                    2,
                    self.global_min + 2 * range_third,
                    self.global_max,
                    3,
                ],
                "RANGE_BOUNDARIES": 0,
                "NODATA_FOR_MISSING": False,
                "NO_DATA": 255,
                "DATA_TYPE": 5,  # Float32
                # "DATA_TYPE": 1,  # Byte
                "OUTPUT": output_path,
            }

            log_message(f"Reclassifying raster: {input_path}")
            log_message(f"Reclassification table:\n {params['TABLE']}\n")
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

        resampled_vrt_path = os.path.join(self.output_dir, "resampled_population.vrt")

        reclassified_vrt_path = os.path.join(
            self.output_dir, "reclassified_population.vrt"
        )
        reclassified_qml_path = os.path.join(
            self.output_dir, "reclassified_population.qml"
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

        # Generate VRT for resampled rasters
        if self.resampled_rasters:
            params = {
                "INPUT": self.resampled_rasters,
                "RESOLUTION": 0,  # Use highest resolution among input files
                "SEPARATE": False,  # Combine into a single band
                "OUTPUT": resampled_vrt_path,
            }
            processing.run("gdal:buildvirtualraster", params)
            log_message(f"Generated VRT for resampled rasters: {resampled_vrt_path}")

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
            source_qml = resources_path("resources", "qml", f"population_3_classes.qml")

            log_message(f"Copying QML from {source_qml} to {reclassified_qml_path}")
            shutil.copyfile(source_qml, reclassified_qml_path)
