# -*- coding: utf-8 -*-

"""📦 OSM Pharmacy Downloader module.

This module contains functionality for downloading pharmacies from OSM.
"""

from .osm_data_downloader_base import OSMDataDownloaderBase


class OSMPharmacyDownloader(OSMDataDownloaderBase):
    """
    Downloads pharmacies from OpenStreetMap.

    This includes:
    - Pharmacies (amenity=pharmacy)
    - Pharmacy buildings
    - Healthcare pharmacies
    - Pharmacy shops
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
        Initialize the OSM Pharmacy downloader.

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
        # Set the output type - pharmacies can be points or polygons (buildings)
        # Use mixed_to_point to handle both and convert polygons to centroids
        self._set_output_type("mixed_to_point")

        # Define the Overpass query for pharmacies
        osm_query = """[out:xml][timeout:60];
(
  node["amenity"="pharmacy"]({{bbox}});
  way["amenity"="pharmacy"]({{bbox}});
  relation["amenity"="pharmacy"]({{bbox}});

  node["building"="pharmacy"]({{bbox}});
  way["building"="pharmacy"]({{bbox}});
  relation["building"="pharmacy"]({{bbox}});

  node["healthcare"="pharmacy"]({{bbox}});
  way["healthcare"="pharmacy"]({{bbox}});
  relation["healthcare"="pharmacy"]({{bbox}});

  node["shop"="pharmacy"]({{bbox}});
  way["shop"="pharmacy"]({{bbox}});
  relation["shop"="pharmacy"]({{bbox}});
);
(._;>;);
out geom;"""

        self.set_osm_query(osm_query)
        self.submit_query()
