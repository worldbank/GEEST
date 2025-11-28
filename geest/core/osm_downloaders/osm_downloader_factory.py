# *- coding: utf-8 -*-

# A factory to generate osm downloaders based on the requested type

"""📦 Osm Downloader Factory module.

This module contains functionality for osm downloader factory.
"""
from geest.core.osm_downloaders import (
    OSMCyclewayDownloader,
    OSMDownloadType,
    OSMRoadsDownloader,
    OSMActiveTransportDownloader,
)


class OSMDownloaderFactory:
    """
    A factory class to create OSM data downloaders based on the specified download type.

    Methods:
        get_osm_downloader(download_type, extents, output_path="", output_crs=None,
                           filename="", use_cache=False, delete_gpkg=True, feedback=None):
            Returns an instance of the appropriate OSM data downloader based on the download type.

    """

    @staticmethod
    def get_osm_downloader(
        download_type: OSMDownloadType,
        extents,
        output_path: str,
        output_crs,
        filename: str = "",
        use_cache: bool = False,
        delete_gpkg: bool = True,
        feedback=None,
    ):
        if download_type == OSMDownloadType.ROAD:
            return OSMRoadsDownloader(
                extents=extents,
                output_path=output_path,
                output_crs=output_crs,
                filename=filename,
                use_cache=use_cache,
                delete_gpkg=delete_gpkg,
                feedback=feedback,
            )
        elif download_type == OSMDownloadType.CYCLE:
            return OSMCyclewayDownloader(
                extents=extents,
                output_path=output_path,
                output_crs=output_crs,
                filename=filename,
                use_cache=use_cache,
                delete_gpkg=delete_gpkg,
                feedback=feedback,
            )
        elif download_type == OSMDownloadType.ACTIVE_TRANSPORT:
            return OSMActiveTransportDownloader(
                extents=extents,
                output_path=output_path,
                output_crs=output_crs,
                filename=filename,
                use_cache=use_cache,
                delete_gpkg=delete_gpkg,
                feedback=feedback,
            )
        else:
            raise ValueError(f"Unsupported download type: {download_type}")
