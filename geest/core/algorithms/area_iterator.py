from qgis.core import (
    QgsFeatureRequest,
    QgsMessageLog,
    QgsVectorLayer,
    QgsProject,
    QgsGeometry,
    Qgis,
)
from typing import Iterator, Tuple


class AreaIterator:
    """
    An iterator to yield pairs of geometries from polygon and bbox layers
    found in a GeoPackage file, along with a progress percentage.

    Attributes:
        gpkg_path (str): The path to the GeoPackage file.

    Precondition:
        study_area_polygons (QgsVectorLayer): The vector layer containing polygons.
        study_area_bboxes (QgsVectorLayer): The vector layer containing bounding boxes.

        There should be a one-to-one correspondence between the polygons and bounding boxes.

    Example usage:
        To use the iterator, simply pass the path to the GeoPackage:

        ```python
        gpkg_path = '/path/to/your/geopackage.gpkg'
        area_iterator = AreaIterator(gpkg_path)

        for polygon_geometry, bbox_geometry, progress_percent in area_iterator:
            QgsMessageLog.logMessage(f"Polygon Geometry: {polygon_geometry.asWkt()}", 'Geest')
            QgsMessageLog.logMessage(f"BBox Geometry: {bbox_geometry.asWkt()}", 'Geest')
            QgsMessageLog.logMessage(f"Progress: {progress_percent:.2f}%", 'Geest')
        ```
    """

    def __init__(self, gpkg_path: str) -> None:
        """
        Initialize the AreaIterator with the path to the GeoPackage.

        Args:
            gpkg_path (str): The file path to the GeoPackage.
        """
        self.gpkg_path = gpkg_path

        # Load the polygon and bbox layers from the GeoPackage
        self.polygon_layer: QgsVectorLayer = QgsVectorLayer(
            f"{gpkg_path}|layername=study_area_polygons", "study_area_polygons", "ogr"
        )
        self.bbox_layer: QgsVectorLayer = QgsVectorLayer(
            f"{gpkg_path}|layername=study_area_bboxes", "study_area_bboxes", "ogr"
        )

        # Verify that both layers were loaded correctly
        if not self.polygon_layer.isValid():
            QgsMessageLog.logMessage(
                "Error: 'study_area_polygons' layer failed to load from the GeoPackage",
                "Geest",
                level=Qgis.Critical,
            )
            raise ValueError(
                "Failed to load 'study_area_polygons' layer from the GeoPackage."
            )

        if not self.bbox_layer.isValid():
            QgsMessageLog.logMessage(
                "Error: 'study_area_bboxes' layer failed to load from the GeoPackage",
                "Geest",
                level=Qgis.Critical,
            )
            raise ValueError(
                "Failed to load 'study_area_bboxes' layer from the GeoPackage."
            )

        # Get the total number of polygon features for progress calculation
        self.total_features: int = self.polygon_layer.featureCount()

    def __iter__(self) -> Iterator[Tuple[QgsGeometry, QgsGeometry, float]]:
        """
        Iterator that yields pairs of geometries from the polygon layer and the corresponding bbox layer,
        along with a progress percentage.

        Yields:
            Iterator[Tuple[QgsGeometry, QgsGeometry, float]]: Yields a tuple of polygon and bbox geometries,
            along with a progress value representing the percentage of the iteration completed.
        """
        try:
            # Ensure both layers have the same CRS
            if self.polygon_layer.crs() != self.bbox_layer.crs():
                QgsMessageLog.logMessage(
                    "Warning: CRS mismatch between polygon and bbox layers",
                    "Geest",
                    level=Qgis.Warning,
                )
                return

            # Iterate over each polygon feature and calculate progress
            for index, polygon_feature in enumerate(self.polygon_layer.getFeatures()):
                polygon_id: int = polygon_feature.id()

                # Request the corresponding bbox feature based on the polygon's ID
                bbox_request: QgsFeatureRequest = QgsFeatureRequest().setFilterFid(
                    polygon_id
                )
                bbox_feature = next(self.bbox_layer.getFeatures(bbox_request), None)

                if bbox_feature:
                    # Calculate the progress as the percentage of features processed
                    progress_percent: float = ((index + 1) / self.total_features) * 100

                    # Yield a tuple with polygon geometry, bbox geometry, and progress percentage
                    yield polygon_feature.geometry(), bbox_feature.geometry(), progress_percent

                else:
                    QgsMessageLog.logMessage(
                        f"Warning: No matching bbox found for polygon ID {polygon_id}",
                        "Geest",
                        level=Qgis.Warning,
                    )

        except Exception as e:
            QgsMessageLog.logMessage(
                f"Critical: Error during iteration - {str(e)}",
                "Geest",
                level=Qgis.Critical,
            )
