# -*- coding: utf-8 -*-
"""📦 Features Per Cell Processor module.

This module contains functionality for features per cell processor.

Performance optimizations:
- Caches grid geometries upfront to avoid repeated getFeature() calls
- Uses prepared geometries for faster intersection tests
- Reduces logging overhead in inner loops
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
    QgsGeometry,
    QgsRectangle,
    QgsSpatialIndex,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QVariant

from geest.core.osm_downloaders import OSMDownloadType
from geest.core.workflows.mappings import CYCLEWAY_CLASSIFICATION, HIGHWAY_CLASSIFICATION
from geest.utilities import log_message, setting


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

    # Initialize variables for cleanup
    grid_index = None
    grid_feature_counts = None
    writer = None

    try:
        # Create a spatial index for the grid layer to optimize intersection queries
        grid_index = QgsSpatialIndex(grid_layer.getFeatures())

        # Create a dictionary to hold the count of intersecting features for each grid cell ID
        grid_feature_counts = {}
        counter = 0
        feature_count = features_layer.featureCount()
        log_interval = max(1, feature_count // 20)  # Log ~20 times during processing

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
                rough_count = len(intersecting_ids)

                # OPTIMIZATION: Use prepared geometry for faster intersection tests
                # This prepares the feature geometry once, then tests against each grid cell
                # Memory-efficient: doesn't cache grid geometries, fetches on demand
                prepared_geom = QgsGeometry.createGeometryEngine(feature_geom.constGet())
                prepared_geom.prepareGeometry()

                # Batch fetch grid features for better performance while staying memory-efficient
                request = QgsFeatureRequest().setFilterFids(intersecting_ids)
                intersecting_ids = [
                    grid_feature.id()
                    for grid_feature in grid_layer.getFeatures(request)
                    if prepared_geom.intersects(grid_feature.geometry().constGet())
                ]

                # Only log occasionally to reduce overhead
                if counter % log_interval == 0:
                    log_message(
                        f"Feature {counter}: {rough_count} rough → {len(intersecting_ids)} refined intersections",
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
            if feedback:
                feedback.setProgress((counter / feature_count) * 100.0)

        len_grid_ids = len(grid_feature_counts)
        log_message(f"{len_grid_ids} intersections found.")

        # OPTIMIZATION: Use batch writing with OGR for much faster GeoPackage creation
        # Instead of writing 2M features one-by-one, we batch them
        log_message(
            f"Writing {len_grid_ids} grid polygons to GeoPackage (batched)...",
            tag="Geest",
            level=Qgis.Info,
        )

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

        # Batch write features for better performance
        # Process in chunks to balance memory and I/O efficiency
        grid_ids = list(grid_feature_counts.keys())
        batch_size = 10000
        total_batches = (len_grid_ids + batch_size - 1) // batch_size

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len_grid_ids)
            batch_ids = grid_ids[start_idx:end_idx]

            # Fetch batch of grid features
            request = QgsFeatureRequest().setFilterFids(batch_ids)
            feature_batch = []

            for grid_feature in grid_layer.getFeatures(request):
                new_feature = QgsFeature()
                new_feature.setGeometry(grid_feature.geometry())
                new_feature.setFields(fields)
                new_feature.setAttribute("id", grid_feature.id())
                new_feature.setAttribute("intersecting_features", grid_feature_counts[grid_feature.id()])
                new_feature.setAttribute("value", None)
                feature_batch.append(new_feature)

            # Write entire batch at once
            writer.addFeatures(feature_batch)

            # Update progress bar and log periodically
            progress = ((batch_num + 1) / total_batches) * 100
            if feedback:
                feedback.setProgress(progress)
            if batch_num % 10 == 0 or batch_num == total_batches - 1:
                log_message(
                    f"Writing batch {batch_num + 1}/{total_batches} ({progress:.1f}%)",
                    tag="Geest",
                    level=Qgis.Info,
                )

            # Clear batch to free memory
            feature_batch.clear()

        # IMPORTANT: Delete writer BEFORE creating the return layer
        # to ensure the GeoPackage file is fully closed and unlocked
        del writer
        writer = None

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

    finally:
        # Explicit cleanup to release memory
        if writer:
            del writer
        if grid_index:
            del grid_index
        if grid_feature_counts:
            grid_feature_counts.clear()
            del grid_feature_counts


def assign_values_to_grid(grid_layer: QgsVectorLayer, feedback: QgsFeedback = None) -> QgsVectorLayer:
    """
    Assign values to grid cells based on the number of intersecting features.

    A value of 3 is assigned to cells that intersect with one feature, and a value of 5 is assigned to
    cells that intersect with more than one feature.

    Uses a single SQL UPDATE statement for maximum performance instead of
    updating features one-by-one.

    Args:
        grid_layer (QgsVectorLayer): The input grid layer containing polygon cells.
        feedback (QgsFeedback): Optional feedback object for progress reporting.

    Returns:
        QgsVectorLayer: The grid layer with values assigned to the 'value' field.
    """
    from osgeo import ogr

    # Extract the GeoPackage path from the layer source
    # Format is typically: "/path/to/file.gpkg|layername=layer_name"
    source = grid_layer.source()
    if "|" in source:
        gpkg_path = source.split("|")[0]
    else:
        gpkg_path = source

    feature_count = grid_layer.featureCount()
    log_message(
        f"Assigning values to {feature_count} grid cells using SQL...",
        tag="Geest",
        level=Qgis.Info,
    )

    # Use OGR to execute SQL - this has SpatiaLite functions available
    # for any GeoPackage triggers that need them
    try:
        ds = ogr.Open(gpkg_path, update=1)
        if ds is None:
            raise Exception(f"Could not open GeoPackage: {gpkg_path}")

        # Single UPDATE statement with CASE expression
        sql = """
            UPDATE grid_with_feature_counts
            SET value = CASE
                WHEN intersecting_features = 1 THEN 3
                WHEN intersecting_features > 1 THEN 5
                ELSE NULL
            END
        """
        ds.ExecuteSQL(sql)
        ds = None  # Close the datasource

        log_message(
            "SQL UPDATE completed",
            tag="Geest",
            level=Qgis.Info,
        )

        # Reload the layer to see the changes
        grid_layer.reload()

        if feedback:
            feedback.setProgress(100.0)

    except Exception as e:
        log_message(
            f"SQL UPDATE failed: {e}",
            tag="Geest",
            level=Qgis.Critical,
        )
        raise e

    return grid_layer


def select_grid_cells_and_assign_transport_score(
    osm_transport_type: OSMDownloadType,
    grid_layer: QgsVectorLayer,
    features_layer: QgsVectorLayer,
    output_path: str,
    feedback: QgsFeedback = None,
    analysis_scale: str = None,
) -> QgsVectorLayer:
    """
    Select grid cells that intersect with features, and assign a value
    based on the most beneficial road type intersecting the cell.

    This function checks BOTH highway and cycleway attributes on each feature
    and assigns the highest score from either attribute type.

    Args:
        osm_transport_type (OSMDownloadType): The type of OSM transport data (road or cycle).
        grid_layer (QgsVectorLayer): The input grid layer containing polygon cells.
        features_layer (QgsVectorLayer): The input OSM layer containing features with highway and/or cycleway attributes.
        output_path (str): The output path for the new grid layer with transport scores.
        feedback (QgsFeedback): Optional feedback object for progress reporting.

    Returns:
        QgsVectorLayer: A new layer with grid cells containing the highest score from the intersecting features.

    Raises:
        Exception: If there are issues creating spatial index or processing features.
    """

    log_message(
        "Selecting grid cells that intersect with features and assigning best transport score (highway or cycleway).",
        tag="Geest",
        level=Qgis.Info,
    )

    # Create a spatial index for the grid layer to optimize intersection queries
    grid_index = QgsSpatialIndex(grid_layer.getFeatures())

    # Create dictionaries to hold the best scores and their source types for each grid cell ID
    grid_most_beneficial_road_scores = {}
    grid_most_beneficial_road_types = {}
    counter = 0
    feature_count = features_layer.featureCount()
    verbose_mode = int(setting(key="verbose_mode", default=0))
    log_interval = max(1, feature_count // 20)  # Log ~20 times during processing

    # Build mapping table based on analysis scale (fallback to existing table if not set)
    scale_key = analysis_scale or "national"
    cycleway_config = CYCLEWAY_CLASSIFICATION.get(scale_key, CYCLEWAY_CLASSIFICATION["national"])
    lookup_table = {}
    for road_type, score in HIGHWAY_CLASSIFICATION.items():
        lookup_table[f"highway_{road_type}"] = score
    for cycle_type, score in cycleway_config.items():
        lookup_table[f"cycleway_{cycle_type}"] = score

    # Check which fields exist ONCE before the loop (for efficiency)
    field_names = features_layer.fields().names()
    has_highway_field = "highway" in field_names
    has_cycleway_field = "cycleway" in field_names

    # Iterate over each feature and use the spatial index to find the intersecting grid cells
    for feature in features_layer.getFeatures():
        feature_geom = feature.geometry()

        if feature_geom.isEmpty():
            continue

        # Check for both highway and cycleway attributes and use the best score
        road_score = 0
        road_type = None

        # Check highway attribute if it exists
        if has_highway_field:
            highway_type = feature.attribute("highway")
            if highway_type:  # Not None and not empty string
                lookup_key = f"highway_{highway_type}"
                highway_score = lookup_table.get(lookup_key, 0)
                if verbose_mode:
                    log_message(
                        f"highway_type='{highway_type}' → lookup_key='{lookup_key}' → score={highway_score}",
                        tag="Geest",
                        level=Qgis.Info,
                    )
                if highway_score > road_score:
                    road_score = highway_score
                    road_type = lookup_key

        # Check cycleway attribute if it exists
        if has_cycleway_field:
            cycleway_type = feature.attribute("cycleway")
            if cycleway_type:  # Not None and not empty string
                lookup_key = f"cycleway_{cycleway_type}"
                cycleway_score = lookup_table.get(lookup_key, 0)
                if verbose_mode:
                    log_message(
                        f"cycleway_type='{cycleway_type}' → lookup_key='{lookup_key}' → score={cycleway_score}",
                        tag="Geest",
                        level=Qgis.Info,
                    )
                if cycleway_score > road_score:
                    road_score = cycleway_score
                    road_type = lookup_key

        # Skip features with no valid score
        if road_score == 0 or road_type is None:
            if verbose_mode:
                log_message(
                    f"Skipping feature: road_score={road_score}, road_type={road_type}", tag="Geest", level=Qgis.Info
                )
            continue

        # OPTIMIZATION: Segment-based spatial index query for linestrings
        # Instead of one huge bbox for the whole line, query smaller bboxes per segment
        # This dramatically reduces false positives for long diagonal roads
        abstract_geom = feature_geom.constGet()
        if feature_geom.type() == QgsWkbTypes.LineGeometry and abstract_geom is not None:
            # Get vertices and query each segment's bbox
            vertices = list(abstract_geom.vertices())
            candidate_set = set()
            for i in range(len(vertices) - 1):
                v1, v2 = vertices[i], vertices[i + 1]
                segment_bbox = QgsRectangle(
                    min(v1.x(), v2.x()), min(v1.y(), v2.y()), max(v1.x(), v2.x()), max(v1.y(), v2.y())
                )
                candidate_set.update(grid_index.intersects(segment_bbox))
            intersecting_ids = list(candidate_set)
        else:
            # Fallback for non-line geometries
            intersecting_ids = grid_index.intersects(feature_geom.boundingBox())

        rough_count = len(intersecting_ids)

        # OPTIMIZATION: Skip cells that already have max score (5)
        # No point checking intersection if we can't improve the score
        candidates_to_check = [
            grid_id for grid_id in intersecting_ids if grid_most_beneficial_road_scores.get(grid_id, 0) < road_score
        ]
        skipped_count = rough_count - len(candidates_to_check)

        if not candidates_to_check:
            # All candidates already have equal or better scores - skip entirely
            counter += 1
            if feedback:
                feedback.setProgress((counter / feature_count) * 100.0)
            continue

        # OPTIMIZATION: Use prepared geometry for faster intersection tests
        # Memory-efficient: doesn't cache grid geometries, fetches on demand via batch request
        prepared_geom = QgsGeometry.createGeometryEngine(feature_geom.constGet())
        prepared_geom.prepareGeometry()

        # Batch fetch grid features for better performance while staying memory-efficient
        request = QgsFeatureRequest().setFilterFids(candidates_to_check)
        intersecting_ids = [
            grid_feature.id()
            for grid_feature in grid_layer.getFeatures(request)
            if prepared_geom.intersects(grid_feature.geometry().constGet())
        ]

        # Log progress periodically (not every feature to reduce overhead)
        if counter % log_interval == 0 or verbose_mode:
            log_message(
                f"Feature {counter}/{feature_count}: {rough_count} candidates, {skipped_count} skipped, {len(intersecting_ids)} intersect ({road_type})",
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
                    grid_most_beneficial_road_types[grid_id] = road_type
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
                grid_most_beneficial_road_types[grid_id] = road_type
        counter += 1
        feedback.setProgress((counter / feature_count) * 100.0)  # We just use nominal intervals for progress updates

    # Summary statistics
    total_cells = len(grid_most_beneficial_road_scores)
    score_counts = {}
    for score in grid_most_beneficial_road_scores.values():
        score_counts[score] = score_counts.get(score, 0) + 1
    max_score_cells = score_counts.get(5, 0)

    log_message(f"{total_cells} grid cells scored. Distribution: {score_counts}", tag="Geest", level=Qgis.Info)
    percent_max = 100 * max_score_cells / max(1, total_cells)
    log_message(
        f"Cells with max score (5): {max_score_cells} ({percent_max:.1f}%)",
        tag="Geest",
        level=Qgis.Info,
    )

    # OPTIMIZATION: Use batch writing for much faster GeoPackage creation
    len_grid_ids = len(grid_most_beneficial_road_scores)
    log_message(
        f"Writing {len_grid_ids} grid polygons to GeoPackage (batched)...",
        tag="Geest",
        level=Qgis.Info,
    )

    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.fileEncoding = "UTF-8"
    options.layerName = "grid_with_feature_counts"

    # Define fields for the new layer: 'id', 'value', and 'road_type'
    fields = QgsFields()
    fields.append(QgsField("id", QVariant.Int))
    # Will be used to hold the scaled value from 0-5
    fields.append(QgsField("value", QVariant.Int))
    # Will be used to track which road/cycleway type gave the best score
    fields.append(QgsField("road_type", QVariant.String))

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

    # Batch write features for better performance
    grid_ids = list(grid_most_beneficial_road_scores.keys())
    batch_size = 10000
    total_batches = (len_grid_ids + batch_size - 1) // batch_size

    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len_grid_ids)
        batch_ids = grid_ids[start_idx:end_idx]

        # Fetch batch of grid features
        request = QgsFeatureRequest().setFilterFids(batch_ids)
        feature_batch = []

        for grid_feature in grid_layer.getFeatures(request):
            new_feature = QgsFeature()
            new_feature.setGeometry(grid_feature.geometry())
            new_feature.setFields(fields)
            grid_id = grid_feature.id()
            new_feature.setAttribute("id", grid_id)
            new_feature.setAttribute("value", grid_most_beneficial_road_scores[grid_id])
            new_feature.setAttribute("road_type", grid_most_beneficial_road_types.get(grid_id, "unknown"))
            feature_batch.append(new_feature)

        # Write entire batch at once
        writer.addFeatures(feature_batch)

        # Update progress bar and log periodically
        progress = ((batch_num + 1) / total_batches) * 100
        if feedback:
            feedback.setProgress(progress)
        if batch_num % 10 == 0 or batch_num == total_batches - 1:
            log_message(
                f"Writing batch {batch_num + 1}/{total_batches} ({progress:.1f}%)",
                tag="Geest",
                level=Qgis.Info,
            )

        # Clear batch to free memory
        feature_batch.clear()

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

    if osm_transport_type == OSMDownloadType.ACTIVE_TRANSPORT:
        cycleway_config = CYCLEWAY_CLASSIFICATION["national"]
        lookup_table = {}
        for road_type, score in HIGHWAY_CLASSIFICATION.items():
            lookup_table[f"highway_{road_type}"] = score
        for cycle_type, score in cycleway_config.items():
            lookup_table[f"cycleway_{cycle_type}"] = score
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
