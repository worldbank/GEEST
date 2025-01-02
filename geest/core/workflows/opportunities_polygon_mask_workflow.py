import os
from qgis.core import (
    QgsRasterLayer,
    Qgis,
    QgsFeedback,
    QgsGeometry,
    QgsVectorLayer,
    QgsProcessingContext,
    QgsVectorLayer,
    QgsGeometry,
)
from qgis.PyQt.QtCore import QVariant
import processing
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem
from geest.utilities import log_message


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
        self.workflow_name = "opportunities_polygon_mask"
        # There are two ways a user can specify the polygon mask layer
        # either as a shapefile path added in a line edit or as a layer source
        # using a QgsMapLayerComboBox. We prioritize the shapefile path, so check that first.
        layer_source = self.attributes.get("polygon_mask_shapefile", None)
        provider_type = "ogr"
        if not layer_source:
            # Fall back to the QgsMapLayerComboBox source
            layer_source = self.attributes.get("polygon_mask_layer_source", None)
            provider_type = self.attributes.get(
                "polygon_mask_layer_provider_type", "ogr"
            )
        if not layer_source:
            log_message(
                "polygon_mask_shapefile not found",
                tag="Geest",
                level=Qgis.Critical,
            )
            return False
        self.features_layer = QgsVectorLayer(layer_source, "polygons", provider_type)
        if not self.features_layer.isValid():
            log_message("polygon_mask_shapefile not valid", level=Qgis.Critical)
            log_message(f"Layer Source: {layer_source}", level=Qgis.Critical)
            return False

        # Workflow directory is the subdir under working_directory
        ## This is usually set in the base class but we override that behaviour for this workflow
        self.workflow_directory = os.path.join(working_directory, "opportunity_masks")
        os.makedirs(self.workflow_directory, exist_ok=True)
        # Again normally auto-set in the base class but we override it here
        self.output_filename = "Opportunities_Mask"
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
        log_message(f"{self.workflow_name}  Processing Started")

        # Step 1: clip the selected features to the current area's clip area
        log_message(f"Clipping features to the current area's clip area")
        clipped_layer = self._clip_features(area_features, clip_area, index)
        log_message(f"Clipped features saved to {clipped_layer.source()}")
        log_message(f"Generating mask layer")
        mask_layer = self.generate_mask_layer(clipped_layer, current_bbox, index)
        log_message(f"Mask layer saved to {mask_layer}")

        return mask_layer

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

        This will be used to create masked version of WEE Score and WEE x Population Score rasters.

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

    # Default implementation of the abstract method - not used in this workflow
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

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
    ):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        pass
