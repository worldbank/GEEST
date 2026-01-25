# coding=utf-8
"""
Copyright (c) 2025. All rights reserved.
Original Author: Tim Sutton

Unit Tests for GHSLDownloader Class
"""

import os
import shutil
import tempfile
import unittest

from qgis.core import QgsFeedback, QgsRectangle

from geest.core.algorithms.ghsl_downloader import GHSLDownloader


class TestGHSLDownloader(unittest.TestCase):
    """Test cases for the GHSLDownloader class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temp directory for test outputs
        self.temp_dir = tempfile.mkdtemp(prefix="test_ghsl_downloader_")

        # Bounding box for Burkina Faso area in EPSG:4326
        # This should intersect with at least one GHSL tile
        # Coordinates: roughly centered on Ouagadougou
        self.burkina_bbox_4326 = QgsRectangle(-5.5, 9.0, 2.5, 15.0)

        # The GHSL tiles use Mollweide projection (ESRI:54009)
        # We need to transform the bbox to Mollweide for the downloader
        # Approximate Mollweide coordinates for Burkina Faso area
        # These values are approximate - the actual transformation would be done in production
        self.burkina_bbox_mollweide = QgsRectangle(-500000, 1000000, 300000, 1700000)

        self.feedback = QgsFeedback()

    def tearDown(self):
        """Clean up temporary directory."""
        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test that GHSLDownloader initializes correctly."""
        downloader = GHSLDownloader(
            extents=self.burkina_bbox_mollweide,
            output_path=self.temp_dir,
            filename="test_ghsl",
            use_cache=True,
            delete_existing=False,
            feedback=self.feedback,
        )

        self.assertIsInstance(downloader, GHSLDownloader)
        self.assertEqual(downloader.extents, self.burkina_bbox_mollweide)
        self.assertEqual(downloader.output_path, self.temp_dir)
        self.assertEqual(downloader.filename, "test_ghsl")
        self.assertTrue(downloader.use_cache)
        self.assertFalse(downloader.delete_existing)
        self.assertIsNotNone(downloader.layer)

    def test_index_layer_loads(self):
        """Test that the tile index layer loads correctly."""
        downloader = GHSLDownloader(
            extents=self.burkina_bbox_mollweide,
            output_path=self.temp_dir,
            filename="test_ghsl",
            feedback=self.feedback,
        )

        # Check that the index layer is valid
        self.assertTrue(downloader.layer.isValid(), "Tile index layer should be valid")

        # Check that it has features
        feature_count = downloader.layer.featureCount()
        self.assertGreater(feature_count, 0, "Tile index layer should have features")

    def test_cache_dir_creation(self):
        """Test that cache directory is created."""
        downloader = GHSLDownloader(
            extents=self.burkina_bbox_mollweide,
            output_path=self.temp_dir,
            filename="test_ghsl",
            feedback=self.feedback,
        )

        cache_dir = downloader._cache_dir()
        self.assertTrue(os.path.exists(cache_dir), "Cache directory should be created")
        self.assertTrue(os.path.isdir(cache_dir), "Cache directory should be a directory")

    def test_tiles_intersecting_bbox(self):
        """Test finding tiles that intersect with the bounding box."""
        downloader = GHSLDownloader(
            extents=self.burkina_bbox_mollweide,
            output_path=self.temp_dir,
            filename="test_ghsl",
            feedback=self.feedback,
        )

        tiles = downloader.tiles_intersecting_bbox()

        # We expect at least one tile to intersect with Burkina Faso
        self.assertIsInstance(tiles, list, "tiles_intersecting_bbox should return a list")
        self.assertGreater(len(tiles), 0, f"Expected at least one tile for Burkina Faso bbox, got {len(tiles)}")

        # Each tile should be a string ID like "R5_C19"
        for tile_id in tiles:
            self.assertIsInstance(tile_id, str, f"Tile ID should be a string, got {type(tile_id)}")
            self.assertRegex(tile_id, r"R\d+_C\d+", f"Tile ID should match pattern R#_C#, got {tile_id}")

    def test_download_and_unpack_tile(self):
        """Test downloading and unpacking a GHSL tile.

        This test actually downloads data from the internet, so it may be slow
        and requires network connectivity.
        """
        downloader = GHSLDownloader(
            extents=self.burkina_bbox_mollweide,
            output_path=self.temp_dir,
            filename="test_ghsl",
            use_cache=True,  # Use cache to avoid re-downloading in repeated tests
            feedback=self.feedback,
        )

        # Find tiles that intersect our bbox
        tiles = downloader.tiles_intersecting_bbox()
        self.assertGreater(len(tiles), 0, "Need at least one tile to test download")

        # Download the first tile
        tile_id = tiles[0]
        unpacked_files = downloader.download_and_unpack_tile(tile_id)

        # Check that we got some files back
        self.assertIsInstance(unpacked_files, list, "download_and_unpack_tile should return a list")
        self.assertGreater(len(unpacked_files), 0, f"Expected unpacked files for tile {tile_id}")

        # Check that each file exists and is not empty
        for file_path in unpacked_files:
            self.assertTrue(os.path.exists(file_path), f"Unpacked file should exist: {file_path}")

            file_size = os.path.getsize(file_path)
            self.assertGreater(
                file_size,
                0,
                f"Unpacked file should not be empty (0 bytes): {file_path}",
            )

            # Log file info for debugging
            print(f"Verified file: {file_path} ({file_size} bytes)")

    def test_download_and_unpack_tile_contains_tif(self):
        """Test that downloaded tile contains a .tif file."""
        downloader = GHSLDownloader(
            extents=self.burkina_bbox_mollweide,
            output_path=self.temp_dir,
            filename="test_ghsl",
            use_cache=True,
            feedback=self.feedback,
        )

        tiles = downloader.tiles_intersecting_bbox()
        self.assertGreater(len(tiles), 0, "Need at least one tile to test")

        tile_id = tiles[0]
        unpacked_files = downloader.download_and_unpack_tile(tile_id)

        # Check that at least one .tif file was unpacked
        tif_files = [f for f in unpacked_files if f.endswith(".tif")]
        self.assertGreater(len(tif_files), 0, f"Expected at least one .tif file in tile {tile_id}")

        # Verify the tif file is a valid size (GHSL tiles are typically several MB)
        for tif_file in tif_files:
            file_size = os.path.getsize(tif_file)
            # GHSL tiles should be at least 1KB (usually much larger)
            self.assertGreater(
                file_size,
                1024,
                f"GHSL .tif file should be larger than 1KB: {tif_file} ({file_size} bytes)",
            )
            print(f"Verified .tif file: {tif_file} ({file_size / 1024:.1f} KB)")

    def test_download_multiple_tiles(self):
        """Test downloading multiple tiles if the bbox spans multiple tiles."""
        # Use a larger bbox that might span multiple tiles
        large_bbox = QgsRectangle(-1000000, 500000, 1000000, 2000000)

        downloader = GHSLDownloader(
            extents=large_bbox,
            output_path=self.temp_dir,
            filename="test_ghsl_multi",
            use_cache=True,
            feedback=self.feedback,
        )

        tiles = downloader.tiles_intersecting_bbox()

        # Download all intersecting tiles (limit to first 2 to keep test fast)
        tiles_to_download = tiles[:2] if len(tiles) > 2 else tiles

        all_files = []
        for tile_id in tiles_to_download:
            unpacked_files = downloader.download_and_unpack_tile(tile_id)
            all_files.extend(unpacked_files)

            # Verify each file is not empty
            for file_path in unpacked_files:
                file_size = os.path.getsize(file_path)
                self.assertGreater(
                    file_size,
                    0,
                    f"File from tile {tile_id} should not be empty: {file_path}",
                )

        print(f"Successfully downloaded {len(tiles_to_download)} tiles with {len(all_files)} total files")

    def test_remote_bbox_returns_valid_result(self):
        """Test that a remote bbox returns a valid result (may or may not have tiles)."""
        # Use a bbox far from typical land areas in Mollweide projection
        # GHSL has near-global coverage, so we just verify the method works
        # and returns a valid list without crashing
        remote_bbox = QgsRectangle(-18000000, -8000000, -17500000, -7500000)

        downloader = GHSLDownloader(
            extents=remote_bbox,
            output_path=self.temp_dir,
            filename="test_ghsl_remote",
            feedback=self.feedback,
        )

        tiles = downloader.tiles_intersecting_bbox()

        # Should return a valid list (may be empty or have tiles depending on coverage)
        self.assertIsInstance(tiles, list)
        # All returned tile IDs should be valid format
        for tile_id in tiles:
            self.assertIsInstance(tile_id, str)
            self.assertRegex(tile_id, r"R\d+_C\d+", f"Tile ID should match pattern R#_C#, got {tile_id}")


class TestGHSLDownloaderIntegration(unittest.TestCase):
    """Integration tests that test the full download workflow."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp(prefix="test_ghsl_integration_")
        self.feedback = QgsFeedback()

    def tearDown(self):
        """Clean up temporary directory."""
        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_full_download_workflow(self):
        """Test the complete download workflow from bbox to unpacked files.

        This is an integration test that verifies the entire download process
        works end-to-end.
        """
        # Use Burkina Faso area in Mollweide projection
        bbox = QgsRectangle(-500000, 1000000, 300000, 1700000)

        downloader = GHSLDownloader(
            extents=bbox,
            output_path=self.temp_dir,
            filename="integration_test",
            use_cache=True,
            delete_existing=False,
            feedback=self.feedback,
        )

        # Step 1: Find intersecting tiles
        tiles = downloader.tiles_intersecting_bbox()
        self.assertGreater(len(tiles), 0, "Should find at least one tile")
        print(f"Found {len(tiles)} intersecting tiles: {tiles}")

        # Step 2: Download first tile
        tile_id = tiles[0]
        unpacked_files = downloader.download_and_unpack_tile(tile_id)

        # Step 3: Verify download results
        self.assertGreater(len(unpacked_files), 0, "Should have unpacked files")

        # Step 4: Verify files are valid (not empty, correct format)
        tif_count = 0
        for file_path in unpacked_files:
            self.assertTrue(os.path.exists(file_path), f"File should exist: {file_path}")

            file_size = os.path.getsize(file_path)
            self.assertGreater(file_size, 0, f"File should not be 0 bytes: {file_path}")

            if file_path.endswith(".tif"):
                tif_count += 1
                # GHSL tiles should be substantial in size
                self.assertGreater(
                    file_size,
                    10000,  # At least 10KB for a valid GeoTIFF
                    f"GHSL .tif should be larger than 10KB: {file_path} ({file_size} bytes)",
                )

        self.assertGreater(tif_count, 0, "Should have at least one .tif file")
        print(f"Integration test passed: {tif_count} .tif file(s) verified")


if __name__ == "__main__":
    unittest.main()
