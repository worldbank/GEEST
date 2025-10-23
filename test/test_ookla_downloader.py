# *- coding: utf-8 -*-
import os
import tempfile

import pytest
from qgis.core import QgsFeedback, QgsRectangle

from geest.core.algorithms.ookla_downloader import OoklaDownloader, OoklaException

FIXED_PARQUET = os.path.join(os.path.dirname(__file__), "test_data", "ookla", "ookla_fixed_random_subset.parquet")
MOBILE_PARQUET = os.path.join(os.path.dirname(__file__), "test_data", "ookla", "ookla_mobile_random_subset.parquet")
# securely set up a unique folder in /tmp for the test output
OUTPUT_DIR = tempfile.mkdtemp(prefix="test_ookla_downloader_")
os.makedirs(OUTPUT_DIR, exist_ok=True)


class DummyFeedback(QgsFeedback):
    def __init__(self):
        super().__init__()
        self.progress = 0

    def setProgress(self, value):
        print(f"Progress: {value}%")
        self.progress = value


def test_ookla_exception():
    with pytest.raises(OoklaException):
        raise OoklaException("Test error")


def test_cache_dir_creation():
    extents = QgsRectangle(-10, -10, 10, 10)
    downloader = OoklaDownloader(extents, output_path=OUTPUT_DIR, filename="test")
    cache_dir = downloader._cache_dir()
    assert os.path.exists(cache_dir)
    assert cache_dir.endswith("ookla_cache/cache")


def test_extract_ookla_data_fixed():
    extents = QgsRectangle(-180, -90, 180, 90)
    downloader = OoklaDownloader(extents, output_path=OUTPUT_DIR, filename="fixed_test")
    output_file = os.path.join(OUTPUT_DIR, "fixed_test_filtered.parquet")
    downloader.extract_ookla_data(FIXED_PARQUET, output_file, (-180, -90, 180, 90))
    assert os.path.exists(output_file)
    # Check file is not empty
    assert os.path.getsize(output_file) > 0


def test_extract_ookla_data_mobile():
    extents = QgsRectangle(-180, -90, 180, 90)
    downloader = OoklaDownloader(extents, output_path=OUTPUT_DIR, filename="mobile_test")
    output_file = os.path.join(OUTPUT_DIR, "mobile_test_filtered.parquet")
    downloader.extract_ookla_data(MOBILE_PARQUET, output_file, (-180, -90, 180, 90))
    assert os.path.exists(output_file)
    assert os.path.getsize(output_file) > 0


def test_combine_vectors():
    extents = QgsRectangle(-180, -90, 180, 90)
    downloader = OoklaDownloader(extents, output_path=OUTPUT_DIR, filename="combined_test")
    fixed_out = os.path.join(OUTPUT_DIR, "fixed_test_filtered.parquet")
    mobile_out = os.path.join(OUTPUT_DIR, "mobile_test_filtered.parquet")
    combined_out = os.path.join(OUTPUT_DIR, "combined_test.parquet")
    downloader.combine_vectors([fixed_out, mobile_out], combined_out)
    assert os.path.exists(combined_out)
    assert os.path.getsize(combined_out) > 0


def test_analysis_intro():
    extents = QgsRectangle(-10, -10, 10, 10)
    downloader = OoklaDownloader(extents, output_path=OUTPUT_DIR, filename="test")
    title, body = downloader.analysis_intro()
    assert "Spatial Filter" in title
    assert "Bounding Box Coordinates" in body
