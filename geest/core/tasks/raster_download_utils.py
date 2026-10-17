# -*- coding: utf-8 -*-
"""Shared helpers for downloading a remote raster and cropping it locally.

Some network/proxy environments block the HTTP Range requests GDAL's
/vsicurl/ driver needs, so global/continental source rasters are downloaded
in full via QgsNetworkAccessManager (the same pattern S2SClient uses) and
then cropped to the study area with a purely local gdal.Translate call.
Used by both the nighttime lights and environmental hazard downloader tasks.
"""

import random
import time
from typing import Callable

from osgeo import gdal
from qgis.core import QgsNetworkAccessManager, QgsRectangle
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

RETRYABLE_STATUS_CODES = {429, 502, 503, 504}
MAX_ATTEMPTS = 4
BACKOFF_BASE_SECONDS = 2.0


def download_file_with_retry(
    url: str,
    destination: str,
    is_canceled: Callable[[], bool],
    on_progress: Callable[[str], None],
    description: str,
    max_attempts: int = MAX_ATTEMPTS,
) -> bool:
    """Download a URL to a local file synchronously, retrying transient HTTP failures.

    Args:
        url: Source URL. May contain percent-encoded characters.
        destination: Local file path to write the downloaded bytes to.
        is_canceled: Callable returning True if the owning task was cancelled.
        on_progress: Callable invoked with human-readable progress messages.
        description: Human-readable name of the dataset, used in error messages.
        max_attempts: Maximum number of attempts before giving up.

    Returns:
        True on success, False if cancelled before completion.

    Raises:
        RuntimeError: On a non-retryable HTTP error or once retries are exhausted.
    """
    network_manager = QgsNetworkAccessManager.instance()
    last_error_message = ""

    for attempt in range(1, max_attempts + 1):
        if is_canceled():
            return False

        request = QNetworkRequest(QUrl(url, QUrl.ParsingMode.TolerantMode))
        reply = network_manager.blockingGet(request)
        status_code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)

        if status_code == 200:
            content = bytes(reply.content())
            if not content:
                last_error_message = f"Downloaded {description} was empty."
            else:
                with open(destination, "wb") as handle:
                    handle.write(content)
                return True
        elif status_code in RETRYABLE_STATUS_CODES:
            last_error_message = f"HTTP {status_code} (temporarily unavailable)"
        else:
            raise RuntimeError(f"Failed to download {description} (HTTP {status_code}) from {url}")

        if attempt >= max_attempts:
            raise RuntimeError(f"Failed to download {description} after {attempt} attempts: {last_error_message}")

        delay = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)) + random.uniform(0.0, 1.0)  # nosec B311
        on_progress(f"{description} source busy, retrying in {delay:.0f}s (attempt {attempt}/{max_attempts})...")
        time.sleep(delay)

    return False


def crop_raster_to_extent(
    source_path: str,
    destination_path: str,
    extent: QgsRectangle,
    extent_crs_authid: str,
    description: str,
    buffer_pct: float = 0.02,
) -> None:
    """Crop a local raster to a buffered extent via gdal.Translate.

    Args:
        source_path: Path to the full downloaded raster.
        destination_path: Path to write the cropped raster to.
        extent: Bounding box to crop to.
        extent_crs_authid: CRS authid (e.g. "EPSG:32626") that ``extent`` is in.
        description: Human-readable name of the dataset, used in error messages.
        buffer_pct: Fraction of the extent's larger dimension to pad by, to
            avoid edge gaps when the output is later reprojected/resampled.

    Raises:
        RuntimeError: If gdal.Translate fails to produce an output dataset.
    """
    buffered_extent = extent.buffered(max(extent.width(), extent.height()) * buffer_pct)
    dataset = gdal.Translate(
        destination_path,
        source_path,
        format="GTiff",
        projWin=[
            buffered_extent.xMinimum(),
            buffered_extent.yMaximum(),
            buffered_extent.xMaximum(),
            buffered_extent.yMinimum(),
        ],
        projWinSRS=extent_crs_authid,
    )
    if dataset is None:
        raise RuntimeError(
            f"Failed to crop {description}: {gdal.GetLastErrorMsg() or 'gdal.Translate returned no dataset.'}"
        )
    dataset = None
