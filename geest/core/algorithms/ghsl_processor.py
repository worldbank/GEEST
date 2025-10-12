# -*- coding: utf-8 -*-
"""
Copyright (c) 2025. All rights reserved.
Original Author: [Your Name]

Raster Processing Module for PyQt Applications

This module provides a comprehensive class for processing raster layers using GDAL,
including virtual raster creation, reclassification, polygonization, and spatial joins.
"""

import os
from pathlib import Path
from typing import List, Optional

import numpy as np
from osgeo import gdal, ogr, osr
from qgis.core import QgsRectangle

from geest.utilities import log_message


class GHSLProcessor:
    """
    A processor to convert GHSL settlement data into vector polygons.

    This class provides functionality to:
    1. Reclassify raster values based on custom logic
    2. Clean rasters for polygonization by setting zero values to NoData
    3. Polygonize raster data into vector format (GeoParquet files)
    4. Combine multiple vector layers into a single file
    5. Perform spatial joins with filtering

    All operations use GDAL raw API exclusively.

    Attributes:
        input_raster_layers: List of input raster file paths.
        polygonized_vector_path: Path to the polygonized geoparquet output.
        joined_vector_path: Path to the spatial join result.
    """

    def __init__(
        self,
        input_raster_paths: List[str],
    ):
        """
        Initialize the GHSLProcessor with input raster layers.

        Args:
            input_raster_paths: List of file paths to single-band TIFF raster layers.

        Raises:
            ValueError: If input_raster_paths is empty or contains invalid paths.
        """
        if not input_raster_paths:
            raise ValueError("Input raster layers list cannot be empty")

        self.input_raster_layers = input_raster_paths
        self.polygonized_vector_path: Optional[str] = None
        self.joined_vector_path: Optional[str] = None

        # Verify all input files exist
        for layer_path in input_raster_paths:
            if not Path(layer_path).exists():
                raise ValueError(f"Input raster layer does not exist: {layer_path}")

    def reclassify_rasters(self, suffix: str = "classified") -> List[str]:
        """
        Reclassify raster values based on specified logic.

        Reclassification rules:
        - Values 10 or 11 are reclassified to 0
        - All other values are reclassified to 1

        The output is a single-band byte (8-bit unsigned integer) raster.

        Args:
            suffix: Suffix to append to output raster filenames.

        Returns:
            List of paths to the created reclassified raster files.

        Raises:
            RuntimeError: If reclassification fails or input raster cannot be opened.
        """
        # Open the input raster dataset
        output_raster_paths = []
        for layer in self.input_raster_layers:
            # replace .tif at the end of the file with _{suffix}.tif
            output_raster_path = os.path.splitext(layer)[0] + f"_{suffix}.tif"
            input_dataset = gdal.Open(layer, gdal.GA_ReadOnly)
            if input_dataset is None:
                raise RuntimeError(f"Failed to open input raster: {layer}")

            # Get raster properties
            raster_band = input_dataset.GetRasterBand(1)
            x_size = input_dataset.RasterXSize
            y_size = input_dataset.RasterYSize
            geotransform = input_dataset.GetGeoTransform()
            projection = input_dataset.GetProjection()

            # Read the raster data as numpy array
            raster_array = raster_band.ReadAsArray()

            # Apply reclassification logic
            # Values 10 or 11 become 0, all others become 1
            reclassified_array = np.where((raster_array == 10) | (raster_array == 11), 0, 1).astype(np.uint8)

            # Create output raster
            driver = gdal.GetDriverByName("GTiff")
            output_dataset = driver.Create(output_raster_path, x_size, y_size, 1, gdal.GDT_Byte)

            if output_dataset is None:
                raise RuntimeError(f"Failed to create output raster: {output_raster_path}")

            # Set geotransform and projection
            output_dataset.SetGeoTransform(geotransform)
            output_dataset.SetProjection(projection)

            # Write the reclassified data
            output_band = output_dataset.GetRasterBand(1)
            output_band.WriteArray(reclassified_array)
            output_band.FlushCache()

            # Close datasets
            input_dataset = None
            output_dataset = None

            output_raster_paths.append(output_raster_path)
        return output_raster_paths

    def clean_raster_for_polygonization(self, input_raster_path: str) -> str:
        """
        Clean raster by setting all 0 values to NoData before polygonization.

        This eliminates the need to filter polygons later - only non-zero
        pixels will be polygonized.

        Args:
            input_raster_path: Path to the reclassified raster.

        Returns:
            Path to the cleaned raster file.

        Raises:
            RuntimeError: If input raster cannot be opened or cleaned raster cannot be created.
        """
        # Create cleaned raster path
        cleaned_path = input_raster_path.replace(".tif", "_cleaned.tif")

        log_message(f"Cleaning raster for polygonization: {input_raster_path} -> {cleaned_path}")

        # Open input raster
        input_dataset = gdal.Open(input_raster_path, gdal.GA_ReadOnly)
        if input_dataset is None:
            raise RuntimeError(f"Failed to open input raster: {input_raster_path}")

        input_band = input_dataset.GetRasterBand(1)
        raster_array = input_band.ReadAsArray()

        # Get raster properties
        cols = input_dataset.RasterXSize
        rows = input_dataset.RasterYSize
        geotransform = input_dataset.GetGeoTransform()
        projection = input_dataset.GetProjection()

        # Create cleaned array - set 0 values to NoData (0)
        nodata_value = 0
        cleaned_array = raster_array.copy()
        cleaned_array[raster_array == 0] = nodata_value

        # Count original vs cleaned pixels
        original_nonzero = np.count_nonzero(raster_array)
        cleaned_nonzero = np.count_nonzero(cleaned_array != nodata_value)
        zeros_removed = np.count_nonzero(raster_array == 0)

        log_message(f"Original non-zero pixels: {original_nonzero}")
        log_message(f"Cleaned non-zero pixels: {cleaned_nonzero}")
        log_message(f"Zero pixels removed: {zeros_removed}")

        # Create output raster
        driver = gdal.GetDriverByName("GTiff")
        output_dataset = driver.Create(cleaned_path, cols, rows, 1, gdal.GDT_Int16)

        if output_dataset is None:
            raise RuntimeError(f"Failed to create cleaned raster: {cleaned_path}")

        # Set properties
        output_dataset.SetGeoTransform(geotransform)
        output_dataset.SetProjection(projection)

        # Write cleaned data and set NoData value
        output_band = output_dataset.GetRasterBand(1)
        output_band.WriteArray(cleaned_array)
        output_band.SetNoDataValue(nodata_value)
        output_band.FlushCache()

        # Close datasets
        input_dataset = None
        output_dataset = None

        log_message(f"Cleaned raster created: {cleaned_path}")
        return cleaned_path

    def polygonize_rasters(self, input_raster_paths: List[str]) -> List[str]:
        """
        Convert raster data to polygon vector features using GDAL Polygonize.

        This method uses 8-way connectivity for polygonization and creates
        GeoParquet vector files with polygons representing contiguous raster values.
        Polygons with value 0 are filtered out for efficiency by pre-cleaning the rasters.

        The output will be written to a GeoParquet file with the same base name
        as the input raster but with a .parquet extension.

        Args:
            input_raster_paths: List of paths to the input raster files to polygonize.

        Returns:
            List of paths to the created polygonized GeoParquet files.

        Raises:
            RuntimeError: If polygonization fails or files cannot be opened.
        """
        # Open the input raster
        class_field_name = "pixel_value"  # Changed from "class" - reserved word issue!
        output_vector_paths = []
        for input_raster_path in input_raster_paths:
            log_message(f"Polygonizing raster: {input_raster_path}")

            # FIRST: Clean the raster by removing 0 values (set to NoData)
            cleaned_raster_path = self.clean_raster_for_polygonization(input_raster_path)
            log_message(f"Using cleaned raster for polygonization: {cleaned_raster_path}")
            raster_dataset = gdal.Open(cleaned_raster_path, gdal.GA_ReadOnly)
            if raster_dataset is None:
                raise RuntimeError(f"Failed to open cleaned raster for polygonization: {cleaned_raster_path}")

            raster_band = raster_dataset.GetRasterBand(1)
            output_vector_path = str(Path(input_raster_path).with_suffix(".parquet"))
            # delete the output file if it already exists
            if Path(output_vector_path).exists():
                Path(output_vector_path).unlink()

            # Create output vector datasource (Parquet)
            driver = ogr.GetDriverByName("Parquet")

            # Remove existing file if present
            if Path(output_vector_path).exists():
                driver.DeleteDataSource(output_vector_path)
            log_message(f"Creating polygonized output at {output_vector_path}")
            vector_datasource = driver.CreateDataSource(output_vector_path)
            if vector_datasource is None:
                raise RuntimeError(f"Failed to create output vector datasource: {output_vector_path}")

            # Get spatial reference from raster
            spatial_reference = osr.SpatialReference()
            spatial_reference.ImportFromWkt(raster_dataset.GetProjection())

            # Create vector layer
            vector_layer = vector_datasource.CreateLayer("polygonized", srs=spatial_reference, geom_type=ogr.wkbPolygon)

            if vector_layer is None:
                raise RuntimeError("Failed to create vector layer in GeoParquet")

            # Create field for classification values
            field_definition = ogr.FieldDefn(class_field_name, ogr.OFTInteger)
            vector_layer.CreateField(field_definition)

            # Polygonize with 8-way connectivity
            # The last parameter (options) can include connectedness=8 for 8-way
            result = gdal.Polygonize(
                raster_band,
                raster_band,  # use the raster with nodata assigned to self mask
                vector_layer,
                0,  # Field index for the classification values
                ["8CONNECTED=8"],  # Use 8-way connectivity
                callback=None,
            )

            if result != 0:
                raise RuntimeError("Polygonization failed")

            # Success! Since we cleaned the raster, all polygons are valid (non-zero values only)
            log_message("Polygonization completed successfully!")

            # Sync the layer to ensure data is written
            vector_layer.SyncToDisk()
            vector_datasource.FlushCache()

            # Count final features
            final_count = vector_layer.GetFeatureCount()
            log_message(f"Created {final_count} polygons (all with non-zero values)")

            # Clean finish - no filtering needed since raster was pre-cleaned
            log_message("Closing datasources...")

            # Close datasets properly
            vector_layer = None
            vector_datasource = None
            raster_dataset = None

            # Verify the file was created and has content
            if Path(output_vector_path).exists():
                file_size = Path(output_vector_path).stat().st_size
                log_message(f"Output file created: {output_vector_path} (size: {file_size} bytes)")
            else:
                log_message(f"ERROR: Output file was not created: {output_vector_path}")

            output_vector_paths.append(output_vector_path)
        return output_vector_paths

    def combine_vectors(
        self, input_vector_paths: List[str], output_vector_path: str, extent: Optional[QgsRectangle]
    ) -> bool:
        """
        Combine multiple vector layers into a single GeoParquet file.

        Args:
            input_vector_paths: List of paths to the input vector files to combine.
            output_vector_path: Path for the output combined GeoParquet file.
            extent: Optional QgsRectangle to filter features by extent.
                   It is assumed the extent is in Mollweide projection (ESRI:54009).
                   If None, all features are included without spatial filtering.

        Returns:
            True if combination was successful.

        Raises:
            RuntimeError: If combination fails or files cannot be opened.
        """
        # convert the QGIS extents to an ogr geometry
        if extent:
            min_x = extent.xMinimum()
            min_y = extent.yMinimum()
            max_x = extent.xMaximum()
            max_y = extent.yMaximum()
            ring = ogr.Geometry(ogr.wkbLinearRing)
            ring.AddPoint(min_x, min_y)
            ring.AddPoint(max_x, min_y)
            ring.AddPoint(max_x, max_y)
            ring.AddPoint(min_x, max_y)
            ring.CloseRings()
            log_message(f"filtering geometry using extents: {extent.toString()}")

        driver = ogr.GetDriverByName("Parquet")
        # Remove existing file if present
        if Path(output_vector_path).exists():
            driver.DeleteDataSource(output_vector_path)
        log_message(f"Creating combined output at {output_vector_path}")
        output_datasource = driver.CreateDataSource(output_vector_path)
        if output_datasource is None:
            raise RuntimeError(f"Failed to create output vector datasource: {output_vector_path}")

        combined_layer = None
        counter = 0

        for input_vector_path in input_vector_paths:
            log_message(f"Adding layer from {input_vector_path} to combined dataset")

            input_datasource = ogr.Open(input_vector_path, gdal.GA_ReadOnly)
            if input_datasource is None:
                raise RuntimeError(f"Failed to open input vector: {input_vector_path}")

            input_layer = input_datasource.GetLayer(0)
            if extent:
                log_message("Checking intersection with extents...")
                log_message(f"Input layer extent: {input_layer.GetExtent()}")
                log_message(f"Filtering extent: {ring.ExportToWkt()}")
                # Confirm that the input vector intersects with the extents
                crs = input_layer.GetSpatialRef()

                log_message(f"Input layer CRS EPSG: {crs.GetAttrValue('AUTHORITY', 1)}")

                input_extent = input_layer.GetExtent()  # returns (minX, maxX, minY, maxY)
                ring_envelope = ring.GetEnvelope()  # returns (minX, maxX, minY, maxY)
                # Check for intersection between two envelopes
                intersects = not (
                    input_extent[1] < ring_envelope[0]  # input maxX < ring minX # noqa W503
                    or input_extent[0] > ring_envelope[1]  # input minX > ring maxX # noqa W503
                    or input_extent[3] < ring_envelope[2]  # input maxY < ring minY # noqa W503
                    or input_extent[2] > ring_envelope[3]  # input minY > ring maxY # noqa W503
                )
                if not intersects:
                    log_message("Input vector layer does not intersect with extents.")
                    continue
                else:
                    log_message("Input vector layer intersects with extents, processing...")
            # Create combined layer if not already created
            if combined_layer is None:
                log_message("Creating combined layer...")
                spatial_reference = input_layer.GetSpatialRef()
                geom_type = input_layer.GetGeomType()
                combined_layer = output_datasource.CreateLayer("combined", srs=spatial_reference, geom_type=geom_type)
                if combined_layer is None:
                    raise RuntimeError("Failed to create combined layer in GeoPackage")

                # Copy field definitions from the first layer
                input_layer_definition = input_layer.GetLayerDefn()
                for i in range(input_layer_definition.GetFieldCount()):
                    field_definition = input_layer_definition.GetFieldDefn(i)
                    combined_layer.CreateField(field_definition)

            # Copy features from input layer to combined layer

            input_layer.ResetReading()
            for feature in input_layer:
                combined_feature = ogr.Feature(combined_layer.GetLayerDefn())
                combined_feature.SetGeometry(feature.GetGeometryRef())

                if counter % 1000 == 0 and counter > 0:
                    log_message(f"Processed {counter} features...")
                # Copy all attributes
                for i in range(feature.GetFieldCount()):
                    combined_feature.SetField(i, feature.GetField(i))

                if extent:
                    # if the feature intersects with the extents, add it
                    feature_geom = feature.GetGeometryRef()

                    feature_envelope = feature_geom.GetEnvelope()  # (minX, maxX, minY, maxY)
                    ring_envelope = ring.GetEnvelope()
                    feature_intersects = not (
                        feature_envelope[1] < ring_envelope[0]  # feature maxX < ring minX # noqa W503
                        or feature_envelope[0] > ring_envelope[1]  # feature minX > ring maxX # noqa W503
                        or feature_envelope[3] < ring_envelope[2]  # feature maxY < ring minY # noqa W503
                        or feature_envelope[2] > ring_envelope[3]  # feature minY > ring maxY # noqa W503
                    )
                    if feature_intersects:
                        combined_layer.CreateFeature(combined_feature)
                        # log_message(f"Attribute {field_name}: {field_value}")
                        counter += 1
                    else:
                        # log_message("Feature does not intersect with extents, skipping...")
                        pass
                else:
                    # Calling function did not constrain by extent, add all features

                    combined_layer.CreateFeature(combined_feature)
                    counter += 1
                combined_feature = None
            log_message(f"Finished adding features from {input_vector_path}")
            # Sync to disk
            combined_layer.SyncToDisk()
            output_datasource.FlushCache()
            log_message(f"Combined layer now has {combined_layer.GetFeatureCount()} features")
            # Close input datasource
            input_datasource = None
        # Close output datasource
        combined_layer = None
        output_datasource = None
        log_message(f"Finished combining vectors. Total features: {counter}")
        return True
