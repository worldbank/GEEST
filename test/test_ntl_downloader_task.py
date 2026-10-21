# -*- coding: utf-8 -*-
"""Unit tests for the nighttime lights downloader task."""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from qgis.core import QgsRectangle
from qgis.PyQt.QtNetwork import QNetworkRequest

from geest.core.tasks.ntl_downloader_task import NTLDownloaderTask


class _FakeReply:
    """Simple fake reply object for QgsNetworkAccessManager mocks."""

    def __init__(self, status_code, content):
        self._status_code = status_code
        self._content = content

    def attribute(self, key):
        if key == QNetworkRequest.Attribute.HttpStatusCodeAttribute:
            return self._status_code
        return None

    def content(self):
        return self._content


class TestNTLDownloaderTask(unittest.TestCase):
    """Tests for NTLDownloaderTask behavior."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_ntl_task_")
        self.extent = QgsRectangle(674100.0, 1637600.0, 964800.0, 1903500.0)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_empty_extent_raises(self):
        with self.assertRaises(ValueError):
            NTLDownloaderTask(
                extent=QgsRectangle(),
                extent_crs_authid="EPSG:32626",
                working_dir=self.temp_dir,
            )

    def test_missing_working_dir_raises(self):
        with self.assertRaises(ValueError):
            NTLDownloaderTask(extent=self.extent, extent_crs_authid="EPSG:32626", working_dir="")

    @patch("geest.core.tasks.raster_download_utils.gdal.Translate")
    @patch("geest.core.tasks.raster_download_utils.QgsNetworkAccessManager")
    def test_run_success_writes_output(self, mock_network_access_manager, mock_translate):
        manager = MagicMock()
        manager.blockingGet.return_value = _FakeReply(200, b"fake-global-tif-bytes")
        mock_network_access_manager.instance.return_value = manager

        def fake_translate(destination, source_path, **kwargs):
            self.assertTrue(os.path.exists(source_path))
            with open(destination, "wb") as handle:
                handle.write(b"fake-cropped-tif-bytes")
            return object()

        mock_translate.side_effect = fake_translate

        task = NTLDownloaderTask(
            extent=self.extent,
            extent_crs_authid="EPSG:32626",
            working_dir=self.temp_dir,
            filename="ntl_test",
        )

        success = task.run()
        self.assertTrue(success)
        self.assertTrue(os.path.exists(task.output_path))
        self.assertEqual(task.output_path, os.path.join(self.temp_dir, "study_area", "ntl_test.tif"))
        # The downloaded global temp file must be cleaned up afterwards.
        self.assertFalse(os.path.exists(task._temp_global_path))

    @patch("geest.core.tasks.raster_download_utils.QgsNetworkAccessManager")
    def test_run_fails_on_permanent_http_error(self, mock_network_access_manager):
        manager = MagicMock()
        manager.blockingGet.return_value = _FakeReply(404, b"")
        mock_network_access_manager.instance.return_value = manager

        task = NTLDownloaderTask(
            extent=self.extent,
            extent_crs_authid="EPSG:32626",
            working_dir=self.temp_dir,
            filename="ntl_test_404",
        )

        errors = []
        task.error_occurred.connect(errors.append)

        success = task.run()
        self.assertFalse(success)
        self.assertFalse(os.path.exists(task.output_path))
        self.assertTrue(errors)
        manager.blockingGet.assert_called_once()  # no retries for a permanent 404
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "ntl_download_error.txt")))

    @patch("geest.core.tasks.raster_download_utils.time.sleep")
    @patch("geest.core.tasks.raster_download_utils.QgsNetworkAccessManager")
    def test_run_retries_transient_http_error_then_succeeds(self, mock_network_access_manager, mock_sleep):
        manager = MagicMock()
        manager.blockingGet.side_effect = [
            _FakeReply(503, b""),
            _FakeReply(503, b""),
            _FakeReply(200, b"fake-global-tif-bytes"),
        ]
        mock_network_access_manager.instance.return_value = manager

        with patch("geest.core.tasks.raster_download_utils.gdal.Translate") as mock_translate:

            def fake_translate(destination, source_path, **kwargs):
                with open(destination, "wb") as handle:
                    handle.write(b"fake-cropped-tif-bytes")
                return object()

            mock_translate.side_effect = fake_translate

            task = NTLDownloaderTask(
                extent=self.extent,
                extent_crs_authid="EPSG:32626",
                working_dir=self.temp_dir,
                filename="ntl_test_retry",
            )
            success = task.run()

        self.assertTrue(success)
        self.assertTrue(os.path.exists(task.output_path))
        self.assertEqual(manager.blockingGet.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("geest.core.tasks.raster_download_utils.time.sleep")
    @patch("geest.core.tasks.raster_download_utils.QgsNetworkAccessManager")
    def test_run_fails_after_exhausting_retries(self, mock_network_access_manager, mock_sleep):
        manager = MagicMock()
        manager.blockingGet.return_value = _FakeReply(503, b"")
        mock_network_access_manager.instance.return_value = manager

        task = NTLDownloaderTask(
            extent=self.extent,
            extent_crs_authid="EPSG:32626",
            working_dir=self.temp_dir,
            filename="ntl_test_fail",
        )

        errors = []
        task.error_occurred.connect(errors.append)

        success = task.run()
        self.assertFalse(success)
        self.assertFalse(os.path.exists(task.output_path))
        self.assertTrue(errors)
        self.assertEqual(manager.blockingGet.call_count, 4)

    @patch("geest.core.tasks.raster_download_utils.gdal.Translate")
    @patch("geest.core.tasks.raster_download_utils.QgsNetworkAccessManager")
    def test_requested_year_is_used_in_source_url(self, mock_network_access_manager, mock_translate):
        manager = MagicMock()
        requested_urls = []

        def fake_blocking_get(request):
            requested_urls.append(request.url().toString())
            return _FakeReply(200, b"fake-global-tif-bytes")

        manager.blockingGet.side_effect = fake_blocking_get
        mock_network_access_manager.instance.return_value = manager

        def fake_translate(destination, source_path, **kwargs):
            with open(destination, "wb") as handle:
                handle.write(b"fake-cropped-tif-bytes")
            return object()

        mock_translate.side_effect = fake_translate

        task = NTLDownloaderTask(
            extent=self.extent,
            extent_crs_authid="EPSG:32626",
            working_dir=self.temp_dir,
            filename="ntl_test_year",
            year=2015,
        )
        self.assertTrue(task.run())
        self.assertTrue(any("2015" in url for url in requested_urls))


if __name__ == "__main__":
    unittest.main()
