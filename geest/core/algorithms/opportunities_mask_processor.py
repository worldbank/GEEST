import os
import shutil
import traceback
from typing import Optional
from qgis.core import (
    QgsRasterLayer,
    Qgis,
    QgsFeedback,
    QgsGeometry,
    QgsVectorLayer,
    QgsProcessingContext,
    QgsVectorLayer,
    QgsGeometry,
    QgsProcessingFeedback,
    QgsTask,
)
import processing
from geest.core import JsonTreeItem
from geest.utilities import log_message, resources_path
from .utilities import (
    subset_vector_layer,
    geometry_to_memory_layer,
    check_and_reproject_layer,
    combine_rasters_to_vrt,
)
from .area_iterator import AreaIterator


class OpportunitiesMaskProcessor(QgsTask):
    """
    A QgsTask subclass for generating job opportunity mask layers.

    It iterates over bounding boxes and study areas, selects the intersecting features
    (if inputs are points or polygons) or in the case of a raster maske, clips the raster
    data to match the study area bbox.

    Args:
        item (JSONTreeItem): Analysis item containing the needed parameters.
        study_area_gpkg_path (str): Path to the GeoPackage containing study area masks.
        output_dir (str): Directory to save the output rasters.
        cell_size_m (float): Cell size for the output rasters.
        context (Optional[QgsProcessingContext]): QGIS processing context.
        feedback (Optional[QgsFeedback]): QGIS feedback object.
        force_clear (bool): Flag to force clearing of all outputs before processing.

    Concrete implementation of a geest insight for masking by job opportunities.

    It will create a raster layer where all cells outside the masked areas (defined
    by the input polygons layer) are set to a no data value.

    This is used when you want to represent the WEE Score and WEE x Population Score
    only in areas where there are job opportunities / job creation initiatives.

    The input layer should be a polygon layer with the job opportunities. Its attributes
    are completely ignored, only the geometry is used to create a mask.

    The output raster will have the same extent and cell size as the study area.

    The output raster will have either have values of 1 in the mask and 0 outside.

    The output raster will be a vrt which is a composite of all the individual area rasters.

    The output raster will be saved in the working directory under a subfolder called 'opportunity_masks'.

    Preconditions:

    This workflow expects that the user has configured the root analysis node dialog with
    the polygon mask settings configured.

    Input can be any of:

    * a point layer (with a buffer distance)
    * a polygon layer (attributes are ignored)
    * a raster layer (any non-null pixel will be set to 1)

    """

    def __init__(
        self,
        item: JsonTreeItem,
        study_area_gpkg_path: str,
        working_directory: str,
        cell_size_m: float,
        context: Optional[QgsProcessingContext] = None,
        feedback: Optional[QgsFeedback] = None,
        force_clear: bool = False,
    ):
        super().__init__("Opportunities Mask Processor", QgsTask.CanCancel)
        self.study_area_gpkg_path = study_area_gpkg_path
        self.cell_size_m = cell_size_m
        self.working_directory = working_directory
        layer: QgsVectorLayer = QgsVectorLayer(
            f"{self.study_area_gpkg_path}|layername=study_area_clip_polygons",
            "study_area_clip_polygons",
            "ogr",
        )
        self.target_crs = layer.crs()
        del layer
        self.context = context
        self.feedback = feedback
        self.clipped_rasters = []
        self.item = item
        self.mask_mode = self.item.attribute(
            "mask_mode", None
        )  # if set,  will be "point", "polygon" or "raster"
        if not self.mask_mode:
            raise Exception("Mask mode not set in the analysis.")

        self.workflow_name = f"opportunities_{self.mask_mode}_mask"
        # In normal workflows this comes from the item, but this workflow is a bit different
        # so we set it manually.
        self.layer_id = "Opportunities_Mask"
        if self.mask_mode == "point":
            self.buffer_distance_m = self.item.attribute("buffer_distance_m", 1000)
        if self.mask_mode in ["point", "polygon"]:
            # There are two ways a user can specify the polygon mask layer
            # either as a shapefile path added in a line edit or as a layer source
            # using a QgsMapLayerComboBox. We prioritize the shapefile path, so check that first.
            layer_source = self.item.attribute(f"{self.mask_mode}_mask_shapefile", None)
            provider_type = "ogr"
            if not layer_source:
                # Fall back to the QgsMapLayerComboBox source
                layer_source = self.item.attribute(
                    f"{self.mask_mode}_mask_layer_source", None
                )
                provider_type = self.item.attribute(
                    f"{self.mask_mode}_mask_layer_provider_type", "ogr"
                )
            if not layer_source:
                log_message(
                    f"{self.mask_mode}_mask_shapefile not found",
                    tag="Geest",
                    level=Qgis.Critical,
                )
                raise Exception(f"{self.mask_mode}_mask_shapefile not found")
            self.features_layer = QgsVectorLayer(
                layer_source, self.mask_mode, provider_type
            )
            if not self.features_layer.isValid():
                log_message(
                    f"{self.mask_mode}_mask_shapefile not valid", level=Qgis.Critical
                )
                log_message(f"Layer Source: {layer_source}", level=Qgis.Critical)
                raise Exception(f"{self.mask_mode}_mask_shapefile not valid")

            # Check the geometries and reproject if necessary
            self.features_layer = check_and_reproject_layer(
                self.features_layer, self.target_crs
            )

        elif self.mask_mode == "raster":
            # Check the input raster is ok. The raster itself does not need to be a mask
            # (i.e. with 1 and nodata values) - we will take care of that in this class.
            # Then the _process_raster_for_area method is where we turn it into a mask
            log_message("Loading source raster mask layer")
            # First try the one defined in the line edit
            self.raster_layer = QgsRasterLayer(
                self.item.attribute("raster_mask_raster"), "Raster Mask", "ogr"
            )
            if not self.raster_layer.isValid():
                # Then fall back to the QgsMapLayerComboBox source
                self.raster_layer = QgsRasterLayer(
                    self.item.attribute("raster_mask_layer_source"),
                    "Raster Mask",
                    self.item.attribute("raster_mask_layer_provider_type"),
                )
            if not self.raster_layer.isValid():
                log_message(
                    "No valid raster layer provided for mask", level=Qgis.Critical
                )
                log_message(
                    f"Raster Source: {self.raster_layer.source()}", level=Qgis.Critical
                )
                raise Exception("No valid raster layer provided for mask")
        # Workflow directory is the subdir under working_directory
        self.workflow_directory = os.path.join(working_directory, "opportunity_masks")
        os.makedirs(self.workflow_directory, exist_ok=True)

        self.output_filename = "Opportunities_Mask"
        # And customise which key we will write the result file to:
        self.result_file_key = "opportunities_mask_result_file"
        self.result_key = "opportunities_mask_result"

        # TODO make user configurable
        self.force_clear = False
        if self.force_clear and os.path.exists(self.workflow_directory):
            for file in os.listdir(self.workflow_directory):
                os.remove(os.path.join(self.workflow_directory, file))

        self.mask_list = []

        log_message(f"---------------------------------------------")
        log_message(f"Initialized WEE Opportunities Mask Workflow")
        log_message(f"---------------------------------------------")
        log_message(f"Item: {self.item.name}")
        log_message(f"Study area GeoPackage path: {self.study_area_gpkg_path}")
        log_message(f"Working_directory: {self.working_directory}")
        log_message(f"Workflow directory: {self.workflow_directory}")
        log_message(f"Cell size: {self.cell_size_m}")
        log_message(f"CRS: {self.target_crs.authid() if self.target_crs else 'None'}")
        log_message(f"Force clear: {self.force_clear}")
        log_message(f"---------------------------------------------")

    def run(self) -> bool:
        """
        Executes the task to process mask for each are.
        """
        try:
            area_iterator = AreaIterator(self.study_area_gpkg_path)
            for index, (current_area, clip_area, current_bbox, progress) in enumerate(
                area_iterator
            ):
                if self.feedback and self.feedback.isCanceled():
                    return False
                if self.mask_mode == "raster":
                    area_raster = self._subset_raster_layer(current_bbox, index)
                    mask_layer = self._process_raster_for_area(
                        current_area, clip_area, current_bbox, area_raster, index
                    )
                else:
                    vector_layer = subset_vector_layer(
                        self.workflow_directory,
                        self.features_layer,
                        current_area,
                        str(index),
                    )
                    mask_layer = self._process_features_for_area(
                        current_area, clip_area, current_bbox, vector_layer, index
                    )
                if mask_layer:
                    self.mask_list.append(mask_layer)

            vrt_filepath = os.path.join(
                self.workflow_directory,
                f"{self.output_filename}_combined.vrt",
            )
            source_qml = resources_path("resources", "qml", "mask.qml")
            vrt_filepath = combine_rasters_to_vrt(
                self.mask_list, self.target_crs, vrt_filepath, source_qml
            )
            self.item.setAttribute(self.result_file_key, vrt_filepath)
            self.item.setAttribute(self.result_key, "Opportunities Mask Created OK")
        except Exception as e:
            log_message(f"Task failed: {e}")
            log_message(traceback.format_exc())
            self.item.setAttribute(self.result_key, str(e))
            return False

    def finished(self, result: bool) -> None:
        """
        Called when the task completes.
        """
        if result:
            log_message("Opportunities mask processing completed successfully.")
        else:
            log_message("Opportunities mask processing failed.")

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
        :current_bbox: Bounding box of the above area.
        :area_features: A vector layer of features to analyse that includes only features in the study area.
            This is created by the base class using the features_layer and the current_area to subset the features.
        :index: Iteration / number of area being processed.

        :return: A raster layer file path if processing completes successfully, False if canceled or failed.
        """
        log_message(f"{self.workflow_name}  Processing Started for area {index}")
        log_message(f"Mask mode: {self.mask_mode}")
        if self.mask_mode == "point":
            log_message("Buffering job opportunity points")
            buffered_points_layer = self._buffer_features(area_features, index)
            log_message(f"Clipping features to the current area's clip area")
            clipped_layer = self._clip_features(buffered_points_layer, clip_area, index)
            log_message(f"Clipped features saved to {clipped_layer.source()}")
            log_message(f"Generating mask layer")
            mask_layer = self.generate_mask_layer(clipped_layer, current_bbox, index)
            log_message(f"Mask layer saved to {mask_layer}")
            return mask_layer
        elif self.mask_mode == "polygon":
            # Step 1: clip the selected features to the current area's clip area
            log_message(f"Clipping features to the current area's clip area")
            clipped_layer = self._clip_features(area_features, clip_area, index)
            log_message(f"Clipped features saved to {clipped_layer.source()}")
            log_message(f"Generating mask layer")
            mask_layer = self.generate_mask_layer(clipped_layer, current_bbox, index)
            log_message(f"Mask layer saved to {mask_layer}")
            return mask_layer
        else:  # Raster
            pass

    def _buffer_features(self, layer: QgsVectorLayer, index: int) -> QgsVectorLayer:
        """
        Buffer the input features by the buffer_distance m.

        Args:
            layer (QgsVectorLayer): The input feature layer.
            index (int): The index of the current area.

        Returns:
            QgsVectorLayer: The buffered features layer.
        """
        output_name = f"opportunites_points_buffered_{index}"

        output_path = os.path.join(self.workflow_directory, f"{output_name}.shp")
        buffered_layer = processing.run(
            "native:buffer",
            {
                "INPUT": layer,
                "DISTANCE": self.buffer_distance_m,
                "SEGMENTS": 15,
                "DISSOLVE": True,
                "OUTPUT": output_path,
            },
        )["OUTPUT"]

        buffered_layer = QgsVectorLayer(output_path, output_name, "ogr")
        return buffered_layer

    def _clip_features(
        self, layer: QgsVectorLayer, clip_area: QgsGeometry, index: int
    ) -> QgsVectorLayer:
        """
        Clip the input features by the clip area.

        Args:
            layer (QgsVectorLayer): The input feature layer.
            clip_area (QgsGeometry): The geometry to clip the features by.
            index (int): The index of the current area.

        Returns:
            QgsVectorLayer: The mask features layer clipped to the clip area.
        """
        output_name = f"opportunites_polygons_clipped_{index}"
        clip_layer = geometry_to_memory_layer(clip_area, self.target_crs, "clip_area")
        output_path = os.path.join(self.workflow_directory, f"{output_name}.shp")
        params = {"INPUT": layer, "OVERLAY": clip_layer, "OUTPUT": output_path}
        output = processing.run("native:clip", params)["OUTPUT"]
        clipped_layer = QgsVectorLayer(output_path, output_name, "ogr")
        return clipped_layer

    def generate_mask_layer(
        self, clipped_layer: QgsVectorLayer, current_bbox: QgsGeometry, index: int
    ) -> None:
        """Generate the mask layer.

        This will be used to create a mask by rasterizing the input polygon layer.

        Args:
            clipped_layer: The clipped vector mask layer.
            current_bbox: The bounding box of the current area.
            index: The index of the current area.
        Returns:
            Path to the mask raster layer generated from the input clipped polygon layer.

        """

        rasterized_polygons_path = os.path.join(
            self.workflow_directory, f"opportunites_mask_{index}.tif"
        )

        params = {
            "INPUT": clipped_layer,
            "FIELD": None,
            "BURN": 1,
            "USE_Z": False,
            "UNITS": 1,
            "WIDTH": self.cell_size_m,
            "HEIGHT": self.cell_size_m,
            "EXTENT": current_bbox.boundingBox(),
            "NODATA": 0,
            "OPTIONS": "",
            "DATA_TYPE": 0,  # byte
            "INIT": None,
            "INVERT": False,
            "EXTRA": "-co NBITS=1 -at",  # -at is for all touched cells
            "OUTPUT": rasterized_polygons_path,
        }

        output = processing.run("gdal:rasterize", params)["OUTPUT"]
        return rasterized_polygons_path

    def _subset_raster_layer(self, bbox: QgsGeometry, index: int):
        """
        Reproject and clip the raster to the bounding box of the current area.

        Overloaded version of the same method in the base class because that one
        fills the raster replacing nodata with 0 which is not what we want for this workflow.

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
            "OUTPUT": reprojected_raster_path,
            "TARGET_EXTENT": f"{bbox.xMinimum()},{bbox.xMaximum()},{bbox.yMinimum()},{bbox.yMaximum()} [{self.target_crs.authid()}]",
        }

        aoi = processing.run(
            "gdal:warpreproject", params, feedback=QgsProcessingFeedback()
        )["OUTPUT"]
        return reprojected_raster_path

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

        In this case we will convert it to a mask raster where any non-null pixel
        is given a value of 1 and all other pixels are set to nodata.


        :current_area: Current polygon from our study area.
        :clip_area: Polygon to clip the raster to.
        :current_bbox: Bounding box of the above area.
        :area_raster: A raster layer of features to analyse that includes only bbox pixels in the study area.
        :index: Index of the current area.

        :return: Path to the reclassified raster.
        """
        log_message(f"{self.workflow_name}  Processing Raster Started for area {index}")
        opportunities_mask_path = os.path.join(
            self.workflow_directory, f"opportunities_mask_{index}.tif"
        )
        # 📒 NOTE: Explanation for the formula logic:
        #
        # (A!=A) identifies NoData cells (since NaN != NaN is True for NoData cells) and sets them to 0.
        # (A==A) identifies valid cells and sets them to 1.
        # This ensures that all valid cells are set to 1 and NoData cells remain as NoData.
        #
        params = {
            "INPUT_A": area_raster,
            "BAND_A": 1,
            "FORMULA": "(A!=A)*0+(A==A)*1",
            "NO_DATA": None,
            "EXTENT_OPT": 0,
            "PROJWIN": None,
            "RTYPE": 0,
            "OPTIONS": "",
            "EXTRA": "",
            "OUTPUT": opportunities_mask_path,
        }

        processing.run("gdal:rastercalculator", params)
        return opportunities_mask_path
