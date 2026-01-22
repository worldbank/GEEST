# -*- coding: utf-8 -*-

"""📦 Ookla Downloader module.

This module contains functionality for ookla downloader.
"""

import os
import timeit
import urllib.request
from typing import Optional

from osgeo import gdal, ogr, osr
from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsFeedback,
    QgsRectangle,
)
from qgis.PyQt.QtCore import QSettings

from geest.core.constants import APPLICATION_NAME
from geest.core.settings import set_setting, setting
from geest.utilities import log_message

ogr.UseExceptions()
gdal.SetConfigOption("AWS_NO_SIGN_REQUEST", "YES")  # no credentials needed for public S3 access
gdal.SetConfigOption("AWS_REGION", "eu-west-1")
gdal.SetConfigOption("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
gdal.SetConfigOption("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", "parquet")


class OoklaException(Exception):
    """Custom exception class for OoklaDownloader errors."""

    pass


class OoklaDownloader:
    """🎯 Ookla Downloader.

    Attributes:
        delete_existing: Delete existing.
        extents: Extents.
        feedback: Feedback.
        filename_prefix: Filename prefix.
        output_path: Output path.
    """

    # Construct VSI S3 path
    FIXED_INTERNET_URL = "/vsis3/ookla-open-data/parquet/performance/type=fixed/year=2025/quarter=3/2025-07-01_performance_fixed_tiles.parquet"
    MOBILE_INTERNET_URL = "/vsis3/ookla-open-data/parquet/performance/type=mobile/year=2025/quarter=3/2025-07-01_performance_mobile_tiles.parquet"

    def __init__(
        self,
        extents: QgsRectangle,
        output_path: str = "",
        filename_prefix: str = "",
        use_cache: bool = False,
        delete_existing: bool = True,
        feedback: Optional[QgsFeedback] = None,
    ):
        """
        Initializes the OoklaDownloader with the specified parameters.

        Args:
            extents (QgsRectangle): The spatial extents for the download, must be in EPSG:4326 projection.
            output_path (str, optional): The output path for the GeoPackage. Defaults to None.
            filename (str, optional): The filename for the output, also used as the layer name in the GeoPackage. Defaults to "".
            use_cache (bool, optional): Whether to use cached data if available. Defaults to False.
            delete_existing (bool, optional): Whether to delete existing files at the output path. Defaults to True.
            feedback (QgsFeedback, optional): Feedback object for progress reporting and cancellation. Defaults to None.

        Attributes:
            extents (QgsRectangle): The spatial extents for the download.
            output_path (str): The output directory path for the GeoPackage files.
            filename_prefix (str): The filename prefix for the output.
                It will have "fixed", "mobile" or "combined" appended to it.
            use_cache (bool): Indicates if cache should be used.
            delete_existing (bool): Indicates if existing files should be deleted.
            feedback (QgsFeedback): Feedback object for progress and cancellation.
            layer: The indexed layer for processing.
        """
        # These are required
        self.extents = extents  # must be specified in the EPSG:4326 projection
        self.output_path = output_path  # The output directory path for GeoPackage files
        self.filename_prefix = filename_prefix  # GeoPackage filename prefix
        self.use_cache = use_cache
        self.delete_existing = delete_existing
        # Unfortunately we are using gdal's built in S3 support,
        # so we cannot route traffic throught QgsNetworkAccessManager
        # self.network_manager = QgsNetworkAccessManager()
        self.feedback = feedback

        # Persist default cache setting on first use.
        qsettings = QSettings()
        cache_key = f"{APPLICATION_NAME}/ookla_use_local_cache"
        if not qsettings.contains(cache_key):
            set_setting(key="ookla_use_local_cache", value=True)

        # Read Ookla threshold settings
        use_thresholds = bool(setting(key="ookla_use_thresholds", default=False))
        self.use_local_cache = bool(setting(key="ookla_use_local_cache", default=True))
        self.local_cache_dir = setting(key="ookla_local_cache_dir", default="")
        if use_thresholds:
            # Convert from Mbps to kbps (multiply by 1000)
            mobile_threshold_mbps = float(setting(key="ookla_mobile_threshold", default=0.0))
            fixed_threshold_mbps = float(setting(key="ookla_fixed_threshold", default=0.0))
            self.mobile_threshold_kbps = mobile_threshold_mbps * 1000
            self.fixed_threshold_kbps = fixed_threshold_mbps * 1000
            log_message(
                f"Ookla thresholds enabled - Mobile: {mobile_threshold_mbps} Mbps, Fixed: {fixed_threshold_mbps} Mbps"
            )
        else:
            # No thresholds - include all data
            self.mobile_threshold_kbps = 0.0
            self.fixed_threshold_kbps = 0.0
            log_message("Ookla thresholds disabled - including all data")

    def _cache_dir(self):
        """
        Returns the directory path used for caching Ookla data, creating it if it does not exist.
        The cache directory is located within the QGIS settings directory under
        'python/ookla_cache/cache'. If the directory does not already exist,
        it will be created.

        Returns:
            str: The absolute path to the Ookla cache directory.
        """

        base = QgsApplication.qgisSettingsDirPath()
        cache_dir = os.path.join(base, "python", "ookla_cache", "cache")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

    def _local_cache_root(self):
        """
        Returns the directory for local Parquet caching.
        """
        if self.local_cache_dir:
            cache_dir = self.local_cache_dir
        else:
            cache_dir = os.path.join(self._cache_dir(), "parquet")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

    def _s3_to_https(self, input_uri: str) -> str:
        """
        Convert /vsis3/bucket/key to https://bucket.s3.amazonaws.com/key.
        """
        if input_uri.startswith("/vsis3/"):
            path = input_uri[len("/vsis3/") :]
            bucket, _, key = path.partition("/")
            return f"https://{bucket}.s3.amazonaws.com/{key}"
        return input_uri

    def _ensure_local_parquet(self, input_uri: str) -> str:
        """
        Download a remote Parquet to local cache if needed and return local path.
        """
        cache_dir = self._local_cache_root()
        filename = os.path.basename(input_uri)
        local_path = os.path.join(cache_dir, filename)
        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            log_message(f"Using cached Ookla parquet: {local_path}")
            return local_path

        url = self._s3_to_https(input_uri)
        tmp_path = f"{local_path}.tmp"
        log_message(f"Downloading Ookla parquet to local cache: {url}")
        try:
            with urllib.request.urlopen(url) as response, open(tmp_path, "wb") as handle:
                while True:
                    if self.feedback is not None and self.feedback.isCanceled():
                        raise OoklaException("Ookla parquet download canceled.")
                    chunk = response.read(8 * 1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
            os.replace(tmp_path, local_path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
        return local_path

    def extract_data(self, output_crs: QgsCoordinateReferenceSystem):
        """
        Main method to extract OOKLA data based on the specified extents and save it to the output path.
        This method handles both fixed and mobile internet data extraction, filtering, and saving.

        Args:
            output_crs (QgsCoordinateReferenceSystem): The coordinate reference system for the output data.

        Raises:
            OoklaException: If there is an error opening the input Parquet files.
        """
        if not self.output_path:
            raise OoklaException("Output path must be specified and non-empty.")
        # Note: All Ookla data and extents must be specified in EPSG:4326 (WGS 84) projection.
        bbox = (
            self.extents.xMinimum(),
            self.extents.yMinimum(),
            self.extents.xMaximum(),
            self.extents.yMaximum(),
        )

        # Prepare output file paths (using GeoPackage for faster Windows performance)
        fixed_output_file = os.path.join(self.output_path, f"{self.filename_prefix}_fixed.gpkg")
        mobile_output_file = os.path.join(self.output_path, f"{self.filename_prefix}_mobile.gpkg")
        combined_output_file = os.path.join(self.output_path, f"{self.filename_prefix}_combined.gpkg")

        fixed_input_uri = self.FIXED_INTERNET_URL
        mobile_input_uri = self.MOBILE_INTERNET_URL
        if self.use_local_cache:
            fixed_input_uri = self._ensure_local_parquet(self.FIXED_INTERNET_URL)
            mobile_input_uri = self._ensure_local_parquet(self.MOBILE_INTERNET_URL)

        # Check if use cache is enabled and files exist
        if self.use_cache and os.path.exists(combined_output_file):
            log_message(f"Using cached Ookla data at: {combined_output_file}")
            return

        # Extract fixed internet data
        log_message("Starting extraction of fixed internet data...")
        try:
            self.extract_ookla_data(fixed_input_uri, fixed_output_file, bbox, output_crs, self.fixed_threshold_kbps)
        except Exception as e:
            raise OoklaException(f"Error extracting fixed internet data: {e}")

        # Extract mobile internet data
        log_message("Starting extraction of mobile internet data...")
        try:
            self.extract_ookla_data(mobile_input_uri, mobile_output_file, bbox, output_crs, self.mobile_threshold_kbps)
        except Exception as e:
            raise OoklaException(f"Error extracting mobile internet data: {e}")

        # Combine fixed and mobile data
        log_message("Combining fixed and mobile internet data...")
        try:
            self.combine_vectors([fixed_output_file, mobile_output_file], combined_output_file, output_crs)
        except Exception as e:
            raise OoklaException(f"Error combining data: {e}")

        log_message(f"Data extraction complete. Combined data saved to: {combined_output_file}")

    def analysis_intro(self):
        """⚙️ Analysis intro.

        Returns:
            The result of the operation.
        """
        title = "Spatial Filter"
        body = (
            f"Filtering Records by Bounding Box\n"
            f"We're narrowing the dataset from the Parquet file\n"
            f"to only those geometries intersecting the bounding box below.\n"
            f"Mobile Threshold: [bold]{self.mobile_threshold_kbps} kbps ({self.mobile_threshold_kbps/1000} Mbps)\n"
            f"Fixed Threshold: [bold]{self.fixed_threshold_kbps} kbps ({self.fixed_threshold_kbps/1000} Mbps)\n"
            f"Bounding Box Coordinates:\n"
            f"  Min X: {self.extents.xMinimum()}\n"
        )
        return (title, body)

    def extract_ookla_data(
        self, input_uri, output_file, bbox_4326, output_crs: QgsCoordinateReferenceSystem, speed_threshold_kbps: float
    ):
        """
        This is the core logic for extracting data from OOKLA. The data
        can either be downloaded from S3 or read from a local Parquet file.

        The data stored in the OOKLA parquet is not a GeoParquet but a regular Parquet (see
        below for the structure). So to process it, we download the data using attribute  filters
        to only fetch records within our bbox and with sufficient upload and download speeds.

        Because it is a parquet file, GDAL will still efficiently fetch only the required row groups
        using HTTP range requests. The output is saved as GeoPackage for better Windows performance.

        Args:
            input_uri (str): The URI of the input Parquet file (can be a local path or S3 path).
            output_file (str): The path to the output GeoPackage file where filtered data will be saved.
            bbox_4326 (tuple): A tuple representing the bounding box (min_x, min_y, max_x, max_y) for filtering.
            output_crs (QgsCoordinateReferenceSystem): The coordinate reference system for the output data.
            speed_threshold_kbps (float): Minimum speed threshold in kbps for both upload and download.
        """
        # Example row from the Parquet file:
        # OGRFeature(ookla):349644
        # quadkey (String) = 0230131221113313
        # tile (String) = POLYGON((-114.614868164062 34.8273320619816, -114.609375 34.8273320619816, -114.609375 34.822822727237, -114.614868164062 34.822822727237, -114.614868164062 34.8273320619816))
        # tile_x (Real) = -114.6121
        # tile_y (Real) = 34.8251
        # avg_d_kbps (Integer64) = 29684
        # avg_u_kbps (Integer64) = 3512
        # avg_lat_ms (Integer64) = 36
        # avg_lat_down_ms (Integer) = 173
        # avg_lat_up_ms (Integer) = 2571
        # tests (Integer64) = 11
        # devices (Integer64) = 1

        found_bbox = (0, 0, 0, 0)  # As we iterate over the features, we'll find the actual bbox
        start_time = timeit.default_timer()

        # Open the input Parquet file from S3
        parquet_driver = ogr.GetDriverByName("Parquet")
        if parquet_driver is None:
            log_message("❌ Parquet driver not available.")
            raise OoklaException("Parquet driver not available.")

        dataset = parquet_driver.Open(input_uri, 0)
        if dataset is None:
            raise OoklaException(f"Failed to open OOKLA data source: {input_uri}")

        # transform to output CRS
        transform = None

        target_spatial_reference = osr.SpatialReference()
        target_spatial_reference.ImportFromEPSG(4326)
        if output_crs.authid() != "EPSG:4326":
            source_spatial_reference = osr.SpatialReference()
            source_spatial_reference.ImportFromEPSG(4326)
            target_spatial_reference = osr.SpatialReference()
            target_spatial_reference.ImportFromEPSG(int(output_crs.authid().split(":")[1]))
            # Force traditional GIS axis order for both source and target
            if hasattr(source_spatial_reference, "SetAxisMappingStrategy"):
                source_spatial_reference.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            if hasattr(target_spatial_reference, "SetAxisMappingStrategy"):
                target_spatial_reference.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            transform = osr.CoordinateTransformation(source_spatial_reference, target_spatial_reference)
            log_message(f"Transforming output to {output_crs.authid()}")
        else:
            log_message("Writing results to EPSG:4326")

        layer = dataset.GetLayer()

        # Create output GeoPackage (much faster on Windows than Parquet)
        gpkg_driver = ogr.GetDriverByName("GPKG")
        if gpkg_driver is None:
            log_message("❌ GPKG driver not available.")
            raise OoklaException("GPKG driver not available.")

        # Delete existing file if it exists (GPKG doesn't overwrite)
        if os.path.exists(output_file):
            os.remove(output_file)

        out_dataset = gpkg_driver.CreateDataSource(output_file)
        out_layer = out_dataset.CreateLayer("ookla_data", target_spatial_reference, geom_type=ogr.wkbPolygon)

        # Copy fields
        # We only will keep the quadkey field and discard the rest
        out_layer.CreateField(ogr.FieldDefn("quadkey", ogr.OFTString))

        min_x, min_y, max_x, max_y = bbox_4326
        count = 0
        kept_count = 0

        # Apply attribute filter for speed and extent directly at the layer level
        # Use the passed speed_threshold_kbps for both upload and download filtering
        filter_expr = (
            f"avg_u_kbps >= {speed_threshold_kbps} AND "
            f"avg_d_kbps >= {speed_threshold_kbps} AND "
            f"tile_x >= {min_x} AND tile_x <= {max_x} AND "
            f"tile_y >= {min_y} AND tile_y <= {max_y}"
        )
        log_message(f"Applying Ookla filter: {filter_expr}")
        layer.SetAttributeFilter(filter_expr)

        # Handle GDAL Parquet driver issues
        try:
            feature_count = layer.GetFeatureCount()
        except RuntimeError:
            feature_count = 0  # Process without knowing total count

        out_layer_defn = out_layer.GetLayerDefn()

        found_min_x = found_min_y = found_max_x = found_max_y = None
        for feature in layer:
            x = feature.GetField("tile_x")
            y = feature.GetField("tile_y")

            # Update found_bbox
            if found_min_x is None or x < found_min_x:
                found_min_x = x
            if found_min_y is None or y < found_min_y:
                found_min_y = y
            if found_max_x is None or x > found_max_x:
                found_max_x = x
            if found_max_y is None or y > found_max_y:
                found_max_y = y

            kept_count += 1
            geom = ogr.CreateGeometryFromWkt(feature.GetField("tile"))
            if transform:
                result = geom.Transform(transform)
                if result != 0:
                    log_message(f"Geometry transformation failed for feature {feature.GetField('quadkey')}")
            out_feature = ogr.Feature(out_layer_defn)
            out_feature.SetGeometry(geom.Clone())
            out_feature.SetField("quadkey", feature.GetField("quadkey"))
            out_layer.CreateFeature(out_feature)
            out_feature.Destroy()

            count += 1
            # Update progress every 100 features
            if count % 100 == 0:
                if feature_count > 0:
                    progress = int((count / feature_count) * 100)
                    if self.feedback is not None:
                        self.feedback.setProgress(progress)
                # Log every 1000 features to avoid log spam
                if count % 1000 == 0:
                    log_message(f"Processed {count} of {feature_count} features...")
                    log_message(f"Kept {kept_count} features so far...")

        # Clean up
        dataset = None
        out_dataset = None

        found_bbox = (found_min_x, found_min_y, found_max_x, found_max_y)
        log_message("OOKLA processing finished")
        log_message(
            f"✅ Filtering complete!\n"
            f"Kept {kept_count} of {feature_count} features.\n"
            f"Filtered data saved to:{output_file}"
            f"Found BBOX: {found_bbox}"
        )
        self.print_timings(
            start_time, title="GeoPackage file generation", message=f"Wrote {kept_count} features to {output_file}."
        )

    def print_timings(self, start_time, title, message):
        """
            Show timing information for a process.

        Args:
            start_time (float): The start time of the process.
            title (str): The title of the timing message.
            message (str): The message to display with the timing information.
        """
        run_time = timeit.default_timer() - start_time
        hours = int(run_time // 3600)
        minutes = int((run_time % 3600) // 60)
        seconds = run_time % 60
        log_message(f"{title}")
        log_message(f"{message}\n" f"⏱️ Hours:{hours}hrs\n" f"⏱️ Minutes:{minutes}mins\n" f"⏱️ Seconds:{seconds:.2}s\n")

    def rasterize_filtered_data(self, input_file, output_raster, pixel_size=0.01):
        """
        This function rasterizes the filtered GeoPackage data into a GeoTIFF with the specified pixel size.

        gdal_rasterize -l ookla_data -burn 1.0 -tr 0.001 0.001 -init 0.0
            -a_nodata 0.0 -ot Byte -of GTiff -co COMPRESS=DEFLATE -co PREDICTOR=2
            -co ZLEVEL=9
            /path/to/ookla_filtered.gpkg OUTPUT.tif

        Args:
            input_file (str): The path to the input GeoPackage file.
            output_raster (str): The path to the output raster file.
            pixel_size (float, optional): The pixel size for the rasterization. Defaults to 0.01.

        """
        start_time = timeit.default_timer()
        NoData_value = 0
        gdal.Rasterize(
            output_raster,
            input_file,
            format="GTIFF",
            outputType=gdal.GDT_Byte,
            creationOptions=[
                "COMPRESS=DEFLATE",
                "PREDICTOR=2",
                "ZLEVEL=9",
            ],
            noData=NoData_value,
            initValues=NoData_value,
            xRes=pixel_size,
            yRes=pixel_size,
            allTouched=True,
            burnValues=1,
        )
        self.print_timings(start_time, title="Rasterization complete.", message=f"Raster saved to {output_raster}.")

    def combine_vectors(self, input_files, output_file, output_crs: QgsCoordinateReferenceSystem):
        """
        This function combines multiple GeoPackage files into a single output file.

        Args:
            input_files (list): A list of input GeoPackage file paths to be combined.
            output_file (str): The path to the output combined GeoPackage file.
            output_crs (QgsCoordinateReferenceSystem): The coordinate reference system for the output data.
        """
        start_time = timeit.default_timer()
        quadkey_set = set()
        duplicate_count = 0
        target_spatial_reference = osr.SpatialReference()
        target_spatial_reference.ImportFromEPSG(4326)
        if output_crs.authid() != "EPSG:4326":
            target_spatial_reference.ImportFromEPSG(int(output_crs.authid().split(":")[1]))

        # Use GPKG driver for output
        gpkg_driver = ogr.GetDriverByName("GPKG")
        if gpkg_driver is None:
            log_message("❌ GPKG driver not available.")
            raise OoklaException("GPKG driver not available.")

        # Delete existing file if it exists
        if os.path.exists(output_file):
            os.remove(output_file)

        out_dataset = gpkg_driver.CreateDataSource(output_file)
        out_layer = out_dataset.CreateLayer("ookla_combined", target_spatial_reference, geom_type=ogr.wkbPolygon)
        out_layer.CreateField(ogr.FieldDefn("quadkey", ogr.OFTString))

        out_layer_defn = out_layer.GetLayerDefn()

        for input_file in input_files:
            # Open input GeoPackage
            dataset = gpkg_driver.Open(input_file, 0)
            if dataset is None:
                log_message(f"⚠️ Could not open {input_file}, skipping...")
                continue

            layer = dataset.GetLayer(0)  # GeoPackage: get first layer

            for feature in layer:
                quadkey = feature.GetField("quadkey")
                if quadkey in quadkey_set:
                    duplicate_count += 1
                    continue
                else:
                    quadkey_set.add(quadkey)
                geom = feature.GetGeometryRef()
                out_feature = ogr.Feature(out_layer_defn)
                out_feature.SetGeometry(geom.Clone())
                out_feature.SetField("quadkey", quadkey)
                out_layer.CreateFeature(out_feature)
                out_feature.Destroy()

            dataset = None

        out_dataset = None
        dataset = None
        quadkey_set = None
        self.print_timings(
            start_time,
            title="Vector Combination Complete",
            message=f"Combined GeoPackage saved to {output_file} with {duplicate_count} duplicates found.",
        )
