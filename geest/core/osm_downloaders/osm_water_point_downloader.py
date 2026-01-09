# -*- coding: utf-8 -*-

"""📦 OSM Water Point Downloader module.

This module contains functionality for downloading water points and water infrastructure from OSM.
"""

from .osm_data_downloader_base import OSMDataDownloaderBase


class OSMWaterPointDownloader(OSMDataDownloaderBase):
    """
    Downloads water points and water infrastructure from OpenStreetMap.

    This includes:
    - Water points
    - Fire hydrants
    - Water wells
    - Water pumps
    - Water tanks
    - Reservoirs
    - Water towers
    - Drinking water fountains
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
        Initialize the OSM Water Point downloader.

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
        # Set the output type - water infrastructure can be points or polygons
        # Use mixed_to_point to handle both and convert polygons to centroids
        self._set_output_type("mixed_to_point")

        # Define the Overpass query for water points
        osm_query = """[out:xml][timeout:120];
(
  node["amenity"="water_point"]({{bbox}});
  way["amenity"="water_point"]({{bbox}});
  relation["amenity"="water_point"]({{bbox}});

  node["emergency"="fire_hydrant"]({{bbox}});
  way["emergency"="fire_hydrant"]({{bbox}});
  relation["emergency"="fire_hydrant"]({{bbox}});

  node["man_made"="water_well"]({{bbox}});
  way["man_made"="water_well"]({{bbox}});
  relation["man_made"="water_well"]({{bbox}});

  node["man_made"="water_pump"]({{bbox}});
  way["man_made"="water_pump"]({{bbox}});
  relation["man_made"="water_pump"]({{bbox}});

  node["man_made"="water_tank"]({{bbox}});
  way["man_made"="water_tank"]({{bbox}});
  relation["man_made"="water_tank"]({{bbox}});

  node["man_made"="reservoir_covered"]({{bbox}});
  way["man_made"="reservoir_covered"]({{bbox}});
  relation["man_made"="reservoir_covered"]({{bbox}});

  node["landuse"="reservoir"]({{bbox}});
  way["landuse"="reservoir"]({{bbox}});
  relation["landuse"="reservoir"]({{bbox}});

  node["man_made"="water_tower"]({{bbox}});
  way["man_made"="water_tower"]({{bbox}});
  relation["man_made"="water_tower"]({{bbox}});

  node["amenity"="drinking_water"]({{bbox}});
  way["amenity"="drinking_water"]({{bbox}});
  relation["amenity"="drinking_water"]({{bbox}});
);
(._;>;);
out geom;"""

        self.set_osm_query(osm_query)
        self.submit_query()
