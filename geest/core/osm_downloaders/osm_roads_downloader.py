from .osm_data_downloader_base import OSMDataDownloaderBase


class OSMRoadsDownloader(OSMDataDownloaderBase):
    def __init__(self):
        """
        Initialize the OSMDataDownloader class.

        Args:
            base_url (str): The base URL for the Overpass API.
            api_key (str): The API key for authentication.
            bounding_box (Dict[str, float]): A dictionary containing the bounding box coordinates
                                             with keys 'S', 'E', 'N', 'W'.
        """
        super().__init__()
        # set the output type to line
        self.set_output_type("line")
        # Define the bounding box coordinates
        S, E, N, W = (
            40.7128,
            -74.0060,
            40.7308,
            -73.9352,
        )  # Example coordinates for New York City

        osm_query = """
Data:data=[out:xml][timeout:25];
(
node["highway"="motorway"]({S},{E},{N},{W});
node["highway"="motorway_link"]({S},{E},{N},{W});
node["highway"="trunk"]({S},{E},{N},{W});
node["highway"="trunk_link"]({S},{E},{N},{W});
node["highway"="primary"]({S},{E},{N},{W});
node["highway"="primary_link"]({S},{E},{N},{W});
node["highway"="secondary"]({S},{E},{N},{W});
node["highway"="secondary_link"]({S},{E},{N},{W});
node["highway"="tertiary"]({S},{E},{N},{W});
node["highway"="tertiary_link"]({S},{E},{N},{W});
node["highway"="unclassified"]({S},{E},{N},{W});
node["highway"="residential"]({S},{E},{N},{W});
node["bicycle_road"="yes"]({S},{E},{N},{W});
node["bicycle"="designated"]({S},{E},{N},{W});
node["highway"="living_street"]({S},{E},{N},{W});
node["highway"="pedestrian"]({S},{E},{N},{W});
node["highway"="service"]({S},{E},{N},{W});
node["service"="parking_aisle"]({S},{E},{N},{W});
node["highway"="escape"]({S},{E},{N},{W});
node["highway"="road"]({S},{E},{N},{W});
node["highway"="construction"]({S},{E},{N},{W});
node["junction"="roundabout"]({S},{E},{N},{W});
node["junction"="circular"]({S},{E},{N},{W});
way["highway"="motorway"]({S},{E},{N},{W});
way["highway"="motorway_link"]({S},{E},{N},{W});
way["highway"="trunk"]({S},{E},{N},{W});
way["highway"="trunk_link"]({S},{E},{N},{W});
way["highway"="primary"]({S},{E},{N},{W});
way["highway"="primary_link"]({S},{E},{N},{W});
way["highway"="secondary"]({S},{E},{N},{W});
way["highway"="secondary_link"]({S},{E},{N},{W});
way["highway"="tertiary"]({S},{E},{N},{W});
way["highway"="tertiary_link"]({S},{E},{N},{W});
way["highway"="unclassified"]({S},{E},{N},{W});
way["highway"="residential"]({S},{E},{N},{W});
way["bicycle_road"="yes"]({S},{E},{N},{W});
way["bicycle"="designated"]({S},{E},{N},{W});
way["highway"="living_street"]({S},{E},{N},{W});
way["highway"="pedestrian"]({S},{E},{N},{W});
way["highway"="service"]({S},{E},{N},{W});
way["service"="parking_aisle"]({S},{E},{N},{W});
way["highway"="escape"]({S},{E},{N},{W});
way["highway"="road"]({S},{E},{N},{W});
way["highway"="construction"]({S},{E},{N},{W});
way["junction"="roundabout"]({S},{E},{N},{W});
way["junction"="circular"]({S},{E},{N},{W});
relation["highway"="motorway"]({S},{E},{N},{W});
relation["highway"="motorway_link"]({S},{E},{N},{W});
relation["highway"="trunk"]({S},{E},{N},{W});
relation["highway"="trunk_link"]({S},{E},{N},{W});
relation["highway"="primary"]({S},{E},{N},{W});
relation["highway"="primary_link"]({S},{E},{N},{W});
relation["highway"="secondary"]({S},{E},{N},{W});
relation["highway"="secondary_link"]({S},{E},{N},{W});
relation["highway"="tertiary"]({S},{E},{N},{W});
relation["highway"="tertiary_link"]({S},{E},{N},{W});
relation["highway"="unclassified"]({S},{E},{N},{W});
relation["highway"="residential"]({S},{E},{N},{W});
relation["bicycle_road"="yes"]({S},{E},{N},{W});
relation["bicycle"="designated"]({S},{E},{N},{W});
relation["highway"="living_street"]({S},{E},{N},{W});
relation["highway"="pedestrian"]({S},{E},{N},{W});
relation["highway"="service"]({S},{E},{N},{W});
relation["service"="parking_aisle"]({S},{E},{N},{W});
relation["highway"="escape"]({S},{E},{N},{W});
relation["highway"="road"]({S},{E},{N},{W});
relation["highway"="construction"]({S},{E},{N},{W});
relation["junction"="roundabout"]({S},{E},{N},{W});
relation["junction"="circular"]({S},{E},{N},{W});
);
(._;>;);
outbody;
"""
        # Format the query with the bounding box
        self.set_extents(S=S, E=E, N=N, W=W)
        self.set_output_path("osm_roads.gpkg")
        self.set_osm_query(self.formatted_query)
