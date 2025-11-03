# coding=utf-8

"""Utilities for Geest."""

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
)

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
        log_message(f"Failed to compute/reproject study area bbox: {e}", tag="Geest", level=Qgis.Warning)
    return extent_mollweide


def add_to_map(
    item: JsonTreeItem,
    key: str = "result_file",
    layer_name: str = None,
    qml_key: str = None,
    group: str = "Geest",
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
                tag="Geest",
                level=Qgis.Warning,
            )
            return

        project = QgsProject.instance()

        # Check if 'Geest' group exists, otherwise create it
        root = project.layerTreeRoot()
        geest_group = root.findGroup(group)
        if geest_group is None:
            geest_group = root.insertGroup(0, group)  # Insert at the top of the layers panel
            geest_group.setIsMutuallyExclusive(True)  # Make the group mutually exclusive

        # Traverse the tree view structure to determine the appropriate subgroup based on paths
        path_list = item.getPaths()
        parent_group = geest_group
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
                tag="Geest",
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

        log_message(
            f"Layer {layer.name()} and its parent groups are now visible.",
            tag="Geest",
            level=Qgis.Info,
        )
