"""Query preparation step."""

import re

from typing import List, Union

from qgis.core import QgsRectangle
from qgis.PyQt.QtCore import QUrl, QUrlQuery

from .exceptions import QueryFactoryException, QueryNotSupported
from .osm import QueryLanguage
from geest.core.i18n import tr
from geest.utilities import log_message

__copyright__ = "Copyright 2021, 3Liz"
__license__ = "GPL version 3"
__email__ = "info@3liz.org"


class QueryPreparation:
    """Prepare the query before sending it to Overpass."""

    def __init__(
        self,
        query: str,
        extent: QgsRectangle = None,
        area: Union[str, List[str]] = None,
        overpass: str = None,
        output_format: str = "xml",
    ):
        """Constructor.

        :param query: The query to prepare.
        :type query: str

        :param extent: The extent to use in 4326, if needed. It can be None.
        :type extent: QgsRectangle

        :param area: A name or a list of place names.
        :type area: str, list(str)
        """
        if overpass is None:
            server = "https://overpass-api.de/api/interpreter"
            self._overpass = QUrl(server)
        else:
            self._overpass = QUrl(overpass)

        self._query = query
        self._query_prepared = query
        self._extent = extent
        self._places = area
        self._output_format = output_format

        self._nominatim = None

        self._query_is_ready = False

    @property
    def query(self) -> str:
        """The original query.

        :return: The original query.
        :rtype: str
        """
        return self._query

    @property
    def final_query(self) -> str:
        """The generated query or None if it's not yet generated.

        :return: The final query.
        :rtype: str
        """
        if self._query_is_ready:
            return self._query_prepared

    def is_oql_query(self) -> bool:
        """Return if the query is written in OQL or not.

        :return: If the it's OQL query.
        :rtype: bool
        """
        return self._query_prepared[-1] == ";"

    def is_compatible(self) -> tuple[bool, str]:
        """The plugin doesn't support all special tags like Overpass Turbo.

        :return: A tuple (bool, reason).
        :rtype: tuple
        """
        # token to look for, error returned to the user
        incompatible_queries = {
            'geometry="center"': "center",
            "out center": "center",
            "{{style": "{{style}}",
            "{{data": "{{data}}",
            "{{date": "{{date}}",
            "{{geocodeId:": "{{geocodeId:}}",
            "{{geocodeBbox:": "{{geocodeBbox:}}",
        }

        for expression, error in incompatible_queries.items():
            if re.search(expression, self._query):
                return False, error

        return True, None

    def replace_bbox(self):
        """Replace {{bbox}} by the extent BBOX if needed.

        The temporary query will be updated.
        """
        template = r"{{bbox}}"
        if not re.search(template, self._query_prepared):
            return
        if self._extent is None:
            raise QueryFactoryException(tr("Missing extent parameter."))

        y_min = self._extent.yMinimum()
        y_max = self._extent.yMaximum()
        x_min = self._extent.xMinimum()
        x_max = self._extent.xMaximum()

        # make sure we don't query for invalid bounds #222
        area_is_too_big = False
        if y_min < -90:
            y_min = -90
            area_is_too_big = True
        if y_max > 90:
            y_max = 90
            area_is_too_big = True
        if x_min < -180:
            x_min = -180
            area_is_too_big = True
        if x_max > 180:
            x_max = 180
            area_is_too_big = True

        if area_is_too_big:
            log_message(
                tr(
                    "The area was overlapping the WGS84 limits ±90 / ±180 degrees. The query has "
                    "been restricted."
                )
            )

        if self.is_oql_query():
            new_string = "{},{},{},{}".format(
                self._format_decimals_wgs84(y_min),
                self._format_decimals_wgs84(x_min),
                self._format_decimals_wgs84(y_max),
                self._format_decimals_wgs84(x_max),
            )
        else:
            new_string = 'e="{}" n="{}" s="{}" w="{}"'.format(
                self._format_decimals_wgs84(x_max),
                self._format_decimals_wgs84(y_max),
                self._format_decimals_wgs84(y_min),
                self._format_decimals_wgs84(x_min),
            )
        self._query_prepared = re.sub(template, new_string, self._query_prepared)

    @staticmethod
    def _format_decimals_wgs84(coordinate: float) -> str:
        """Reduce the number of decimals, see #344"""
        # https://en.wikipedia.org/wiki/Decimal_degrees
        # We keep 5 decimals : individual trees, houses
        multiplier = 10**5
        number = str(int(coordinate * multiplier) / multiplier)
        number = number.rstrip("0")
        number = number.rstrip(".")
        return number

    def clean_query(self):
        """Remove extra characters that might be present in the query.

        The temporary query will be updated.
        """
        query = self._query_prepared.strip()

        # Correction of ; in the OQL at the end
        self._query_prepared = re.sub(r";;$", ";", query)
        self._query_prepared = re.sub(r";\\n", ";", self._query_prepared)

    def prepare_query(self):
        """Prepare the query before sending it to Overpass.

        The temporary query will be updated.

        :return: The final query.
        :rtype: basestring
        """
        result, error = self.is_compatible()
        if not result:
            raise QueryNotSupported(error)

        self.clean_query()
        self.replace_bbox()

        self._query_is_ready = True
        return self._query_prepared

    def prepare_url(self, output: QueryLanguage = None) -> str:
        """Prepare a query to be as an URL.

        if the query is not ready to be URL prepared, a None is returned.

        :return: The URL encoded with the query.
        :rtype: basestring
        """
        if not self._query_is_ready:
            return None

        if self._output_format:
            query = re.sub(
                r'output="[a-z]*"',
                f'output="{self._output_format}"',
                self._query_prepared,
            )
            query = re.sub(r"\[out:[a-z]*", f"[out:{self._output_format}", query)
        else:
            query = self._query_prepared

        url_query = QUrl(self._overpass)
        query_string = QUrlQuery()
        query_string.addQueryItem("data", query)
        if output == QueryLanguage.XML:
            query_string.addQueryItem("target", "xml")
        elif output == QueryLanguage.OQL:
            query_string.addQueryItem("target", "mapql")
        query_string.addQueryItem("info", "QgisQuickOSMPlugin")
        url_query.setQuery(query_string)
        return url_query.toString()
