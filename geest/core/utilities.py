# coding=utf-8

"""Utilities for GeoE3."""

__copyright__ = "Copyright 2022, Tim Sutton"
__license__ = "GPL version 3"
__email__ = "tim@kartoza.com"
__revision__ = "$Format:%H$"

# -----------------------------------------------------------
# Copyright (C) 2022 Tim Sutton
# -----------------------------------------------------------
# Licensed under the terms of GNU GPL 3
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# ---------------------------------------------------------------------

import os

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsLayerTreeGroup,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.utils import iface

from ..utilities import log_message
from .json_tree_item import JsonTreeItem


def extent_mollweide(working_directory, log_message=print):
    """
    Get the study area bbox from the project working directory's study_area.gpkg, compute the extent,
    reproject to Mollweide (ESRI:54009), and return the extent in Mollweide projection.
    """
    extent_mollweide = None
    try:
        study_area_path = os.path.join(working_directory, "study_area", "study_area.gpkg")
        log_message(f"Looking for study area layer: {study_area_path}")
        if os.path.exists(study_area_path):
            log_message(f"Found study area layer: {study_area_path}")
            layer = QgsVectorLayer(study_area_path, "study_area", "ogr")
            if layer.isValid():
                log_message("Study area layer is valid")
            else:
                log_message("Study area layer is NOT valid", level=Qgis.Critical)
            log_message(f"Study area layer has {layer.featureCount()} features")
            if layer.isValid() and layer.featureCount() > 0:
                extent = layer.extent()
                log_message(f"Study area bbox in layer CRS: {extent.toString()}")
                src_crs = layer.crs()
                log_message(f"Study area layer CRS: {src_crs.authid()}")
                dst_crs = QgsCoordinateReferenceSystem("ESRI:54009")  # Mollweide needed for ghsl
                transform = QgsCoordinateTransform(src_crs, dst_crs, QgsProject.instance())
                extent_mollweide = transform.transformBoundingBox(extent)
                log_message(f"Study area bbox in Mollweide: {extent_mollweide}")
    except Exception as e:
        log_message(f"Failed to compute/reproject study area bbox: {e}", tag="GeoE3", level=Qgis.Warning)
    return extent_mollweide


def add_to_map(
    item: JsonTreeItem,
    key: str = "result_file",
    layer_name: str = None,
    qml_key: str = None,
    group: str = "GeoE3",
):
    """Add the item to the map."""
    log_message(item.attributesAsMarkdown())
    layer_uri = item.attribute(f"{key}")
    log_message(f"Adding {layer_uri} for key {key} to map")
    if layer_uri:
        if not layer_name:
            layer_name = item.data(0)

        if "gpkg" in layer_uri:
            log_message(f"Adding GeoPackage layer: {layer_name}")
            layer = QgsVectorLayer(layer_uri, layer_name, "ogr")
            if qml_key:
                qml_path = item.attribute(qml_key)
                if qml_path:
                    result = layer.loadNamedStyle(qml_path)  # noqa: F841
                    del result
        else:
            log_message(f"Adding raster layer: {layer_name}")
            layer = QgsRasterLayer(layer_uri, layer_name)

        if not layer.isValid():
            log_message(
                f"Layer {layer_name} is invalid and cannot be added.",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            return

        project = QgsProject.instance()

        # Check if 'GeoE3' group exists, otherwise create it
        root = project.layerTreeRoot()
        geoe3_group = root.findGroup(group)
        if geoe3_group is None:
            geoe3_group = root.insertGroup(0, group)  # Insert at the top of the layers panel
            geoe3_group.setIsMutuallyExclusive(True)  # Make the group mutually exclusive

        # Traverse the tree view structure to determine the appropriate subgroup based on paths
        path_list = item.getPaths()
        parent_group = geoe3_group
        # truncate the last item from the path list
        # as we want to add the layer to the group
        # that is the parent of the layer
        path_list = path_list[:-1]

        for path in path_list:
            sub_group = parent_group.findGroup(path)
            if sub_group is None:
                sub_group = parent_group.addGroup(path)
                sub_group.setIsMutuallyExclusive(True)  # Make each subgroup mutually exclusive

            parent_group = sub_group

        # Check if a layer with the same data source exists in the correct group
        existing_layer = None
        layer_tree_layer = None
        for child in parent_group.children():
            if isinstance(child, QgsLayerTreeGroup):
                continue
            if child.layer().source() == layer_uri:
                existing_layer = child.layer()
                layer_tree_layer = child
                break

        # If the layer exists, refresh it instead of removing and re-adding
        if existing_layer is not None:
            log_message(
                f"Refreshing existing layer: {existing_layer.name()}",
                tag="GeoE3",
                level=Qgis.Info,
            )
            # Make the layer visible
            layer_tree_layer.setItemVisibilityChecked(True)
            existing_layer.reload()
        else:
            # Add the new layer to the appropriate subgroup
            QgsProject.instance().addMapLayer(layer, False)
            layer_tree_layer = parent_group.addLayer(layer)
            layer_tree_layer.setExpanded(False)  # Collapse the legend for the layer by default
            log_message(f"Added layer: {layer.name()} to group: {parent_group.name()}")

        # Ensure the layer and its parent groups are visible
        current_group = parent_group
        while current_group is not None:
            current_group.setExpanded(True)  # Expand the group
            current_group.setItemVisibilityChecked(True)  # Set the group to be visible
            current_group = current_group.parent()

        # Set the layer itself to be visible
        layer_tree_layer.setItemVisibilityChecked(True)

        # Invalidate cached tiles for this layer and force an immediate canvas redraw
        repaint_layer = existing_layer if existing_layer is not None else layer
        repaint_layer.triggerRepaint()
        iface.mapCanvas().refresh()

        log_message(
            f"Layer {layer.name()} and its parent groups are now visible.",
            tag="GeoE3",
            level=Qgis.Info,
        )


def add_grid_layer_to_map(
    item: "JsonTreeItem",
    column_name: str,
    working_directory: str,
    layer_name: str = None,
    group: str = "GeoE3",
):
    """Add a styled grid layer to the map for a specific column.

    This function creates a layer from study_area_grid and applies the
    indicator-vector-template.qml style with the column name substituted.

    Args:
        item: The tree item (indicator/factor/dimension) to display.
        column_name: The column in study_area_grid to symbolize.
        working_directory: Path to the working directory containing study_area.gpkg.
        layer_name: Optional display name for the layer. Defaults to item name.
        group: The top-level group name. Defaults to "GeoE3".
    """
    import tempfile

    from geest.utilities import resources_path

    log_message(f"add_grid_layer_to_map called with column: {column_name}")
    log_message(f"Working directory: {working_directory}")

    if not working_directory:
        log_message(
            "Working directory is not set. Cannot add grid layer.",
            tag="GeoE3",
            level=Qgis.Warning,
        )
        return

    # Construct the GeoPackage path
    gpkg_path = os.path.join(working_directory, "study_area", "study_area.gpkg")
    if not os.path.exists(gpkg_path):
        log_message(
            f"GeoPackage not found: {gpkg_path}",
            tag="GeoE3",
            level=Qgis.Warning,
        )
        return

    # Create layer URI for study_area_grid
    layer_uri = f"{gpkg_path}|layername=study_area_grid"

    if not layer_name:
        layer_name = f"{item.data(0)} (Grid)"

    log_message(f"Adding grid layer for column: {column_name}")
    log_message(f"Layer URI: {layer_uri}")
    log_message(f"Layer name: {layer_name}")

    # Load the layer
    layer = QgsVectorLayer(layer_uri, layer_name, "ogr")
    if not layer.isValid():
        log_message(
            f"Layer {layer_name} is invalid and cannot be added.",
            tag="GeoE3",
            level=Qgis.Warning,
        )
        return

    # Verify the column exists in the layer
    field_names = [field.name() for field in layer.fields()]
    log_message(f"Available columns: {field_names[:10]}...")  # Log first 10
    if column_name not in field_names:
        log_message(
            f"Column '{column_name}' not found in study_area_grid. Available columns: {field_names}",
            tag="GeoE3",
            level=Qgis.Warning,
        )
        return

    # Apply filter to exclude NULL values for the column being visualized
    filter_expression = f'"{column_name}" IS NOT NULL'
    layer.setSubsetString(filter_expression)
    log_message(f"Applied filter: {filter_expression}")

    # Load the QML template and substitute the column name
    template_path = resources_path("resources", "qml", "indicator-vector-template.qml")
    log_message(f"Template path: {template_path}")
    if not os.path.exists(template_path):
        log_message(
            f"QML template not found: {template_path}",
            tag="GeoE3",
            level=Qgis.Warning,
        )
        return

    with open(template_path, "r") as f:
        qml_content = f.read()

    # Replace the [attribute] placeholder with the actual column name
    qml_content = qml_content.replace("[attribute]", column_name)
    log_message(f"Substituted column '{column_name}' in QML template")

    # Write to a temporary file and apply the style
    with tempfile.NamedTemporaryFile(mode="w", suffix=".qml", delete=False) as tmp:
        tmp.write(qml_content)
        tmp_path = tmp.name

    try:
        result = layer.loadNamedStyle(tmp_path)
        if not result[0]:
            log_message(
                f"Failed to apply style: {result[1]}",
                tag="GeoE3",
                level=Qgis.Warning,
            )
    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    project = QgsProject.instance()

    # Check if 'GeoE3' group exists, otherwise create it
    root = project.layerTreeRoot()
    geoe3_group = root.findGroup(group)
    if geoe3_group is None:
        geoe3_group = root.insertGroup(0, group)
        geoe3_group.setIsMutuallyExclusive(True)

    # Traverse the tree view structure to determine the appropriate subgroup
    path_list = item.getPaths()
    parent_group = geoe3_group
    # Truncate the last item from the path list
    path_list = path_list[:-1]

    for path in path_list:
        sub_group = parent_group.findGroup(path)
        if sub_group is None:
            sub_group = parent_group.addGroup(path)
            sub_group.setIsMutuallyExclusive(True)
        parent_group = sub_group

    # Check if a layer with the same name exists in the group
    existing_layer = None
    layer_tree_layer = None
    for child in parent_group.children():
        if isinstance(child, QgsLayerTreeGroup):
            continue
        if child.layer().name() == layer_name:
            existing_layer = child.layer()
            layer_tree_layer = child
            break

    # If the layer exists, update its style and filter instead of re-adding
    if existing_layer is not None:
        log_message(f"Refreshing existing layer: {existing_layer.name()}")
        # Update filter for the column being visualized
        existing_layer.setSubsetString(filter_expression)
        # Re-apply style to existing layer
        with tempfile.NamedTemporaryFile(mode="w", suffix=".qml", delete=False) as tmp:
            tmp.write(qml_content)
            tmp_path = tmp.name
        try:
            existing_layer.loadNamedStyle(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        layer_tree_layer.setItemVisibilityChecked(True)
        existing_layer.triggerRepaint()
    else:
        # Add the new layer
        QgsProject.instance().addMapLayer(layer, False)
        layer_tree_layer = parent_group.addLayer(layer)
        layer_tree_layer.setExpanded(False)
        log_message(f"Added layer: {layer.name()} to group: {parent_group.name()}")

    # Ensure the layer and its parent groups are visible
    current_group = parent_group
    while current_group is not None:
        current_group.setExpanded(True)
        current_group.setItemVisibilityChecked(True)
        current_group = current_group.parent()

    layer_tree_layer.setItemVisibilityChecked(True)

    # Refresh the canvas
    repaint_layer = existing_layer if existing_layer is not None else layer
    repaint_layer.triggerRepaint()
    iface.mapCanvas().refresh()


def add_pyramid_layer_to_map(
    item: "JsonTreeItem",
    column_name: str,
    working_directory: str,
    cell_size_m: float,
    analysis_scale: str = "national",
    layer_name: str = None,
    group: str = "GeoE3",
):
    """Add a scale-dependent pyramid of grid layers for one output column.

    Replaces add_grid_layer_to_map() for local/national (square-grid)
    analyses: instead of one single-resolution layer, builds/refreshes a
    multi-resolution vector pyramid (see geest.core.grid_pyramid_utils) and
    adds one QgsLayerTreeGroup containing one layer per exposed pyramid
    level, each scale-dependent so only one renders at a given zoom -
    replacing the need to ever rasterize/mask a GeoTIFF for visualization.

    Regional (H3) analyses fall back to add_grid_layer_to_map(): H3's
    7-child hex hierarchy doesn't support 2x2 quad aggregation.

    Local/national analyses whose project uses the H3 grid type (see
    geest.core.grid_type_utils) build/refresh an H3-resolution pyramid
    (geest.core.h3_pyramid_utils) instead of the square-grid one; both
    pyramid shapes feed the same scale-dependent layer-tree builder below,
    which only needs a list of exposed (table_or_None) levels and a
    parallel list of scale denominators - it has no notion of grid shape.

    Args:
        item: The tree item (indicator/factor/dimension/analysis) to display.
        column_name: The column in study_area_grid to symbolize.
        working_directory: Path to the working directory containing study_area.gpkg.
        cell_size_m: The analysis grid's native cell size. Ignored for H3
            projects, whose resolution comes from model.json instead.
        analysis_scale: "national"/"local" or "regional".
        layer_name: Optional display name for the output group. Defaults to item name.
        group: The top-level group name. Defaults to "GeoE3".
    """
    if analysis_scale == "regional":
        add_grid_layer_to_map(item, column_name, working_directory, layer_name, group)
        return

    if not working_directory:
        log_message("Working directory is not set. Cannot add pyramid layer.", tag="GeoE3", level=Qgis.Warning)
        return

    gpkg_path = os.path.join(working_directory, "study_area", "study_area.gpkg")
    if not os.path.exists(gpkg_path):
        log_message(f"GeoPackage not found: {gpkg_path}", tag="GeoE3", level=Qgis.Warning)
        return

    from geest.core import grid_type_utils
    from geest.core.grid_pyramid_utils import is_pyramid_fresh, scale_denominator_for_cell_size

    grid_type = grid_type_utils.get_grid_type(working_directory)

    if grid_type == "h3":
        from geest.core.h3_pyramid_utils import (
            get_exposed_h3_levels,
            h3_effective_cell_size_m,
            refresh_h3_pyramid_column,
        )

        h3_resolution = grid_type_utils.get_h3_resolution(working_directory)
        if not is_pyramid_fresh(gpkg_path, column_name):
            if not refresh_h3_pyramid_column(gpkg_path, column_name, h3_resolution):
                log_message(
                    f"Failed to build H3 pyramid for column '{column_name}'.",
                    tag="GeoE3",
                    level=Qgis.Warning,
                )
                return

        # Finest first: [(h3_resolution, table_or_None), ...].
        levels = get_exposed_h3_levels(gpkg_path, column_name, h3_resolution)
        scales = [scale_denominator_for_cell_size(h3_effective_cell_size_m(res)) for res, _table in levels]
        level_suffixes = [f"res {res}" for res, _table in levels]
    else:
        from geest.core.grid_pyramid_utils import get_exposed_levels, refresh_pyramid_column

        if not is_pyramid_fresh(gpkg_path, column_name):
            if not refresh_pyramid_column(gpkg_path, column_name, cell_size_m):
                log_message(
                    f"Failed to build pyramid for column '{column_name}'.",
                    tag="GeoE3",
                    level=Qgis.Warning,
                )
                return

        # Finest first: [(cell_size_m, table_or_None), ...].
        levels = get_exposed_levels(gpkg_path, column_name, cell_size_m)
        scales = [scale_denominator_for_cell_size(cs) for cs, _table in levels]
        level_suffixes = [f"{int(cs)}m" for cs, _table in levels]

    if not layer_name:
        layer_name = item.data(0)

    _build_pyramid_level_group(
        item=item,
        column_name=column_name,
        gpkg_path=gpkg_path,
        layer_name=layer_name,
        group=group,
        levels=levels,
        scales=scales,
        level_suffixes=level_suffixes,
    )


def _build_pyramid_level_group(
    item: "JsonTreeItem",
    column_name: str,
    gpkg_path: str,
    layer_name: str,
    group: str,
    levels: list,
    scales: list,
    level_suffixes: list,
) -> None:
    """Build/refresh the scale-dependent QgsLayerTreeGroup for one pyramid.

    Shared tail of add_pyramid_layer_to_map() for both the square-grid and
    H3 pyramids: given the exposed levels (finest first) and a parallel
    list of scale denominators/display-name suffixes, it is entirely
    agnostic of the pyramid's grid shape.

    Args:
        item: The tree item (indicator/factor/dimension/analysis) to display.
        column_name: The column in study_area_grid to symbolize.
        gpkg_path: Path to the GeoPackage containing study_area_grid.
        layer_name: Display name for the output group.
        group: The top-level group name.
        levels: List of (level_key, table_name_or_None) tuples, finest
            first. table_name_or_None is None for the base level, meaning
            "use study_area_grid itself". level_key is only consumed by the
            caller (to build level_suffixes) and is otherwise unused here.
        scales: Parallel list of scale denominators, one per level.
        level_suffixes: Parallel list of human-readable suffixes (e.g.
            "200m" or "res 6") used to name each level's layer.
    """
    import tempfile

    from geest.utilities import resources_path

    template_path = resources_path("resources", "qml", "indicator-vector-template.qml")
    if not os.path.exists(template_path):
        log_message(f"QML template not found: {template_path}", tag="GeoE3", level=Qgis.Warning)
        return
    with open(template_path, "r") as f:
        qml_template = f.read()

    project = QgsProject.instance()
    root = project.layerTreeRoot()
    geoe3_group = root.findGroup(group)
    if geoe3_group is None:
        geoe3_group = root.insertGroup(0, group)
        geoe3_group.setIsMutuallyExclusive(True)

    path_list = item.getPaths()[:-1]
    parent_group = geoe3_group
    for path in path_list:
        sub_group = parent_group.findGroup(path)
        if sub_group is None:
            sub_group = parent_group.addGroup(path)
            sub_group.setIsMutuallyExclusive(True)
        parent_group = sub_group

    # Replace any previously-added pyramid group for this output so re-runs
    # don't accumulate duplicate groups/layers. removeChildNode() alone only
    # detaches the tree node - it does not deregister the underlying
    # QgsMapLayer objects from QgsProject, which would otherwise leak one
    # set of 3 layers per repeat click.
    existing_output_group = parent_group.findGroup(layer_name)
    if existing_output_group is not None:
        stale_layer_ids = [child.layerId() for child in existing_output_group.children() if hasattr(child, "layerId")]
        if stale_layer_ids:
            project.removeMapLayers(stale_layer_ids)
        parent_group.removeChildNode(existing_output_group)
    # Deliberately NOT mutually exclusive: all levels stay checked
    # simultaneously, and setScaleBasedVisibility() on each layer is what
    # decides which one actually renders at the current zoom.
    output_group = parent_group.addGroup(layer_name)

    for index, (_level_key, table_name) in enumerate(levels):
        # Every level table (including the base study_area_grid itself) is
        # a wide table using the same real column name - there's no
        # separate "value" field, so filtering/styling is identical at
        # every level.
        layer_uri = f"{gpkg_path}|layername={table_name or 'study_area_grid'}"

        level_layer_name = f"{layer_name} ({level_suffixes[index]})"
        vlayer = QgsVectorLayer(layer_uri, level_layer_name, "ogr")
        if not vlayer.isValid():
            log_message(f"Pyramid level layer is invalid: {layer_uri}", tag="GeoE3", level=Qgis.Warning)
            continue

        vlayer.setSubsetString(f'"{column_name}" IS NOT NULL')

        qml_content = qml_template.replace("[attribute]", column_name)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".qml", delete=False) as tmp:
            tmp.write(qml_content)
            tmp_path = tmp.name
        try:
            result = vlayer.loadNamedStyle(tmp_path)
            if not result[0]:
                log_message(f"Failed to apply style to {level_layer_name}: {result[1]}", level=Qgis.Warning)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        # Finest level has no inner (zoomed-in) limit; coarsest has no outer
        # (zoomed-out) limit. Adjacent levels share their boundary scale
        # exactly, for a seamless handoff with neither gap nor overlap.
        vlayer.setScaleBasedVisibility(True)
        vlayer.setMaximumScale(0 if index == 0 else scales[index - 1])
        vlayer.setMinimumScale(0 if index == len(levels) - 1 else scales[index])

        project.addMapLayer(vlayer, False)
        layer_tree_layer = output_group.addLayer(vlayer)
        layer_tree_layer.setItemVisibilityChecked(True)

    output_group.setExpanded(False)
    current_group = parent_group
    while current_group is not None:
        current_group.setExpanded(True)
        current_group.setItemVisibilityChecked(True)
        current_group = current_group.parent()

    iface.mapCanvas().refresh()
    log_message(f"Added pyramid layer group '{layer_name}' with {len(levels)} scale-dependent levels.")

    log_message(
        f"Grid layer {layer_name} for column {column_name} added to map.",
        tag="GeoE3",
        level=Qgis.Info,
    )


def validate_network_layer(layer_path: str, expected_crs: QgsCoordinateReferenceSystem) -> tuple:
    """Validate network layer for road network analysis.

    Args:
        layer_path: Path to network layer (may include |layername=)
        expected_crs: Expected coordinate reference system

    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    if not layer_path:
        return False, "No network layer configured"

    # Check file exists
    base_path = layer_path.split("|")[0] if "|" in layer_path else layer_path
    if not os.path.exists(base_path):
        return False, f"Network layer file not found: {base_path}"

    # Load and validate layer
    layer = QgsVectorLayer(layer_path, "validation", "ogr")
    if not layer.isValid():
        return False, f"Network layer is invalid or cannot be loaded: {layer_path}"

    # Check geometry type
    if layer.geometryType() != QgsWkbTypes.GeometryType.LineGeometry:
        return False, "Network layer must be a line (polyline) layer"

    # Check CRS match
    if layer.crs() != expected_crs:
        return (
            False,
            f"Network layer CRS ({layer.crs().authid()}) doesn't match project CRS ({expected_crs.authid()})",
        )

    return True, None
