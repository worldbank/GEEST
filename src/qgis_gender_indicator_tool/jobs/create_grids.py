import os
from qgis.core import QgsVectorLayer, QgsProcessingFeedback
import processing


class GridCreator:
    def __init__(self, h_spacing=100, v_spacing=100):
        """
        Initializes the GridCreator class with default grid spacing.

        Args:
            h_spacing (float): Horizontal spacing for the grid (default is 100 meters).
            v_spacing (float): Vertical spacing for the grid (default is 100 meters).
        """
        self.h_spacing = h_spacing
        self.v_spacing = v_spacing

    def create_grids(self, layer, output_dir, crs, merged_output_path):
        """
        Creates grids for the input polygon layer, clips them, and merges them into a single grid.

        Args:
            layer (QgsVectorLayer): The input polygon layer to grid.
            output_dir (str): The directory to save the grid outputs.
            crs (QgsCoordinateReferenceSystem): The coordinate reference system (CRS) for the grids.
            merged_output_path (str): The output path for the merged grid.

        Returns:
            QgsVectorLayer: The merged grid layer.
        """
        # Check if the merged grid already exists
        if os.path.exists(merged_output_path):
            print(f"Merged grid already exists: {merged_output_path}")
            return QgsVectorLayer(
                merged_output_path, "merged_grid", "ogr"
            )  # Load the existing merged grid layer
            
        layer = QgsVectorLayer(
            layer, "country_layer", "ogr"
        )
        if not layer.isValid():
            raise ValueError("Invalid country layer")

        # Reproject the country layer if necessary
        if layer.crs() != crs:
            layer = processing.run(
                "native:reprojectlayer",
                {
                    "INPUT": layer,
                    "TARGET_CRS": crs,
                    "OUTPUT": "memory:",
                },
                feedback=QgsProcessingFeedback(),
            )["OUTPUT"]

        all_grids = []

        # Loop through each feature in the polygon layer
        for feature in layer.getFeatures():
            geom = feature.geometry()

            # Check if the geometry is multipart
            if geom.isMultipart():
                parts = (
                    geom.asGeometryCollection()
                )  # Separate multipart geometry into parts
            else:
                parts = [geom]  # Single part geometry

            # Loop through each part of the geometry
            for part_id, part in enumerate(parts):
                part_area = part.area()

                # Get the extent of each part
                part_extent = part.boundingBox()

                # Define the output grid path for each part
                grid_output_path = (
                    f"{output_dir}/grid_{feature.id()}_part_{part_id}.gpkg"
                )

                # Check if the grid already exists
                if os.path.exists(grid_output_path):
                    print(f"Grid file already exists: {grid_output_path}")
                    grid_layer = QgsVectorLayer(
                        grid_output_path, "grid_layer", "ogr"
                    )  # Load the existing grid layer
                else:
                    print(f"Creating grid: {grid_output_path}")
                    # Define grid creation parameters
                    grid_params = {
                        "TYPE": 2,  # Rectangle (polygon)
                        "EXTENT": part_extent,  # Use the extent of the current part
                        "HSPACING": self.h_spacing,  # Horizontal spacing
                        "VSPACING": self.v_spacing,  # Vertical spacing
                        "CRS": crs,  # Coordinate reference system (CRS)
                        "OUTPUT": grid_output_path,  # Output path for the grid file
                    }

                    # Create the grid using QGIS processing
                    grid_result = processing.run("native:creategrid", grid_params)
                    grid_layer = grid_result["OUTPUT"]  # Get the grid layer

                    # Clip the grid to the polygon feature (to restrict it to the boundaries)
                    clipped_grid_output_path = (
                        f"{output_dir}/clipped_grid_{feature.id()}_part_{part_id}.gpkg"
                    )
                    clip_params = {
                        "INPUT": grid_layer,  # The grid we just created
                        "OVERLAY": layer,  # The layer we're clipping to
                        "OUTPUT": clipped_grid_output_path,
                    }
                    clip_result = processing.run("native:clip", clip_params)
                    grid_layer = clip_result["OUTPUT"]  # The clipped grid

                # Add the generated or loaded grid to the list
                all_grids.append(grid_layer)

        # Merge all grids into a single layer
        print(f"Merging grids into: {merged_output_path}")
        merge_params = {"LAYERS": all_grids, "CRS": crs, "OUTPUT": merged_output_path}
        merged_grid = processing.run("native:mergevectorlayers", merge_params)["OUTPUT"]
        return merged_grid
