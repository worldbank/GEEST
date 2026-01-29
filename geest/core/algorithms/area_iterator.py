# -*- coding: utf-8 -*-

"""📦 Area Iterator module.

This module contains functionality for area iterator.
"""

from typing import Iterator, Tuple

from qgis.core import Qgis, QgsFeatureRequest, QgsGeometry, QgsVectorLayer

from geest.utilities import log_message


class AreaIterator:
    """
    An iterator to yield sets of geometries from polygon, study_area_clip_polygons and bbox layers
    found in a GeoPackage file, along with a progress percentage.

    This iterator matches features across layers using the 'area_name' field rather than
    Feature IDs (FIDs), ensuring correct pairing across layers.

    Attributes:
        gpkg_path (str): The path to the GeoPackage file.

    Precondition:
        study_area_polygons (QgsVectorLayer): The vector layer containing polygons with 'area_name' field.
        study_area_clip_polygons (QgsVectorLayer): The vector layer containing polygons expanded to
            completely include the intersecting grid cells along the boundary, with matching 'area_name' field.
        study_area_bboxes (QgsVectorLayer): The vector layer containing bounding boxes with matching 'area_name' field.

        All three layers must have the 'area_name' attribute for matching.
        There should be a one-to-one correspondence between polygons and bounding boxes.
        Clip polygons may be missing for some areas; in such cases, the polygon geometry is used as a fallback.

    Example usage:
        To use the iterator, simply pass the path to the GeoPackage:

        ```python
        gpkg_path = '/path/to/your/geopackage.gpkg'
        area_iterator = AreaIterator(gpkg_path)

        for index, (current_area, clip_area, current_bbox, progress) in enumerate(
            area_iterator
        ):

            log_message(f"Area Name: {area_name}")
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
            raise ValueError("Failed to load 'study_area_polygons' layer from the GeoPackage.")

        if not self.clip_polygon_layer.isValid():
            log_message(
                "Error: 'study_area_clip_polygons' layer failed to load from the GeoPackage",
                tag="Geest",
                level=Qgis.Critical,
            )
            raise ValueError("Failed to load 'study_area_clip_polygons' layer from the GeoPackage.")

        if not self.bbox_layer.isValid():
            log_message(
                "Error: 'study_area_bboxes' layer failed to load from the GeoPackage",
                tag="Geest",
                level=Qgis.Critical,
            )
            raise ValueError("Failed to load 'study_area_bboxes' layer from the GeoPackage.")

        # Get the total number of polygon features for progress calculation
        self.total_features: int = self.polygon_layer.featureCount()

    def area_count(self) -> int:
        """
        Return the total number of areas to be processed.

        Returns:
            int: The total number of polygon features.
        """
        return self.total_features

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

            # Memory-efficient approach: use stored area attribute if available,
            # otherwise compute it (for backwards compatibility with older data)
            feature_areas = []
            has_area_field = "geom_area" in [f.name() for f in self.polygon_layer.fields()]

            for feature in self.polygon_layer.getFeatures():
                geom = feature.geometry()
                if geom and not geom.isEmpty():
                    # Use stored area if available (faster), otherwise compute
                    if has_area_field:
                        area = feature["geom_area"]
                        if area is None or area == 0:
                            area = geom.area()
                    else:
                        area = geom.area()
                    feature_areas.append((feature.id(), area))

            # Sort by area (ascending) - only IDs and areas in memory, not full features
            feature_areas.sort(key=lambda x: x[1])

            # Now iterate in sorted order, fetching features one at a time
            for index, (fid, _area) in enumerate(feature_areas):
                # Fetch the polygon feature by ID
                request = QgsFeatureRequest().setFilterFid(fid)
                polygon_feature = next(self.polygon_layer.getFeatures(request), None)
                if polygon_feature is None:
                    continue

                # Get the area_name from the polygon feature for matching
                # This is more reliable than FID matching
                area_name = polygon_feature["area_name"]

                # Query clip_polygon and bbox by area_name instead of FID
                # This ensures correct matching even when feature IDs don't align
                clip_request = QgsFeatureRequest().setFilterExpression(f"area_name = '{area_name}'")
                bbox_request = QgsFeatureRequest().setFilterExpression(f"area_name = '{area_name}'")

                clip_feature = next(self.clip_polygon_layer.getFeatures(clip_request), None)
                bbox_feature = next(self.bbox_layer.getFeatures(bbox_request), None)

                # Require bbox_feature but allow clip_feature to be missing
                if bbox_feature:
                    # Calculate the progress as the percentage of features processed
                    progress_percent: float = ((index + 1) / self.total_features) * 100

                    # Use clip_feature geometry if available, otherwise fall back to polygon geometry
                    clip_geom = clip_feature.geometry() if clip_feature else polygon_feature.geometry()

                    if not clip_feature:
                        log_message(
                            f"Info: No clip_polygon found for area '{area_name}', using polygon geometry as fallback",
                            tag="Geest",
                            level=Qgis.Info,
                        )

                    # Yield a tuple with polygon geometry, clip geometry, bbox geometry, and progress percentage
                    yield polygon_feature.geometry(), clip_geom, bbox_feature.geometry(), progress_percent

                else:
                    log_message(
                        f"Warning: No matching bbox feature found for area '{area_name}'",
                        tag="Geest",
                        level=Qgis.Warning,
                    )

        except Exception as e:
            log_message(
                f"Critical: Error during iteration - {str(e)}",
                tag="Geest",
                level=Qgis.Critical,
            )
