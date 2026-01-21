# -*- coding: utf-8 -*-
"""OSM Active Transport Downloader module.

This module combines roads and cycleways into a single dataset
for Active Transport analysis.
"""

from typing import Optional

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeedback,
    QgsRectangle,
)

from geest.utilities import log_message

from .osm_data_downloader_base import OSMDataDownloaderBase


class OSMActiveTransportDownloader(OSMDataDownloaderBase):
    """OSM Active Transport Downloader.

    Downloads BOTH roads (highway attribute) and cycleways (cycleway attribute)
    in a single query and combines them into one dataset.

    This allows the Active Transport analysis to evaluate both road types
    and select the best score for walkability/cyclability.
    """

    def __init__(
        self,
        extents: QgsRectangle,
        output_path: str = "",
        output_crs: Optional[QgsCoordinateReferenceSystem] = None,
        filename: str = "",  # will also set the layer name in the gpkg
        use_cache: bool = False,
        delete_gpkg: bool = True,
        feedback: Optional[QgsFeedback] = None,
    ):
        """
        Initialize the OSMActiveTransportDownloader class.

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
        # Set the output type to line
        # Note the timeout - 60s needed to allow for larger country queries
        self._set_output_type("line")

        # Combined OSM query that gets BOTH highway and cycleway features
        # This query will fetch features with either highway tags OR cycleway tags (or both)
        osm_query = """[out:xml][timeout:60];
(
  /* Roads with highway tags */
  way["highway"="motorway"]({{bbox}});
  way["highway"="motorway_link"]({{bbox}});
  way["highway"="trunk"]({{bbox}});
  way["highway"="trunk_link"]({{bbox}});
  way["highway"="primary"]({{bbox}});
  way["highway"="primary_link"]({{bbox}});
  way["highway"="secondary"]({{bbox}});
  way["highway"="secondary_link"]({{bbox}});
  way["highway"="tertiary"]({{bbox}});
  way["highway"="tertiary_link"]({{bbox}});
  way["highway"="unclassified"]({{bbox}});
  way["highway"="residential"]({{bbox}});
  way["highway"="living_street"]({{bbox}});
  way["highway"="pedestrian"]({{bbox}});
  way["highway"="service"]({{bbox}});
  way["highway"="escape"]({{bbox}});
  way["highway"="road"]({{bbox}});
  way["highway"="construction"]({{bbox}});
  way["highway"="footway"]({{bbox}});
  way["highway"="path"]({{bbox}});
  way["highway"="steps"]({{bbox}});
  way["highway"="track"]({{bbox}});
  way["highway"="bridleway"]({{bbox}});
  way["highway"="cycleway"]({{bbox}});
  way["highway"="proposed"]({{bbox}});
  way["highway"="raceway"]({{bbox}});
  way["highway"="bus_guideway"]({{bbox}});

  /* Cycleways with cycleway tags */
  way["cycleway"="lane"]({{bbox}});
  way["cycleway"="shared_lane"]({{bbox}});
  way["cycleway"="share_busway"]({{bbox}});
  way["cycleway"="track"]({{bbox}});
  way["cycleway"="separate"]({{bbox}});
  way["cycleway"="crossing"]({{bbox}});
  way["cycleway"="shoulder"]({{bbox}});
  way["cycleway"="link"]({{bbox}});

  /* Relations with cycleway tags */
  relation["cycleway"="lane"]({{bbox}});
  relation["cycleway"="shared_lane"]({{bbox}});
  relation["cycleway"="share_busway"]({{bbox}});
  relation["cycleway"="track"]({{bbox}});
  relation["cycleway"="separate"]({{bbox}});
  relation["cycleway"="crossing"]({{bbox}});
  relation["cycleway"="shoulder"]({{bbox}});
  relation["cycleway"="link"]({{bbox}});

  /* Other bicycle-related tags */
  way["bicycle_road"="yes"]({{bbox}});
  way["bicycle"="designated"]({{bbox}});

  /* Junctions */
  way["junction"="roundabout"]({{bbox}});
  way["junction"="circular"]({{bbox}});
);
(._;>;);
out geom;"""

        self.set_osm_query(osm_query)
        self.submit_query()
        log_message("OSMActiveTransportDownloader Initialized")
        log_message("Combined roads and cycleways will be downloaded in a single query")
        log_message("Now call process_response to convert from osm xml to gpkg")
