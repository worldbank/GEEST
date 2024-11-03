import os
from qgis.core import (
    QgsMessageLog,
    QgsField,
    Qgis,
    QgsFeedback,
    QgsGeometry,
    QgsVectorLayer,
    QgsProcessingContext,
    QgsVectorLayer,
    QgsGeometry,
    QgsRasterBlock,
    QgsRaster,
    QgsRasterFileWriter,
    QgsRectangle,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QVariant
import processing
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem


class StreetLightsBufferWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'use_street_lights' workflow.
    """

    def __init__(
        self,
        item: JsonTreeItem,
        cell_size_m: float,
        feedback: QgsFeedback,
        context: QgsProcessingContext,
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param item: Item containing workflow parameters.
        :param cell_size_m: Cell size in meters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        """
        super().__init__(
            item, cell_size_m, feedback, context
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.workflow_name = "use_street_lights"

        layer_path = self.attributes.get("street_lights_shapefile", None)

        if not layer_path:
            QgsMessageLog.logMessage(
                "Invalid raster found in street_lights_shapefile, trying street_lights_point_layer_source.",
                tag="Geest",
                level=Qgis.Warning,
            )
            layer_path = self.attributes.get("street_lights_point_layer_source", None)
            if not layer_path:
                QgsMessageLog.logMessage(
                    "No points layer found in street_lights_point_layer_source.",
                    tag="Geest",
                    level=Qgis.Warning,
                )
                return False

        self.features_layer = QgsVectorLayer(layer_path, "points", "ogr")
        if not self.features_layer.isValid():
            QgsMessageLog.logMessage(
                "street_lights_point_layer not valid", tag="Geest", level=Qgis.Critical
            )
            QgsMessageLog.logMessage(
                f"Layer Source: {layer_path}", tag="Geest", level=Qgis.Critical
            )
            return False

        self.buffer_distance = 20  # 20m buffer
        self.workflow_is_legacy = False  # This is a new workflow, not a legacy one

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
        QgsMessageLog.logMessage(
            f"{self.workflow_name}  Processing Started", tag="Geest", level=Qgis.Info
        )

        # Step 1: Buffer the selected features
        buffered_layer = self._buffer_features(
            area_features, f"{self.layer_id}_buffered_{index}"
        )

        # Step 2: Rasterize the buffered layer and assign scores
        raster_output = self._rasterize_and_score(buffered_layer, current_bbox, index)

        return raster_output

    def _buffer_features(
        self, layer: QgsVectorLayer, output_name: str
    ) -> QgsVectorLayer:
        """
        Buffer the input features by the buffer_distance km.

        Args:
            layer (QgsVectorLayer): The input feature layer.
            output_name (str): A name for the output buffered layer.

        Returns:
            QgsVectorLayer: The buffered features layer.
        """
        output_path = os.path.join(self.workflow_directory, f"{output_name}.shp")
        buffered_layer = processing.run(
            "native:buffer",
            {
                "INPUT": layer,
                "DISTANCE": self.buffer_distance,  # 20m buffer
                "SEGMENTS": 15,
                "DISSOLVE": True,
                "OUTPUT": output_path,
            },
        )["OUTPUT"]

        buffered_layer = QgsVectorLayer(output_path, output_name, "ogr")
        return buffered_layer

    # Remove once all workflows are updated
    def do_execute(self):
        pass

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

    def _rasterize_and_score(
        self, buffered_layer: QgsVectorLayer, bbox: QgsGeometry, index: int
    ) -> str:
        """
        Rasterize the buffered layer and assign scores based on the overlap percentage
        Args:
            buffered_layer (QgsVectorLayer): Buffered layer to rasterize.
            bbox (QgsGeometry): Bounding box of the study area.
            index (int): Index of the current area.

        Returns:
            str: Path to the raster file.
        """
        QgsMessageLog.logMessage(
            "Rasterizing and scoring buffered layer", tag="Geest", level=Qgis.Info
        )

        xmin, ymin, xmax, ymax = bbox.boundingBox().toRectF().getCoords()
        width = int((xmax - xmin) / self.cell_size_m)
        height = int((ymax - ymin) / self.cell_size_m)

        raster_block = QgsRasterBlock(QgsRaster.DataType_Int32, width, height)
        raster_block.fill(0)  # Initialize with zeros

        for feature in buffered_layer.getFeatures():
            geom = feature.geometry()
            if geom.type() == QgsWkbTypes.PolygonGeometry:
                for row in range(height):
                    for col in range(width):
                        cell_geom = QgsGeometry.fromRect(
                            QgsRectangle(
                                xmin + col * self.cell_size_m,
                                ymax - (row + 1) * self.cell_size_m,
                                xmin + (col + 1) * self.cell_size_m,
                                ymax - row * self.cell_size_m,
                            )
                        )
                        intersection = geom.intersection(cell_geom)
                        if intersection.isEmpty():
                            continue
                        overlap_percent = (intersection.area() / cell_geom.area()) * 100

                        # Assign scores based on overlap percentage
                        if 80 <= overlap_percent <= 100:
                            raster_block.setValue(
                                col, row, max(raster_block.value(col, row), 5)
                            )
                        elif 60 <= overlap_percent < 80:
                            raster_block.setValue(
                                col, row, max(raster_block.value(col, row), 4)
                            )
                        elif 40 <= overlap_percent < 60:
                            raster_block.setValue(
                                col, row, max(raster_block.value(col, row), 3)
                            )
                        elif 20 <= overlap_percent < 40:
                            raster_block.setValue(
                                col, row, max(raster_block.value(col, row), 2)
                            )
                        elif 1 <= overlap_percent < 20:
                            raster_block.setValue(
                                col, row, max(raster_block.value(col, row), 1)
                            )

        # Write the raster to file
        output_path = os.path.join(
            self.workflow_directory,
            f"{self.layer_id}_{index}.tif",
        )
        writer = QgsRasterFileWriter(output_path)
        writer.writeRaster(
            raster_block.data(), width, height, bbox.boundingBox(), buffered_layer.crs()
        )

        QgsMessageLog.logMessage(
            f"Raster written to {output_path}", tag="Geest", level=Qgis.Info
        )

        return output_path
