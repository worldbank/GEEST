# -*- coding: utf-8 -*-

"""📦 OSM Kindergarten/Childcare Downloader module.

This module contains functionality for downloading kindergartens and childcare facilities from OSM.
"""

from .osm_data_downloader_base import OSMDataDownloaderBase


class OSMKindergartenDownloader(OSMDataDownloaderBase):
    """
    Downloads kindergarten and childcare facilities from OpenStreetMap.

    This includes:
    - Kindergartens
    - Childcare centers
    - Nurseries
    - Daycare facilities
    - Social facilities for childcare
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
        Initialize the OSM Kindergarten/Childcare downloader.

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
        # Set the output type - childcare facilities can be points or polygons (buildings)
        # Use mixed_to_point to handle both and convert polygons to centroids
        self._set_output_type("mixed_to_point")

        # Define the Overpass query for kindergarten/childcare facilities
        osm_query = """[out:xml][timeout:60];
(
  /* Primary and most common tagging */
  node["amenity"="kindergarten"]({{bbox}});
  way["amenity"="kindergarten"]({{bbox}});
  relation["amenity"="kindergarten"]({{bbox}});

  /* Childcare equivalents commonly used for kindergartens */
  node["amenity"="childcare"]({{bbox}});
  way["amenity"="childcare"]({{bbox}});
  relation["amenity"="childcare"]({{bbox}});

  node["social_facility"="childcare"]({{bbox}});
  way["social_facility"="childcare"]({{bbox}});
  relation["social_facility"="childcare"]({{bbox}});

  node["social_facility"="daycare"]({{bbox}});
  way["social_facility"="daycare"]({{bbox}});
  relation["social_facility"="daycare"]({{bbox}});

  /* Building-based tagging (structure-level) */
  node["building"="kindergarten"]({{bbox}});
  way["building"="kindergarten"]({{bbox}});
  relation["building"="kindergarten"]({{bbox}});
);
(._;>;);
out geom;"""

        self.set_osm_query(osm_query)
        self.submit_query()
