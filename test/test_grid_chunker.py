import unittest
from geest.core.tasks.grid_chunker import GridChunker
from osgeo import ogr, osr
import os


class TestGridChunker(unittest.TestCase):

    def setUp(self):
        self.grid_chunker = GridChunker(0, 100, 0, 100, 10, 5)

    def test_chunks(self):
        chunks = list(self.grid_chunker.chunks())
        self.assertEqual(len(chunks), 4)
        expected_chunks = [
            {"index": 0, "x_start": 0, "x_end": 50, "y_start": 0, "y_end": 50},
            {"index": 1, "x_start": 0, "x_end": 50, "y_start": 50, "y_end": 100},
            {"index": 2, "x_start": 50, "x_end": 100, "y_start": 0, "y_end": 50},
            {"index": 3, "x_start": 50, "x_end": 100, "y_start": 50, "y_end": 100},
        ]
        for chunk, expected_chunk in zip(chunks, expected_chunks):
            self.assertEqual(chunk, expected_chunk)

    def test_total_cells_in_chunk(self):
        self.assertEqual(self.grid_chunker.total_cells_in_chunk(), 25)

    def test_write_chunks_to_gpkg(self):
        gpkg_path = "test_chunks.gpkg"
        self.grid_chunker.write_chunks_to_gpkg(gpkg_path)
        self.assertTrue(os.path.exists(gpkg_path))

        driver = ogr.GetDriverByName("GPKG")
        data_source = driver.Open(gpkg_path, 0)
        self.assertIsNotNone(data_source)

        layer = data_source.GetLayer()
        self.assertEqual(layer.GetFeatureCount(), 4)

        for feature in layer:
            self.assertIn(feature.GetField("index"), [0, 1, 2, 3])

        data_source = None
        os.remove(gpkg_path)


if __name__ == "__main__":
    unittest.main()
