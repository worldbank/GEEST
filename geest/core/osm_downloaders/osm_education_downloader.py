# -*- coding: utf-8 -*-

"""📦 OSM Universities and Training Facilities Downloader module.

This module contains functionality for downloading universities and training facilities from OSM.
Note: Primary schools and kindergartens are handled by separate downloaders.
"""

from .osm_data_downloader_base import OSMDataDownloaderBase


class OSMEducationDownloader(OSMDataDownloaderBase):
    """
    Downloads universities and training facilities from OpenStreetMap.

    This includes:
    - Universities and colleges
    - Training centers
    - Vocational training facilities
    - Education faculties

    Note: Primary schools and kindergartens are handled by separate downloaders
    (OSMPrimarySchoolDownloader and OSMKindergartenDownloader).
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
        # Use mixed_to_point to handle both and convert polygons to centroids
        self._set_output_type("mixed_to_point")

        # Define the Overpass query for education and training facilities
        # Note: This targets universities, colleges, and training centers
        # Schools and kindergartens are handled by separate downloaders
        osm_query = """[out:xml][timeout:60];
(
  node["amenity"="university"]({{bbox}});
  way["amenity"="university"]({{bbox}});
  relation["amenity"="university"]({{bbox}});

  node["amenity"="college"]({{bbox}});
  way["amenity"="college"]({{bbox}});
  relation["amenity"="college"]({{bbox}});

  node["education"="faculty"]({{bbox}});
  way["education"="faculty"]({{bbox}});
  relation["education"="faculty"]({{bbox}});

  node["amenity"="vocational_training"]({{bbox}});
  way["amenity"="vocational_training"]({{bbox}});
  relation["amenity"="vocational_training"]({{bbox}});

  node["amenity"="training"]({{bbox}});
  way["amenity"="training"]({{bbox}});
  relation["amenity"="training"]({{bbox}});

  node["building"="university"]({{bbox}});
  way["building"="university"]({{bbox}});
  relation["building"="university"]({{bbox}});

  node["building"="college"]({{bbox}});
  way["building"="college"]({{bbox}});
  relation["building"="college"]({{bbox}});
);
(._;>;);
out geom;"""

        self.set_osm_query(osm_query)
        self.submit_query()
