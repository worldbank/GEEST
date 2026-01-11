# -*- coding: utf-8 -*-
"""EPLEX Raster Processor module.

This module contains functionality for creating rasters filled with EPLEX scores
when women considerations are disabled.
"""
import os
from typing import Optional

import numpy as np
from osgeo import gdal
from qgis.core import Qgis

from geest.utilities import log_message


def create_eplex_raster(
    eplex_score: float,
    template_raster_path: str,
    output_path: str,
) -> Optional[str]:
    """Create a raster filled with the EPLEX score value.

    This function creates a new raster with the same spatial properties
    (extent, resolution, projection) as a template raster, but with all
    pixels filled with the EPLEX score value.

    Args:
        eplex_score: The EPLEX score value to fill the raster with (0-5 range)
        template_raster_path: Path to a template raster to copy spatial properties from
        output_path: Path where the output raster should be saved

    Returns:
        Path to the created raster file, or None if creation failed
    """
    if not os.path.exists(template_raster_path):
        log_message(
            f"Template raster does not exist: {template_raster_path}",
            tag="Geest",
            level=Qgis.Warning,
        )
        return None

    try:
        # Open template raster
        template_ds = gdal.Open(template_raster_path)
        if not template_ds:
            log_message(
                f"Failed to open template raster: {template_raster_path}",
                tag="Geest",
                level=Qgis.Warning,
            )
            return None

        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Create output raster with same dimensions as template
        driver = gdal.GetDriverByName("GTiff")
        out_ds = driver.Create(
            output_path,
            template_ds.RasterXSize,
            template_ds.RasterYSize,
            1,
            gdal.GDT_Float32,
        )

        if not out_ds:
            log_message(
                f"Failed to create output raster: {output_path}",
                tag="Geest",
                level=Qgis.Warning,
            )
            template_ds = None
            return None

        # Set geotransform and projection from template
        out_ds.SetGeoTransform(template_ds.GetGeoTransform())
        out_ds.SetProjection(template_ds.GetProjection())

        # Get output band
        band = out_ds.GetRasterBand(1)

        # Read template band to get nodata mask
        template_band = template_ds.GetRasterBand(1)
        template_data = template_band.ReadAsArray()
        template_nodata = template_band.GetNoDataValue()

        # Create output array filled with EPLEX score
        out_array = np.full_like(template_data, eplex_score, dtype=np.float32)

        # Preserve nodata areas from template
        if template_nodata is not None:
            out_array[template_data == template_nodata] = template_nodata
            band.SetNoDataValue(template_nodata)

        # Write array to output raster
        band.WriteArray(out_array)
        band.FlushCache()

        # Close datasets
        template_ds = None
        out_ds = None

        log_message(
            f"Created EPLEX raster ({eplex_score}): {output_path}",
            tag="Geest",
            level=Qgis.Info,
        )

        return output_path

    except Exception as e:
        log_message(
            f"Error creating EPLEX raster: {e}",
            tag="Geest",
            level=Qgis.Critical,
        )
        return None
