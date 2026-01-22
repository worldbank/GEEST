#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""📦 Ookla module.

This module contains functionality for ookla.
"""

import sys
import timeit

from osgeo import gdal, ogr
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn
from rich.table import Table

# Global console and color palette
console = Console()
PALETTE = {
    "accent": "#ECB44B",  # gold
    "neutral": "#959696",  # gray
    "primary": "#57A0C7",  # blue
}
panel_width = 78
minimum_upload_kbps = 10000
minimum_download_kbps = 20000

ogr.UseExceptions()
gdal.SetConfigOption("AWS_NO_SIGN_REQUEST", "YES")  # no credentials needed for public S3 access
gdal.SetConfigOption("AWS_REGION", "eu-west-1")
gdal.SetConfigOption("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
gdal.SetConfigOption("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", "parquet")

# Construct VSI S3 path
path_fixed_internet = "/vsis3/ookla-open-data/parquet/performance/type=fixed/year=2025/quarter=3/2025-07-01_performance_fixed_tiles.parquet"
path_mobile_internet = "/vsis3/ookla-open-data/parquet/performance/type=mobile/year=2025/quarter=3/2025-07-01_performance_mobile_tiles.parquet"


def print_bbox_diagram(bbox, title="BBOX Diagram"):
    """🔄 Print bbox diagram.

    Args:
        bbox: Bbox.
        title: Title.
    """
    console = Console()
    # Pretty ASCII-art diagram
    bbox_diagram = f"""[{PALETTE['neutral']}]
        ({bbox[0]:.2f}, {bbox[3]:.2f})
                     ┌───────────────────────┐
                     │                       │
                     │        BBOX AREA      │
                     │                       │
                     └───────────────────────┘
                                ({bbox[2]:.2f}, {bbox[1]:.2f})[{PALETTE['neutral']}]
    """
    console.print(
        Panel(
            bbox_diagram.strip(),
            border_style=PALETTE["primary"],
            title=f"[bold {PALETTE['accent']}]{title}[/bold {PALETTE['accent']}]",
            width=panel_width,
        )
    )


def print_analysis_intro():
    """🔄 Print analysis intro."""
    title = "Spatial Filter"
    console.print(
        Panel(
            f"[bold {PALETTE['accent']}]Filtering Records by Bounding Box[/bold {PALETTE['accent']}]\n"
            f"[{PALETTE['neutral']}]We’re narrowing the dataset from the Parquet file[/]\n"
            f"[{PALETTE['neutral']}]to only those geometries intersecting the bounding box below.[/]\n"
            f"Mimimum Upload Speed: [bold]{minimum_upload_kbps} kbps[/bold]\n"
            f"Minimum Download Speed: [bold]{minimum_download_kbps} kbps[/bold]\n",
            title=f"[bold {PALETTE['accent']}]{title}[/bold {PALETTE['accent']}]",
            border_style=PALETTE["primary"],
            width=panel_width,
        )
    )


def print_bbox_table(bbox):
    """🔄 Print bbox table.

    Args:
        bbox: Bbox.
    """
    title = "Bounding Box Coordinates"
    table = Table(
        title=f"[bold {PALETTE['accent']}]{title}[/bold {PALETTE['accent']}]",
        show_lines=True,
        width=panel_width,
        border_style=PALETTE["primary"],
    )
    table.add_column("Corner", justify="center", style=f"bold {PALETTE['accent']}")
    table.add_column("X", justify="right", style=PALETTE["neutral"])
    table.add_column("Y", justify="right", style=PALETTE["neutral"])
    table.add_row("Top-Left", f"{bbox[0]:,.2f}", f"{bbox[3]:,.2f}")
    table.add_row("Bottom-Right", f"{bbox[2]:,.2f}", f"{bbox[1]:,.2f}")
    table.add_row("Bottom-Left", f"{bbox[0]:,.2f}", f"{bbox[1]:,.2f}")
    table.add_row("Top-Right", f"{bbox[2]:,.2f}", f"{bbox[3]:,.2f}")
    console.print(table)


def extract_ookla_data(input_file, output_file, bbox):
    """🔄 Extract ookla data.

    Args:
        input_file: Input file.
        output_file: Output file.
        bbox: Bbox.
    """
    # Example row from the Parquet file:
    # OGRFeature(ookla):349644
    # quadkey (String) = 0230131221113313
    # tile (String) = POLYGON((-114.614868164062 34.8273320619816, -114.609375 34.8273320619816, -114.609375 34.822822727237, -114.614868164062 34.822822727237, -114.614868164062 34.8273320619816))
    # tile_x (Real) = -114.6121
    # tile_y (Real) = 34.8251
    # avg_d_kbps (Integer64) = 29684
    # avg_u_kbps (Integer64) = 3512
    # avg_lat_ms (Integer64) = 36
    # avg_lat_down_ms (Integer) = 173
    # avg_lat_up_ms (Integer) = 2571
    # tests (Integer64) = 11
    # devices (Integer64) = 1

    found_bbox = (0, 0, 0, 0)  # As we iterate over the features, we'll find the actual bbox
    start_time = timeit.default_timer()
    progress_bar = Progress(
        # left label — styled task description
        TextColumn(f"[bold {PALETTE['primary']}]\u25b6 {{task.description}}[/]", justify="right"),
        # custom bar with brand colors
        BarColumn(
            bar_width=panel_width - 29,
            complete_style=PALETTE["accent"],
            finished_style=PALETTE["neutral"],
            pulse_style=PALETTE["primary"],
        ),
        # middle label — percentage with custom color
        TextColumn(f"[{PALETTE['accent']}]{'{task.percentage:>5.1f}'}%[/]"),
        # right label — time remaining, styled grey
        TimeRemainingColumn(compact=True),
        console=console,
    )
    progress_bar.columns[1].bar_style = PALETTE["primary"]
    # Open the input Parquet file
    driver = ogr.GetDriverByName("Parquet")
    if driver is None:
        console.print("[red]❌ Parquet driver not available.[/red]")
        sys.exit(1)

    dataset = driver.Open(input_file, 0)
    if dataset is None:
        console.print(f"[red]❌ Failed to open file: {input_file}[/red]")
        sys.exit(1)

    layer = dataset.GetLayer()
    out_dataset = driver.CreateDataSource(output_file)
    out_layer = out_dataset.CreateLayer("filtered_data", geom_type=ogr.wkbPolygon)

    # Copy fields
    # We only will keep the quadkey field and discard the rest
    out_layer.CreateField(ogr.FieldDefn("quadkey", ogr.OFTString))

    min_x, min_y, max_x, max_y = bbox
    count = 0
    kept_count = 0
    min_x, min_y, max_x, max_y = bbox

    # Apply attribute filter for speed and extent directly at the layer level
    filter_expr = (
        f"avg_u_kbps >= {minimum_upload_kbps} AND "
        f"avg_d_kbps >= {minimum_download_kbps} AND "
        f"tile_x >= {min_x} AND tile_x <= {max_x} AND "
        f"tile_y >= {min_y} AND tile_y <= {max_y}"
    )
    layer.SetAttributeFilter(filter_expr)
    feature_count = layer.GetFeatureCount()
    out_layer_defn = out_layer.GetLayerDefn()
    process_task = progress_bar.add_task(description=f"[{PALETTE['primary']}]Processing...", total=feature_count)
    progress_bar.start()

    found_min_x = found_min_y = found_max_x = found_max_y = None

    for feature in layer:
        x = feature.GetField("tile_x")
        y = feature.GetField("tile_y")

        # Update found_bbox
        if found_min_x is None or x < found_min_x:
            found_min_x = x
        if found_min_y is None or y < found_min_y:
            found_min_y = y
        if found_max_x is None or x > found_max_x:
            found_max_x = x
        if found_max_y is None or y > found_max_y:
            found_max_y = y

        kept_count += 1
        geom = ogr.CreateGeometryFromWkt(feature.GetField("tile"))
        out_feature = ogr.Feature(out_layer_defn)
        out_feature.SetGeometry(geom.Clone())
        out_feature.SetField("quadkey", feature.GetField("quadkey"))
        out_layer.CreateFeature(out_feature)
        out_feature.Destroy()

        count += 1
        if count % 1000 == 0:
            progress_bar.update(process_task, total=feature_count, completed=count)
            progress_bar.refresh()

    # Final progress bar update
    progress_bar.remove_task(process_task)
    progress_bar.stop()

    # Clean up
    dataset = None
    out_dataset = None

    found_bbox = (found_min_x, found_min_y, found_max_x, found_max_y)
    print_bbox_diagram(found_bbox)
    print_bbox_diagram(bbox, title="Extent of Processed Data")
    console.print(
        Panel(
            f"[bold {PALETTE['primary']}]✅ Filtering complete![/bold {PALETTE['primary']}]\n"
            f"[{PALETTE['neutral']}]Kept {kept_count} of {feature_count} features.[/]\n"
            f"[{PALETTE['neutral']}]Filtered data saved to:[/] [bold]{output_file}[/bold]",
            border_style=PALETTE["accent"],
            title=f"[white on {PALETTE['primary']}] Done [/white on {PALETTE['primary']}]",
            width=panel_width,
        )
    )
    print_timings(start_time, title="Parquet file generation", message=f"Wrote {kept_count} features to {output_file}.")


def print_timings(start_time, title, message):
    """🔄 Print timings.

    Args:
        start_time: Start time.
        title: Title.
        message: Message.
    """
    # print the time as hours, minutes, seconds etc.
    run_time = timeit.default_timer() - start_time
    hours = int(run_time // 3600)
    minutes = int((run_time % 3600) // 60)
    seconds = run_time % 60
    console.print(
        Panel(
            f"[bold {PALETTE['neutral']}]{message}[/bold {PALETTE['neutral']}]\n"
            f"[bold {PALETTE['primary']}]⏱️ Hours:[/bold {PALETTE['primary']}] {hours}hrs"
            f"[bold {PALETTE['primary']}] Minutes:[/bold {PALETTE['primary']}] {minutes}mins"
            f"[bold {PALETTE['primary']}] Seconds:[/bold {PALETTE['primary']}] {seconds:.2f}s",
            title=f"[bold {PALETTE['accent']}]{title}[/bold {PALETTE['accent']}]",
            border_style=PALETTE["accent"],
            width=panel_width,
        )
    )


def rasterize_filtered_data(input_file, output_raster, pixel_size=0.01):
    """🔄 Rasterize filtered data.

    Args:
        input_file: Input file.
        output_raster: Output raster.
        pixel_size: Pixel size.
    """
    # This function rasterizes the filtered Parquet data into a GeoTIFF
    # with the specified pixel size.
    # gdal_rasterize -l ookla_filtered -burn 1.0 -tr 0.001 0.001 -init 0.0 -a_nodata 0.0 -ot Byte -of GTiff -co COMPRESS=DEFLATE -co PREDICTOR=2 -co ZLEVEL=9 /home/timlinux/dev/python/GEEST/data/ookla_filtered.parquet OUTPUT.tif
    # from osgeo import gdal
    start_time = timeit.default_timer()
    NoData_value = 0
    gdal.Rasterize(
        output_raster,
        input_file,
        format="GTIFF",
        outputType=gdal.GDT_Byte,
        creationOptions=[
            "COMPRESS=DEFLATE",
            "PREDICTOR=2",
            "ZLEVEL=9",
        ],
        noData=NoData_value,
        initValues=NoData_value,
        xRes=pixel_size,
        yRes=pixel_size,
        allTouched=True,
        burnValues=1,
    )
    print_timings(start_time, title="Rasterization complete.", message=f"Raster saved to {output_raster}.")


def combine_vectors(input_files, output_file):
    """🔄 Combine vectors.

    Args:
        input_files: Input files.
        output_file: Output file.
    """
    # This function combines multiple vector files into a single output file.
    start_time = timeit.default_timer()
    quadkey_set = set()
    duplicate_count = 0
    driver = ogr.GetDriverByName("Parquet")
    out_dataset = driver.CreateDataSource(output_file)
    out_layer = out_dataset.CreateLayer("combined_data", geom_type=ogr.wkbPolygon)
    out_layer.CreateField(ogr.FieldDefn("quadkey", ogr.OFTString))

    out_layer_defn = out_layer.GetLayerDefn()

    for input_file in input_files:
        dataset = driver.Open(input_file, 0)
        layer = dataset.GetLayer()

        for feature in layer:
            quadkey = feature.GetField("quadkey")
            if quadkey in quadkey_set:
                duplicate_count += 1
                continue
            else:
                quadkey_set.add(quadkey)
            geom = feature.GetGeometryRef()
            out_feature = ogr.Feature(out_layer_defn)
            out_feature.SetGeometry(geom.Clone())
            out_feature.SetField("quadkey", quadkey)
            out_layer.CreateFeature(out_feature)
            out_feature.Destroy()

        dataset = None

    out_dataset = None
    dataset = None
    quadkey_set = None
    print_timings(
        start_time,
        title="Vector Combination Complete",
        message=f"Combined vector saved to {output_file} with {duplicate_count} duplicates found.",
    )


if __name__ == "__main__":
    # prompt the user if they wish to use a local copy of the Ookla data or the S3 path
    console.print("[bold]Select Data Source:[/bold]")
    console.print("1. Use local copy of Ookla data (data/ookla-fixed.parquet and data/ookla-mobile.parquet)")
    console.print("2. Use local unit test data for Ookla data (test/test_data/ookla/)")
    console.print("3. Use Ookla data from S3")
    choice = console.input("Enter choice (1-2): ")
    if choice == "1":
        console.print("[bold]Using local copy of Ookla data.[/bold]")
        console.print("Make sure you have downloaded the data from S3 first!")
        console.print("and placed it in the data/ folder as ookla-fixed.parquet")
        console.print("and ookla-mobile.parquet.")

        input_file_fixed = "data/ookla-fixed.parquet"
        input_file_mobile = "data/ookla-mobile.parquet"
    if choice == "2":
        console.print("[bold]Using unit test Ookla data.[/bold]")

        input_file_fixed = "test/test_data/ookla/ookla_fixed_random_subset.parquet"
        input_file_mobile = "test/test_data/ookla/ookla_mobile_random_subset.parquet"
    else:
        input_file_fixed = path_fixed_internet
        input_file_mobile = path_mobile_internet

    output_vector_fixed = "data/ookla-fixed-filtered.parquet"
    output_vector_mobile = "data/ookla-mobile-filtered.parquet"
    output_vector_combined = "data/ookla-combined-filtered.parquet"
    output_raster_fixed = "data/ookla-fixed-filtered.tif"
    output_raster_mobile = "data/ookla-mobile-filtered.tif"
    output_raster_combined = "data/ookla-combined-filtered.tif"
    # Use rich to prompt the user whether they want to test with the
    # bbox of st lucia (small area), portugal (medium area), or usa (large area)
    console.print("[bold]Select Bounding Box Area:[/bold]")
    console.print("1. St. Lucia (Small Area)")
    console.print("2. Portugal (Medium Area)")
    console.print("3. USA (Large Area)")
    console.print("4. Global (Very Large Area) [Not Recommended]")
    choice = console.input("Enter choice (1-4): ")
    if choice == "1":
        bbox = (-61.0, 13.7, -60.8, 14.1)  # Example St. Lucia
    elif choice == "2":
        bbox = (-9.5, 36.9, -6.2, 42.2)  # Example Portugal
    elif choice == "3":
        bbox = (-125.0, 24.0, -66.0, 49.0)  # Example USA
    else:
        bbox = (-180.0, -90.0, 180.0, 90.0)

    print_analysis_intro()
    print_bbox_diagram(bbox, title="Extent of Interest")
    print_bbox_table(bbox)
    extract_ookla_data(input_file_fixed, output_vector_fixed, bbox)
    extract_ookla_data(input_file_mobile, output_vector_mobile, bbox)
    combine_vectors([output_vector_fixed, output_vector_mobile], output_vector_combined)
    rasterize_filtered_data(output_vector_fixed, output_raster_fixed, pixel_size=0.0001)
    rasterize_filtered_data(output_vector_mobile, output_raster_mobile, pixel_size=0.0001)
    rasterize_filtered_data(output_vector_combined, output_raster_combined, pixel_size=0.0001)
