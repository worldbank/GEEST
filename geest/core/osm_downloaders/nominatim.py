"""Manage nominatim connexion."""

import json
import logging
import os

from qgis.PyQt.QtCore import QDir, QTemporaryFile, QUrlQuery

from .downloader import Downloader
from .exceptions import (
    NetWorkErrorException,
    NominatimAreaException,
    NominatimBadRequest,
)
from .osm import OsmType

__copyright__ = "Copyright 2021, 3Liz"
__license__ = "GPL version 3"
__email__ = "info@3liz.org"

# from QuickOSM.qgis_plugin_tools.tools.resources import plugin_test_data_path

LOGGER = logging.getLogger("QuickOSM")
# The order is important. The first server will be the default.
NOMINATIM_SERVERS = [
    "https://nominatim.qgis.org/search?",
    "https://nominatim.openstreetmap.org/search?",
]


class Nominatim(Downloader):
    """Manage connexion to Nominatim."""

    def __init__(self, url: str = None):
        """Constructor.

        :param url: URL of Nominatim server.
        :type url: basestring
        """
        super().__init__(url)

        temporary = QTemporaryFile(os.path.join(QDir.tempPath(), "request-XXXXXX.json"))
        temporary.open()
        self.result_path = temporary.fileName()
        temporary.close()

    def error(self, messages: str):
        """Display the status in logger"""
        for message in messages:
            LOGGER.error(message)
        raise NetWorkErrorException("Nominatim API", ", ".join(messages))

    def query(self, query: str) -> dict:
        """Perform a nominatim query.

        :param query: Query to execute on the nominatim server.
        :type query: basestring

        :return: The result of the query as a dictionary.
        :rtype: dict

        :raise NetWorkErrorException:
        """

        query_string = QUrlQuery()
        query_string.addQueryItem("q", query)
        query_string.addQueryItem("format", "json")
        query_string.addQueryItem("info", "QgisQuickOSMPlugin")
        self._url.setQuery(query_string)

        # Use GET for Nominatim
        # https://github.com/3liz/QuickOSM/issues/472
        self.download(get=True)

        with open(self.result_path, encoding="utf8") as json_file:
            data = json.load(json_file)
            if not data:
                raise NominatimBadRequest(query)
            return data

    def get_first_polygon_from_query(self, query: str) -> str:
        """Get first OSM_ID of a Nominatim area.

        :param query: Query to execute.
        :type query: basestring

        :return: First relation's with an "osm_id".
        :rtype: int

        :raise NominatimAreaException:
        """
        data = self.query(query)
        for result in data:
            if result.get("osm_type") == OsmType.Relation.name.lower():
                osm_id = result.get("osm_id")
                if osm_id:
                    return osm_id

        # If no result has been return
        raise NominatimAreaException(query)

    def get_first_point_from_query(self, query: str, hack_test: bool = False) -> tuple:
        """Get first longitude, latitude of a Nominatim point.

        :param query: Query to execute.
        :type query: basestring

        :return: First node with its longitude and latitude.
        :rtype: tuple(float, float)

        :raise NominatimAreaException:
        """
        data = self.query(query)
        for result in data:
            lon = result.get("lon")
            lat = result.get("lat")
            if lon and lat:
                return lon, lat
