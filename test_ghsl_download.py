#!/usr/bin/env python
# coding=utf-8
"""Quick test script to verify GHSL downloader works.

Run this in the QGIS Python console or with: python test_ghsl_download.py
"""

import os
import tempfile

from qgis.core import QgsFeedback, QgsRectangle

from geest.core.algorithms.ghsl_downloader import GHSLDownloader
from geest.core.algorithms.ghsl_processor import GHSLProcessor


def test_ghsl_download():
    """Test GHSL download for a small area (Burkina Faso region).

    Returns:
        bool: True if the test passes, False otherwise.
    """

    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="ghsl_test_")
    print(f"Output directory: {temp_dir}")

    # Burkina Faso area in Mollweide (ESRI:54009)
    bbox = QgsRectangle(-500000, 1000000, 300000, 1700000)
    print(f"Bounding box (Mollweide): {bbox.toString()}")

    feedback = QgsFeedback()

    # Step 1: Create downloader
    print("\n--- Step 1: Initialize downloader ---")
    downloader = GHSLDownloader(
        extents=bbox,
        output_path=temp_dir,
        filename="test_ghsl",
        use_cache=True,
        feedback=feedback,
    )

    # Check if index layer is valid
    if not downloader.layer.isValid():
        print("ERROR: Tile index layer is NOT valid!")
        print("This could mean parquet/gpkg driver issue.")
        return False
    print(f"Index layer valid: {downloader.layer.isValid()}")
    print(f"Index layer features: {downloader.layer.featureCount()}")

    # Step 2: Find intersecting tiles
    print("\n--- Step 2: Find intersecting tiles ---")
    tiles = downloader.tiles_intersecting_bbox()
    print(f"Found {len(tiles)} intersecting tiles: {tiles}")

    if not tiles:
        print("ERROR: No tiles found!")
        return False

    # Step 3: Download first tile only (to keep test fast)
    print("\n--- Step 3: Download first tile ---")
    tile_id = tiles[0]
    print(f"Downloading tile: {tile_id}")

    unpacked_files = downloader.download_and_unpack_tile(tile_id)
    print(f"Unpacked {len(unpacked_files)} files")

    for f in unpacked_files:
        size = os.path.getsize(f)
        print(f"  - {os.path.basename(f)}: {size} bytes")
        if size == 0:
            print("    ERROR: File is 0 bytes!")
            return False

    # Step 4: Find the .tif file
    tif_files = [f for f in unpacked_files if f.endswith(".tif")]
    if not tif_files:
        print("ERROR: No .tif file found in unpacked files!")
        return False

    print("\n--- Step 4: Process tile ---")
    processor = GHSLProcessor(input_raster_paths=tif_files)

    # Reclassify
    print("Reclassifying...")
    reclassified = processor.reclassify_rasters(suffix="reclass")
    print(f"Reclassified: {reclassified}")

    # Polygonize
    print("Polygonizing...")
    try:
        polygonized = processor.polygonize_rasters(reclassified)
        print(f"Polygonized: {polygonized}")
    except Exception as e:
        print(f"ERROR during polygonization: {e}")
        print("This is expected if Parquet OGR driver is not available.")
        return False

    print("\n--- SUCCESS ---")
    print("GHSL downloader and processor work correctly!")
    return True


if __name__ == "__main__":
    test_ghsl_download()
