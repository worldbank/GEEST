# -*- coding: utf-8 -*-
"""Unit tests for the environmental hazard downloader task."""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from qgis.core import QgsRectangle
from qgis.PyQt.QtNetwork import QNetworkRequest

from geest.core.tasks.env_hazard_downloader_task import EnvHazardDownloaderTask


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


class TestEnvHazardDownloaderTask(unittest.TestCase):
    """Tests for EnvHazardDownloaderTask behavior."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_env_hazard_task_")
        self.extent = QgsRectangle(674100.0, 1637600.0, 964800.0, 1903500.0)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_empty_extent_raises(self):
        with self.assertRaises(ValueError):
            EnvHazardDownloaderTask(
                hazard_id="fire",
                extent=QgsRectangle(),
                extent_crs_authid="EPSG:32626",
                working_dir=self.temp_dir,
            )

    def test_missing_working_dir_raises(self):
        with self.assertRaises(ValueError):
            EnvHazardDownloaderTask(
                hazard_id="fire", extent=self.extent, extent_crs_authid="EPSG:32626", working_dir=""
            )

    def test_unknown_hazard_id_raises(self):
        with self.assertRaises(ValueError):
            EnvHazardDownloaderTask(
                hazard_id="not-a-hazard",
                extent=self.extent,
                extent_crs_authid="EPSG:32626",
                working_dir=self.temp_dir,
            )

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

        task = EnvHazardDownloaderTask(
            hazard_id="fire",
            extent=self.extent,
            extent_crs_authid="EPSG:32626",
            working_dir=self.temp_dir,
            filename="fire_hazard_test",
        )

        success = task.run()
        self.assertTrue(success)
        self.assertTrue(os.path.exists(task.output_path))
        self.assertEqual(task.output_path, os.path.join(self.temp_dir, "study_area", "fire_hazard_test.tif"))
        self.assertFalse(os.path.exists(task._temp_global_path))

    @patch("geest.core.tasks.raster_download_utils.QgsNetworkAccessManager")
    def test_run_fails_on_permanent_http_error(self, mock_network_access_manager):
        manager = MagicMock()
        manager.blockingGet.return_value = _FakeReply(404, b"")
        mock_network_access_manager.instance.return_value = manager

        task = EnvHazardDownloaderTask(
            hazard_id="flood",
            extent=self.extent,
            extent_crs_authid="EPSG:32626",
            working_dir=self.temp_dir,
            filename="flood_hazard_404",
        )

        errors = []
        task.error_occurred.connect(errors.append)

        success = task.run()
        self.assertFalse(success)
        self.assertFalse(os.path.exists(task.output_path))
        self.assertTrue(errors)
        manager.blockingGet.assert_called_once()  # no retries for a permanent 404
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "flood_hazard_download_error.txt")))

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

            task = EnvHazardDownloaderTask(
                hazard_id="cyclone",
                extent=self.extent,
                extent_crs_authid="EPSG:32626",
                working_dir=self.temp_dir,
                filename="cyclone_hazard_retry",
            )
            success = task.run()

        self.assertTrue(success)
        self.assertTrue(os.path.exists(task.output_path))
        self.assertEqual(manager.blockingGet.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    def test_default_filename_derived_from_hazard_id(self):
        with patch("geest.core.tasks.raster_download_utils.QgsNetworkAccessManager"):
            task = EnvHazardDownloaderTask(
                hazard_id="drought",
                extent=self.extent,
                extent_crs_authid="EPSG:32626",
                working_dir=self.temp_dir,
            )
        self.assertEqual(task.output_path, os.path.join(self.temp_dir, "study_area", "drought_hazard.tif"))

    def test_source_url_matches_hazard_id(self):
        with patch("geest.core.tasks.raster_download_utils.QgsNetworkAccessManager"):
            task = EnvHazardDownloaderTask(
                hazard_id="landslide",
                extent=self.extent,
                extent_crs_authid="EPSG:32626",
                working_dir=self.temp_dir,
            )
        self.assertIn("landslide", task.source_url.lower())


if __name__ == "__main__":
    unittest.main()
