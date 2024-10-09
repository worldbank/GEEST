import os
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsGeometry,
    QgsVectorLayer,
    QgsField,
    QgsSpatialIndex,
    QgsProcessingFeedback,
)
import processing
from .utilities import GridAligner


class RasterPolylineGridScore:
    def __init__(
        self,
        country_boundary,
        pixel_size,
        working_dir,
        crs,
        input_polylines,
        output_path,
    ):
        self.country_boundary = country_boundary
        self.pixel_size = pixel_size
        self.working_dir = working_dir
        self.crs = crs
        self.input_polylines = input_polylines
        self.output_path = output_path
        # Initialize GridAligner with grid size
        self.grid_aligner = GridAligner(grid_size=100)

    def raster_polyline_grid_score(self):
        """
        Generates a raster based on the number of input points within each grid cell.
        :param country_boundary: Layer defining the country boundary to clip the grid.
        :param cellsize: The size of each grid cell.
        :param crs: The CRS in which the grid and raster will be projected.
        :param input_polylines: Layer of point features to count within each grid cell.
        """

        output_dir = os.path.dirname(self.output_path)

        # Define output directory and ensure it's created
        os.makedirs(output_dir, exist_ok=True)

        # Load grid layer from the Geopackage
        geopackage_path = os.path.join(
            self.working_dir, "study_area", "study_area.gpkg"
        )
        if not os.path.exists(geopackage_path):
            raise ValueError(f"Geopackage not found at {geopackage_path}.")

        grid_layer = QgsVectorLayer(
            f"{geopackage_path}|layername=study_area_grid", "merged_grid", "ogr"
        )

        area_layer = QgsVectorLayer(
            f"{geopackage_path}|layername=study_area_polygons",
            "study_area_polygons",
            "ogr",
        )

        geometries = [feature.geometry() for feature in area_layer.getFeatures()]

        # Combine all geometries into one using unaryUnion
        area_geometry = QgsGeometry.unaryUnion(geometries)

        # grid_geometry = grid_layer.getGeometry()

        aligned_bbox = self.grid_aligner.align_bbox(
            area_geometry.boundingBox(), area_layer.extent()
        )

        # Extract polylines by location
        grid_output = processing.run(
            "native:extractbylocation",
            {
                "INPUT": grid_layer,
                "PREDICATE": [0],
                "INTERSECT": self.input_polylines,
                "OUTPUT": "TEMPORARY_OUTPUT",
            },
            feedback=QgsProcessingFeedback(),
        )["OUTPUT"]

        grid_layer = grid_output

        # Add score field
        provider = grid_layer.dataProvider()
        field_name = "line_score"
        if not grid_layer.fields().indexFromName(field_name) >= 0:
            provider.addAttributes([QgsField(field_name, QVariant.Int)])
            grid_layer.updateFields()

        # Create spatial index for the input points
        if self.input_polylines.crs() != self.crs:
            self.input_polylines = processing.run(
                "native:reprojectlayer",
                {
                    "INPUT": self.input_polylines,
                    "TARGET_CRS": self.crs,
                    "OUTPUT": "memory:",
                },
                feedback=QgsProcessingFeedback(),
            )["OUTPUT"]
        polyline_index = QgsSpatialIndex(self.input_polylines.getFeatures())

        # Count points within each grid cell and assign a score
        reclass_vals = {}
        for grid_feat in grid_layer.getFeatures():
            grid_geom = grid_feat.geometry()
            # Get intersecting points
            intersecting_ids = polyline_index.intersects(grid_geom.boundingBox())

            # Initialize a set to store unique intersecting line feature IDs
            unique_intersections = set()

            # Check each potentially intersecting line feature
            for line_id in intersecting_ids:
                line_feat = self.input_polylines.getFeature(line_id)
                line_geom = line_feat.geometry()

                # Perform a detailed intersection check
                if grid_feat.geometry().intersects(line_geom):
                    unique_intersections.add(line_id)

            num_polylines = len(unique_intersections)

            # Reclassification logic: assign score based on the number of points
            reclass_val = 5 if num_polylines >= 2 else 3 if num_polylines == 1 else 0
            reclass_vals[grid_feat.id()] = reclass_val

        # Apply the score values to the grid
        grid_layer.startEditing()
        for grid_feat in grid_layer.getFeatures():
            grid_layer.changeAttributeValue(
                grid_feat.id(),
                provider.fieldNameIndex(field_name),
                reclass_vals[grid_feat.id()],
            )
        grid_layer.commitChanges()

        # Merge the output vector layers
        merge = processing.run(
            "native:mergevectorlayers",
            {"LAYERS": [grid_layer], "CRS": self.crs, "OUTPUT": "TEMPORARY_OUTPUT"},
            feedback=QgsProcessingFeedback(),
        )["OUTPUT"]

        xmin, xmax, ymin, ymax = (
            aligned_bbox.xMinimum(),
            aligned_bbox.xMaximum(),
            aligned_bbox.yMinimum(),
            aligned_bbox.yMaximum(),
        )  # Extent of the aligned bbox

        print(f"Extent: {xmin}, {xmax}, {ymin}, {ymax}")

        # Rasterize the clipped grid layer to generate the raster
        # output_file = os.path.join(output_dir, "rasterized_grid.tif")
        rasterize_params = {
            "INPUT": merge,
            "FIELD": field_name,
            "BURN": 0,
            "USE_Z": False,
            "UNITS": 1,
            "WIDTH": self.pixel_size,
            "HEIGHT": self.pixel_size,
            "EXTENT": f"{xmin},{ymin},{xmax},{ymax}",
            "NODATA": None,
            "OPTIONS": "",
            "DATA_TYPE": 5,  # Use Int32 for scores
            "OUTPUT": "TEMPORARY_OUTPUT",
        }

        output_file = processing.run(
            "gdal:rasterize", rasterize_params, feedback=QgsProcessingFeedback()
        )["OUTPUT"]

        processing.run(
            "gdal:cliprasterbymasklayer",
            {
                "INPUT": output_file,
                "MASK": self.country_boundary,
                "NODATA": -9999,
                "CROP_TO_CUTLINE": True,
                "OUTPUT": self.output_path,
            },
            feedback=QgsProcessingFeedback(),
        )
