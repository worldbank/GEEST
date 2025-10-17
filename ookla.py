#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

from osgeo import ogr
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from rich.table import Table

# Global console and color palette
console = Console()
PALETTE = {
    "accent": "#ECB44B",  # gold
    "neutral": "#959696",  # gray
    "primary": "#57A0C7",  # blue
}
panel_width = 78

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
    console.print(
        Panel.fit(
            f"[bold {PALETTE['accent']}]Filtering Records by Bounding Box[/bold {PALETTE['accent']}]\n"
            f"[{PALETTE['neutral']}]We’re narrowing the dataset from the Parquet file[/]\n"
            f"[{PALETTE['neutral']}]to only those geometries intersecting the bounding box below.[/]",
            title=f"[white on {PALETTE['primary']}] Spatial Filter [/white on {PALETTE['primary']}]",
            border_style=PALETTE["primary"],
            width=panel_width,
        )
    )


def print_bbox_table(bbox):
    table = Table(
        title=f"[bold white on {PALETTE['primary']}]Bounding Box Coordinates[/bold white on {PALETTE['primary']}]",
        show_lines=True,
        width=panel_width,
        border_style=PALETTE["neutral"],
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
    progress_bar = Progress()
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
    for i in range(layer.GetLayerDefn().GetFieldCount()):
        out_layer.CreateField(layer.GetLayerDefn().GetFieldDefn(i))

    min_x, min_y, max_x, max_y = bbox
    feature_count = layer.GetFeatureCount()
    kept_count = 0

    out_layer_defn = out_layer.GetLayerDefn()

    # Define the bounding box
    min_x, min_y, max_x, max_y = bbox

    feature_count = layer.GetFeatureCount()
    process_task = progress_bar.add_task(f"[bold{PALETTE['primary']}]Processing...", total=feature_count)
    count = 0
    kept_count = 0
    progress_bar.start()
    # Filter and copy features within the bounding box
    for feature in layer:
        # get the x from the tilw_x field and y from the tile_y field
        x = float(feature.GetField("tile_x"))
        y = float(feature.GetField("tile_y"))
        # Update found_bbox
        if x < found_bbox[0] or found_bbox[0] == 0:
            found_bbox = (x, found_bbox[1], found_bbox[2], found_bbox[3])
        if y < found_bbox[1] or found_bbox[1] == 0:
            found_bbox = (found_bbox[0], y, found_bbox[2], found_bbox[3])
        if x > found_bbox[2]:
            found_bbox = (found_bbox[0], found_bbox[1], x, found_bbox[3])
        if y > found_bbox[3]:
            found_bbox = (found_bbox[0], found_bbox[1], found_bbox[2], y)
        # Check if the point is within the bounding box
        if min_x <= x <= max_x and min_y <= y <= max_y:
            kept_count += 1
            # read the geometry as test WKT from the tile field
            geom = ogr.CreateGeometryFromWkt(feature.GetField("tile"))
            out_feature = ogr.Feature(out_layer_defn)
            out_feature.SetGeometry(geom.Clone())
            for i in range(out_layer_defn.GetFieldCount()):
                out_feature.SetField(out_layer_defn.GetFieldDefn(i).GetNameRef(), feature.GetField(i))
            out_layer.CreateFeature(out_feature)
            out_feature.Destroy()

        count += 1
        # use rich progress bar to show progress
        progress_bar.update(process_task, total=feature_count, completed=count)
        if count % 1000 == 0:
            progress_bar.refresh()

    progress_bar.remove_task(process_task)
    progress_bar.stop()

    # Clean up
    dataset = None
    out_dataset = None

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


if __name__ == "__main__":
    input_file = "data/ookla.parquet"
    output_file = "data/ookla_filtered.parquet"
    bbox = (-125.0, 24.0, -66.0, 49.0)  # Example USA

    print_analysis_intro()
    print_bbox_diagram(bbox, title="Extent of Interest")
    print_bbox_table(bbox)
    filter_ookla_data(input_file, output_file, bbox)
