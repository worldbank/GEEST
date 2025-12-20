# -*- coding: utf-8 -*-

"""📦 OSM Financial Facilities Downloader module.

This module contains functionality for downloading financial facilities from OSM.
"""

from .osm_data_downloader_base import OSMDataDownloaderBase


class OSMFinancialDownloader(OSMDataDownloaderBase):
    """
    Downloads financial facilities from OpenStreetMap.

    This includes:
    - Banks
    - ATMs
    - Microfinance institutions
    - Money transfer services
    - Credit unions
    - Bureau de change
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
        Initialize the OSM Financial Facilities downloader.

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
        # Set the output type - financial facilities can be points or polygons
        self._set_output_type("point")

        # Define the Overpass query for financial facilities
        osm_query = """[out:xml][timeout:60];
(
  node["amenity"="bank"]({{bbox}});
  way["amenity"="bank"]({{bbox}});
  relation["amenity"="bank"]({{bbox}});
  node["amenity"="atm"]({{bbox}});
  way["amenity"="atm"]({{bbox}});
  node["amenity"="microfinance"]({{bbox}});
  way["amenity"="microfinance"]({{bbox}});
  relation["amenity"="microfinance"]({{bbox}});
  node["amenity"="money_transfer"]({{bbox}});
  way["amenity"="money_transfer"]({{bbox}});
  relation["amenity"="money_transfer"]({{bbox}});
  node["amenity"="credit_union"]({{bbox}});
  way["amenity"="credit_union"]({{bbox}});
  relation["amenity"="credit_union"]({{bbox}});
  node["amenity"="bureau_de_change"]({{bbox}});
  way["amenity"="bureau_de_change"]({{bbox}});
  relation["amenity"="bureau_de_change"]({{bbox}});
  node["amenity"="mobile_money_agent"]({{bbox}});
  way["amenity"="mobile_money_agent"]({{bbox}});
);
(._;>;);
out geom;"""

        self.set_osm_query(osm_query)
        self.submit_query()
