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
import sys
from math import floor

from qgis.core import (
    Qgis,
    QgsLayerTreeGroup,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
)

from ..utilities import log_message
from .json_tree_item import JsonTreeItem


class CoreUtils:
    """
    Core utilities
    """

    @staticmethod
    def which(name, flags=os.X_OK):
        """Search PATH for executable files with the given name.

        ..note:: This function was taken verbatim from the twisted framework,
          licence available here:
          http://twistedmatrix.com/trac/browser/tags/releases/twisted-8.2.0/LICENSE

        On newer versions of MS-Windows, the PATHEXT environment variable will be
        set to the list of file extensions for files considered executable. This
        will normally include things like ".EXE". This function will also find
        files
        with the given name ending with any of these extensions.

        On MS-Windows the only flag that has any meaning is os.F_OK. Any other
        flags will be ignored.

        :param name: The name for which to search.
        :type name: C{str}

        :param flags: Arguments to L{os.access}.
        :type flags: C{int}

        :returns: A list of the full paths to files found, in the order in which
            they were found.
        :rtype: C{list}
        """
        result = []
        # pylint: disable=W0141
        extensions = [
            _f for _f in os.environ.get("PATHEXT", "").split(os.pathsep) if _f
        ]
        # pylint: enable=W0141
        path = os.environ.get("PATH", None)
        # In c6c9b26 we removed this hard coding for issue #529 but I am
        # adding it back here in case the user's path does not include the
        # gdal binary dir on OSX but it is actually there. (TS)
        if sys.platform == "darwin":  # Mac OS X
            gdal_prefix = (
                "/Library/Frameworks/GDAL.framework/Versions/Current/Programs/"
            )
            path = "%s:%s" % (path, gdal_prefix)

        if path is None:
            return []

        for p in path.split(os.pathsep):
            p = os.path.join(p, name)
            if os.access(p, flags):
                result.append(p)
            for e in extensions:
                path_extensions = p + e
                if os.access(path_extensions, flags):
                    result.append(path_extensions)

        return result


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
                    result = layer.loadNamedStyle(qml_path)
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
            geest_group = root.insertGroup(
                0, group
            )  # Insert at the top of the layers panel
            geest_group.setIsMutuallyExclusive(
                True
            )  # Make the group mutually exclusive

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
                sub_group.setIsMutuallyExclusive(
                    True
                )  # Make each subgroup mutually exclusive

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
            layer_tree_layer.setExpanded(
                False
            )  # Collapse the legend for the layer by default
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
