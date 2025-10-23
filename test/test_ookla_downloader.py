# -*- coding: utf-8 -*-
import os
import tempfile
import unittest

from osgeo import ogr
from qgis.core import QgsFeedback, QgsRectangle

from geest.core.algorithms.ookla_downloader import OoklaDownloader, OoklaException


class DummyFeedback(QgsFeedback):
    def __init__(self):
        super().__init__()
        self.progress = 0

    def setProgress(self, value):
        print(f"Progress: {value}%")
        self.progress = value


class TestOoklaDownloader(unittest.TestCase):
    """Test suite for OoklaDownloader class."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures before all test methods."""
        cls.fixed_parquet = os.path.join(
            os.path.dirname(__file__), "test_data", "ookla", "ookla_fixed_random_subset.parquet"
        )
        cls.mobile_parquet = os.path.join(
            os.path.dirname(__file__), "test_data", "ookla", "ookla_mobile_random_subset.parquet"
        )
        # securely set up a unique folder in /tmp for the test output
        cls.output_dir = tempfile.mkdtemp(prefix="test_ookla_downloader_")
        os.makedirs(cls.output_dir, exist_ok=True)

    def test_ookla_exception(self):
        """Test that OoklaException can be raised."""
        with self.assertRaises(OoklaException):
            raise OoklaException("Test error")

    def test_cache_dir_creation(self):
        """Test that cache directory is created correctly."""
        # Portugal
        extents = QgsRectangle(-9.50, 36.90, -6.20, 42.20)
        downloader = OoklaDownloader(extents, output_path=self.output_dir, filename="test")
        cache_dir = downloader._cache_dir()
        self.assertTrue(os.path.exists(cache_dir))
        self.assertTrue(cache_dir.endswith("ookla_cache/cache"))

    def test_extract_ookla_data_fixed(self):
        """Test extraction of fixed internet data."""
        extents = QgsRectangle(-9.50, 36.90, -6.20, 42.20)
        downloader = OoklaDownloader(extents, output_path=self.output_dir, filename="fixed_test")
        output_file = os.path.join(self.output_dir, "fixed_test_filtered.parquet")
        downloader.extract_ookla_data(self.fixed_parquet, output_file, (-9.50, 36.90, -6.20, 42.20))
        self.assertTrue(os.path.exists(output_file))
        # Check file is not empty
        self.assertGreater(os.path.getsize(output_file), 0)
        # count the features in the output file  and confirm there are 100
        # using ogr
        driver = ogr.GetDriverByName("Parquet")
        dataset = driver.Open(output_file, 0)
        layer = dataset.GetLayer()
        feature_count = layer.GetFeatureCount()
        self.assertEqual(feature_count, 4)

    def test_extract_ookla_data_mobile(self):
        """Test extraction of mobile internet data."""
        extents = QgsRectangle(-9.50, 36.90, -6.20, 42.20)
        downloader = OoklaDownloader(extents, output_path=self.output_dir, filename="mobile_test")
        output_file = os.path.join(self.output_dir, "mobile_test_filtered.parquet")
        downloader.extract_ookla_data(self.mobile_parquet, output_file, (-9.50, 36.90, -6.20, 42.20))
        self.assertTrue(os.path.exists(output_file))
        self.assertGreater(os.path.getsize(output_file), 0)
        # count the features in the output file  and confirm there are 100
        # using ogr
        driver = ogr.GetDriverByName("Parquet")
        dataset = driver.Open(output_file, 0)
        layer = dataset.GetLayer()
        feature_count = layer.GetFeatureCount()
        self.assertEqual(feature_count, 4)

    def test_combine_vectors(self):
        """Test combining fixed and mobile vector data."""
        extents = QgsRectangle(-9.50, 36.90, -6.20, 42.20)
        downloader = OoklaDownloader(extents, output_path=self.output_dir, filename="combined_test")
        fixed_output_file = os.path.join(self.output_dir, "fixed_test_filtered.parquet")
        mobile_output_file = os.path.join(self.output_dir, "mobile_test_filtered.parquet")
        combined_output_file = os.path.join(self.output_dir, "combined_test.parquet")

        downloader.extract_ookla_data(self.fixed_parquet, fixed_output_file, (-9.50, 36.90, -6.20, 42.20))
        downloader.extract_ookla_data(self.mobile_parquet, mobile_output_file, (-9.50, 36.90, -6.20, 42.20))

        downloader.combine_vectors([fixed_output_file, mobile_output_file], combined_output_file)
        self.assertTrue(os.path.exists(combined_output_file))
        self.assertGreater(os.path.getsize(combined_output_file), 0)
        # count the features in the output file  and confirm there are 100
        # using ogr
        driver = ogr.GetDriverByName("Parquet")
        dataset = driver.Open(combined_output_file, 0)
        layer = dataset.GetLayer()
        feature_count = layer.GetFeatureCount()
        self.assertEqual(feature_count, 8)

    def test_analysis_intro(self):
        """Test that analysis intro returns correct title and body."""
        extents = QgsRectangle(-9.50, 36.90, -6.20, 42.20)
        downloader = OoklaDownloader(extents, output_path=self.output_dir, filename="test")
        title, body = downloader.analysis_intro()
        self.assertIn("Spatial Filter", title)
        self.assertIn("Bounding Box Coordinates", body)


if __name__ == "__main__":
    unittest.main()
