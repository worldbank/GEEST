import os
import shutil
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
)
from qgis.PyQt.QtCore import QVariant
import processing
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem
from geest.utilities import log_message, resources_path


class OpportunitiesPolygonMaskWorkflow(WorkflowBase):
    """
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

    """

    def __init__(
        self,
        item: JsonTreeItem,
        cell_size_m: float,
        feedback: QgsFeedback,
        context: QgsProcessingContext,
        working_directory: str = None,
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param attributes: Item containing workflow parameters (should be node type: analysis).
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        :working_directory: Folder containing study_area.gpkg and where the outputs will be placed. If not set will be taken from QSettings.
        """
        log_message(f"Working_directory: {working_directory}")
        super().__init__(
            item=item,
            cell_size_m=cell_size_m,
            feedback=feedback,
            context=context,
            working_directory=working_directory,
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree

        self.mask_mode = self.attributes.get(
            "mask_mode", None
        )  # if set,  will be "point", "polygon" or "raster"
        if not self.mask_mode:
            raise Exception("Mask mode not set in the analysis.")

        self.workflow_name = f"opportunities_{self.mask_mode}_mask"
        # In normal workflows this comes from the item, but this workflow is a bit different
        # so we set it manually.
        self.layer_id = "Opportunities_Mask"
        if self.mask_mode == "point":
            self.buffer_distance_m = self.attributes.get("buffer_distance_m", 1000)
        if self.mask_mode in ["point", "polygon"]:
            # There are two ways a user can specify the polygon mask layer
            # either as a shapefile path added in a line edit or as a layer source
            # using a QgsMapLayerComboBox. We prioritize the shapefile path, so check that first.
            layer_source = self.attributes.get(f"{self.mask_mode}_mask_shapefile", None)
            provider_type = "ogr"
            if not layer_source:
                # Fall back to the QgsMapLayerComboBox source
                layer_source = self.attributes.get(
                    f"{self.mask_mode}_mask_layer_source", None
                )
                provider_type = self.attributes.get(
                    f"{self.mask_mode}_mask_layer_provider_type", "ogr"
                )
            if not layer_source:
                log_message(
                    f"{self.mask_mode}_mask_shapefile not found",
                    tag="Geest",
                    level=Qgis.Critical,
                )
                return False
            self.features_layer = QgsVectorLayer(
                layer_source, self.mask_mode, provider_type
            )
            if not self.features_layer.isValid():
                log_message(
                    f"{self.mask_mode}_mask_shapefile not valid", level=Qgis.Critical
                )
                log_message(f"Layer Source: {layer_source}", level=Qgis.Critical)
                return False
        elif self.mask_mode == "raster":
            # The base class has all the logic for clipping the raster layer
            # we just need to assign it to self.raster_layer
            # Then the _process_raster_for_area method is where we turn it into a mask
            log_message("Loading source raster mask layer")
            # First try the one defined in the line edit
            self.raster_layer = QgsRasterLayer(
                self.attributes.get("raster_mask_raster"), "Raster Mask", "ogr"
            )
            if not self.raster_layer.isValid():
                # Then fall back to the QgsMapLayerComboBox source
                self.raster_layer = QgsRasterLayer(
                    self.attributes.get("raster_mask_layer_source"),
                    "Raster Mask",
                    self.attributes.get("raster_mask_layer_provider_type"),
                )
            if not self.raster_layer.isValid():
                log_message(
                    "No valid raster layer provided for mask", level=Qgis.Critical
                )
                log_message(
                    f"Raster Source: {self.raster_layer.source()}", level=Qgis.Critical
                )
                return False
        # Workflow directory is the subdir under working_directory
        ## This is usually set in the base class but we override that behaviour for this workflow
        self.workflow_directory = os.path.join(working_directory, "opportunity_masks")
        os.makedirs(self.workflow_directory, exist_ok=True)
        # Again, normally auto-set in the base class but we override it here:
        self.output_filename = "Opportunities_Mask"
        # And customise which key we will write the result file to (see base class for notes):
        self.result_file_key = "opportunities_mask_result_file"
        self.result_key = "opportunities_mask_result"

        # Section below to be removed

        # These folders should already exist from the aggregation analysis and population raster processing
        self.wee_by_population_folder = os.path.join(
            working_directory, "wee_by_population_score"
        )

        if not os.path.exists(self.wee_by_population_folder):
            raise Exception(
                f"WEE folder not found.\n{self.wee_by_population_folder}\nPlease run WEE raster processing first."
            )

        # TODO make user configurable
        self.force_clear = False
        if self.force_clear and os.path.exists(self.workflow_directory):
            for file in os.listdir(self.workflow_directory):
                os.remove(os.path.join(self.workflow_directory, file))

        log_message("Initialized WEE Opportunities Polygon Mask Workflow")

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
            # The raster workflow is handled by the base class
            # We just need to set the self.raster_layer attribute in the
            # ctor for it to be initiated.
            #
            # Override the implementations in this class's _process_raster_for_area
            # for the actual processing logic.
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
        clip_layer = self.geometry_to_memory_layer(clip_area, "clip_area")
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

    def process_wee_score(self, mask_path, index):
        """

        TODO MOVE TO ITS OWN WORKFLOW, CURRENTLY NOT USED


        Apply the work opportunities mask to the WEE Score raster layer.
        """

        # Load your raster layer
        wee_path = os.path.join(
            self.wee_by_population_folder, "wee_by_population_score.vrt"
        )
        wee_by_population_layer = QgsRasterLayer(wee_path, "WEE by Population Score")

        if not wee_by_population_layer.isValid():
            log_message(f"The raster layer is invalid!\n{wee_path}\nTrying WEE score")
            wee_by_population_path = os.path.join(
                os.pardir(self.wee_by_population_folder), "wee_by_population_score.vrt"
            )
            wee_by_population_layer = QgsRasterLayer(
                wee_path, "WEE By Population Score"
            )
            if not wee_by_population_layer.isValid():
                raise Exception(
                    f"Neither WEE x Population nor WEE Score layers are valid.\n{wee_path}\n"
                )
        else:
            # Get the extent of the raster layer
            extent = wee_by_population_layer.extent()

            # Get the data provider for the raster layer
            provider = wee_by_population_layer.dataProvider()

            # Get the raster's width, height, and size of cells
            width = provider.xSize()
            height = provider.ySize()

            cell_width = extent.width() / width
            cell_height = extent.height() / height
        log_message(f"Raster layer loaded: {wee_path}")
        log_message(f"Raster extent: {extent}")
        log_message(f"Raster cell size: {cell_width} x {cell_height}")

        log_message(f"Masked WEE Score raster saved to {output}")
        opportunities_mask = os.path.join(
            self.workflow_directory, "oppotunities_mask.tif"
        )
        params = {
            "INPUT_A": wee_by_population_layer,
            "BAND_A": 1,
            "INPUT_B": rasterized_polygons_path,
            "BAND_B": 1,
            "FORMULA": "A*B",
            "NO_DATA": None,
            "EXTENT_OPT": 3,
            "PROJWIN": None,
            "RTYPE": 0,
            "OPTIONS": "",
            "EXTRA": "",
            "OUTPUT": opportunities_mask,
        }

        processing.run("gdal:rastercalculator", params)
        self.output_rasters.append(opportunities_mask)

        log_message(f"WEE SCORE raster saved to {opportunities_mask}")

    def apply_qml_style(self, source_qml: str, qml_path: str) -> None:

        log_message(f"Copying QML style from {source_qml} to {qml_path}")
        # Apply QML Style
        if os.path.exists(source_qml):
            shutil.copy(source_qml, qml_path)
        else:
            log_message("QML style file not found. Skipping QML copy.")

    def _combine_rasters_to_vrt(self, rasters: list) -> None:
        """
        Combine all the rasters into a single VRT file. Overrides the
        base class method to apply the custom QML style to the VRT.

        Args:
            rasters: The rasters to combine into a VRT.

        Returns:
            vrtpath (str): The file path to the VRT file.
        """
        vrt_filepath = super()._combine_rasters_to_vrt(rasters)
        if not vrt_filepath:
            return False

        qml_filepath = os.path.join(
            self.workflow_directory,
            f"{self.output_filename}_combined.qml",
        )
        source_qml = resources_path("resources", "qml", f"mask.qml")
        log_message(f"Copying QML from {source_qml} to {qml_filepath}")
        shutil.copyfile(source_qml, qml_filepath)
        log_message(f"Applying QML style to VRT: {qml_filepath}")
        return vrt_filepath

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

    # Default implementation of the abstract method - not used in this workflow
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

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
    ):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        pass
