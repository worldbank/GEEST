# -*- coding: utf-8 -*-

"""📦 OSM Primary School Downloader module.

This module contains functionality for downloading primary schools from OSM.
"""

from .osm_data_downloader_base import OSMDataDownloaderBase


class OSMPrimarySchoolDownloader(OSMDataDownloaderBase):
    """
    Downloads primary schools from OpenStreetMap.

    This includes:
    - Schools (amenity=school)
    - Educational institutions
    - School buildings
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
        Initialize the OSM Primary School downloader.

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
        # Set the output type - schools can be points or polygons (buildings)
        # Use mixed_to_point to handle both and convert polygons to centroids
        self._set_output_type("mixed_to_point")

        # Define the Overpass query for schools
        osm_query = """[out:xml][timeout:60];
(
  node["amenity"="school"]({{bbox}});
  way["amenity"="school"]({{bbox}});
  relation["amenity"="school"]({{bbox}});

  node["building"="school"]({{bbox}});
  way["building"="school"]({{bbox}});
  relation["building"="school"]({{bbox}});

  node["office"="educational_institution"]({{bbox}});
  way["office"="educational_institution"]({{bbox}});
  relation["office"="educational_institution"]({{bbox}});

  node["education"="school"]({{bbox}});
  way["education"="school"]({{bbox}});
  relation["education"="school"]({{bbox}});
);
(._;>;);
out geom;"""

        self.set_osm_query(osm_query)
        self.submit_query()
