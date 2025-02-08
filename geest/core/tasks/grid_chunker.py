import os
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
        geom (ogr.Geometry): The geometry to check for intersections. (e.g. an island or land area)
        cell_size (float): Size of each cell in the grid.
        chunk_size (int): Number of cells in each chunk.
        epsg (int): The EPSG code of the grid.

    Methods:
        log_message(message):
            Logs a message to the console.

        chunks():
            Yields chunks of the grid with their bounding box coordinates.

        total_cells_in_chunk():
            Returns the total number of cells in a chunk.

        total_chunks():
            Returns the total number of chunks.

        set_geometry(wkb_geometry):
            Sets the geometry for the grid chunker.

        create_layer_if_not_exists(gpkg_path):
            Create a GPKG layer if it does not exist.

        write_chunks_to_gpkg(gpkg_path):
            Writes the chunk polygon boundaries to a GeoPackage.

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
        epsg: int,
        geometry: bytes = None,
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
            epsg (int): The EPSG code of the grid.
            geometry (bytes): The geometry in WKB format.
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
        self.epsg = epsg
        self.set_geometry(geometry)
        self.layer_name = "chunks"
        self.gpkg_path = None  # Initialize gpkg_path

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

    def create_layer_if_not_exists(self, gpkg_path):
        """
        Create a GPKG layer if it does not exist.
        """

        if not os.path.exists(gpkg_path):
            # Create new GPKG
            driver = ogr.GetDriverByName("GPKG")
            driver.CreateDataSource(self.gpkg_path)

        data_source = ogr.Open(gpkg_path, 1)
        layer = data_source.GetLayerByName(self.layer_name)
        if layer is not None:
            data_source = None
            return  # Already exists
        # Create the spatial reference, WGS84
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(self.epsg)
        # Create it
        layer = data_source.CreateLayer(self.layer_name, srs, geom_type=ogr.wkbPolygon)
        # Add fields
        field_index = ogr.FieldDefn("index", ogr.OFTInteger)
        layer.CreateField(field_index)
        # Add a field to label the chunks as "inside" or "edge"
        field_type = ogr.FieldDefn("type", ogr.OFTString)
        layer.CreateField(field_type)
        layer.SyncToDisk()

        data_source = None

    def write_chunks_to_gpkg(self, gpkg_path):
        """
        Writes the chunk polygon boundaries to a GeoPackage using the GDAL OGR API.

        If self.geometry is not none, chunks that do not intersect with the geom
        will be excluded. Additionally, chunks will be labelled as "inside" or "edge"
        so that the user can easily filter out chunks that are completely inside the geometry.

        Args:
            gpkg_path (str): The file path to the GeoPackage.
        """
        self.create_layer_if_not_exists(gpkg_path=gpkg_path)
        data_source = ogr.Open(gpkg_path, 1)
        layer = data_source.GetLayerByName(self.layer_name)
        if not layer:
            raise RuntimeError(
                f"Could not open target layer {self.layer_name} in {gpkg_path}"
            )
        # Create the feature and set values
        layer.StartTransaction()

        for chunk in self.chunks():
            feature = ogr.Feature(layer.GetLayerDefn())
            feature.SetField("index", chunk["index"])
            polygon = chunk["geometry"]
            feature.SetGeometry(polygon)
            feature.SetField("type", chunk["type"])
            layer.CreateFeature(feature)
            feature = None
        layer.CommitTransaction()
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
            log_message(f"Processing chunk (x) {x_block_start} of {self.x_range_count}")
            x_block_end = min(x_block_start + self.chunk_size, self.x_range_count)

            x_start_coord = self.xmin + x_block_start * self.cell_size
            x_end_coord = self.xmin + x_block_end * self.cell_size

            for y_block_start in y_blocks:
                log_message(
                    f"Processing chunk (y) {y_block_start} of {self.y_range_count}"
                )
                y_block_end = min(y_block_start + self.chunk_size, self.y_range_count)

                y_start_coord = self.ymin + y_block_start * self.cell_size
                y_end_coord = self.ymin + y_block_end * self.cell_size

                # Create polygon from bounding box coordinates
                ring = ogr.Geometry(ogr.wkbLinearRing)
                ring.AddPoint(x_start_coord, y_start_coord)
                ring.AddPoint(x_end_coord, y_start_coord)
                ring.AddPoint(x_end_coord, y_end_coord)
                ring.AddPoint(x_start_coord, y_end_coord)
                ring.AddPoint(x_start_coord, y_start_coord)

                polygon = ogr.Geometry(ogr.wkbPolygon)
                polygon.AddGeometry(ring)
                chunk_position = None
                # if the geometry is not none and the polygon intersects with it, add it to the layer
                if self.geometry is not None and self.geometry.Intersects(polygon):
                    if self.geometry.Contains(polygon):
                        chunk_position = "inside"
                    else:
                        chunk_position = "edge"
                else:
                    chunk_position = "undefined"
                log_message(
                    f"Created Chunk bbox: {x_start_coord}, {x_end_coord}, {y_start_coord}, {y_end_coord}, {chunk_position}"
                )
                yield {
                    "index": index,
                    "x_start": x_start_coord,
                    "x_end": x_end_coord,
                    "y_start": y_start_coord,
                    "y_end": y_end_coord,
                    "geometry": polygon,
                    "type": chunk_position,
                }
                index += 1

    def total_cells_in_chunk(self):
        """
        Returns the total number of cells in a chunk.

        Returns:
            int: The total number of cells in a chunk.
        """
        return self.chunk_size * self.chunk_size

    def total_chunks(self):
        """
        Returns the total number of chunks.

        Returns:
            int: The total number of chunks.
        """
        count = int(self.x_range_count / self.chunk_size) * int(
            self.y_range_count / self.chunk_size
        )
        log_message(f"Total chunks: {count}")
        return count
