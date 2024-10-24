import datetime
import os
import traceback
from abc import ABC, abstractmethod
from qgis.core import (
    QgsFeedback,
    QgsVectorLayer,
    QgsMessageLog,
    Qgis,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsFeatureRequest,
    QgsGeometry,
    QgsProcessingFeedback,
    QgsProcessingException,
    QgsVectorLayer,
    QgsMessageLog,
    QgsVectorFileWriter,
    QgsWkbTypes,
    Qgis,
)
import processing
from qgis.PyQt.QtCore import QSettings, pyqtSignal
from geest.core import JsonTreeItem, setting
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
        self.features_layer = None  # set in concrete class if needed
        self.raster_layer = None  # set in concrete class if needed
        self.output_crs = self.bboxes_layer.crs()
        # Will be populated by the workflow
        self.attributes = self.item.data(3)
        self.layer_id = self.attributes.get("ID", "").lower().replace(" ", "_")
        self.attributes["Result"] = "Not Run"

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

        self.attributes["Execution Start Time"] = datetime.datetime.now().isoformat()

        QgsMessageLog.logMessage("Processing Started", tag="Geest", level=Qgis.Info)

        feedback = QgsProcessingFeedback()
        output_rasters = []
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
                if self.features_layer:
                    area_features = self._select_features(
                        self.features_layer,
                        current_area,
                        output_prefix=f"{self.layer_id}_area_features_{index}",
                    )
                    if area_features.featureCount() == 0:
                        continue

                    # Step 2: Process the area features
                    raster_output = self._process_area(
                        current_area=current_area,
                        current_bbox=current_bbox,
                        area_features=area_features,
                        index=index,
                    )

                else:  # assumes we are processing a raster input
                    raster_output = self._subset_raster(
                        self.raster_layer,
                        current_area,
                        output_prefix=f"{self.output_prefix}_area_features_{index}",
                    )

                # Multiply the area by its matching mask layer in study_area folder
                masked_layer = self._mask_raster(
                    raster_path=raster_output,
                    area_geometry=current_area,
                    output_name=f"{self.output_prefix}_masked_{index}.shp",
                    index=index,
                )
                output_rasters.append(masked_layer)
            # Combine all area rasters into a VRT
            vrt_filepath = self._combine_rasters_to_vrt(output_rasters)
            self.attributes["Indicator Result File"] = vrt_filepath
            self.attributes["Indicator Result"] = (
                f"{self.workflow_name} Workflow Completed"
            )

            QgsMessageLog.logMessage(
                f"{self.workflow_name} Completed. Output VRT: {vrt_filepath}",
                tag="Geest",
                level=Qgis.Info,
            )
            self.attributes["Execution End Time"] = datetime.datetime.now().isoformat()
            self.attributes["Error File"] = None
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
            self.attributes["Indicator Result"] = f"{self.workflow_name} Workflow Error"
            self.attributes["Indicator Result File"] = ""

            # Write the traceback to error.txt in the workflow_directory
            error_path = os.path.join(self.workflow_directory, "error.txt")
            with open(error_path, "w") as f:
                f.write(f"Failed to process {self.workflow_name}: {e}\n")
                f.write(traceback.format_exc())
            self.attributes["Error File"] = error_path
            return False

    @abstractmethod
    def _process_area(
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

        :return: A raster layer if processing completes successfully, False if canceled or failed.
        """
        pass

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

    def _select_features(
        self, layer: QgsVectorLayer, area_geom: QgsGeometry, output_prefix: str
    ) -> QgsVectorLayer:
        """
        Select features from the input layer that intersect with the given area geometry
        using the QGIS API. The selected features are stored in the working directory layer.

        Args:
            layer (QgsVectorLayer): The input layer to select features from (e.g., points, lines, polygons).
            area_geom (QgsGeometry): The current area geometry for which intersections are evaluated.
            output_name (str): A name for the output temporary layer to store selected features.

        Returns:
            QgsVectorLayer: A new temporary layer containing features that intersect with the given area geometry.
        """
        QgsMessageLog.logMessage(
            f"{self.workflow_name} Select Features Started",
            tag="Geest",
            level=Qgis.Info,
        )
        output_path = os.path.join(self.workflow_directory, f"{output_prefix}.shp")

        # Get the WKB type (geometry type) of the input layer (e.g., Point, LineString, Polygon)
        geometry_type = layer.wkbType()

        # Determine geometry type name based on input layer's geometry
        if QgsWkbTypes.geometryType(geometry_type) == QgsWkbTypes.PointGeometry:
            geometry_name = "Point"
        elif QgsWkbTypes.geometryType(geometry_type) == QgsWkbTypes.LineGeometry:
            geometry_name = "LineString"
        else:
            raise QgsProcessingException(f"Unsupported geometry type: {geometry_type}")

        # Create a memory layer to store the selected features with the correct geometry type
        crs = layer.crs().authid()
        temp_layer = QgsVectorLayer(
            f"{geometry_name}?crs={crs}", output_prefix, "memory"
        )
        temp_layer_data = temp_layer.dataProvider()

        # Add fields to the temporary layer
        temp_layer_data.addAttributes(layer.fields())
        temp_layer.updateFields()

        # Iterate through features and select those that intersect with the area
        request = QgsFeatureRequest(area_geom.boundingBox()).setFilterRect(
            area_geom.boundingBox()
        )
        selected_features = [
            feat
            for feat in layer.getFeatures(request)
            if feat.geometry().intersects(area_geom)
        ]
        temp_layer_data.addFeatures(selected_features)

        QgsMessageLog.logMessage(
            f"{self.workflow_name} writing {len(selected_features)} features",
            tag="Geest",
            level=Qgis.Info,
        )

        # Save the memory layer to a file for persistence
        QgsVectorFileWriter.writeAsVectorFormat(
            temp_layer, output_path, "UTF-8", temp_layer.crs(), "ESRI Shapefile"
        )

        QgsMessageLog.logMessage(
            f"{self.workflow_name} Select Features Ending", tag="Geest", level=Qgis.Info
        )

        return QgsVectorLayer(output_path, output_prefix, "ogr")

    def _rasterize(
        self, input_layer: QgsVectorLayer, bbox: QgsGeometry, index: int
    ) -> str:
        """

        ⭐️🚩⭐️ Warning this is not DRY - almost same function exists in study_area.py

        Rasterize the grid layer based on the 'value' attribute.

        Args:
            input_layer (QgsVectorLayer): The layer to rasterize.
            bbox (QgsGeometry): The bounding box for the raster extents.
            index (int): The current index used for naming the output raster.

        Returns:
            str: The file path to the rasterized output.
        """
        QgsMessageLog.logMessage("--- Rasterizingrid", tag="Geest", level=Qgis.Info)
        QgsMessageLog.logMessage(f"--- bbox {bbox}", tag="Geest", level=Qgis.Info)
        QgsMessageLog.logMessage(f"--- index {index}", tag="Geest", level=Qgis.Info)

        output_path = os.path.join(
            self.workflow_directory,
            f"{self.output_prefix}_buffered_{index}.tif",
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
            "FIELD": "value",
            "BURN": 0,
            "USE_Z": False,
            "UNITS": 1,
            "WIDTH": x_res,
            "HEIGHT": y_res,
            "EXTENT": f"{bbox.xMinimum()},{bbox.xMaximum()},{bbox.yMinimum()},{bbox.yMaximum()} [{self.target_crs.authid()}]",
            "NODATA": 0,
            "OPTIONS": "",
            "DATA_TYPE": 0,
            "INIT": 1,
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
