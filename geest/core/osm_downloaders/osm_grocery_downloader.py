# -*- coding: utf-8 -*-

"""📦 OSM Grocery Downloader module.

This module contains functionality for downloading grocery stores and markets from OSM.
"""

from .osm_data_downloader_base import OSMDataDownloaderBase


class OSMGroceryDownloader(OSMDataDownloaderBase):
    """
    Downloads grocery stores and markets from OpenStreetMap.

    This includes:
    - Greengrocers
    - Fruit shops
    - Vegetable shops
    - Marketplaces
    """

    def __init__(
        self,
        extents,
        output_path: str,
        output_crs,
        filename: str = "",
        use_cache: bool = False,
        delete_gpkg: bool = True,
        feedback=None,
    ):
        """
        Initialize the OSM Grocery downloader.

        Args:
            extents: The bounding box for the area to download data for.
            output_path: The path to the output directory.
            output_crs: The CRS to use for the output data.
            filename: The name of the output file (without extension).
            use_cache: Whether to use cached data if available.
            delete_gpkg: Whether to delete the GeoPackage after processing.
            feedback: A QgsFeedback object for progress reporting.
        """
        super().__init__(
            extents=extents,
            output_path=output_path,
            output_crs=output_crs,
            filename=filename,
            use_cache=use_cache,
            delete_gpkg=delete_gpkg,
            feedback=feedback,
        )
        # Set the output type - grocery stores can be points or polygons (buildings)
        # Use mixed_to_point to handle both and convert polygons to centroids
        self._set_output_type("mixed_to_point")

        # Define the Overpass query for grocery stores
        osm_query = """[out:xml][timeout:60];
(
  node["shop"="greengrocer"]({{bbox}});
  way["shop"="greengrocer"]({{bbox}});
  relation["shop"="greengrocer"]({{bbox}});

  node["shop"="fruit"]({{bbox}});
  way["shop"="fruit"]({{bbox}});
  relation["shop"="fruit"]({{bbox}});

  node["shop"="vegetable"]({{bbox}});
  way["shop"="vegetable"]({{bbox}});
  relation["shop"="vegetable"]({{bbox}});

  node["amenity"="marketplace"]({{bbox}});
  way["amenity"="marketplace"]({{bbox}});
  relation["amenity"="marketplace"]({{bbox}});
);
(._;>;);
out geom;"""

        self.set_osm_query(osm_query)
        self.submit_query()
