# -*- coding: utf-8 -*-

"""📦 Ghsl Downloader module.

This module contains functionality for ghsl downloader.
"""
import os
import zipfile

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsFeatureRequest,
    QgsFeedback,
    QgsFileDownloader,
    QgsNetworkAccessManager,
    QgsRectangle,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QEventLoop, QUrl

from geest.utilities import log_message, resources_path


class GHSLDownloader:
    """🎯 G H S L Downloader.

    Attributes:
        base_url: Base url.
        delete_existing: Delete existing.
        extents: Extents.
        feedback: Feedback.
        filename: Filename.
    """

    BASE_URL = (
        "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/"
        "GHS_SMOD_GLOBE_R2023A/GHS_SMOD_E2030_GLOBE_R2023A_54009_1000/"
        "V2-0/tiles/"
    )

    def __init__(
        self,
        extents: QgsRectangle,
        output_path: str = None,
        filename: str = "",  # will also set the layer name in the gpkg
        use_cache: bool = False,
        delete_existing: bool = True,
        feedback: QgsFeedback = None,
    ):
        """
        Initializes the GHSLDownloader with the specified parameters.

        Args:
            extents (QgsRectangle): The spatial extents for the download, must be in Mollweide ESRI:54009 projection.
            output_path (str, optional): The output path for the GeoPackage. Defaults to None.
            filename (str, optional): The filename for the output, also used as the layer name in the GeoPackage. Defaults to "".
            use_cache (bool, optional): Whether to use cached data if available. Defaults to False.
            delete_existing (bool, optional): Whether to delete existing files at the output path. Defaults to True.
            feedback (QgsFeedback, optional): Feedback object for progress reporting and cancellation. Defaults to None.

        Attributes:
            extents (QgsRectangle): The spatial extents for the download.
            output_path (str): The output path for the GeoPackage.
            filename (str): The filename and layer name for the output.
            use_cache (bool): Indicates if cache should be used.
            delete_existing (bool): Indicates if existing files should be deleted.
            network_manager (QgsNetworkAccessManager): Network manager for handling requests.
            feedback (QgsFeedback): Feedback object for progress and cancellation.
            layer: The indexed layer for processing.
            base_url (str): The base URL for data download.
        """
        # These are required
        self.extents = extents  # must be specified in the Mollweide ESRI:54009 projection
        self.output_path = output_path  # The output path for the GeoPackage
        self.filename = filename  # will also set the layer name in the gpkg
        self.use_cache = use_cache
        self.delete_existing = delete_existing
        self.network_manager = QgsNetworkAccessManager()
        self.feedback = feedback
        self.layer = self._index_layer()
        self.base_url = self.BASE_URL

    # ---------------- Utilities ----------------
    def _cache_dir(self):
        """
        Returns the directory path used for caching GHSL data, creating it if it does not exist.
        The cache directory is located within the QGIS settings directory under
        'python/plugins/ghsl_cache/cache'. If the directory does not already exist,
        it will be created.

        Returns:
            str: The absolute path to the GHSL cache directory.
        """

        base = QgsApplication.qgisSettingsDirPath()
        cache_dir = os.path.join(base, "python", "ghsl_cache", "cache")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

    # ---------------- Tile grid ----------------
    def _index_layer(self) -> QgsVectorLayer:
        """
        Create an index layer using the geoparquet file
        in the resources/gsh folder.

        This layer can be used to find which tiles intersect
        the study area so that we can download GSH data for
        the area of interest.

        Returns:
            QgsVectorLayer: The index layer.
        """
        layer_path = resources_path("resources", "ghsl", "ghs-mod-2023-tile-scheme.parquet")
        log_message(f"Loading tile index layer from {layer_path}")
        layer = QgsVectorLayer(layer_path, "tiles", "ogr")
        # Set the layer crs to mollweide
        layer.setCrs(QgsCoordinateReferenceSystem("ESRI:54009"))

        return layer

    def tiles_intersecting_bbox(self):
        """
        Finds and returns the IDs of tiles that intersect with the current bounding box.
        This method queries the associated layer for features whose geometries intersect
        with the bounding box defined by `self.extents`. The IDs of the intersecting tiles
        are collected and returned as a list.

        Returns:
            list: A list of tile IDs (as found in the 'tile_id' attribute) that intersect with the bounding box.
        """

        log_message(f"Finding tiles intersecting bbox: {self.extents.toString()}")

        # get the features that intersect the bbox
        intersecting = []
        request = QgsFeatureRequest().setFilterRect(self.extents)
        for feat in self.layer.getFeatures(request):
            log_message(f"\n - {feat['tile_id']}")
            intersecting.append(feat["tile_id"])
        return intersecting

    def download_and_unpack_tile(self, tile_id):
        """Download and unpack a GHS tile.

        Args:
            tile_id (str): The ID of the tile to download.

        Returns:
            list: A list of paths to the unpacked files.
        """
        cache_dir = self._cache_dir()
        zip_name = f"GHS_SMOD_E2030_GLOBE_R2023A_54009_1000_V2_0_{tile_id}.zip"
        zip_path = os.path.join(cache_dir, zip_name)

        # 1. Cache check
        if not os.path.exists(zip_path):
            url = self.BASE_URL + zip_name
            log_message(f"Downloading {url} to {zip_path}...")

            loop = QEventLoop()

            def on_finished():
                """🔄 On finished."""
                log_message(f"Download finished: {zip_path}")
                loop.quit()

            def on_error(err_code, err_msg):
                """🔄 On error.

                Args:
                    err_code: Err code.
                    err_msg: Err msg.
                """
                log_message(f"Download error {err_code}: {err_msg}")
                loop.quit()

            downloader = QgsFileDownloader(QUrl(url), zip_path, authcfg="", httpMethod=Qgis.HttpMethod.Get)
            downloader.downloadCompleted.connect(on_finished)
            downloader.downloadError.connect(on_error)

            loop.exec_()
        else:
            log_message(f"Using cached zip: {zip_path}")

        # 2. Unpack
        extracted_dir = os.path.join(cache_dir, tile_id)
        os.makedirs(extracted_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zf:
            if not all(os.path.exists(os.path.join(extracted_dir, f)) for f in zf.namelist()):
                zf.extractall(path=extracted_dir)
                log_message(f"Extracted {tile_id} to {extracted_dir}")
            else:
                log_message(f"{tile_id} already unpacked in {extracted_dir}")

            return [os.path.join(extracted_dir, f) for f in zf.namelist()]
