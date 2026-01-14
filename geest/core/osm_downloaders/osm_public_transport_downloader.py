# -*- coding: utf-8 -*-
"""OSM Public Transport Downloader module.

This module downloads public transport stops and stations from OpenStreetMap,
including bus stops, tram stops, train stations, ferry terminals, and subway entrances.
"""
from typing import Optional

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeedback,
    QgsRectangle,
)

from geest.utilities import log_message

from .osm_data_downloader_base import OSMDataDownloaderBase


class OSMPublicTransportDownloader(OSMDataDownloaderBase):
    """OSM Public Transport Downloader.

    Downloads public transport infrastructure including:
    - Bus stops
    - Tram stops
    - Train stations and halts
    - Ferry terminals
    - Subway entrances
    - Platform areas

    Handles both point (node) and polygon (way/relation) geometries.
    """

    def __init__(
        self,
        extents: QgsRectangle,
        output_path: str = "",
        output_crs: Optional[QgsCoordinateReferenceSystem] = None,
        filename: str = "",
        use_cache: bool = False,
        delete_gpkg: bool = True,
        feedback: Optional[QgsFeedback] = None,
    ):
        """
        Initialize the OSMPublicTransportDownloader class.

        Args:
            extents: A QgsRectangle object containing the bounding box coordinates for the query.
            output_path: Directory where the GeoPackage will be saved.
            output_crs: Target coordinate reference system for the output.
            filename: Name for the output file (also used as layer name in gpkg).
            use_cache: Whether to use cached data if available.
            delete_gpkg: Whether to delete existing gpkg before creating new one.
            feedback: QgsFeedback object for progress reporting and cancellation.
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
        # Set the output type to handle mixed geometries (points + polygons)
        # Polygons (platforms, station buildings) will be converted to centroids and merged with point data
        self._set_output_type("mixed_to_point")

        # OSM Overpass query for public transport infrastructure
        # This query fetches various types of public transport nodes and areas
        osm_query = """[out:xml][timeout:60];
(
  /* Bus stops */
  node["highway"="bus_stop"]({{bbox}});
  node["public_transport"="stop_position"]["bus"="yes"]({{bbox}});
  node["public_transport"="platform"]["bus"="yes"]({{bbox}});
  way["public_transport"="platform"]["bus"="yes"]({{bbox}});

  /* Tram stops */
  node["railway"="tram_stop"]({{bbox}});
  node["public_transport"="stop_position"]["tram"="yes"]({{bbox}});
  node["public_transport"="platform"]["tram"="yes"]({{bbox}});
  way["public_transport"="platform"]["tram"="yes"]({{bbox}});

  /* Train stations and halts */
  node["railway"="station"]({{bbox}});
  node["railway"="halt"]({{bbox}});
  way["railway"="station"]({{bbox}});
  way["railway"="halt"]({{bbox}});
  relation["railway"="station"]({{bbox}});
  node["public_transport"="station"]({{bbox}});
  way["public_transport"="station"]({{bbox}});

  /* Subway/Metro */
  node["railway"="subway_entrance"]({{bbox}});
  node["railway"="station"]["station"="subway"]({{bbox}});
  way["railway"="station"]["station"="subway"]({{bbox}});

  /* Ferry terminals */
  node["amenity"="ferry_terminal"]({{bbox}});
  way["amenity"="ferry_terminal"]({{bbox}});

  /* General public transport platforms */
  node["public_transport"="platform"]({{bbox}});
  way["public_transport"="platform"]({{bbox}});

  /* Public transport stations (generic) */
  node["public_transport"="stop_position"]({{bbox}});
);
(._;>;);
out geom;"""

        self.set_osm_query(osm_query)
        self.submit_query()
        log_message("OSMPublicTransportDownloader Initialized")
        log_message("Public transport stops and stations will be downloaded")
        log_message("Mixed geometries (points + polygons) will be handled")
        log_message("Now call process_response to convert from osm xml to gpkg")
