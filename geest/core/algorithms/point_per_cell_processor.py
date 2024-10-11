from qgis.core import (
    QgsVectorLayer,
    QgsProcessingFeedback,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProject,
    QgsRasterLayer,
    QgsProcessingException,
    QgsFeature,
    QgsGeometry,
    QgsVectorFileWriter,
    edit,
    QgsMessageLog,
    Qgis,
)
import processing  # QGIS processing toolbox
from .area_iterator import AreaIterator
from typing import List, Tuple
import os


class PointPerCellProcessor:
    """
    A class to process spatial areas and perform spatial analysis using QGIS processing algorithms.

    This class iterates over areas (polygons) and corresponding bounding boxes within a GeoPackage.
    For each area, it performs spatial operations on the input layer representing pedestrian or other point features,
    and a grid layer from the same GeoPackage. The results are processed and rasterized.

    The following steps are performed for each area:

    1. Select points (from a points layer) that intersect with the current area.
    2. Select grid cells (from the `study_area_grid` layer in the GeoPackage) that intersect with the points, ensuring no duplicates.
    3. Assign values to the grid cells based on the number of intersecting features:
        - A value of 3 if the grid cell intersects only one feature.
        - A value of 5 if the grid cell intersects more than one feature.
    4. Rasterize the grid cells, using their assigned values to create a raster for each area.
    5. Convert the resulting raster to byte format to minimize space usage.
    6. After processing all areas, combine the resulting byte rasters into a single VRT file.

    Attributes:
        gpkg_path (str): Path to the GeoPackage containing the study areas, bounding boxes, and grid.
        points_layer (QgsVectorLayer): A point layer representing pedestrian crossings or other point features.
        workflow_directory (str): Directory where temporary and output files will be stored.
        grid_layer (QgsVectorLayer): A grid layer (study_area_grid) loaded from the GeoPackage.

    Example:
        ```python
        processor = PointPerCellProcessor(points_layer, '/path/to/workflow_directory', '/path/to/your/geopackage.gpkg')
        processor.process_areas()
        ```
    """

    def __init__(
        self,
        points_layer: QgsVectorLayer,
        workflow_directory: str,
        gpkg_path: str,
    ) -> None:
        """
        Initialize the PointPerCellProcessor with the points layer, working directory, and the GeoPackage path.

        Args:
            points_layer (QgsVectorLayer): The input point layer representing features like pedestrian crossings.
            workflow_directory (str): Directory where temporary and final output files will be stored.
            gpkg_path (str): Path to the GeoPackage file containing the study areas, bounding boxes, and grid layer.
        """
        self.points_layer = points_layer
        self.workflow_directory = (
            workflow_directory  # low level folder where we write the workflow outputs
        )
        self.gpkg_path = gpkg_path  # top level folder where gpkg is etc

        # Load the grid layer from the GeoPackage
        self.grid_layer = QgsVectorLayer(
            f"{self.gpkg_path}|layername=study_area_grid", "study_area_grid", "ogr"
        )
        if not self.grid_layer.isValid():

            raise QgsProcessingException(
                f"Failed to load 'study_area_grid' layer from the GeoPackage. at {self.gpkg_path}"
            )
        QgsMessageLog.logMessage("Point per Cell Processor Initialised")

    def process_areas(self) -> None:
        """
        Main function to iterate over areas from the GeoPackage and perform the analysis for each area.

        This function processes areas (defined by polygons and bounding boxes) from the GeoPackage using
        the provided input layers (points, grid). It applies the steps of selecting intersecting
        features, assigning values to grid cells, rasterizing the grid, converting to byte format, and finally
        combining the rasters into a VRT.

        Raises:
            QgsProcessingException: If any processing step fails during the execution.
        """
        feedback = QgsProcessingFeedback()
        area_iterator = AreaIterator(
            self.gpkg_path
        )  # Use the class-level GeoPackage path

        # Iterate over areas and perform the analysis for each
        for index, (current_area, current_bbox, progress) in enumerate(area_iterator):
            feedback.pushInfo(
                f"Processing area {index+1} with progress {progress:.2f}%"
            )

            # Step 2: Select points that intersect with the current area and store in a temporary layer
            area_points = self._select_features(
                self.points_layer, current_area, "area_points"
            )

            # Step 3: Select grid cells that intersect with points
            area_grid = self._select_grid_cells(self.grid_layer, area_points)

            # Step 4: Assign values to grid cells
            area_grid = self._assign_values_to_grid(area_grid)

            # Step 5: Rasterize the grid layer using the assigned values
            raster_output = self._rasterize_grid(area_grid, current_bbox, index)

            # Step 6: Convert the raster to byte format
            byte_raster = self._convert_to_byte_raster(raster_output, index)

        # Step 7: Combine the resulting byte rasters into a single VRT
        self._combine_rasters_to_vrt(index + 1)

    def _select_features(
        self, layer: QgsVectorLayer, area_geom: QgsGeometry, output_name: str
    ) -> QgsVectorLayer:
        """
        Select features from the input layer that intersect with the given area geometry.

        Args:
            layer (QgsVectorLayer): The input layer (e.g., points for crossings) to select features from.
            area_geom (QgsGeometry): The current area geometry for which intersections are evaluated.
            output_name (str): A name for the output temporary layer to store selected features.

        Returns:
            QgsVectorLayer: A new temporary layer containing features that intersect with the given area geometry.
        """
        output_path = os.path.join(self.workflow_directory, f"{output_name}.shp")
        params = {
            "INPUT": layer,
            "PREDICATE": [0],  # Intersects predicate
            "GEOMETRY": area_geom,
            "OUTPUT": output_path,
        }
        result = processing.run("native:extractbyextent", params)
        return QgsVectorLayer(result["OUTPUT"], output_name, "ogr")

    def _select_grid_cells(
        self,
        grid_layer: QgsVectorLayer,
        points_layer: QgsVectorLayer,
    ) -> QgsVectorLayer:
        """
        Select grid cells that intersect with points by iterating over features and adding them to a set.

        Args:
            grid_layer (QgsVectorLayer): The input grid layer containing polygon cells.
            points_layer (QgsVectorLayer): The input layer containing points (e.g., pedestrian crossings).

        Returns:
            QgsVectorLayer: A temporary layer containing grid cells that intersect with points.
        """
        output_path = os.path.join(self.workflow_directory, "area_grid_selected.shp")
        intersected_grid_ids = set()  # Set to track unique intersecting grid cell IDs

        # Iterate over points and find intersecting grid cells
        for point_feature in points_layer.getFeatures():
            for grid_feature in grid_layer.getFeatures():
                if grid_feature.geometry().intersects(point_feature.geometry()):
                    intersected_grid_ids.add(grid_feature.id())

        # Collect the selected grid cells into a new temporary layer
        selected_grid_features = [
            f for f in grid_layer.getFeatures() if f.id() in intersected_grid_ids
        ]
        selected_grid_layer = self._create_temp_layer(
            selected_grid_features, output_path
        )

        return selected_grid_layer

    def _create_temp_layer(
        self, features: List[QgsFeature], output_path: str
    ) -> QgsVectorLayer:
        """
        Create a temporary vector layer with the provided features.

        Args:
            features (List[QgsFeature]): A list of selected QgsFeatures to add to the temporary layer.
            output_path (str): The file path for storing the temporary output layer.

        Returns:
            QgsVectorLayer: A new temporary vector layer containing the selected features.
        """
        crs = features[0].geometry().crs() if features else None
        temp_layer = QgsVectorLayer(
            "Polygon?crs={}".format(crs.authid()), "temporary_layer", "memory"
        )
        temp_layer_data = temp_layer.dataProvider()

        # Add fields and features to the new layer
        temp_layer_data.addAttributes([f.fieldName() for f in features[0].fields()])
        temp_layer.updateFields()

        temp_layer_data.addFeatures(features)

        # Save the memory layer to a file for persistence
        QgsVectorFileWriter.writeAsVectorFormat(
            temp_layer, output_path, "UTF-8", temp_layer.crs(), "ESRI Shapefile"
        )

        return QgsVectorLayer(output_path, os.path.basename(output_path), "ogr")

    def _assign_values_to_grid(self, grid_layer: QgsVectorLayer) -> QgsVectorLayer:
        """
        Assign values to grid cells based on the number of intersecting features.

        A value of 3 is assigned to cells that intersect with one feature, and a value of 5 is assigned to
        cells that intersect with more than one feature.

        Args:
            grid_layer (QgsVectorLayer): The input grid layer containing polygon cells.

        Returns:
            QgsVectorLayer: The grid layer with values assigned to the 'value' field.
        """
        with edit(grid_layer):
            for feature in grid_layer.getFeatures():
                intersecting_features = feature["intersecting_features"]
                if intersecting_features == 1:
                    feature["value"] = 3
                elif intersecting_features > 1:
                    feature["value"] = 5
                grid_layer.updateFeature(feature)
        return grid_layer

    def _rasterize_grid(
        self, grid_layer: QgsVectorLayer, bbox: QgsGeometry, index: int
    ) -> str:
        """
        Rasterize the grid layer based on the 'value' attribute.

        Args:
            grid_layer (QgsVectorLayer): The grid layer to rasterize.
            bbox (QgsGeometry): The bounding box for the raster extents.
            index (int): The current index used for naming the output raster.

        Returns:
            str: The file path to the rasterized output.
        """
        QgsMessageLog.logMessage("--- Rasterizing grid", tag="Geest", level=Qgis.Info)
        QgsMessageLog.logMessage(f"--- bbox {bbox}", tag="Geest", level=Qgis.Info)
        QgsMessageLog.logMessage(f"--- index {index}", tag="Geest", level=Qgis.Info)

        output_path = os.path.join(
            self.workflow_directory, f"raster_output_{index}.tif"
        )
        params = {
            "INPUT": grid_layer,
            "FIELD": "value",
            "EXTENT": bbox.boundingBox(),
            "OUTPUT": output_path,
        }
        processing.run("gdal:rasterize", params)
        return output_path

    def _convert_to_byte_raster(self, raster_path: str, index: int) -> str:
        """
        Convert the raster to byte format to reduce the file size.

        Args:
            raster_path (str): The path to the input raster to be converted.
            index (int): The current index for naming the output byte raster.

        Returns:
            str: The file path to the byte raster output.
        """
        byte_raster_path = os.path.join(
            self.workflow_directory, f"byte_raster_{index}.tif"
        )
        params = {
            "INPUT": raster_path,
            "BAND": 1,
            "OUTPUT": byte_raster_path,
            "TYPE": 1,  # Byte format
        }
        processing.run("gdal:translate", params)
        return byte_raster_path

    def _combine_rasters_to_vrt(self, num_rasters: int) -> None:
        """
        Combine all the byte rasters into a single VRT file.

        Args:
            num_rasters (int): The number of rasters to combine into a VRT.
        """
        raster_paths = [
            os.path.join(self.workflow_directory, f"byte_raster_{i}.tif")
            for i in range(num_rasters)
        ]
        vrt_path = os.path.join(self.workflow_directory, "combined_rasters.vrt")
        params = {"INPUT": raster_paths, "OUTPUT": vrt_path}
        processing.run("gdal:buildvrt", params)
