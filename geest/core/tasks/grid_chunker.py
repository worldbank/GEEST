from osgeo import ogr, osr
from geest.utilities import log_message


class GridChunker:
    """
    A class to divide a bbox into chunks and process each chunk.



    Attributes:
        xmin (float): Minimum x-coordinate of the grid.
        xmax (float): Maximum x-coordinate of the grid.
        ymin (float): Minimum y-coordinate of the grid.
        ymax (float): Maximum y-coordinate of the grid.
        cell_size (float): Size of each cell in the grid.
        chunk_size (int): Number of cells in each chunk.

    Methods:
        log_message(message):
            Logs a message to the console.

        chunks():
            Yields chunks of the grid with their bounding box coordinates.

        total_cells_in_chunk():
            Returns the total number of cells in a chunk.

    Example:
        grid_chunker = GridChunker(0, 100, 0, 100, 10, 5)
        for chunk in grid_chunker.chunks():
            print(chunk)

        total_cells = grid_chunker.total_cells_in_chunk()
        print(f"Total cells in each chunk: {total_cells}")
    """

    def __init__(
        self,
        xmin: float,
        xmax: float,
        ymin: float,
        ymax: float,
        cell_size: float,
        chunk_size: int,
    ):
        """
        Initializes the GridChunker with the given grid boundaries, cell size, and chunk size.

        Args:
            xmin (float): Minimum x-coordinate of the grid.
            xmax (float): Maximum x-coordinate of the grid.
            ymin (float): Minimum y-coordinate of the grid.
            ymax (float): Maximum y-coordinate of the grid.
            cell_size (float): Size of each cell in the grid.
            chunk_size (int): Number of cells in each chunk.
        """
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.cell_size = cell_size  # size in map units of each cell (typically meters)
        self.chunk_size = (
            chunk_size  # number of cells in each chunk in both x and y directions
        )
        # e.g. chunk size of 5 would mean 5x5 cells in each chunk

        self.x_range_count = int((xmax - xmin) / cell_size)
        self.y_range_count = int((ymax - ymin) / cell_size)
        self.geometry = None

    def set_geometry(self, wkb_geometry):
        """
        Sets the geometry for the grid chunker.

        Args:
            wkb_geometry (bytes): The geometry in WKB format.
        """
        if wkb_geometry is None:
            self.geometry = None
            return

        self.geometry = ogr.CreateGeometryFromWkb(wkb_geometry)

        # If the geometry is a 3d geometry, convert it to 2d
        if self.geometry.GetCoordinateDimension() == 3:
            self.geometry.FlattenTo2D()

        # Check the geom is a single part and if not, raise an error
        if self.geometry.GetGeometryCount() > 1:
            raise ValueError("The geometry must be a single part.")

        # Check the geom is a polygon and if not, raise an error
        if self.geometry.GetGeometryType() != ogr.wkbPolygon:
            # Get the geomtery type name from the geometry type
            geom_type_name = ogr.GeometryTypeToName(self.geometry.GetGeometryType())
            raise ValueError(
                f"The geometry must be a polygon. Received a geometry of type {geom_type_name}"
            )

        # check the geom is in the same projection as the grid by seeing if they intersect
        if not self.geometry.Intersects(self.geometry):
            raise ValueError("The geometry must be in the same projection as the grid.")

    def write_chunks_to_gpkg(self, gpkg_path):
        """
        Writes the chunk polygon boundaries to a GeoPackage using the GDAL OGR API.

        If self.geometry is not none, chunks that do not intersect with the geom
        will be excluded. Additionally, chunks will be labelled as "inside" or "edge"
        so that the user can easily filter out chunks that are completely inside the geometry.

        Args:
            gpkg_path (str): The file path to the GeoPackage.
        """

        # Create the data source
        driver = ogr.GetDriverByName("GPKG")
        data_source = driver.CreateDataSource(gpkg_path)

        # Create the spatial reference, WGS84
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)

        # Create the layer
        layer = data_source.CreateLayer("chunks", srs, ogr.wkbPolygon)

        # Add fields
        field_index = ogr.FieldDefn("index", ogr.OFTInteger)
        layer.CreateField(field_index)
        # Add a field to label the chunks as "inside" or "edge"
        field_type = ogr.FieldDefn("type", ogr.OFTString)
        layer.CreateField(field_type)

        # Create the feature and set values
        for chunk in self.chunks():
            feature = ogr.Feature(layer.GetLayerDefn())
            feature.SetField("index", chunk["index"])

            # Create polygon from bounding box coordinates
            ring = ogr.Geometry(ogr.wkbLinearRing)
            ring.AddPoint(chunk["x_start"], chunk["y_start"])
            ring.AddPoint(chunk["x_end"], chunk["y_start"])
            ring.AddPoint(chunk["x_end"], chunk["y_end"])
            ring.AddPoint(chunk["x_start"], chunk["y_end"])
            ring.AddPoint(chunk["x_start"], chunk["y_start"])

            polygon = ogr.Geometry(ogr.wkbPolygon)
            polygon.AddGeometry(ring)

            feature.SetGeometry(polygon)

            # if the geometry is not none and the polygon intersects with it, add it to the layer
            if self.geometry is not None and self.geometry.Intersects(polygon):
                layer.CreateFeature(feature)
                if self.geometry.Contains(polygon):
                    feature.SetField("type", "inside")
                    layer.SetFeature(feature)
                else:
                    feature.SetField("type", "edge")
                    layer.SetFeature(feature)
            else:
                layer.CreateFeature(feature)
                layer.SetFeature(feature)
            feature = None

        # Close the data source
        data_source = None

    def chunks(self):
        """
        Yields chunks of the grid with their bounding box coordinates.

        Yields:
            dict: A dictionary containing the index and bounding box coordinates of each chunk.
        """
        x_blocks = range(0, self.x_range_count, self.chunk_size)
        y_blocks = range(0, self.y_range_count, self.chunk_size)
        index = 0

        for x_block_start in x_blocks:
            log_message(f"Processing chunk {x_block_start} of {self.x_range_count}")
            x_block_end = min(x_block_start + self.chunk_size, self.x_range_count)

            x_start_coord = self.xmin + x_block_start * self.cell_size
            x_end_coord = self.xmin + x_block_end * self.cell_size

            for y_block_start in y_blocks:
                log_message(f"Processing chunk {y_block_start} of {self.y_range_count}")
                y_block_end = min(y_block_start + self.chunk_size, self.y_range_count)

                y_start_coord = self.ymin + y_block_start * self.cell_size
                y_end_coord = self.ymin + y_block_end * self.cell_size

                log_message(
                    f"Created Chunk bbox: {x_start_coord}, {x_end_coord}, {y_start_coord}, {y_end_coord}"
                )
                yield {
                    "index": index,
                    "x_start": x_start_coord,
                    "x_end": x_end_coord,
                    "y_start": y_start_coord,
                    "y_end": y_end_coord,
                }
                index += 1

    def total_cells_in_chunk(self):
        """
        Returns the total number of cells in a chunk.

        Returns:
            int: The total number of cells in a chunk.
        """
        return self.chunk_size * self.chunk_size
