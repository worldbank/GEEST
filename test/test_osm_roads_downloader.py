import unittest
from unittest.mock import MagicMock, patch
from qgis.core import QgsRectangle
from geest.core.osm_downloaders.osm_roads_downloader import OSMRoadsDownloader


class TestOSMRoadsDownloader(unittest.TestCase):
    def setUp(self):
        self.mock_extents = QgsRectangle(35.34463, 8.6056, 35.35706, 8.64769)
        self.mock_output_path = "test_osm_roads_output.gpkg"

    def test_initialization_without_canvas(self):
        downloader = OSMRoadsDownloader(
            extents=self.mock_extents, output_path=self.mock_output_path
        )

        self.assertEqual(downloader.extents, self.mock_extents)
        self.assertEqual(downloader.output_path, self.mock_output_path)

    def test_set_output_type_called(self):
        downloader = OSMRoadsDownloader(
            extents=self.mock_extents, output_path=self.mock_output_path
        )
        self.assertEqual(downloader.output_type, "line")

    @patch(
        "geest.core.osm_downloaders.osm_roads_downloader.OSMDataDownloaderBase.set_osm_query"
    )
    @patch(
        "geest.core.osm_downloaders.osm_roads_downloader.OSMDataDownloaderBase.submit_query"
    )
    def test_osm_query_and_submission(self, mock_submit_query, mock_set_osm_query):
        downloader = OSMRoadsDownloader(
            extents=self.mock_extents, output_path=self.mock_output_path
        )

        mock_set_osm_query.assert_called_once()
        mock_submit_query.assert_called_once()
        self.assertIn("[out:xml][timeout:25];", mock_set_osm_query.call_args[0][0])

    @patch("geest.core.osm_downloaders.osm_roads_downloader.log_message")
    def test_log_message_called(self, mock_log_message):
        OSMRoadsDownloader(extents=self.mock_extents, output_path=self.mock_output_path)
        mock_log_message.assert_called_once_with("OSMRoadsDownloader Initialized")


if __name__ == "__main__":
    unittest.main()
