# -*- coding: utf-8 -*-

"""📦 OSM Health Facility Downloader module.

This module contains functionality for downloading hospitals and clinics from OSM.
"""

from .osm_data_downloader_base import OSMDataDownloaderBase


class OSMHealthFacilityDownloader(OSMDataDownloaderBase):
    """
    Downloads health facilities from OpenStreetMap.

    This includes:
    - Hospitals
    - Clinics
    - Doctors' offices
    - Dentists
    - Healthcare centers
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
        Initialize the OSM Health Facility downloader.

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
        # Set the output type - health facilities can be points or polygons (buildings)
        # Use mixed_to_point to handle both and convert polygons to centroids
        self._set_output_type("mixed_to_point")

        # Define the Overpass query for health facilities
        osm_query = """[out:xml][timeout:60];
(
  /* Primary amenity-based healthcare tagging */
  node["amenity"="hospital"]({{bbox}});
  way["amenity"="hospital"]({{bbox}});
  relation["amenity"="hospital"]({{bbox}});

  node["amenity"="clinic"]({{bbox}});
  way["amenity"="clinic"]({{bbox}});
  relation["amenity"="clinic"]({{bbox}});

  node["amenity"="doctors"]({{bbox}});
  way["amenity"="doctors"]({{bbox}});
  relation["amenity"="doctors"]({{bbox}});

  node["amenity"="dentist"]({{bbox}});
  way["amenity"="dentist"]({{bbox}});
  relation["amenity"="dentist"]({{bbox}});

  /* Healthcare key (increasingly used in some regions) */
  node["healthcare"="hospital"]({{bbox}});
  way["healthcare"="hospital"]({{bbox}});
  relation["healthcare"="hospital"]({{bbox}});

  node["healthcare"="clinic"]({{bbox}});
  way["healthcare"="clinic"]({{bbox}});
  relation["healthcare"="clinic"]({{bbox}});

  node["healthcare"="doctor"]({{bbox}});
  way["healthcare"="doctor"]({{bbox}});
  relation["healthcare"="doctor"]({{bbox}});

  node["healthcare"="dentist"]({{bbox}});
  way["healthcare"="dentist"]({{bbox}});
  relation["healthcare"="dentist"]({{bbox}});

  /* Building-based tagging (structure-level, may require curation) */
  node["building"="hospital"]({{bbox}});
  way["building"="hospital"]({{bbox}});
  relation["building"="hospital"]({{bbox}});

  node["building"="clinic"]({{bbox}});
  way["building"="clinic"]({{bbox}});
  relation["building"="clinic"]({{bbox}});
);
(._;>;);
out geom;"""

        self.set_osm_query(osm_query)
        self.submit_query()
