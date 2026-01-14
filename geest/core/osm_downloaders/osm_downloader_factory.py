# *- coding: utf-8 -*-

# A factory to generate osm downloaders based on the requested type

"""📦 Osm Downloader Factory module.

This module contains functionality for osm downloader factory.
"""
from .osm_download_type import OSMDownloadType
from .osm_active_transport_downloader import OSMActiveTransportDownloader
from .osm_public_transport_downloader import OSMPublicTransportDownloader
from .osm_education_downloader import OSMEducationDownloader
from .osm_financial_downloader import OSMFinancialDownloader
from .osm_kindergarten_downloader import OSMKindergartenDownloader
from .osm_primary_school_downloader import OSMPrimarySchoolDownloader
from .osm_pharmacy_downloader import OSMPharmacyDownloader
from .osm_grocery_downloader import OSMGroceryDownloader
from .osm_green_space_downloader import OSMGreenSpaceDownloader
from .osm_health_facility_downloader import OSMHealthFacilityDownloader
from .osm_water_point_downloader import OSMWaterPointDownloader


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
        if download_type == OSMDownloadType.ACTIVE_TRANSPORT:
            return OSMActiveTransportDownloader(
                extents=extents,
                output_path=output_path,
                output_crs=output_crs,
                filename=filename,
                use_cache=use_cache,
                delete_gpkg=delete_gpkg,
                feedback=feedback,
            )
        elif download_type == OSMDownloadType.PUBLIC_TRANSPORT:
            return OSMPublicTransportDownloader(
                extents=extents,
                output_path=output_path,
                output_crs=output_crs,
                filename=filename,
                use_cache=use_cache,
                delete_gpkg=delete_gpkg,
                feedback=feedback,
            )
        elif download_type == OSMDownloadType.EDUCATION:
            return OSMEducationDownloader(
                extents=extents,
                output_path=output_path,
                output_crs=output_crs,
                filename=filename,
                use_cache=use_cache,
                delete_gpkg=delete_gpkg,
                feedback=feedback,
            )
        elif download_type == OSMDownloadType.FINANCIAL:
            return OSMFinancialDownloader(
                extents=extents,
                output_path=output_path,
                output_crs=output_crs,
                filename=filename,
                use_cache=use_cache,
                delete_gpkg=delete_gpkg,
                feedback=feedback,
            )
        elif download_type == OSMDownloadType.KINDERGARTEN:
            return OSMKindergartenDownloader(
                extents=extents,
                output_path=output_path,
                output_crs=output_crs,
                filename=filename,
                use_cache=use_cache,
                delete_gpkg=delete_gpkg,
                feedback=feedback,
            )
        elif download_type == OSMDownloadType.PRIMARY_SCHOOL:
            return OSMPrimarySchoolDownloader(
                extents=extents,
                output_path=output_path,
                output_crs=output_crs,
                filename=filename,
                use_cache=use_cache,
                delete_gpkg=delete_gpkg,
                feedback=feedback,
            )
        elif download_type == OSMDownloadType.PHARMACY:
            return OSMPharmacyDownloader(
                extents=extents,
                output_path=output_path,
                output_crs=output_crs,
                filename=filename,
                use_cache=use_cache,
                delete_gpkg=delete_gpkg,
                feedback=feedback,
            )
        elif download_type == OSMDownloadType.GROCERY:
            return OSMGroceryDownloader(
                extents=extents,
                output_path=output_path,
                output_crs=output_crs,
                filename=filename,
                use_cache=use_cache,
                delete_gpkg=delete_gpkg,
                feedback=feedback,
            )
        elif download_type == OSMDownloadType.GREEN_SPACE:
            return OSMGreenSpaceDownloader(
                extents=extents,
                output_path=output_path,
                output_crs=output_crs,
                filename=filename,
                use_cache=use_cache,
                delete_gpkg=delete_gpkg,
                feedback=feedback,
            )
        elif download_type == OSMDownloadType.HEALTH_FACILITY:
            return OSMHealthFacilityDownloader(
                extents=extents,
                output_path=output_path,
                output_crs=output_crs,
                filename=filename,
                use_cache=use_cache,
                delete_gpkg=delete_gpkg,
                feedback=feedback,
            )
        elif download_type == OSMDownloadType.WATER_POINT:
            return OSMWaterPointDownloader(
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
