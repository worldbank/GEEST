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


class RasterPolygonGridScore:
    def __init__(
        self,
        country_boundary,
        pixel_size,
        working_dir,
        crs,
        input_polygons,
        output_path,
    ):
        self.country_boundary = country_boundary
        self.pixel_size = pixel_size
        self.working_dir = working_dir
        self.crs = crs
        self.input_polygons = input_polygons
        self.output_path = output_path
        # Initialize GridAligner with grid size
        self.grid_aligner = GridAligner(grid_size=100)

    def raster_polygon_grid_score(self):
        """
        Generates a raster based on the number of input points within each grid cell.
        :param country_boundary: Layer defining the country boundary to clip the grid.
        :param cellsize: The size of each grid cell.
        :param output_path: Path to save the output raster.
        :param crs: The CRS in which the grid and raster will be projected.
        :param input_polygons: Layer of point features to count within each grid cell.
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
                "INTERSECT": self.input_polygons,
                "OUTPUT": "TEMPORARY_OUTPUT",
            },
            feedback=QgsProcessingFeedback(),
        )["OUTPUT"]

        grid_layer = grid_output

        # Add score field
        provider = grid_layer.dataProvider()
        field_name = "poly_score"
        if not grid_layer.fields().indexFromName(field_name) >= 0:
            provider.addAttributes([QgsField(field_name, QVariant.Int)])
            grid_layer.updateFields()

        # Create spatial index for the input points
        # Reproject the country layer if necessary
        if self.input_polygons.crs() != self.crs:
            self.input_polygons = processing.run(
                "native:reprojectlayer",
                {
                    "INPUT": self.input_polygons,
                    "TARGET_CRS": self.crs,
                    "OUTPUT": "memory:",
                },
                feedback=QgsProcessingFeedback(),
            )["OUTPUT"]
        polygon_index = QgsSpatialIndex(self.input_polygons.getFeatures())

        # Count points within each grid cell and assign a score
        reclass_vals = {}
        for grid_feat in grid_layer.getFeatures():
            grid_geom = grid_feat.geometry()
            # Get intersecting points
            intersecting_ids = polygon_index.intersects(grid_geom.boundingBox())

            # Initialize a set to store unique intersecting line feature IDs
            unique_intersections = set()

            # Initialize variable to keep track of the maximum perimeter
            max_perimeter = 0

            for poly_id in intersecting_ids:
                poly_feat = self.input_polygons.getFeature(poly_id)
                poly_geom = poly_feat.geometry()

                if grid_feat.geometry().intersects(poly_geom):
                    unique_intersections.add(poly_id)
                    perimeter = poly_geom.length()

                    # Update max_perimeter if this perimeter is larger
                    if perimeter > max_perimeter:
                        max_perimeter = perimeter

            # Assign reclassification value based on the maximum perimeter
            if max_perimeter > 1000:  # Very large blocks
                reclass_val = 1
            elif 751 <= max_perimeter <= 1000:  # Large blocks
                reclass_val = 2
            elif 501 <= max_perimeter <= 750:  # Moderate blocks
                reclass_val = 3
            elif 251 <= max_perimeter <= 500:  # Small blocks
                reclass_val = 4
            elif 0 < max_perimeter <= 250:  # Very small blocks
                reclass_val = 5
            else:
                reclass_val = 0  # No intersection

            reclass_vals[grid_feat.id()] = reclass_val

        # Step 5: Apply the score values to the grid
        grid_layer.startEditing()
        for grid_feat in grid_layer.getFeatures():
            grid_layer.changeAttributeValue(
                grid_feat.id(),
                provider.fieldNameIndex(field_name),
                reclass_vals[grid_feat.id()],
            )
        grid_layer.commitChanges()

        merged_output_vector = os.path.join(output_dir, "merged_grid_vector.shp")

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

        # Rasterize the clipped grid layer to generate the raster
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
