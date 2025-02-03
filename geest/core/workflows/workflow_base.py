import datetime
import os
import shutil
import traceback
from abc import ABC, abstractmethod
from qgis.core import (
    QgsFeedback,
    QgsVectorLayer,
    Qgis,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsGeometry,
    QgsProcessingFeedback,
    QgsProcessingException,
    QgsVectorLayer,
    Qgis,
)
import processing
from qgis.PyQt.QtCore import QSettings, pyqtSignal, QObject
from geest.core import JsonTreeItem, setting
from geest.utilities import resources_path
from geest.core.algorithms import (
    AreaIterator,
    subset_vector_layer,
    geometry_to_memory_layer,
    check_and_reproject_layer,
    combine_rasters_to_vrt,
)
from geest.core.constants import GDAL_OUTPUT_DATA_TYPE
from geest.utilities import log_message, log_layer_count


class WorkflowBase(QObject):
    """
    Abstract base class for all workflows.
    Every workflow must accept an attributes dictionary and a QgsFeedback object.
    """

    # Signal for progress changes - will be propagated to the task that owns this workflow
    progressChanged = pyqtSignal(int)

    def __init__(
        self,
        item: JsonTreeItem,
        cell_size_m: 100.0,
        feedback: QgsFeedback,
        context: QgsProcessingContext,
        working_directory: str = None,
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param item: JsonTreeItem object representing the task.
        :param cell_size_m: The cell size in meters for the analysis.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        :working_directory: Folder containing study_area.gpkg and where the outputs will be placed. If not set will be taken from QSettings.
        """
        super().__init__()
        log_layer_count()  # For performance tuning, write the number of open layers to a log file
        # we will log the layer count again at then end of the workflow
        self.item = item  # ⭐️ This is a reference - whatever you change in this item will directly update the tree
        self.cell_size_m = cell_size_m
        self.feedback = feedback
        self.context = context  # QgsProcessingContext
        self.workflow_name = None  # This is set in the concrete class
        # This is set in the setup panel
        self.settings = QSettings()
        # This is the top level folder for work files
        if working_directory:
            log_message(f"Working directory set to {working_directory}")
            self.working_directory = working_directory
        else:
            log_message(
                "Working directory not set. Using last working directory from settings."
            )
            self.working_directory = self.settings.value("last_working_directory", "")
        if not self.working_directory:
            raise ValueError("Working directory not set.")
        # This is the lower level directory for this workflow's outputs
        self.workflow_directory = self._create_workflow_directory()
        self.gpkg_path: str = os.path.join(
            self.working_directory, "study_area", "study_area.gpkg"
        )
        if not os.path.exists(self.gpkg_path):
            raise ValueError(f"Study area geopackage not found at {self.gpkg_path}.")
        self.bboxes_layer = QgsVectorLayer(
            f"{self.gpkg_path}|layername=study_area_bboxes", "study_area_bboxes", "ogr"
        )
        self.areas_layer = QgsVectorLayer(
            f"{self.gpkg_path}|layername=study_area_polygons",
            "study_area_polygons",
            "ogr",
        )
        self.clip_areas_layer = QgsVectorLayer(
            f"{self.gpkg_path}|layername=study_area_clip_polygons",
            "study_area_clip_polygons",
            "ogr",
        )
        self.grid_layer = QgsVectorLayer(
            f"{self.gpkg_path}|layername=study_area_grid", "study_area_grid", "ogr"
        )
        self.features_layer = None  # set in concrete class if needed
        self.raster_layer = None  # set in concrete class if needed
        self.target_crs = self.bboxes_layer.crs()

        self.result_file_key = "result_file"
        self.result_key = "result"

        # Will be populated by the workflow
        self.attributes = self.item.attributes()
        self.layer_id = self.attributes.get("id", "").lower().replace(" ", "_")
        self.aggregation = False
        self.analysis_mode = self.item.attribute("analysis_mode", "")
        self.progressChanged.emit(0)
        self.output_filename = self.attributes.get("output_filename", "")

    #
    # Every concrete subclass needs to implement these three methods
    #

    @abstractmethod
    def _process_features_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
    ) -> str:
        """
        Executes the actual workflow logic for a single area
        Must be implemented by subclasses.

        :current_area: Current polygon from our study area.
        :clip_area: Current area but expanded to coincide with grid cell boundaries.
        :current_bbox: Bounding box of the above area.
        :area_features: A vector layer of features to analyse that includes only features in the study area.
        :index: Iteration / number of area being processed.

        :return: A raster layer file path if processing completes successfully, False if canceled or failed.
        """
        pass

    @abstractmethod
    def _process_raster_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_raster: str,
        index: int,
    ):
        """
        Executes the actual workflow logic for a single area using a raster.

        :current_area: Current polygon from our study area.
        :clip_area: Polygon to clip the raster to which is aligned to cell edges.
        :current_bbox: Bounding box of the above area.
        :area_raster: A raster layer of features to analyse that includes only bbox pixels in the study area.
        :index: Index of the current area.

        :return: Path to the reclassified raster.
        """
        pass

    @abstractmethod
    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
    ):
        """
        Executes the actual workflow logic for a single area using an aggregate.

        :current_area: Current polygon from our study area.
        :current_bbox: Bounding box of the above area.
        :index: Index of the current area.

        :return: Path to the reclassified raster.
        """
        pass

    # ------------------- END OF ABSTRACT METHODS -------------------

    def execute(self) -> bool:
        """
        Main function to iterate over areas from the GeoPackage and perform the analysis for each area.

        This function processes areas (defined by polygons and bounding boxes) from the GeoPackage using
        the provided input layers (features, grid). It applies the steps of selecting intersecting
        features, then passes them to process area for further processing.

        Raises:
            QgsProcessingException: If any processing step fails during the execution.

        Returns:
            True if the workflow completes successfully, False if canceled or failed.
        """

        # Do this here rather than in the ctor in case the result key is changed
        # in the concrete class
        self.attributes[self.result_key] = "Not Run"

        log_message(f"Executing {self.workflow_name}")
        log_message("----------------------------------")
        verbose_mode = int(setting(key="verbose_mode", default=0))
        if verbose_mode:
            log_message(self.item.attributesAsMarkdown())
            log_message("----------------------------------")

        self.attributes["execution_start_time"] = datetime.datetime.now().isoformat()

        log_message("Processing Started")

        feedback = QgsProcessingFeedback()
        output_rasters = []

        try:
            if self.features_layer and type(self.features_layer) == QgsVectorLayer:
                log_message(
                    f"Features layer for {self.workflow_name} is {self.features_layer.source()}"
                )
                self.features_layer = check_and_reproject_layer(
                    self.features_layer, self.target_crs
                )
        except Exception as e:
            error_file = os.path.join(self.workflow_directory, "error.txt")
            if os.path.exists(error_file):
                os.remove(error_file)
            # Write the traceback to error.txt in the workflow_directory
            error_path = os.path.join(self.workflow_directory, "error.txt")
            with open(error_path, "w") as f:
                f.write(f"Failed to process {self.workflow_name}: {e}\n")
                f.write(traceback.format_exc())

            log_message(
                f"Failed to reproject features layer for {self.workflow_name}: {e}",
                tag="Geest",
                level=Qgis.Critical,
            )
            log_message(
                traceback.format_exc(),
                tag="Geest",
                level=Qgis.Critical,
            )
            self.attributes[self.result_key] = f"{self.workflow_name} Workflow Error"
            self.attributes[self.result_file_key] = ""
            self.attributes["error_file"] = error_path
            self.attributes["error"] = (
                f"Failed to reproject features layer for {self.workflow_name}: {e}"
            )
            return False

        area_iterator = AreaIterator(self.gpkg_path)
        log_layer_count()  # For performance tuning, write the number of open layers to a log file
        try:
            for index, (current_area, clip_area, current_bbox, progress) in enumerate(
                area_iterator
            ):
                feedback.pushInfo(
                    f"{self.workflow_name} Processing area {index} with progress {progress:.2f}%"
                )
                if self.feedback.isCanceled():
                    log_message(
                        f"{self.class_name} Processing was canceled by the user.",
                        tag="Geest",
                        level=Qgis.Warning,
                    )
                raster_output = None
                # Step 1: Select features that intersect with the current area
                if self.features_layer:  # we are processing a vector input
                    area_features = self._subset_vector_layer(
                        current_area,
                        output_prefix=f"{self.layer_id}_area_features_{index}",
                    )
                    # if area_features.featureCount() == 0:
                    #    continue

                    # Step 2: Process the area features - work happens in concrete class
                    raster_output = self._process_features_for_area(
                        current_area=current_area,
                        clip_area=clip_area,
                        current_bbox=current_bbox,
                        area_features=area_features,
                        index=index,
                    )
                elif (
                    self.aggregation == False
                ):  # assumes we are processing a raster input
                    area_raster = self._subset_raster_layer(
                        bbox=current_bbox, index=index
                    )
                    raster_output = self._process_raster_for_area(
                        current_area=current_area,
                        clip_area=clip_area,
                        current_bbox=current_bbox,
                        area_raster=area_raster,
                        index=index,
                    )
                elif self.aggregation == True:  # we are processing an aggregate
                    raster_output = self._process_aggregate_for_area(
                        current_area=current_area,
                        clip_area=clip_area,
                        current_bbox=current_bbox,
                        index=index,
                    )

                # clip the area by its matching mask layer in study_area geopackage
                masked_layer = self._mask_raster(
                    raster_path=raster_output,
                    area_geometry=clip_area,
                    index=index,
                )
                output_rasters.append(masked_layer)
                self.progressChanged.emit(int(progress))
            # Combine all area rasters into a VRT
            vrt_filepath = self._combine_rasters_to_vrt(output_rasters)
            self.attributes[self.result_file_key] = vrt_filepath
            self.attributes[self.result_key] = (
                f"{self.workflow_name} Workflow Completed"
            )

            log_message(
                f"{self.workflow_name} Completed. Output VRT: {vrt_filepath}",
                tag="Geest",
                level=Qgis.Info,
            )
            self.attributes["execution_end_time"] = datetime.datetime.now().isoformat()
            self.attributes["error_file"] = None
            log_layer_count()  # For performance tuning, write the number of open layers to a log file
            return True

        except Exception as e:
            # remove error.txt if it exists
            error_file = os.path.join(self.workflow_directory, "error.txt")
            if os.path.exists(error_file):
                os.remove(error_file)

            log_message(
                f"Failed to process {self.workflow_name}: {e}",
                tag="Geest",
                level=Qgis.Critical,
            )
            log_message(
                traceback.format_exc(),
                tag="Geest",
                level=Qgis.Critical,
            )
            self.attributes[self.result_key] = f"{self.workflow_name} Workflow Error"
            self.attributes[self.result_file_key] = ""

            # Write the traceback to error.txt in the workflow_directory
            error_path = os.path.join(self.workflow_directory, "error.txt")
            with open(error_path, "w") as f:
                f.write(f"Failed to process {self.workflow_name}: {e}\n")
                f.write(traceback.format_exc())
            self.attributes["error_file"] = error_path
            self.attributes["error"] = f"Failed to process {self.workflow_name}: {e}"
            log_layer_count()  # For performance tuning, write the number of open layers to a log file
            return False

    def _create_workflow_directory(self) -> str:
        """
        Creates the directory for this workflow if it doesn't already exist.
        It will be in the scheme of working_dir/dimension/factor/indicator

        :return: The path to the workflow directory
        """
        paths = self.item.getPaths()
        directory = os.path.join(self.working_directory, *paths)
        # Create the directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)

        return directory

    def _subset_vector_layer(
        self, area_geom: QgsGeometry, output_prefix: str
    ) -> QgsVectorLayer:
        """
        Select features from the features layer that intersect with the given area geometry.

        Args:
            area_geom (QgsGeometry): The current area geometry for which intersections are evaluated.
            output_prefix (str): A name for the output temporary layer to store selected features.

        Returns:
            QgsVectorLayer: A new temporary layer containing features that intersect with the given area geometry.
        """
        if type(self.features_layer) != QgsVectorLayer:
            return None
        log_message(
            f"{self.workflow_name} Select Features Started",
            tag="Geest",
            level=Qgis.Info,
        )
        layer = subset_vector_layer(
            self.workflow_directory, self.features_layer, area_geom, output_prefix
        )
        return layer

    def _subset_raster_layer(self, bbox: QgsGeometry, index: int):
        """
        Reproject and clip the raster to the bounding box of the current area.

        :param bbox: The bounding box of the current area.
        :param index: The index of the current area.

        :return: The path to the reprojected and clipped raster.
        """
        # Convert the bbox to QgsRectangle
        bbox = bbox.boundingBox()

        reprojected_raster_path = os.path.join(
            self.workflow_directory,
            f"{self.layer_id}_clipped_and_reprojected_{index}.tif",
        )

        params = {
            "INPUT": self.raster_layer,
            "TARGET_CRS": self.target_crs,
            "RESAMPLING": 0,
            "TARGET_RESOLUTION": self.cell_size_m,
            "NODATA": -9999,
            "OUTPUT": "TEMPORARY_OUTPUT",
            "TARGET_EXTENT": f"{bbox.xMinimum()},{bbox.xMaximum()},{bbox.yMinimum()},{bbox.yMaximum()} [{self.target_crs.authid()}]",
        }

        aoi = processing.run(
            "gdal:warpreproject", params, feedback=QgsProcessingFeedback()
        )["OUTPUT"]

        params = {
            "INPUT": aoi,
            "BAND": 1,
            "FILL_VALUE": 0,
            "OUTPUT": reprojected_raster_path,
        }
        processing.run("native:fillnodata", params)
        return reprojected_raster_path

    def _rasterize(
        self,
        input_layer: QgsVectorLayer,
        bbox: QgsGeometry,
        index: int,
        value_field: str = "value",
        default_value: int = 0,
    ) -> str:
        """

        ⭐️🚩⭐️ Warning this is not DRY - almost same function exists in study_area.py

        Rasterize the grid layer based on the 🔴'value'🔴 attribute field.

        Nodata will be set to 255

        On-land pixels will be set to 0 or whatever is specified in the default_value parameter.

        Args:
            input_layer (QgsVectorLayer): The layer to rasterize.
            bbox (QgsGeometry): The bounding box for the raster extents.
            index (int): The current index used for naming the output raster.
            value_field (str): The field to use for rasterization.
            default_value (int): The default value to use for the raster.

        Returns:
            str: The file path to the rasterized output.
        """
        if not input_layer or not input_layer.isValid():
            return False
        log_message("--- Rasterizing geometry")
        log_message(f"--- bbox {bbox}")
        log_message(f"--- index {index}")

        output_path = os.path.join(
            self.workflow_directory,
            f"{self.layer_id}_{index}.tif",
        )
        if not input_layer.isValid():
            log_message(f"Layer failed to load! {input_layer}")
            return
        else:
            log_message(f"Rasterizing {input_layer}")

        # Ensure resolution parameters are properly formatted as float values
        x_res = self.cell_size_m  # pixel size in X direction
        y_res = self.cell_size_m  # pixel size in Y direction
        bbox = bbox.boundingBox()
        # Define rasterization parameters for the temporary layer
        params = {
            "INPUT": input_layer,
            "FIELD": f"{value_field}",
            "BURN": 0,
            "USE_Z": False,
            "UNITS": 1,
            "WIDTH": x_res,
            "HEIGHT": y_res,
            "EXTENT": f"{bbox.xMinimum()},{bbox.xMaximum()},{bbox.yMinimum()},{bbox.yMaximum()} [{self.target_crs.authid()}]",
            "NODATA": 255,
            "OPTIONS": "",
            "DATA_TYPE": GDAL_OUTPUT_DATA_TYPE,
            "INIT": default_value,  # will set all cells to this value if not otherwise set
            "INVERT": False,
            "EXTRA": f"-a_srs {self.target_crs.authid()} -at",  # Assign all touched pixels
            "OUTPUT": output_path,
        }

        #'OUTPUT':'TEMPORARY_OUTPUT'})

        processing.run("gdal:rasterize", params)
        log_message(f"Rasterize Parameter: {params}")
        log_message(f"Rasterize complete for: {output_path}")
        log_message(f"Created raster: {output_path}")
        return output_path

    def _mask_raster(
        self, raster_path: str, area_geometry: QgsGeometry, index: int
    ) -> str:
        """
        Multiply the raster by the area geometry to mask the raster to the area.

        Args:
            raster_path (str): The path to the raster file.
            area_geometry (QgsGeometry): The geometry to use as a mask.
            index (int): The index of the current area.

        Returns:
            str: The path to the masked raster.
        """
        if not raster_path:
            return False
        output_name = f"{self.layer_id}_masked_{index}.tif"
        output_path = os.path.join(self.workflow_directory, output_name)
        log_message(
            f"Masking raster {raster_path} for area {index} to {output_path}",
            tag="Geest",
            level=Qgis.Info,
        )
        # verify the raster path exists
        if not os.path.exists(raster_path):
            log_message(
                f"Raster file not found at {raster_path}",
                tag="Geest",
                level=Qgis.Warning,
            )
            raise QgsProcessingException(f"Raster file not found at {raster_path}")
        # Convert the geometry to a memory layer in the self.target_crs
        log_message(f"Creating mask layer for area from polygon {index}")
        mask_layer = geometry_to_memory_layer(
            area_geometry, self.target_crs, f"mask_layer_{index}"
        )
        log_message(f"Mask layer created: {mask_layer}")
        # Clip the raster by the mask layer
        params = {
            "INPUT": f"{raster_path}",
            "MASK": mask_layer,
            "OUTPUT": f"{output_path}",
            "SOURCE_CRS": None,
            "TARGET_CRS": None,
            "TARGET_EXTENT": None,
            "NODATA": 255,
            "ALPHA_BAND": False,
            "CROP_TO_CUTLINE": True,
            "KEEP_RESOLUTION": False,
            "SET_RESOLUTION": False,
            "X_RESOLUTION": None,
            "Y_RESOLUTION": None,
            "MULTITHREADING": False,
            "OPTIONS": "",
            "DATA_TYPE": GDAL_OUTPUT_DATA_TYPE,
            "EXTRA": "",
        }
        processing.run("gdal:cliprasterbymasklayer", params)
        log_message(f"Masked raster created: {output_path}")
        return output_path

    def _combine_rasters_to_vrt(self, rasters: list) -> None:
        """
        Combine all the rasters into a single VRT file.

        Args:
            rasters: The rasters to combine into a VRT.

        Returns:
            vrtpath (str): The file path to the VRT file.
        """

        vrt_filepath = os.path.join(
            self.workflow_directory,
            f"{self.output_filename}_combined.vrt",
        )
        role = self.item.role
        source_qml = resources_path("resources", "qml", f"{role}.qml")
        vrt_filepath = combine_rasters_to_vrt(
            rasters, self.target_crs, vrt_filepath, source_qml
        )
        return vrt_filepath
