# -*- coding: utf-8 -*-

"""📦 OSM Education Facilities Downloader module.

This module contains functionality for downloading education and training facilities from OSM.
"""

from .osm_data_downloader_base import OSMDataDownloaderBase


class OSMEducationDownloader(OSMDataDownloaderBase):
    """
    Downloads education and training facilities from OpenStreetMap.

    This includes:
    - Schools (primary, secondary)
    - Universities and colleges
    - Training centers
    - Kindergartens
    - Vocational schools
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
        Initialize the OSM Education Facilities downloader.

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
        # Set the output type - education facilities can be points or polygons
        self._set_output_type("point")

        # Define the Overpass query for education facilities
        osm_query = """[out:xml][timeout:60];
(
  node["amenity"="school"]({{bbox}});
  way["amenity"="school"]({{bbox}});
  relation["amenity"="school"]({{bbox}});
  node["amenity"="university"]({{bbox}});
  way["amenity"="university"]({{bbox}});
  relation["amenity"="university"]({{bbox}});
  node["amenity"="college"]({{bbox}});
  way["amenity"="college"]({{bbox}});
  relation["amenity"="college"]({{bbox}});
  node["amenity"="kindergarten"]({{bbox}});
  way["amenity"="kindergarten"]({{bbox}});
  relation["amenity"="kindergarten"]({{bbox}});
  node["amenity"="training"]({{bbox}});
  way["amenity"="training"]({{bbox}});
  relation["amenity"="training"]({{bbox}});
  node["amenity"="language_school"]({{bbox}});
  way["amenity"="language_school"]({{bbox}});
  relation["amenity"="language_school"]({{bbox}});
  node["amenity"="driving_school"]({{bbox}});
  way["amenity"="driving_school"]({{bbox}});
  relation["amenity"="driving_school"]({{bbox}});
  node["amenity"="music_school"]({{bbox}});
  way["amenity"="music_school"]({{bbox}});
  relation["amenity"="music_school"]({{bbox}});
);
(._;>;);
out geom;"""

        self.set_osm_query(osm_query)
        self.submit_query()
