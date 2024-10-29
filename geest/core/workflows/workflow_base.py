import datetime
import os
import shutil
import traceback
from abc import ABC, abstractmethod
from qgis.core import (
    QgsFeedback,
    QgsVectorLayer,
    QgsMessageLog,
    Qgis,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsFeature,
    QgsGeometry,
    QgsProcessingFeedback,
    QgsProcessingException,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsMessageLog,
    QgsWkbTypes,
    Qgis,
)
import processing
from qgis.PyQt.QtCore import QSettings, pyqtSignal
from geest.core import JsonTreeItem, setting
from geest.utilities import resources_path
from geest.core.algorithms import AreaIterator


class WorkflowBase(ABC):
    """
    Abstract base class for all workflows.
    Every workflow must accept an attributes dictionary and a QgsFeedback object.
    """

    # Signal for progress changes - will be propagated to the task that owns this workflow
    progressChanged = pyqtSignal(int)

    def __init__(
        self, item: JsonTreeItem, feedback: QgsFeedback, context: QgsProcessingContext
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param attributes: Item containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        """
        self.item = item  # ⭐️ This is a reference - whatever you change in this item will directly update the tree
        self.feedback = feedback
        self.context = context  # QgsProcessingContext
        self.workflow_name = None  # This is set in the concrete class
        # This is set in the setup panel
        self.settings = QSettings()
        # This is the top level folder for work files
        self.working_directory = self.settings.value("last_working_directory", "")
        if not self.working_directory:
            raise ValueError("Working directory not set.")
        # This is the lower level directory for this workflow
        self.workflow_directory = self._create_workflow_directory()
        self.pixel_size = 100.0  # TODO get from data model
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
        self.grid_layer = QgsVectorLayer(
            f"{self.gpkg_path}|layername=study_area_grid", "study_area_grid", "ogr"
        )
        self.features_layer = None  # set in concrete class if needed
        self.raster_layer = None  # set in concrete class if needed
        self.target_crs = self.bboxes_layer.crs()
        # Will be populated by the workflow
        self.attributes = self.item.data(3)
        self.layer_id = self.attributes.get("id", "").lower().replace(" ", "_")
        self.attributes["result"] = "Not Run"
        self.workflow_is_legacy = True
        self.aggregation = False

    #
    # Every concrete subclass needs to implement these three methods
    #

    @abstractmethod
    def do_execute(self) -> bool:
        """
        Executes the actual workflow logic.
        Must be implemented by subclasses.

        :return: True if the workflow completes successfully, False if canceled or failed.
        """
        pass

    @abstractmethod
    def _process_features_for_area(
        self,
        current_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
    ) -> str:
        """
        Executes the actual workflow logic for a single area
        Must be implemented by subclasses.

        :current_area: Current polygon from our study area.
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
        current_bbox: QgsGeometry,
        area_raster: str,
        index: int,
    ):
        """
        Executes the actual workflow logic for a single area using a raster.

        :current_area: Current polygon from our study area.
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

    # ------------------- END OF ABSCRACT METHODS -------------------

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

        QgsMessageLog.logMessage(
            f"Executing {self.workflow_name}", tag="Geest", level=Qgis.Info
        )
        QgsMessageLog.logMessage(
            "----------------------------------", tag="Geest", level=Qgis.Info
        )
        verbose_mode = int(setting(key="verbose_mode", default=0))
        if verbose_mode:
            for item in self.attributes.items():
                QgsMessageLog.logMessage(
                    f"{item[0]}: {item[1]}", tag="Geest", level=Qgis.Info
                )
            QgsMessageLog.logMessage(
                "----------------------------------", tag="Geest", level=Qgis.Info
            )

        self.attributes["execution_start_time"] = datetime.datetime.now().isoformat()

        QgsMessageLog.logMessage("Processing Started", tag="Geest", level=Qgis.Info)

        #
        # TODO: Remove this once all workflows are updated to the new structure
        #

        if self.workflow_is_legacy:
            return self.do_execute()

        #
        # END TODO
        #

        feedback = QgsProcessingFeedback()
        output_rasters = []

        if self.features_layer and type(self.features_layer) == QgsVectorLayer:
            self.features_layer = self._check_and_reproject_layer()

        area_iterator = AreaIterator(self.gpkg_path)
        try:
            for index, (current_area, current_bbox, progress) in enumerate(
                area_iterator
            ):
                feedback.pushInfo(
                    f"{self.workflow_name} Processing area {index} with progress {progress:.2f}%"
                )
                if self.feedback.isCanceled():
                    QgsMessageLog.logMessage(
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
                        current_bbox=current_bbox,
                        area_raster=area_raster,
                        index=index,
                    )
                elif self.aggregation == True:  # we are processing an aggregate
                    raster_output = self._process_aggregate_for_area(
                        current_area=current_area,
                        current_bbox=current_bbox,
                        index=index,
                    )

                # Multiply the area by its matching mask layer in study_area folder
                masked_layer = self._mask_raster(
                    raster_path=raster_output,
                    area_geometry=current_area,
                    index=index,
                )
                output_rasters.append(masked_layer)
            # Combine all area rasters into a VRT
            vrt_filepath = self._combine_rasters_to_vrt(output_rasters)
            self.attributes["result_file"] = vrt_filepath
            self.attributes["result"] = f"{self.workflow_name} Workflow Completed"

            QgsMessageLog.logMessage(
                f"{self.workflow_name} Completed. Output VRT: {vrt_filepath}",
                tag="Geest",
                level=Qgis.Info,
            )
            self.attributes["execution_end_time"] = datetime.datetime.now().isoformat()
            self.attributes["error_file"] = None
            return True

        except Exception as e:
            # remove error.txt if it exists
            error_file = os.path.join(self.workflow_directory, "error.txt")
            if os.path.exists(error_file):
                os.remove(error_file)

            QgsMessageLog.logMessage(
                f"Failed to process {self.workflow_name}: {e}",
                tag="Geest",
                level=Qgis.Critical,
            )
            QgsMessageLog.logMessage(
                traceback.format_exc(),
                tag="Geest",
                level=Qgis.Critical,
            )
            self.attributes["result"] = f"{self.workflow_name} Workflow Error"
            self.attributes["result_file"] = ""

            # Write the traceback to error.txt in the workflow_directory
            error_path = os.path.join(self.workflow_directory, "error.txt")
            with open(error_path, "w") as f:
                f.write(f"Failed to process {self.workflow_name}: {e}\n")
                f.write(traceback.format_exc())
            self.attributes["error_file"] = error_path
            return False

    def _create_workflow_directory(self, *subdirs: str) -> str:
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
        QgsMessageLog.logMessage(
            f"{self.workflow_name} Select Features Started",
            tag="Geest",
            level=Qgis.Info,
        )
        output_path = os.path.join(self.workflow_directory, f"{output_prefix}.shp")

        # Get the WKB type (geometry type) of the input layer (e.g., Point, LineString, Polygon)
        geometry_type = self.features_layer.wkbType()

        # Determine geometry type name based on input layer's geometry
        if QgsWkbTypes.geometryType(geometry_type) == QgsWkbTypes.PointGeometry:
            geometry_name = "Point"
        elif QgsWkbTypes.geometryType(geometry_type) == QgsWkbTypes.LineGeometry:
            geometry_name = "LineString"
        elif QgsWkbTypes.geometryType(geometry_type) == QgsWkbTypes.PolygonGeometry:
            geometry_name = "Polygon"
        else:
            raise QgsProcessingException(f"Unsupported geometry type: {geometry_type}")

        params = {
            "INPUT": self.features_layer,
            "PREDICATE": [0],  # Intersects predicate
            "GEOMETRY": area_geom,
            "EXTENT": area_geom.boundingBox(),
            "OUTPUT": output_path,
        }
        result = processing.run("native:extractbyextent", params)
        return QgsVectorLayer(result["OUTPUT"], output_prefix, "ogr")

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
            "TARGET_RESOLUTION": self.pixel_size,
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

    def _check_and_reproject_layer(self):
        """
        Checks if the features layer has the expected CRS. If not, it reprojects the layer.

        Returns:
            QgsVectorLayer: The input layer, either reprojected or unchanged.

        Note: Also updates self.features_layer to point to the reprojected layer.
        """
        if self.features_layer.crs() != self.target_crs:
            QgsMessageLog.logMessage(
                f"Reprojecting layer from {self.features_layer.crs().authid()} to {self.target_crs.authid()}",
                "Geest",
                level=Qgis.Info,
            )
            reproject_result = processing.run(
                "native:reprojectlayer",
                {
                    "INPUT": self.features_layer,
                    "TARGET_CRS": self.target_crs,
                    "OUTPUT": "memory:",  # Reproject in memory
                },
                feedback=QgsProcessingFeedback(),
            )
            reprojected_layer = reproject_result["OUTPUT"]
            if not reprojected_layer.isValid():
                raise QgsProcessingException("Reprojected layer is invalid.")
            self.features_layer = reprojected_layer
        # If CRS matches, return the original layer
        return self.features_layer

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
        QgsMessageLog.logMessage("--- Rasterizing grid", tag="Geest", level=Qgis.Info)
        QgsMessageLog.logMessage(f"--- bbox {bbox}", tag="Geest", level=Qgis.Info)
        QgsMessageLog.logMessage(f"--- index {index}", tag="Geest", level=Qgis.Info)

        output_path = os.path.join(
            self.workflow_directory,
            f"{self.layer_id}_{index}.tif",
        )
        if not input_layer.isValid():
            QgsMessageLog.logMessage(
                f"Layer failed to load! {input_layer}", "Geest", Qgis.Info
            )
            return
        else:
            QgsMessageLog.logMessage(f"Rasterizing {input_layer}", "Geest", Qgis.Info)

        # Ensure resolution parameters are properly formatted as float values
        x_res = 100.0  # 100m pixel size in X direction
        y_res = 100.0  # 100m pixel size in Y direction
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
            "DATA_TYPE": 0,  # byte
            "INIT": default_value,  # will set all cells to this value if not otherwise set
            "INVERT": False,
            "EXTRA": f"-a_srs {self.target_crs.authid()}",
            "OUTPUT": output_path,
        }

        #'OUTPUT':'TEMPORARY_OUTPUT'})

        processing.run("gdal:rasterize", params)
        QgsMessageLog.logMessage(
            f"Rasterize Parameter: {params}", tag="Geest", level=Qgis.Info
        )

        QgsMessageLog.logMessage(
            f"Rasterize complete for: {output_path}",
            tag="Geest",
            level=Qgis.Info,
        )

        QgsMessageLog.logMessage(
            f"Created raster: {output_path}", tag="Geest", level=Qgis.Info
        )
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
        QgsMessageLog.logMessage(
            f"Masking raster {raster_path} with area {index} to {output_path}",
            tag="Geest",
            level=Qgis.Info,
        )
        # verify the raster path exists
        if not os.path.exists(raster_path):
            QgsMessageLog.logMessage(
                f"Raster file not found at {raster_path}",
                tag="Geest",
                level=Qgis.Warning,
            )
            raise QgsProcessingException(f"Raster file not found at {raster_path}")
        # Convert the geometry to a memory layer in the self.tartget_crs
        mask_layer = QgsVectorLayer(f"Polygon", "mask", "memory")
        mask_layer.setCrs(self.target_crs)
        feature = QgsFeature()
        feature.setGeometry(area_geometry)
        mask_layer.dataProvider().addFeatures([feature])
        mask_layer.commitChanges()
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
            "DATA_TYPE": 0,  # byte - TODO softcode this for aggregation we want float
            "EXTRA": "",
        }
        processing.run("gdal:cliprasterbymasklayer", params)
        return output_path

    def _combine_rasters_to_vrt(self, rasters: list) -> None:
        """
        Combine all the rasters into a single VRT file.

        Args:
            rasters: The rasters to combine into a VRT.

        Returns:
            vrtpath (str): The file path to the VRT file.
        """
        if not rasters:
            QgsMessageLog.logMessage(
                "No valid raster layers found to combine into VRT.",
                tag="Geest",
                level=Qgis.Warning,
            )
            return
        vrt_filepath = os.path.join(
            self.workflow_directory,
            f"{self.layer_id}_final_combined.vrt",
        )
        qml_filepath = os.path.join(
            self.workflow_directory,
            f"{self.layer_id}_final_combined.qml",
        )
        QgsMessageLog.logMessage(
            f"Creating VRT of layers '{vrt_filepath}' layer to the map.",
            tag="Geest",
            level=Qgis.Info,
        )
        checked_rasters = []
        for raster in rasters:
            if raster and os.path.exists(raster) and QgsRasterLayer(raster).isValid():
                checked_rasters.append(raster)
            else:
                QgsMessageLog.logMessage(
                    f"Skipping invalid or non-existent raster: {raster}",
                    tag="Geest",
                    level=Qgis.Warning,
                )

        if not checked_rasters:
            QgsMessageLog.logMessage(
                "No valid raster layers found to combine into VRT.",
                tag="Geest",
                level=Qgis.Warning,
            )
            return

        # Define the VRT parameters
        params = {
            "INPUT": checked_rasters,
            "RESOLUTION": 0,  # Use highest resolution among input files
            "SEPARATE": False,  # Combine all input rasters as a single band
            "OUTPUT": vrt_filepath,
            "PROJ_DIFFERENCE": False,
            "ADD_ALPHA": False,
            "ASSIGN_CRS": self.target_crs,
            "RESAMPLING": 0,
            "SRC_NODATA": "255",
            "EXTRA": "",
        }

        # Run the gdal:buildvrt processing algorithm to create the VRT
        processing.run("gdal:buildvirtualraster", params)
        QgsMessageLog.logMessage(
            f"Created VRT: {vrt_filepath}", tag="Geest", level=Qgis.Info
        )

        # Add the VRT to the QGIS map
        vrt_layer = QgsRasterLayer(vrt_filepath, f"{self.layer_id}_final VRT")
        # Copy the appropriate QML over too
        role = self.item.role
        source_qml = resources_path("resources", "qml", f"{role}.qml")
        QgsMessageLog.logMessage(
            f"Copying QML from {source_qml} to {qml_filepath}",
            tag="Geest",
            level=Qgis.Info,
        )
        shutil.copyfile(source_qml, qml_filepath)

        if not vrt_layer.isValid():
            QgsMessageLog.logMessage(
                "VRT Layer generation failed.", tag="Geest", level=Qgis.Critical
            )
            return False

        return vrt_filepath
