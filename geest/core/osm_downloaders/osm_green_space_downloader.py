# -*- coding: utf-8 -*-

"""📦 OSM Green Space Downloader module.

This module contains functionality for downloading green spaces and parks from OSM.
"""

from .osm_data_downloader_base import OSMDataDownloaderBase


class OSMGreenSpaceDownloader(OSMDataDownloaderBase):
    """
    Downloads green spaces and parks from OpenStreetMap.

    This includes:
    - Parks
    - Gardens
    - National parks
    - Protected areas
    - Nature reserves
    - Recreation grounds
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
        Initialize the OSM Green Space downloader.

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
        # Set the output type - green spaces are typically polygons
        # Use mixed_to_point to handle both points and polygons, converting polygons to centroids
        self._set_output_type("mixed_to_point")

        # Define the Overpass query for green spaces
        osm_query = """[out:xml][timeout:60];
(
  node["leisure"="park"]({{bbox}});
  way["leisure"="park"]({{bbox}});
  relation["leisure"="park"]({{bbox}});

  node["boundary"="national_park"]({{bbox}});
  way["boundary"="national_park"]({{bbox}});
  relation["boundary"="national_park"]({{bbox}});

  node["boundary"="protected_area"]({{bbox}});
  way["boundary"="protected_area"]({{bbox}});
  relation["boundary"="protected_area"]({{bbox}});

  node["leisure"="garden"]({{bbox}});
  way["leisure"="garden"]({{bbox}});
  relation["leisure"="garden"]({{bbox}});

  node["leisure"="nature_reserve"]({{bbox}});
  way["leisure"="nature_reserve"]({{bbox}});
  relation["leisure"="nature_reserve"]({{bbox}});

  node["landuse"="recreation_ground"]({{bbox}});
  way["landuse"="recreation_ground"]({{bbox}});
  relation["landuse"="recreation_ground"]({{bbox}});

  node["landuse"="grass"]({{bbox}});
  way["landuse"="grass"]({{bbox}});
  relation["landuse"="grass"]({{bbox}});
);
(._;>;);
out geom;"""

        self.set_osm_query(osm_query)
        self.submit_query()
