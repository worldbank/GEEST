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

from geest.utilities import log_message


class GHSLProcessor:
    """
    A processor to convert GHSL settlement data into vector polygons.

    This class provides functionality to:
    1. Create virtual rasters from multiple single-band TIFF files
    2. Reclassify raster values based on custom logic
    3. Polygonize raster data into vector format
    4. Perform spatial joins between vector layers

    All operations use GDAL raw API exclusively.

    Attributes:
        virtual_raster_path: Path to the created virtual raster file.
        reclassified_raster_path: Path to the reclassified raster output.
        polygonized_vector_path: Path to the polygonized GeoPackage output.
        joined_vector_path: Path to the spatial join result GeoPackage.
    """

    def __init__(
        self,
        input_raster_paths: List[str],
    ):
        """
        Initialize the RasterProcessor with input raster layers.

        Args:
            input_raster_layers: List of file paths to single-band TIFF raster layers.

        Raises:
            ValueError: If input_raster_layers is empty or contains invalid paths.
        """
        if not input_raster_paths:
            raise ValueError("Input raster layers list cannot be empty")

        self.input_raster_layers = input_raster_paths
        self.virtual_raster_path: Optional[str] = None
        self.reclassified_raster_path: Optional[str] = None
        self.polygonized_vector_path: Optional[str] = None
        self.joined_vector_path: Optional[str] = None

        # Verify all input files exist
        for layer_path in input_raster_paths:
            if not Path(layer_path).exists():
                raise ValueError(f"Input raster layer does not exist: {layer_path}")

    def create_virtual_raster(self, output_path: str) -> str:
        """
        Create a virtual raster from multiple single-band TIFF files.

        This method combines all input raster layers into a single virtual raster
        using GDAL's BuildVRT functionality.

        Args:
            output_path: File path for the output virtual raster (.vrt file).

        Returns:
            The path to the created virtual raster file.

        Raises:
            RuntimeError: If virtual raster creation fails.
        """
        build_vrt_options = gdal.BuildVRTOptions(resolution="highest", addAlpha=False)

        virtual_dataset = gdal.BuildVRT(output_path, self.input_raster_layers, options=build_vrt_options)

        if virtual_dataset is None:
            raise RuntimeError(
                f"Failed to create virtual raster at {output_path}. " f"Check input files and GDAL configuration."
            )

        virtual_dataset.FlushCache()
        virtual_dataset = None  # Close the dataset

        self.virtual_raster_path = output_path
        return output_path

    def reclassify_rasters(self, suffix: str = "classified") -> list:
        """
        Reclassify raster values based on specified logic.

        Reclassification rules:
        - Values 10 or 11 are reclassified to 0
        - All other values are reclassified to 1

        The output is a single-band byte (8-bit unsigned integer) raster.

        Args:
            input_raster_path: Path to the input raster to be reclassified.
            output_raster_path: Path for the output reclassified TIFF file.

        Returns:
            The paths to the created reclassified raster files.

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

            self.reclassified_raster_path = output_raster_path
            output_raster_paths.append(output_raster_path)
        return output_raster_paths

    def clean_raster_for_polygonization(self, input_raster_path: str) -> str:
        """
        Clean raster by setting all 0 values to NoData before polygonization.

        This eliminates the need to filter polygons later - only non-zero
        pixels will be polygonized.

        Args:
            input_raster_path: Path to the reclassified raster

        Returns:
            Path to the cleaned raster file
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

    def polygonize_rasters(self, input_raster_paths: list) -> list:
        """
        Convert raster data to polygon vector features using GDAL Polygonize.

        This method uses 8-way connectivity for polygonization and creates a
        GeoPackage vector layer with polygons representing contiguous raster values.
        Polygons with value 0 are filtered out for efficiency.

        The output will be written to a geoparquet file with the same base name
        as the input raster but with a .parquet extension.

        Args:
            input_raster_paths: List of paths to the input raster file to polygonize.

        Returns:
            The list of paths to the created polygonized GeoParquet files.

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

    def spatial_join_with_filter(
        self,
        input_vector_path: str,
        polygonized_vector_path: str,
        output_vector_path: str,
    ) -> str:
        """
        Perform a spatial join between an input vector and polygonized classification.

        This method keeps only those features from the input vector that intersect
        with polygons having a class value of 1 from the polygonized layer.
        Features intersecting with class value 0 are discarded.

        Args:
            input_vector_path: Path to the input vector file for spatial join.
            polygonized_vector_path: Path to the polygonized GeoPackage created earlier.
            output_vector_path: Path for the output GeoPackage with join results.

        Returns:
            The path to the created output vector file.

        Raises:
            RuntimeError: If spatial join fails or files cannot be opened.
        """
        # Open the input vector layer
        input_datasource = ogr.Open(input_vector_path, gdal.GA_ReadOnly)
        if input_datasource is None:
            raise RuntimeError(f"Failed to open input vector: {input_vector_path}")

        input_layer = input_datasource.GetLayer(0)

        # Open the polygonized vector layer
        polygonized_datasource = ogr.Open(polygonized_vector_path, gdal.GA_ReadOnly)
        if polygonized_datasource is None:
            raise RuntimeError(f"Failed to open polygonized vector: {polygonized_vector_path}")

        # Get the filtered layer (should be layer index 1)
        if polygonized_datasource.GetLayerCount() > 1:
            polygonized_layer = polygonized_datasource.GetLayer(1)
        else:
            polygonized_layer = polygonized_datasource.GetLayer(0)

        # Create output datasource
        driver = ogr.GetDriverByName("GPKG")

        if Path(output_vector_path).exists():
            driver.DeleteDataSource(output_vector_path)

        output_datasource = driver.CreateDataSource(output_vector_path)
        if output_datasource is None:
            raise RuntimeError(f"Failed to create output vector datasource: {output_vector_path}")

        # Create output layer with same schema as input
        spatial_reference = input_layer.GetSpatialRef()
        output_layer = output_datasource.CreateLayer(
            "spatial_join_result",
            srs=spatial_reference,
            geom_type=input_layer.GetGeomType(),
        )

        # Copy field definitions from input layer
        input_layer_definition = input_layer.GetLayerDefn()
        for i in range(input_layer_definition.GetFieldCount()):
            field_definition = input_layer_definition.GetFieldDefn(i)
            output_layer.CreateField(field_definition)

        # Perform spatial join with filtering
        input_layer.ResetReading()
        for input_feature in input_layer:
            input_geometry = input_feature.GetGeometryRef()

            # Check if input geometry intersects with any polygon with class = 1
            polygonized_layer.SetSpatialFilter(input_geometry)

            # If there's at least one intersecting polygon, keep the feature
            intersects_with_class_one = False
            for polygonized_feature in polygonized_layer:
                class_value = polygonized_feature.GetField("class")
                if class_value == 1:
                    intersects_with_class_one = True
                    break

            if intersects_with_class_one:
                # Create new feature in output layer
                output_feature = ogr.Feature(output_layer.GetLayerDefn())
                output_feature.SetGeometry(input_geometry)

                # Copy all attributes
                for i in range(input_layer_definition.GetFieldCount()):
                    output_feature.SetField(i, input_feature.GetField(i))

                output_layer.CreateFeature(output_feature)
                output_feature = None

            polygonized_layer.SetSpatialFilter(None)

        # Close all datasources
        input_datasource = None
        polygonized_datasource = None
        output_datasource = None

        self.joined_vector_path = output_vector_path
        return output_vector_path

    def process_full_workflow(
        self,
        virtual_raster_output: str,
        reclassified_output: str,
        polygonized_output: str,
        input_vector_for_join: str,
        joined_output: str,
    ) -> dict:
        """
        Execute the complete raster processing workflow.

        This method orchestrates all processing steps in sequence:
        1. Create virtual raster from input layers
        2. Reclassify the virtual raster
        3. Polygonize the reclassified raster
        4. Perform spatial join with another vector layer

        Args:
            virtual_raster_output: Output path for virtual raster (.vrt).
            reclassified_output: Output path for reclassified raster (.tif).
            polygonized_output: Output path for polygonized vector (.gpkg).
            input_vector_for_join: Input vector file path for spatial join.
            joined_output: Output path for spatial join result (.gpkg).

        Returns:
            Dictionary containing paths to all output files with keys:
            'virtual_raster', 'reclassified_raster', 'polygonized_vector',
            'joined_vector'.

        Raises:
            RuntimeError: If any step in the workflow fails.
        """
        results = {}

        # Step 1: Create virtual raster
        results["virtual_raster"] = self.create_virtual_raster(virtual_raster_output)

        # Step 2: Reclassify the virtual raster
        results["reclassified_raster"] = self.reclassify_raster(results["virtual_raster"], reclassified_output)

        # Step 3: Polygonize the reclassified raster
        results["polygonized_vector"] = self.polygonize_raster(results["reclassified_raster"], polygonized_output)

        # Step 4: Perform spatial join
        results["joined_vector"] = self.spatial_join_with_filter(
            input_vector_for_join, results["polygonized_vector"], joined_output
        )

        return results
