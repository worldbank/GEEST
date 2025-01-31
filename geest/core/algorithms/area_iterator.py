from qgis.core import (
    QgsFeatureRequest,
    QgsVectorLayer,
    QgsGeometry,
    Qgis,
)
from typing import Iterator, Tuple
from geest.utilities import log_message


class AreaIterator:
    """
    An iterator to yield sets of geometries from polygon, study_area_clip_polygons and bbox layers
    found in a GeoPackage file, along with a progress percentage.

    Attributes:
        gpkg_path (str): The path to the GeoPackage file.

    Precondition:
        study_area_polygons (QgsVectorLayer): The vector layer containing polygons.
        study_area_clip_polygons (QgsVectorLayer): The vector layer containing polygons expanded to
            completely include the intersecting grid cells along the boundary.
        study_area_bboxes (QgsVectorLayer): The vector layer containing bounding boxes.

        There should be a one-to-one correspondence between the polygons and bounding boxes.

    Example usage:
        To use the iterator, simply pass the path to the GeoPackage:

        ```python
        gpkg_path = '/path/to/your/geopackage.gpkg'
        area_iterator = AreaIterator(gpkg_path)

        for index, (current_area, clip_area, current_bbox, progress) in enumerate(
            area_iterator
        ):

            log_message(f"Polygon ID: {id}")
            log_message(f"Polygon Geometry: {polygon_geometry.asWkt()}")
            log_message(f"Clip Polygon Geometry: {clip_geometry.asWkt()}")
            log_message(f"BBox Geometry: {bbox_geometry.asWkt()}")
            log_message(f"Progress: {progress_percent:.2f}%")
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
        self.clip_polygon_layer: QgsVectorLayer = QgsVectorLayer(
            f"{gpkg_path}|layername=study_area_clip_polygons",
            "study_area_clip_polygons",
            "ogr",
        )
        self.bbox_layer: QgsVectorLayer = QgsVectorLayer(
            f"{gpkg_path}|layername=study_area_bboxes", "study_area_bboxes", "ogr"
        )

        # Verify that both layers were loaded correctly
        if not self.polygon_layer.isValid():
            log_message(
                "Error: 'study_area_polygons' layer failed to load from the GeoPackage",
                tag="Geest",
                level=Qgis.Critical,
            )
            raise ValueError(
                "Failed to load 'study_area_polygons' layer from the GeoPackage."
            )

        if not self.clip_polygon_layer.isValid():
            log_message(
                "Error: 'study_area_clip_polygons' layer failed to load from the GeoPackage",
                tag="Geest",
                level=Qgis.Critical,
            )
            raise ValueError(
                "Failed to load 'study_area_clip_polygons' layer from the GeoPackage."
            )

        if not self.bbox_layer.isValid():
            log_message(
                "Error: 'study_area_bboxes' layer failed to load from the GeoPackage",
                tag="Geest",
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
            # Ensure all  layers have the same CRS
            if self.polygon_layer.crs() != self.bbox_layer.crs():
                log_message(
                    "Warning: CRS mismatch between polygon and bbox layers",
                    tag="Geest",
                    level=Qgis.Warning,
                )
                return

            if self.polygon_layer.crs() != self.clip_polygon_layer.crs():
                log_message(
                    "Warning: CRS mismatch between polygon and clip layers",
                    tag="Geest",
                    level=Qgis.Warning,
                )
                return

            # Iterate over each polygon feature and calculate progress

            # Sort polygon features by area in ascending order
            sorted_features = sorted(
                self.polygon_layer.getFeatures(), key=lambda f: f.geometry().area()
            )
            for index, polygon_feature in enumerate(sorted_features):
                polygon_id: int = polygon_feature.id()
                # Request the corresponding bbox feature based on the polygon's ID
                feature_request: QgsFeatureRequest = QgsFeatureRequest().setFilterFid(
                    polygon_id
                )
                clip_feature = next(
                    self.clip_polygon_layer.getFeatures(feature_request), None
                )
                bbox_feature = next(self.bbox_layer.getFeatures(feature_request), None)

                if bbox_feature and clip_feature:
                    # Calculate the progress as the percentage of features processed
                    progress_percent: float = ((index + 1) / self.total_features) * 100

                    # Yield a tuple with polygon geometry, bbox geometry, and progress percentage
                    yield polygon_feature.geometry(), clip_feature.geometry(), bbox_feature.geometry(), progress_percent

                else:
                    log_message(
                        f"Warning: No matching bbox or clip feature found for polygon ID {polygon_id}",
                        tag="Geest",
                        level=Qgis.Warning,
                    )

        except Exception as e:
            log_message(
                f"Critical: Error during iteration - {str(e)}",
                tag="Geest",
                level=Qgis.Critical,
            )
