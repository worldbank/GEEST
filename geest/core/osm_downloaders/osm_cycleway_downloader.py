# -*- coding: utf-8 -*-

# Add optional typing
"""📦 Osm Cycleway Downloader module.

This module contains functionality for osm cycleway downloader.
"""

from typing import Optional

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeedback,
    QgsRectangle,
)

from geest.utilities import log_message

from .osm_data_downloader_base import OSMDataDownloaderBase


class OSMCyclewayDownloader(OSMDataDownloaderBase):
    """🎯 O S M Cycleway Downloader."""

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
        Initialize the OSMDownloader class.

        Args:
            extents: A QgsRectangle object containing the bounding box coordinates for the query.
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
        # set the output type to line
        # note the timeout - 60s needed to allow for larger country queries
        self._set_output_type("line")
        osm_query = """[out:xml][timeout:60];
(
  way["cycleway"="lane"]({{bbox}});
  way["cycleway"="shared_lane"]({{bbox}});
  way["cycleway"="share_busway"]({{bbox}});
  way["cycleway"="track"]({{bbox}});
  way["cycleway"="separate"]({{bbox}});
  way["cycleway"="crossing"]({{bbox}});
  way["cycleway"="shoulder"]({{bbox}});
  way["cycleway"="link"]({{bbox}});
  relation["cycleway"="lane"]({{bbox}});
  relation["cycleway"="shared_lane"]({{bbox}});
  relation["cycleway"="share_busway"]({{bbox}});
  relation["cycleway"="track"]({{bbox}});
  relation["cycleway"="separate"]({{bbox}});
  relation["cycleway"="crossing"]({{bbox}});
  relation["cycleway"="shoulder"]({{bbox}});
  relation["cycleway"="link"]({{bbox}});
);
(._;>;);
out geom;"""
        # outbody;""" ### Dont move the quotes to the next line !!!!
        # if you do the query_prepare will think the format is not in oql format

        self.set_osm_query(osm_query)
        self.submit_query()
        log_message("OSMCyclewayDownloader Initialized")
        log_message("Now call process_response to convert from osm xml to gpkg")
