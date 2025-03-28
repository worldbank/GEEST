from qgis.core import (
    QgsRectangle,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
)
from qgis.gui import QgsMapCanvas
from .osm_data_downloader_base import OSMDataDownloaderBase
from geest.utilities import log_message


class OSMRoadsDownloader(OSMDataDownloaderBase):
    def __init__(
        self,
        extents: QgsRectangle,
        output_path: str = None,
    ):
        """
        Initialize the OSMRoadsDownloader class.

        Args:
            extents: A QgsRectangle object containing the bounding box coordinates for the query.
        """
        super().__init__(extents=extents, output_path=output_path)
        # set the output type to line
        self._set_output_type("line")
        osm_query = """[out:xml][timeout:25];
(
node["highway"="motorway"]({{bbox}});
node["highway"="motorway_link"]({{bbox}});
node["highway"="trunk"]({{bbox}});
node["highway"="trunk_link"]({{bbox}});
node["highway"="primary"]({{bbox}});
node["highway"="primary_link"]({{bbox}});
node["highway"="secondary"]({{bbox}});
node["highway"="secondary_link"]({{bbox}});
node["highway"="tertiary"]({{bbox}});
node["highway"="tertiary_link"]({{bbox}});
node["highway"="unclassified"]({{bbox}});
node["highway"="residential"]({{bbox}});
node["bicycle_road"="yes"]({{bbox}});
node["bicycle"="designated"]({{bbox}});
node["highway"="living_street"]({{bbox}});
node["highway"="pedestrian"]({{bbox}});
node["highway"="service"]({{bbox}});
node["service"="parking_aisle"]({{bbox}});
node["highway"="escape"]({{bbox}});
node["highway"="road"]({{bbox}});
node["highway"="construction"]({{bbox}});
node["junction"="roundabout"]({{bbox}});
node["junction"="circular"]({{bbox}});
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
way["bicycle_road"="yes"]({{bbox}});
way["bicycle"="designated"]({{bbox}});
way["highway"="living_street"]({{bbox}});
way["highway"="pedestrian"]({{bbox}});
way["highway"="service"]({{bbox}});
way["service"="parking_aisle"]({{bbox}});
way["highway"="escape"]({{bbox}});
way["highway"="road"]({{bbox}});
way["highway"="construction"]({{bbox}});
way["junction"="roundabout"]({{bbox}});
way["junction"="circular"]({{bbox}});
relation["highway"="motorway"]({{bbox}});
relation["highway"="motorway_link"]({{bbox}});
relation["highway"="trunk"]({{bbox}});
relation["highway"="trunk_link"]({{bbox}});
relation["highway"="primary"]({{bbox}});
relation["highway"="primary_link"]({{bbox}});
relation["highway"="secondary"]({{bbox}});
relation["highway"="secondary_link"]({{bbox}});
relation["highway"="tertiary"]({{bbox}});
relation["highway"="tertiary_link"]({{bbox}});
relation["highway"="unclassified"]({{bbox}});
relation["highway"="residential"]({{bbox}});
relation["bicycle_road"="yes"]({{bbox}});
relation["bicycle"="designated"]({{bbox}});
relation["highway"="living_street"]({{bbox}});
relation["highway"="pedestrian"]({{bbox}});
relation["highway"="service"]({{bbox}});
relation["service"="parking_aisle"]({{bbox}});
relation["highway"="escape"]({{bbox}});
relation["highway"="road"]({{bbox}});
relation["highway"="construction"]({{bbox}});
relation["junction"="roundabout"]({{bbox}});
relation["junction"="circular"]({{bbox}});
);
(._;>;);
out geom;"""
        # outbody;""" ### Dont move the quotes to the next line !!!!
        ### if you do the query_prepare will think the format is not in oql format

        self.set_osm_query(osm_query)
        self.submit_query()
        log_message("OSMRoadsDownloader Initialized")
