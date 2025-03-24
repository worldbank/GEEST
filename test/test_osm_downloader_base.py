import unittest
from unittest.mock import MagicMock, patch
from qgis.core import QgsVectorLayer
from geest.core.osm_downloaders.osm_data_downloader_base import OSMDataDownloaderBase


class TestOSMDataDownloaderBase(unittest.TestCase):
    def setUp(self):
        """Set up the test environment."""
        self.downloader = OSMDataDownloaderBase()
        self.downloader.network_manager = MagicMock()

    def test_set_extents(self):
        """Test setting bounding box extents."""
        self.downloader.set_extents(10.0, 10.0, 10.1, 10.1)
        self.assertEqual(
            self.downloader.extents,
            {"south": 10.0, "east": 10.0, "north": 10.1, "west": 10.1},
        )

    def test_set_osm_query(self):
        """Test setting the OSM query."""
        query = "[out:json];node(50.7,7.1,50.8,7.25);out;"
        self.downloader.set_osm_query(query)
        self.assertEqual(self.downloader.formatted_query, query)

    def test_set_output_path(self):
        """Test setting the output path."""
        output_path = "output.gpkg"
        self.downloader.set_output_path(output_path)
        self.assertEqual(self.downloader.output_path, output_path)

    def test_set_output_type_valid(self):
        """Test setting a valid output type."""
        self.downloader.set_output_type("point")
        self.assertEqual(self.downloader.output_type, "point")

    def test_set_output_type_invalid(self):
        """Test setting an invalid output type."""
        with self.assertRaises(ValueError):
            self.downloader.set_output_type("invalid_type")

    @patch("geest.core.osm_downloaders.osm_data_downloader_base.log_message")
    def test_make_request_successful(self, mock_log_message):
        """Test making a successful request."""
        mock_reply = MagicMock()
        mock_reply.attribute.return_value = 200
        mock_reply.content.return_value = b'{"key": "value"}'
        self.downloader.network_manager.blockingPost.return_value = mock_reply

        params = {"key": "value"}
        with patch("json.loads", return_value={"key": "value"}):
            response = self.downloader.make_request("endpoint", params)
            self.assertEqual(
                response, {"key": "value"}, f"Response not as expected: {response}"
            )

    def test_make_request_http_error(self):
        """Test handling HTTP errors."""
        mock_reply = MagicMock()
        mock_reply.attribute.return_value = 404
        self.downloader.network_manager.blockingPost.return_value = mock_reply

        with self.assertRaises(RuntimeError):
            self.downloader.make_request("endpoint", {})

    def test_process_line_response(self):
        """Test processing line response."""
        response_data = """
        <osm>
            <node id="1" lat="10.0" lon="10.0" />
            <node id="2" lat="10.1" lon="10.1" />
            <way id="100">
                <nd ref="1" />
                <nd ref="2" />
            </way>
        </osm>
        """
        self.downloader.output_path = "output.gpkg"
        with patch("qgis.core.QgsVectorFileWriter.writeAsVectorFormat") as mock_writer:
            self.downloader.process_line_response(response_data)
            mock_writer.assert_called_once()

    def test_process_point_response(self):
        """Test processing point response."""
        response_data = """
        <osm>
            <node id="1" lat="10.0" lon="10.0" />
        </osm>
        """
        self.downloader.output_path = "output.gpkg"
        with patch("qgis.core.QgsVectorFileWriter.writeAsVectorFormat") as mock_writer:
            self.downloader.process_point_response(response_data)
            mock_writer.assert_called_once()

    def test_process_polygon_response(self):
        """Test processing polygon response."""
        response_data = """
        <osm>
            <node id="1" lat="10.0" lon="10.0" />
            <node id="2" lat="10.1" lon="10.1" />
            <node id="3" lat="10.0" lon="10.1" />
            <way id="100">
                <nd ref="1" />
                <nd ref="2" />
                <nd ref="3" />
            </way>
        </osm>
        """
        self.downloader.output_path = "output.gpkg"
        with patch("qgis.core.QgsVectorFileWriter.writeAsVectorFormat") as mock_writer:
            self.downloader.process_polygon_response(response_data)
            mock_writer.assert_called_once()


if __name__ == "__main__":
    unittest.main()
