#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

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


def print_bbox_diagram(bbox, title="BBOX Diagram"):
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


def filter_ookla_data(input_file, output_file, bbox):
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
        Panel.fit(
            f"[bold {PALETTE['primary']}]✅ Filtering complete![/bold {PALETTE['primary']}]\n"
            f"[{PALETTE['neutral']}]Kept {kept_count} of {feature_count} features.[/]\n"
            f"[{PALETTE['neutral']}]Filtered data saved to:[/] [bold]{output_file}[/bold]",
            border_style=PALETTE["accent"],
            title=f"[white on {PALETTE['primary']}] Done [/white on {PALETTE['primary']}]",
            width=panel_width,
        )
    )


def rasterize_filtered_data(input_file, output_raster, pixel_size=0.01):
    # This function rasterizes the filtered Parquet data into a GeoTIFF
    # with the specified pixel size.
    # gdal_rasterize -l ookla_filtered -burn 1.0 -tr 0.001 0.001 -init 0.0 -a_nodata 0.0 -ot Byte -of GTiff -co COMPRESS=DEFLATE -co PREDICTOR=2 -co ZLEVEL=9 /home/timlinux/dev/python/GEEST/data/ookla_filtered.parquet OUTPUT.tif
    # from osgeo import gdal
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


if __name__ == "__main__":
    input_file = "data/ookla.parquet"
    output_file = "data/ookla_filtered.parquet"
    output_raster = "data/ookla_filtered.tif"
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
    filter_ookla_data(input_file, output_file, bbox)
    rasterize_filtered_data(output_file, output_raster, pixel_size=0.01)
