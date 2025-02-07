import unittest
from geest.core.tasks.grid_chunker import GridChunker
from osgeo import ogr, osr
import os


class TestGridChunker(unittest.TestCase):

    def setUp(self):
        self.grid_chunker = GridChunker(0, 100, 0, 100, 10, 5)

    def tearDown(self):
        self.grid_chunker = None
        return super().tearDown()

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

    def test_set_geometry_valid(self):
        # Create a simple square polygon in WKB format
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(0, 0)
        ring.AddPoint(100, 0)
        ring.AddPoint(100, 100)
        ring.AddPoint(0, 100)
        ring.AddPoint(0, 0)
        polygon = ogr.Geometry(ogr.wkbPolygon)
        polygon.AddGeometry(ring)
        wkb_geometry = polygon.ExportToWkb()

        self.grid_chunker.set_geometry(wkb_geometry)
        self.assertIsNotNone(self.grid_chunker.geometry)
        self.assertTrue(self.grid_chunker.geometry.Intersects(polygon))

    def test_set_geometry_invalid_multipolygon(self):
        # Create a multipolygon in WKB format
        ring1 = ogr.Geometry(ogr.wkbLinearRing)
        ring1.AddPoint(0, 0)
        ring1.AddPoint(50, 0)
        ring1.AddPoint(50, 50)
        ring1.AddPoint(0, 50)
        ring1.AddPoint(0, 0)
        polygon1 = ogr.Geometry(ogr.wkbPolygon)
        polygon1.AddGeometry(ring1)

        ring2 = ogr.Geometry(ogr.wkbLinearRing)
        ring2.AddPoint(60, 60)
        ring2.AddPoint(100, 60)
        ring2.AddPoint(100, 100)
        ring2.AddPoint(60, 100)
        ring2.AddPoint(60, 60)
        polygon2 = ogr.Geometry(ogr.wkbPolygon)
        polygon2.AddGeometry(ring2)

        multipolygon = ogr.Geometry(ogr.wkbMultiPolygon)
        multipolygon.AddGeometry(polygon1)
        multipolygon.AddGeometry(polygon2)
        wkb_geometry = multipolygon.ExportToWkb()

        with self.assertRaises(ValueError):
            self.grid_chunker.set_geometry(wkb_geometry)

    def test_set_geometry_invalid_non_polygon(self):
        # Create a point in WKB format
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(0, 0)
        wkb_geometry = point.ExportToWkb()

        with self.assertRaises(ValueError):
            self.grid_chunker.set_geometry(wkb_geometry)

    def test_write_chunks_to_gpkg_with_geometry(self):
        # Create a simple square polygon in WKB format
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(0, 0)
        ring.AddPoint(100, 0)
        ring.AddPoint(100, 100)
        ring.AddPoint(0, 100)
        ring.AddPoint(0, 0)
        polygon = ogr.Geometry(ogr.wkbPolygon)
        polygon.AddGeometry(ring)
        wkb_geometry = polygon.ExportToWkb()

        self.grid_chunker.set_geometry(wkb_geometry)

        gpkg_path = "test_chunks_with_geometry.gpkg"
        self.grid_chunker.write_chunks_to_gpkg(gpkg_path)
        self.assertTrue(os.path.exists(gpkg_path))

        driver = ogr.GetDriverByName("GPKG")
        data_source = driver.Open(gpkg_path, 0)
        self.assertIsNotNone(data_source)

        layer = data_source.GetLayer()
        self.assertEqual(layer.GetFeatureCount(), 4)

        for feature in layer:
            self.assertIn(feature.GetField("index"), [0, 1, 2, 3])
            self.assertIn(feature.GetField("type"), ["inside", "edge"])

        data_source = None
        os.remove(gpkg_path)


if __name__ == "__main__":
    unittest.main()
