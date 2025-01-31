from qgis.core import (
    edit,
    Qgis,
    QgsCoordinateTransformContext,
    QgsFeature,
    QgsFeatureRequest,
    QgsFields,
    QgsField,
    QgsProcessingException,
    QgsSpatialIndex,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsWkbTypes,
)
import processing
from qgis.PyQt.QtCore import QVariant
from typing import List
from geest.utilities import log_message


def select_grid_cells(
    grid_layer: QgsVectorLayer,
    features_layer: QgsVectorLayer,
    output_path: str,
) -> QgsVectorLayer:
    """
    Select grid cells that intersect with features, count the number of intersecting features for each cell,
    and create a new grid layer with the count information. This supports features of any geometry type (points, lines, polygons).

    Args:
        grid_layer (QgsVectorLayer): The input grid layer containing polygon cells.
        features_layer (QgsVectorLayer): The input layer containing features (e.g., points, lines, polygons).
        output_path (str): The output path for the new grid layer with feature counts.

    Returns:
        QgsVectorLayer: A new layer with grid cells containing a count of intersecting features.
    """
    log_message(
        "Selecting grid cells that intersect with features and counting intersections.",
        tag="Geest",
        level=Qgis.Info,
    )

    # Create a spatial index for the grid layer to optimize intersection queries
    grid_index = QgsSpatialIndex(grid_layer.getFeatures())

    # Create a dictionary to hold the count of intersecting features for each grid cell ID
    grid_feature_counts = {}

    # Iterate over each feature and use the spatial index to find the intersecting grid cells
    for feature in features_layer.getFeatures():
        feature_geom = feature.geometry()

        # Use bounding box only for point geometries; otherwise, use the actual geometry for intersection checks
        if feature_geom.isEmpty():
            continue

        if feature_geom.type() == QgsWkbTypes.PointGeometry:
            # For point geometries, use bounding box to find intersecting grid cells
            intersecting_ids = grid_index.intersects(feature_geom.boundingBox())
        else:
            # For line and polygon geometries, check actual geometry against grid cells
            intersecting_ids = grid_index.intersects(
                feature_geom.boundingBox()
            )  # Initial rough filter
            log_message(
                f"{len(intersecting_ids)} rough intersections found.",
                tag="Geest",
                level=Qgis.Info,
            )
            intersecting_ids = [
                grid_id
                for grid_id in intersecting_ids
                if grid_layer.getFeature(grid_id).geometry().intersects(feature_geom)
            ]
            log_message(
                f"{len(intersecting_ids)} refined intersections found.",
                tag="Geest",
                level=Qgis.Info,
            )

        # Iterate over the intersecting grid cell IDs and count intersections
        for grid_id in intersecting_ids:
            if grid_id in grid_feature_counts:
                grid_feature_counts[grid_id] += 1
            else:
                grid_feature_counts[grid_id] = 1

    log_message(f"{len(grid_feature_counts)} intersections found.")

    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.fileEncoding = "UTF-8"
    options.layerName = "grid_with_feature_counts"

    # Define fields for the new layer: only 'id' and 'intersecting_features'
    fields = QgsFields()
    fields.append(QgsField("id", QVariant.Int))
    fields.append(QgsField("intersecting_features", QVariant.Int))
    # Will be used to hold the scaled value from 0-5
    fields.append(QgsField("value", QVariant.Int))

    writer = QgsVectorFileWriter.create(
        fileName=output_path,
        fields=fields,
        geometryType=grid_layer.wkbType(),
        srs=grid_layer.crs(),
        transformContext=QgsCoordinateTransformContext(),
        options=options,
    )
    if writer.hasError() != QgsVectorFileWriter.NoError:
        raise QgsProcessingException(
            f"Failed to create output layer: {writer.errorMessage()}"
        )

    # Select only grid cells based on the keys (grid IDs) in the grid_feature_counts dictionary
    request = QgsFeatureRequest().setFilterFids(list(grid_feature_counts.keys()))
    log_message(
        f"Looping over {len(grid_feature_counts.keys())} grid polygons",
        tag="Geest",
        level=Qgis.Info,
    )
    counter = 0
    for grid_feature in grid_layer.getFeatures(request):
        log_message(f"Writing Feature #{counter}")
        counter += 1
        new_feature = QgsFeature()
        new_feature.setGeometry(grid_feature.geometry())  # Use the original geometry

        # Set the 'id' and 'intersecting_features' attributes
        new_feature.setFields(fields)
        new_feature.setAttribute("id", grid_feature.id())  # Set the grid cell ID
        new_feature.setAttribute(
            "intersecting_features", grid_feature_counts[grid_feature.id()]
        )
        new_feature.setAttribute("value", None)

        # Write the feature to the new layer
        writer.addFeature(new_feature)

    del writer  # Finalize the writer and close the file

    log_message(
        f"Grid cells with feature counts saved to {output_path}",
        tag="Geest",
        level=Qgis.Info,
    )

    return QgsVectorLayer(
        f"{output_path}|layername=grid_with_feature_counts",
        "grid_with_feature_counts",
        "ogr",
    )


def assign_values_to_grid(grid_layer: QgsVectorLayer) -> QgsVectorLayer:
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
