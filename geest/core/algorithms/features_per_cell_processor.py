# -*- coding: utf-8 -*-
"""📦 Features Per Cell Processor module.

This module contains functionality for features per cell processor.
"""
from qgis import processing  # noqa: F401
from qgis.core import (
    Qgis,
    QgsCoordinateTransformContext,
    QgsFeature,
    QgsFeatureRequest,
    QgsFeedback,
    QgsField,
    QgsFields,
    QgsSpatialIndex,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsWkbTypes,
    edit,
)
from qgis.PyQt.QtCore import QVariant

from geest.core.osm_downloaders import OSMDownloadType
from geest.utilities import log_message, setting

highway_lookup_table = {
    "residential": 4,
    "living_street": 4,
    "pedestrian": 4,
    "footway": 4,
    "steps": 4,
    "tertiary": 3,
    "tertiary_link": 3,
    "cycleway": 3,
    "path": 3,
    "secondary": 2,
    "unclassified": 2,
    "service": 2,
    "road": 2,
    "bridleway": 2,
    "secondary_link": 2,
    "track": 1,
    "primary": 1,
    "primary_link": 1,
    "motorway": 0,
    "trunk": 0,
    "motorway_link": 0,
    "trunk_link": 0,
    "bus_guideway": -1,
    "escape": -1,
    "raceway": -1,
    "construction": -1,
    "proposed": -1,
}
cycleway_lookup_table = {
    "lane": 3,
    "shared_lane": 3,
    "share_busway": 3,
    "track": 3,
    "separate": 3,
    "crossing": 3,
    "shoulder": 3,
    "link": 3,
}


def select_grid_cells_and_count_features(
    grid_layer: QgsVectorLayer,
    features_layer: QgsVectorLayer,
    output_path: str,
    feedback: QgsFeedback = None,
) -> QgsVectorLayer:
    """
    Select grid cells that intersect with features, count the number of intersecting features for each cell,
    and create a new grid layer with the count information. This supports features of any geometry type (points, lines, polygons).

    Args:
        grid_layer (QgsVectorLayer): The input grid layer containing polygon cells.
        features_layer (QgsVectorLayer): The input layer containing features (e.g., points, lines, polygons).
        output_path (str): The output path for the new grid layer with feature counts.
        feedback (QgsFeedback): Optional feedback object for progress reporting.

    Returns:
        QgsVectorLayer: A new layer with grid cells containing a count of intersecting features.

    Raises:
        Exception: If there are issues creating spatial index or processing features.
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
    counter = 0
    feature_count = features_layer.featureCount()
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
            intersecting_ids = grid_index.intersects(feature_geom.boundingBox())  # Initial rough filter
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
        counter += 1
        feedback.setProgress((counter / feature_count) * 100.0)  # We just use nominal intervals for progress updates

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
        raise Exception(f"Failed to create output layer: {writer.errorMessage()}")

    # Select only grid cells based on the keys (grid IDs) in the grid_feature_counts dictionary
    request = QgsFeatureRequest().setFilterFids(list(grid_feature_counts.keys()))
    log_message(
        f"Looping over {len(grid_feature_counts.keys())} grid polygons",
        tag="Geest",
        level=Qgis.Info,
    )

    for grid_feature in grid_layer.getFeatures(request):
        log_message(f"Writing Feature #{counter}")
        counter += 1
        new_feature = QgsFeature()
        new_feature.setGeometry(grid_feature.geometry())  # Use the original geometry

        # Set the 'id' and 'intersecting_features' attributes
        new_feature.setFields(fields)
        new_feature.setAttribute("id", grid_feature.id())  # Set the grid cell ID
        new_feature.setAttribute("intersecting_features", grid_feature_counts[grid_feature.id()])
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


def assign_values_to_grid(grid_layer: QgsVectorLayer, feedback: QgsFeedback = None) -> QgsVectorLayer:
    """
    Assign values to grid cells based on the number of intersecting features.

    A value of 3 is assigned to cells that intersect with one feature, and a value of 5 is assigned to
    cells that intersect with more than one feature.

    Args:
        grid_layer (QgsVectorLayer): The input grid layer containing polygon cells.
        feedback (QgsFeedback): Optional feedback object for progress reporting.

    Returns:
        QgsVectorLayer: The grid layer with values assigned to the 'value' field.
    """
    feature_count = grid_layer.featureCount()
    counter = 0
    with edit(grid_layer):
        for feature in grid_layer.getFeatures():
            intersecting_features = feature["intersecting_features"]
            if intersecting_features == 1:
                feature["value"] = 3
            elif intersecting_features > 1:
                feature["value"] = 5
            grid_layer.updateFeature(feature)
            counter += 1
            if feedback:
                feedback.setProgress((counter / feature_count) * 100.0)
    return grid_layer


def select_grid_cells_and_assign_transport_score(
    osm_transport_type: OSMDownloadType,
    grid_layer: QgsVectorLayer,
    features_layer: QgsVectorLayer,
    output_path: str,
    feedback: QgsFeedback = None,
) -> QgsVectorLayer:
    """
    Select grid cells that intersect with features, and assign a value
    based on the most beneficial road type intersecting the cell.

    Args:
        osm_transport_type (OSMDownloadType): The type of OSM transport data to use for scoring.
        grid_layer (QgsVectorLayer): The input grid layer containing polygon cells.
        features_layer (QgsVectorLayer): The input OSM Roads layer containing features (e.g., lines).
        output_path (str): The output path for the new grid layer with transport scores.
        feedback (QgsFeedback): Optional feedback object for progress reporting.

    Returns:
        QgsVectorLayer: A new layer with grid cells containing the highest score from the intersecting features.

    Raises:
        Exception: If there are issues creating spatial index or processing features.
        ValueError: If the OSM transport type is unsupported.
    """

    log_message(
        "Selecting grid cells that intersect with features and assigning a score.",
        tag="Geest",
        level=Qgis.Info,
    )

    if osm_transport_type == OSMDownloadType.CYCLE:
        lookup_table = cycleway_lookup_table
    elif osm_transport_type == OSMDownloadType.ROAD:
        lookup_table = highway_lookup_table
    else:
        raise ValueError(f"Unsupported OSM transport type: {osm_transport_type}")

    # Create a spatial index for the grid layer to optimize intersection queries
    grid_index = QgsSpatialIndex(grid_layer.getFeatures())

    # Create a dictionary to hold the count of intersecting features for each grid cell ID
    grid_most_beneficial_road_scores = {}
    counter = 0
    feature_count = features_layer.featureCount()
    verbose_mode = int(setting(key="verbose_mode", default=0))
    # Iterate over each feature and use the spatial index to find the intersecting grid cells
    for feature in features_layer.getFeatures():
        feature_geom = feature.geometry()
        road_type = feature["highway"]
        road_score = lookup_table.get(road_type, 0)  # Default to
        if feature_geom.isEmpty():
            continue

        # Check actual geometry against grid cells
        intersecting_ids = grid_index.intersects(feature_geom.boundingBox())  # Initial rough filter

        if verbose_mode:
            log_message(
                f"Finding intersections for road type '{road_type}' with score {road_score}.",
                tag="Geest",
                level=Qgis.Info,
            )
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
        if verbose_mode:
            log_message(
                f"{len(intersecting_ids)} refined intersections found.",
                tag="Geest",
                level=Qgis.Info,
            )

        # Iterate over the intersecting grid cell IDs and count intersections
        for grid_id in intersecting_ids:
            if grid_id in grid_most_beneficial_road_scores:
                # Only update if the new road score is higher than the existing one
                if road_score > grid_most_beneficial_road_scores[grid_id]:
                    if verbose_mode:
                        log_message(f"Promoting score {road_score} to grid ID {grid_id}.", tag="Geest", level=Qgis.Info)
                    grid_most_beneficial_road_scores[grid_id] = road_score
                else:
                    if verbose_mode:
                        log_message(
                            f"Existing score {grid_most_beneficial_road_scores[grid_id]} for grid ID {grid_id} is higher than or equal to new score {road_score}, not updating.",
                            tag="Geest",
                            level=Qgis.Info,
                        )
            else:
                if verbose_mode:
                    log_message(
                        "Grid cell not found in list of most beneficial scores, assigning new score.",
                        tag="Geest",
                        level=Qgis.Info,
                    )
                    log_message(f"Assigning score {road_score} to grid ID {grid_id}.", tag="Geest", level=Qgis.Info)
                grid_most_beneficial_road_scores[grid_id] = road_score
        counter += 1
        feedback.setProgress((counter / feature_count) * 100.0)  # We just use nominal intervals for progress updates

    log_message(f"{len(grid_most_beneficial_road_scores)} intersections found.")

    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.fileEncoding = "UTF-8"
    options.layerName = "grid_with_feature_counts"

    # Define fields for the new layer: only 'id' and 'intersecting_features'
    fields = QgsFields()
    fields.append(QgsField("id", QVariant.Int))
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
        raise Exception(f"Failed to create output layer: {writer.errorMessage()}")

    # Select only grid cells based on the keys (grid IDs) in the grid_feature_counts dictionary
    request = QgsFeatureRequest().setFilterFids(list(grid_most_beneficial_road_scores.keys()))
    log_message(
        f"Looping over {len(grid_most_beneficial_road_scores.keys())} grid polygons",
        tag="Geest",
        level=Qgis.Info,
    )

    for grid_feature in grid_layer.getFeatures(request):
        # log_message(f"Writing Feature #{counter}")
        counter += 1
        new_feature = QgsFeature()
        new_feature.setGeometry(grid_feature.geometry())  # Use the original geometry

        # Set the 'id' and 'intersecting_features' attributes
        new_feature.setFields(fields)
        new_feature.setAttribute("id", grid_feature.id())  # Set the grid cell ID
        new_feature.setAttribute("value", grid_most_beneficial_road_scores[grid_feature.id()])

        # Write the feature to the new layer
        writer.addFeature(new_feature)

    del writer  # Finalize the writer and close the file

    log_message(
        f"Grid cells with OSM feature scores saved to {output_path}",
        tag="Geest",
        level=Qgis.Info,
    )

    return QgsVectorLayer(
        # Note the output is a Parquet file, not a geopackage
        # so there is nothing like |layername=...
        f"{output_path}",
        "grid_with_feature_scores",
        "ogr",
    )


def osm_mapping_table(osm_transport_type: OSMDownloadType) -> str:
    """
    Returns an HTML table as a string that maps OSM transport types to their scores.

    Args:
        osm_transport_type (OSMDownloadType): The type of OSM transport data.

    Returns:
        str: An HTML table as a string mapping transport types to scores.

    Raises:
        ValueError: If the OSM transport type is unsupported.
    """

    if osm_transport_type == OSMDownloadType.CYCLE:
        lookup_table = cycleway_lookup_table
    elif osm_transport_type == OSMDownloadType.ROAD:
        lookup_table = highway_lookup_table
    else:
        raise ValueError(f"Unsupported OSM transport type: {osm_transport_type}")

    # Prepare data for column wrapping
    items = list(lookup_table.items())
    max_rows = 10
    num_columns = (len(items) + max_rows - 1) // max_rows

    # Split items into columns
    columns = []
    for col in range(num_columns):
        start = col * max_rows
        end = start + max_rows
        columns.append(items[start:end])

    # Build HTML table
    table_html = '<table border="1" style="border-collapse:collapse;">\n'
    # Header row
    table_html += "<tr>"
    for col in range(num_columns):
        table_html += "<th>Type</th><th>Score</th>"
    table_html += "</tr>\n"

    # Data rows
    for row in range(max_rows):
        table_html += "<tr>"
        for col in columns:
            if row < len(col):
                k, v = col[row]
                table_html += f"<td>{k}</td><td>{v}</td>"
            else:
                table_html += "<td></td><td></td>"
        table_html += "</tr>\n"
    table_html += "</table>"

    return table_html
