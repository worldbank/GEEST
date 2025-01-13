import os
import shutil
from qgis.core import (
    QgsProcessingException,
    QgsCoordinateReferenceSystem,
    QgsGeometry,
    QgsFeature,
    QgsWkbTypes,
    QgsVectorLayer,
    QgsRasterLayer,
    Qgis,
    QgsProcessingFeedback,
)
import processing
from geest.utilities import log_message


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


def subset_vector_layer(
    workflow_directory: str,
    features_layer: QgsVectorLayer,
    area_geom: QgsGeometry,
    output_prefix: str,
) -> QgsVectorLayer:
    """
    Select features from the features layer that intersect with the given area geometry.

    Args:
        features_layer (QgsVectorLayer): The input features layer.
        area_geom (QgsGeometry): The current area geometry for which intersections are evaluated.
        output_prefix (str): A name for the output temporary layer to store selected features.

    Returns:
        QgsVectorLayer: A new temporary layer containing features that intersect with the given area geometry.
    """
    if type(features_layer) != QgsVectorLayer:
        return None
    log_message(f"subset_vector_layer Select Features Started")
    output_path = os.path.join(workflow_directory, f"{output_prefix}.shp")

    # Get the WKB type (geometry type) of the input layer (e.g., Point, LineString, Polygon)
    geometry_type = features_layer.wkbType()

    # Determine geometry type name based on input layer's geometry
    if QgsWkbTypes.geometryType(geometry_type) == QgsWkbTypes.PointGeometry:
        geometry_name = "Point"
    elif QgsWkbTypes.geometryType(geometry_type) == QgsWkbTypes.LineGeometry:
        geometry_name = "LineString"
    elif QgsWkbTypes.geometryType(geometry_type) == QgsWkbTypes.PolygonGeometry:
        geometry_name = "Polygon"
    else:
        raise QgsProcessingException(f"Unsupported geometry type: {geometry_type}")

    params = {
        "INPUT": features_layer,
        "PREDICATE": [0],  # Intersects predicate
        "GEOMETRY": area_geom,
        "EXTENT": area_geom.boundingBox(),
        "OUTPUT": output_path,
    }
    result = processing.run("native:extractbyextent", params)
    return QgsVectorLayer(result["OUTPUT"], output_prefix, "ogr")


def geometry_to_memory_layer(
    geometry: QgsGeometry, target_crs: QgsCoordinateReferenceSystem, layer_name: str
):
    """
    Convert a QgsGeometry to a memory layer.

    Args:
        geometry (QgsGeometry): The polygon geometry to convert.
        target_crs (QgsCoordinateReferenceSystem): The CRS to assign to the memory layer
        layer_name (str): The name to assign to the memory layer.

    Returns:
        QgsVectorLayer: The memory layer containing the geometry.
    """
    memory_layer = QgsVectorLayer("Polygon", layer_name, "memory")
    memory_layer.setCrs(target_crs)
    feature = QgsFeature()
    feature.setGeometry(geometry)
    memory_layer.dataProvider().addFeatures([feature])
    memory_layer.commitChanges()
    return memory_layer


def check_and_reproject_layer(
    features_layer: QgsVectorLayer, target_crs: QgsCoordinateReferenceSystem
):
    """
    Checks if the features layer has valid geometries and the expected CRS.

    Geometry errors are fixed using the native:fixgeometries algorithm.
    If the layer's CRS does not match the target CRS, it is reprojected using the
    native:reprojectlayer algorithm.

    Args:
        features_layer (QgsVectorLayer): The input features layer.
        target_crs (QgsCoordinateReferenceSystem): The target CRS for the layer.

    Returns:
        QgsVectorLayer: The input layer, either reprojected or unchanged.

    Note: Also updates self.features_layer to point to the reprojected layer.
    """
    # check if the layer has a valid CRS
    if not features_layer.crs().isValid():
        raise QgsProcessingException("Layer has no CRS.")

    params = {
        "INPUT": features_layer,
        "METHOD": 1,  # Structure method
        "OUTPUT": "memory:",  # Reproject in memory,
    }
    fixed_features_layer = processing.run("native:fixgeometries", params)["OUTPUT"]
    log_message("Fixed features layer geometries")

    if fixed_features_layer.crs() != target_crs:
        log_message(
            f"Reprojecting layer from {fixed_features_layer.crs().authid()} to {target_crs.authid()}",
            tag="Geest",
            level=Qgis.Info,
        )
        reproject_result = processing.run(
            "native:reprojectlayer",
            {
                "INPUT": fixed_features_layer,
                "TARGET_CRS": target_crs,
                "OUTPUT": "memory:",  # Reproject in memory
            },
            feedback=QgsProcessingFeedback(),
        )
        reprojected_layer = reproject_result["OUTPUT"]
        if not reprojected_layer.isValid():
            raise QgsProcessingException("Reprojected layer is invalid.")
        features_layer = reprojected_layer
    else:
        features_layer = fixed_features_layer
    # If CRS matches, return the original layer
    return features_layer


def combine_rasters_to_vrt(
    rasters: list,
    target_crs: QgsCoordinateReferenceSystem,
    vrt_filepath: str,
    source_qml: str = None,
) -> None:
    """
    Combine all the rasters into a single VRT file.

    Args:
        rasters: The rasters to combine into a VRT.
        target_crs: The CRS to assign to the VRT.
        vrt_filepath: The full path of the output VRT file to create.
        source_qml: The source QML file to apply to the VRT.

    Returns:
        vrtpath (str): The file path to the VRT file.
    """
    if not rasters:
        log_message(
            "No valid raster layers found to combine into VRT.",
            tag="Geest",
            level=Qgis.Warning,
        )
        return

    log_message(f"Creating VRT of layers as '{vrt_filepath}'.")
    checked_rasters = []
    for raster in rasters:
        if raster and os.path.exists(raster) and QgsRasterLayer(raster).isValid():
            checked_rasters.append(raster)
        else:
            log_message(
                f"Skipping invalid or non-existent raster: {raster}",
                tag="Geest",
                level=Qgis.Warning,
            )

    if not checked_rasters:
        log_message(
            "No valid raster layers found to combine into VRT.",
            tag="Geest",
            level=Qgis.Warning,
        )
        return

    # Define the VRT parameters
    params = {
        "INPUT": checked_rasters,
        "RESOLUTION": 0,  # Use highest resolution among input files
        "SEPARATE": False,  # Combine all input rasters as a single band
        "OUTPUT": vrt_filepath,
        "PROJ_DIFFERENCE": False,
        "ADD_ALPHA": False,
        "ASSIGN_CRS": target_crs,
        "RESAMPLING": 0,
        # "SRC_NODATA": "255",
        "EXTRA": "",
    }

    # Run the gdal:buildvrt processing algorithm to create the VRT
    processing.run("gdal:buildvirtualraster", params)
    log_message(f"Created VRT: {vrt_filepath}")

    # Copy the appropriate QML over too
    destination_qml = os.path.splitext(vrt_filepath)[0] + ".qml"
    log_message(f"Copying QML from {source_qml} to {destination_qml}")
    shutil.copyfile(source_qml, destination_qml)

    vrt_layer = QgsRasterLayer(vrt_filepath, "Final VRT")
    if not vrt_layer.isValid():
        log_message("VRT Layer generation failed.", level=Qgis.Critical)
        return False
    del vrt_layer

    return vrt_filepath
