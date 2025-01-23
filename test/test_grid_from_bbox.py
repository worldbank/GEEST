import unittest
from unittest.mock import MagicMock
import math

from osgeo import ogr
from qgis.core import QgsTask

# Assuming the GridFromBbox class is already imported.
# from your_module_or_package import GridFromBbox


class TestGridFromBbox(unittest.TestCase):

    def test_run_with_basic_polygon(self):
        """
        Test that grid cells are correctly generated and intersect a simple square geometry.
        """
        # Define a simple square geometry: (0,0), (0,10), (10,10), (10,0)
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(0, 0)
        ring.AddPoint(0, 10)
        ring.AddPoint(10, 10)
        ring.AddPoint(10, 0)
        ring.AddPoint(0, 0)

        square_polygon = ogr.Geometry(ogr.wkbPolygon)
        square_polygon.AddGeometry(ring)

        # Chunk bounding box: same as the square
        bbox_chunk = (0, 10, 0, 10)

        # Create a
