# -*- coding: utf-8 -*-

import os
import zipfile

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeatureRequest,
    QgsFeedback,
    QgsFileDownloader,
    QgsMessageLog,
    QgsNetworkAccessManager,
    QgsProject,
    QgsRectangle,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QEventLoop
from qgis.utils import iface

from geest.utilities import log_message, resources_path


class GHSLDownloader:
    BASE_URL = (
        "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/"
        "GHS_SMOD_GLOBE_R2023A/GHS_SMOD_E2030_GLOBE_R2023A_54009_1000/"
        "V2-0/tiles/"
    )

    def __init__(
        self,
        extents: QgsRectangle,
        output_path: str = None,
        output_crs: QgsCoordinateReferenceSystem = None,
        filename: str = "",  # will also set the layer name in the gpkg
        use_cache: bool = False,
        delete_gpkg: bool = True,
        feedback: QgsFeedback = None,
    ):
        # These are required
        self.extents = extents
        self.output_path = output_path  # The output path for the GeoPackage
        self.output_crs = output_crs
        self.filename = filename  # will also set the layer name in the gpkg
        self.use_cache = use_cache
        self.delete_gpkg = delete_gpkg
        self.network_manager = QgsNetworkAccessManager()
        self.feedback = feedback

        self.base_url = self.BASE_URL

        self.plugin_name = "ghsl_fetcher"
        self.layer = self._index_layer()
        self.crs_wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        self.crs_mollweide = QgsCoordinateReferenceSystem("ESRI:54009")
        self.transform = QgsCoordinateTransform(
            self.crs_wgs84, self.crs_mollweide, QgsProject.instance().transformContext()
        )

    # ---------------- Utilities ----------------
    def _cache_dir(self):
        base = QgsApplication.qgisSettingsDirPath()
        cache_dir = os.path.join(base, "python", "plugins", self.plugin_name, "cache")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

    def _notify(self, msg, level=Qgis.Info, tag="GHSLFetcher"):
        QgsMessageLog.logMessage(msg, tag, level)
        if not iface:
            return
        if level == Qgis.Critical:
            iface.messageBar().pushCritical(tag, msg)
        elif level == Qgis.Warning:
            iface.messageBar().pushWarning(tag, msg)
        elif level == Qgis.Success:
            iface.messageBar().pushSuccess(tag, msg)
        else:
            iface.messageBar().pushMessage(tag, msg, level=Qgis.Info, duration=5)

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
        log_message(f"Finding tiles intersecting bbox: {self.extents.toString()}")
        bbox_mollweiide = self.transform.transform(self.extents)
        log_message(f"\n Transformed to Mollweide: {bbox_mollweiide.toString()}")

        # get the features that intersect the bbox
        intersecting = []
        request = QgsFeatureRequest().setFilterRect(bbox_mollweiide)
        for feat in self.layer.getFeatures(request):
            log_message(f"\n - {feat['tile_id']}")
            intersecting.append(feat["tile_id"])
        return intersecting

    def download_and_unpack_tile(self, tile_id):
        cache_dir = self._cache_dir()
        zip_name = f"GHS_SMOD_E2030_GLOBE_R2023A_54009_1000_V2_0_{tile_id}.zip"
        zip_path = os.path.join(cache_dir, zip_name)

        # 1. Cache check
        if not os.path.exists(zip_path):
            url = self.BASE_URL + zip_name
            self._notify(f"Downloading {url} …", Qgis.Info)

            loop = QEventLoop()

            def on_finished():
                self._notify(f"Downloaded {zip_name} → {zip_path}", Qgis.Success)
                loop.quit()

            def on_error(err_code, err_msg):
                self._notify(f"Download error {err_code}: {err_msg}", Qgis.Critical)
                loop.quit()

            downloader = QgsFileDownloader(url, zip_path, authcfg="", method=QgsFileDownloader.HttpGet)
            downloader.downloadCompleted.connect(on_finished)
            downloader.downloadError.connect(on_error)

            loop.exec_()
        else:
            self._notify(f"Using cached zip: {zip_path}", Qgis.Info)

        # 2. Unpack
        extracted_dir = os.path.join(cache_dir, tile_id)
        os.makedirs(extracted_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zf:
            if not all(os.path.exists(os.path.join(extracted_dir, f)) for f in zf.namelist()):
                zf.extractall(path=extracted_dir)
                self._notify(f"Extracted {tile_id} → {extracted_dir}", Qgis.Success)
            else:
                self._notify(f"{tile_id} already unpacked in {extracted_dir}", Qgis.Info)

            return [os.path.join(extracted_dir, f) for f in zf.namelist()]
