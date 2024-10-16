from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsVectorLayer,
    QgsRasterLayer,
    Qgis,
)
from qgis.PyQt.QtCore import QVariant
import processing


# Call QGIS process to assign a CRS to a layer
def assign_crs_to_raster_layer(
    layer: QgsRasterLayer, crs: QgsCoordinateReferenceSystem
) -> QgsVectorLayer:
    """
    Assigns a CRS to a layer and returns the layer.

    Args:
        layer: The layer to assign the CRS to.
        crs: The CRS to assign to the layer.

    Returns:
        The layer with the assigned CRS.
    """
    processing.run("gdal:assignprojection", {"INPUT": layer, "CRS": crs})
    return layer


def assign_crs_to_vector_layer(
    layer: QgsVectorLayer, crs: QgsCoordinateReferenceSystem
) -> QgsVectorLayer:
    """
    Assigns a CRS to a layer and returns the layer.

    Args:
        layer: The layer to assign the CRS to.
        crs: The CRS to assign to the layer.

    Returns:
        The layer with the assigned CRS.
    """
    output = processing.run(
        "native:assignprojection",
        {"INPUT": layer, "CRS": crs, "OUTPUT": "TEMPORARY_OUTPUT"},
    )["OUTPUT"]
    return output
