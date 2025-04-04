import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod

from qgis.core import (
    QgsVectorLayer,
    QgsFeature,
    QgsRectangle,
    QgsGeometry,
    QgsField,
    QgsVectorFileWriter,
    QgsPointXY,
    QgsNetworkAccessManager,
)
from qgis.PyQt.QtCore import QVariant, QUrl, QByteArray
from qgis.PyQt.QtNetwork import QNetworkRequest

from geest.core import setting
from geest.utilities import log_message
from .query_preparation import QueryPreparation


class OSMDataDownloaderBase(ABC):
    def __init__(self, extents: QgsRectangle, output_path: str = None):
        """
        Initialize the OSMDataDownloaderBase class.

        Args:
            QgsRectangle: A QgsRectangle object containing the bounding box coordinates.
        """
        self.base_url = (
            "https://overpass-api.de/api/interpreter?info=QgisQuickOSMPlugin"
        )
        self.network_manager = QgsNetworkAccessManager()
        self.osm_query = None  # The raw Overpass API query
        self.formatted_query = None  # The Overpass API query with bbox substituted
        self.output_type = None  # Possible values: 'point', 'line', 'polygon'
        # These are required
        self.extents = extents  # The bounding box extents (S, E, N, W)
        self.output_path = output_path  # The output path for the GeoPackage
        if self.extents is None:
            raise ValueError("Bounding box extents not set.")
        if self.output_path is None:
            raise ValueError("Output path not set.")

    def set_osm_query(self, query: str) -> None:
        """Set the Overpass API query.

        Setting the query will also set the formatted query with the bounding box
        coordinates substituted.

        Args:
            query (str): The Overpass API query string. Use string
                formatting to substitute the bounding box coordinates.
                e.g. "node["highway"="motorway"]({S},{E},{N},{W});"

        """
        if self.extents is None:
            raise ValueError("Bounding box extents not set.")
        if query is None:
            raise ValueError("OSM query not provided.")
        self.osm_query = query
        self.osm_query = self.osm_query.replace("\n", "%0A")
        preparer = QueryPreparation(self.osm_query, self.extents)
        final_query = preparer.prepare_query()
        self.formatted_query = final_query
        log_message("OSM Query Set")

    def _set_output_type(self, output_type: str) -> None:
        """Set the output type for the data.

        Args:
            output_type (str): The type of output data ('point', 'line', 'polygon').
        """
        if output_type not in ["point", "line", "polygon"]:
            raise ValueError(
                "Invalid output type. Must be 'point', 'line', or 'polygon'."
            )
        self.output_type = output_type

    def submit_query(self) -> None:
        """Download OSM data using the Overpass API and save it as a shapefile."""
        request = QNetworkRequest()
        request.setUrl(QUrl(self.base_url))

        if self.formatted_query is None:
            raise ValueError(
                "OSM query not set. Please set the query before submitting."
            )
        if self.output_path is None:
            raise ValueError(
                "Output path not set. Please set the output path before submitting."
            )

        # Send the request and connect the finished signal
        response = self.network_manager.blockingPost(
            request, QByteArray(f"data={self.formatted_query}".encode())
        )

        # Check HTTP status code
        status_code = response.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if status_code is None:
            raise RuntimeError("No status code received. Network issue?")

        if status_code == 404:
            raise RuntimeError(f"Error 404: Endpoint {self.base_url} not found.")
        elif status_code == 401:
            raise ValueError("Invalid API token. Please check your credentials.")
        elif status_code == 429:
            raise RuntimeError("API quota exceeded. Please try again later.")
        elif status_code >= 400:
            # Generic error handling for other client/server errors
            raise RuntimeError(f"HTTP Error {status_code}: {response.content()}")

        if status_code == 200:
            response_data = response.content().data().decode("utf-8")
            if self.output_type == "point":
                self.process_point_response(response_data)
            elif self.output_type == "line":
                self.process_line_response(response_data)
            elif self.output_type == "polygon":
                self.process_polygon_response(response_data)
            else:
                raise ValueError(
                    "Invalid output type. Must be 'point', 'line', or 'polygon'."
                )
            self.process_line_response(response_data)
        else:
            raise RuntimeError(f"Request failed with error: {response.errorMessage()}")

    def process_line_response(self, response_data: str) -> None:
        """Process the OSM response and save it as a GeoPackage."""
        root = ET.fromstring(response_data)
        layer = QgsVectorLayer("LineString?crs=EPSG:4326", "OSM Line Data", "memory")
        provider = layer.dataProvider()
        provider.addAttributes([QgsField("id", QVariant.String)])
        layer.updateFields()

        for way in root.findall(".//way"):
            way_id = way.get("id")
            coords = []
            for nd in way.findall("nd"):
                ref = nd.get("ref")
                node = root.find(f".//node[@id='{ref}']")
                if node is not None:
                    lat = float(node.get("lat"))
                    lon = float(node.get("lon"))
                    coords.append(QgsPointXY(lon, lat))

            if coords:
                feature = QgsFeature()
                feature.setGeometry(QgsGeometry.fromPolylineXY(coords))
                feature.setAttributes([way_id])
                provider.addFeature(feature)

        QgsVectorFileWriter.writeAsVectorFormat(
            layer, self.output_path, "UTF-8", layer.crs(), "GPKG"
        )
        print(f"GeoPackage written to: {self.output_path}")

    def process_point_response(self, response_data: str) -> None:
        """Process the OSM response and save it as a GeoPackage."""
        root = ET.fromstring(response_data)
        layer = QgsVectorLayer("Point?crs=EPSG:4326", "OSM Point Data", "memory")
        provider = layer.dataProvider()
        provider.addAttributes([QgsField("id", QVariant.String)])
        layer.updateFields()

        for node in root.findall(".//node"):
            node_id = node.get("id")
            lat = float(node.get("lat"))
            lon = float(node.get("lon"))
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
            feature.setAttributes([node_id])
            provider.addFeature(feature)

        QgsVectorFileWriter.writeAsVectorFormat(
            layer, self.output_path, "UTF-8", layer.crs(), "GPKG"
        )
        print(f"GeoPackage written to: {self.output_path}")

    def process_polygon_response(self, response_data: str) -> None:
        """Process the OSM response and save it as a GeoPackage."""
        root = ET.fromstring(response_data)
        layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "OSM Polygon Data", "memory")
        provider = layer.dataProvider()
        provider.addAttributes([QgsField("id", QVariant.String)])
        layer.updateFields()

        for way in root.findall(".//way"):
            way_id = way.get("id")
            coords = []
            for nd in way.findall("nd"):
                ref = nd.get("ref")
                node = root.find(f".//node[@id='{ref}']")
                if node is not None:
                    lat = float(node.get("lat"))
                    lon = float(node.get("lon"))
                    coords.append(QgsPointXY(lon, lat))

            if coords and coords[0] == coords[-1]:  # Ensure the polygon is closed
                feature = QgsFeature()
                feature.setGeometry(QgsGeometry.fromPolygonXY([coords]))
                feature.setAttributes([way_id])
                provider.addFeature(feature)

        QgsVectorFileWriter.writeAsVectorFormat(
            layer, self.output_path, "UTF-8", layer.crs(), "GPKG"
        )
        print(f"GeoPackage written to: {self.output_path}")
