from qgis.core import (
    Qgis,
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
    QgsProcessingFeedback,
    QgsGeometry,
    QgsField,
    QgsFeature,
    QgsWkbTypes,
    QgsProcessingException,
    QgsMessageLog,
    QgsVectorFileWriter,
    QgsFeatureRequest,
    edit,
    QgsRasterLayer,
    QgsProject,
    QgsProcessingContext,
)
from qgis.PyQt.QtCore import QVariant
import processing
import os
from typing import List
from .area_iterator import AreaIterator


class SafetyPerCellProcessor:
    """
    A class to process perceived safety factors per spatial cell, similar to the PolygonPerCellProcessor structure.

    This class processes perceived safety factors for various areas by:
    - Reprojecting the input safety layer.
    - Selecting features intersecting with predefined study areas.
    - Assigning values based on perceived safety.
    - Rasterizing the results.
    - Combining rasterized results into a single VRT file.

    Args:
        output_prefix (str): Prefix for the output files.
        cell_size_m (float): The cell size in meters for the analysis.
        safety_layer (QgsVectorLayer): The input layer containing safety data.
        safety_field (str): The field in the safety layer containing perceived safety values.
        workflow_directory (str): Directory where output files will be stored.
        gpkg_path (str): Path to the GeoPackage with study areas.
        context (QgsProcessingContext): The processing context to pass objects to the thread.
    Returns:
        str: The path to the created VRT file.
    """

    def __init__(
        self,
        output_prefix: str,
        cell_size_m: float,
        safety_layer: QgsVectorLayer,
        safety_field: str,
        workflow_directory: str,
        gpkg_path: str,
        context: QgsProcessingContext,
    ) -> None:
        """
        Initialize the SafetyPerCellProcessor.

        Args:
            output_prefix (str): Prefix for the output files.
            safety_layer (QgsVectorLayer): The input layer containing safety data.
            workflow_directory (str): Directory where output files will be stored.
            gpkg_path (str): Path to the GeoPackage with study areas.
        """
        self.output_prefix = output_prefix
        self.cell_size_m = cell_size_m
        self.safety_layer = safety_layer
        self.workflow_directory = workflow_directory
        self.gpkg_path = gpkg_path
        self.safety_field = safety_field
        self.context = (
            context  # Used to pass objects to the thread. e.g. the QgsProject Instance
        )

        # Load the grid layer from the GeoPackage
        self.grid_layer = QgsVectorLayer(
            f"{self.gpkg_path}|layername=study_area_grid", "study_area_grid", "ogr"
        )
        if not self.grid_layer.isValid():
            raise QgsProcessingException(
                f"Failed to load 'study_area_grid' layer from {self.gpkg_path}"
            )
        if not self.safety_layer.isValid():
            raise QgsProcessingException(
                f"Failed to load safety layer from {self.safety_layer.source()}"
            )

    def process_areas(self) -> None:
        """
        Main function to iterate over areas and process safety data for each area.
        """
        feedback = QgsProcessingFeedback()

        # Step 1: Reproject the safety layer
        reprojected_safety_layer = self._reproject_layer(
            self.safety_layer, self.grid_layer.crs()
        )

        # Use the AreaIterator to loop over study areas from the GeoPackage
        area_iterator = AreaIterator(
            self.gpkg_path
        )  # Call the iterator from the other file

        for index, (current_area, current_bbox, progress) in enumerate(area_iterator):
            feedback.pushInfo(
                f"Processing area {index + 1} with progress {progress:.2f}%"
            )

            # Step 2: Select features that intersect the current area
            area_features = self._select_features(
                reprojected_safety_layer,
                current_area,
                f"{self.output_prefix}_safety_features_{index+1}",
            )

            # Step 3: Assign reclassification values based on perceived safety
            reclassified_layer = self._assign_reclassification_to_safety(area_features)

            # Step 4: Rasterize the safety data
            self._rasterize_safety(reclassified_layer, current_bbox, index)

        # Step 5: Combine the resulting rasters into a single VRT
        vrt_filepath = self._combine_rasters_to_vrt(index + 1)
        return vrt_filepath

    def _reproject_layer(
        self, layer: QgsVectorLayer, target_crs: QgsCoordinateReferenceSystem
    ) -> QgsVectorLayer:
        """
        Reproject the input layer to match the CRS of the grid layer.
        """
        QgsMessageLog.logMessage(
            f"Reprojecting {layer.name()} to {target_crs.authid()}", level=Qgis.Info
        )
        return processing.run(
            "native:reprojectlayer",
            {"INPUT": layer, "TARGET_CRS": target_crs, "OUTPUT": "memory:"},
        )["OUTPUT"]

    def _select_features(
        self, layer: QgsVectorLayer, area_geom: QgsGeometry, output_name: str
    ) -> QgsVectorLayer:
        """
        Select features from the layer that intersect with the given area geometry.
        """
        output_path = os.path.join(self.workflow_directory, f"{output_name}.shp")
        request = QgsFeatureRequest(area_geom.boundingBox()).setFilterRect(
            area_geom.boundingBox()
        )
        selected_features = [
            feat
            for feat in layer.getFeatures(request)
            if feat.geometry().intersects(area_geom)
        ]
        return self._write_features_to_layer(
            layer, selected_features, output_path, output_name
        )

    def _assign_reclassification_to_safety(
        self, layer: QgsVectorLayer
    ) -> QgsVectorLayer:
        """
        Assign reclassification values to polygons based on perceived safety.
        """
        with edit(layer):
            if layer.fields().indexFromName("value") == -1:
                layer.dataProvider().addAttributes([QgsField("value", QVariant.Int)])
                layer.updateFields()

            for feature in layer.getFeatures():
                perceived_safety = feature[self.safety_field]
                # Scale perceived safety values between 0 and 5
                reclass_val = self._scale_value(perceived_safety, 0, 100, 0, 5)
                feature.setAttribute("value", reclass_val)
                layer.updateFeature(feature)
        return layer

    def _scale_value(self, value, min_in, max_in, min_out, max_out):
        """
        Scale value from input range (min_in, max_in) to output range (min_out, max_out).
        """
        return (value - min_in) / (max_in - min_in) * (max_out - min_out) + min_out

    def _rasterize_safety(
        self, polygon_layer: QgsVectorLayer, bbox: QgsGeometry, index: int
    ) -> None:
        """
        Rasterize the safety polygons.
        """
        output_path = os.path.join(
            self.workflow_directory, f"{self.output_prefix}_safety_raster_{index}.tif"
        )
        bbox = bbox.boundingBox()
        params = {
            "INPUT": polygon_layer,
            "FIELD": "value",
            "BURN": None,
            "USE_Z": False,
            "UNITS": 1,
            "WIDTH": self.cell_size_m,
            "HEIGHT": self.cell_size_m,
            "EXTENT": f"{bbox.xMinimum()},{bbox.xMaximum()},{bbox.yMinimum()},{bbox.yMaximum()}",
            "NODATA": 255,
            "DATA_TYPE": 0,
            "OUTPUT": output_path,
        }
        processing.run("gdal:rasterize", params)
        QgsMessageLog.logMessage(
            f"Created raster for safety area: {output_path}", level=Qgis.Info
        )

    def _combine_rasters_to_vrt(self, num_rasters: int) -> None:
        """
        Combine all rasters into a VRT.
        """
        raster_files = [
            os.path.join(
                self.workflow_directory, f"{self.output_prefix}_safety_raster_{i}.tif"
            )
            for i in range(num_rasters)
        ]
        vrt_path = os.path.join(
            self.workflow_directory, f"{self.output_prefix}_safety_combined.vrt"
        )
        processing.run(
            "gdal:buildvirtualraster", {"INPUT": raster_files, "OUTPUT": vrt_path}
        )
        QgsMessageLog.logMessage(f"Created combined VRT: {vrt_path}", level=Qgis.Info)
        # Add the VRT to the QGIS map
        vrt_layer = QgsRasterLayer(vrt_path, f"{self.output_prefix}_combined VRT")

        if vrt_layer.isValid():
            self.context.project().addMapLayer(vrt_layer)
            QgsMessageLog.logMessage(
                "Added VRT layer to the map.", tag="Geest", level=Qgis.Info
            )
        else:
            QgsMessageLog.logMessage(
                "Failed to add VRT layer to the map.", tag="Geest", level=Qgis.Critical
            )
        return vrt_path

    def _write_features_to_layer(
        self,
        layer: QgsVectorLayer,
        features: List[QgsFeature],
        output_path: str,
        output_name: str,
    ) -> QgsVectorLayer:
        """
        Write selected features to a new layer.
        """
        crs = layer.crs().authid()
        temp_layer = QgsVectorLayer(f"Polygon?crs={crs}", output_name, "memory")
        temp_layer_data = temp_layer.dataProvider()
        temp_layer_data.addAttributes(layer.fields())
        temp_layer.updateFields()
        temp_layer_data.addFeatures(features)
        QgsVectorFileWriter.writeAsVectorFormat(
            temp_layer, output_path, "UTF-8", temp_layer.crs(), "ESRI Shapefile"
        )
        return QgsVectorLayer(output_path, output_name, "ogr")
