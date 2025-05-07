import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
import time
import os

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
from osgeo import ogr


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
        # Use the base name of the output path + .xml to store the overpass response
        self.output_xml_path = output_path.replace(".gpkg", ".xml")
        if os.path.exists(self.output_xml_path):
            os.remove(self.output_xml_path)
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
        log_message("Sending request to Overpass API...")
        with open(self.output_xml_path, "wb") as output_file:
            response = self.network_manager.blockingPost(
                request, QByteArray(f"data={self.formatted_query}".encode())
            )
            output_file.write(response.content().data())
        log_message("Request sent. Response received...")

        # Check HTTP status code
        status_code = response.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        log_message(f"HTTP Status Code: {status_code}")
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

            if self.output_type == "point":
                log_message("Processing point data...")
                self.process_point_response()
            elif self.output_type == "line":
                log_message("Processing line data...")
                self.process_line_response()
            elif self.output_type == "polygon":
                log_message("Processing polygon data...")
                self.process_polygon_response()
            else:
                raise ValueError(
                    "Invalid output type. Must be 'point', 'line', or 'polygon'."
                )
        else:
            raise RuntimeError(f"Request failed with error: {response.errorMessage()}")

    def process_line_response(self) -> None:
        """Process the streamed OSM XML response and save it as a GeoPackage."""
        total_start = time.perf_counter()

        # Open the OSM XML file
        osm_driver = ogr.GetDriverByName("OSM")
        osm_data_source = osm_driver.Open(self.output_xml_path, 0)  # 0 means read-only
        if osm_data_source is None:
            raise RuntimeError(f"Failed to open OSM XML file: {self.output_xml_path}")

        # Get the 'lines' layer from the OSM data source
        lines_layer = osm_data_source.GetLayerByName("lines")
        if lines_layer is None:
            raise RuntimeError("No 'lines' layer found in the OSM XML file.")

        # Create the output GeoPackage
        gpkg_driver = ogr.GetDriverByName("GPKG")
        if os.path.exists(self.output_path):
            gpkg_driver.DeleteDataSource(self.output_path)
        output_data_source = gpkg_driver.CreateDataSource(self.output_path)
        if output_data_source is None:
            raise RuntimeError(f"Failed to create GeoPackage: {self.output_path}")

        # Create the output layer
        srs = lines_layer.GetSpatialRef()
        output_layer = output_data_source.CreateLayer(
            "OSM Line Data", srs, ogr.wkbLineString
        )
        if output_layer is None:
            raise RuntimeError("Failed to create output layer in GeoPackage.")

        # Add fields to the output layer
        id_field = ogr.FieldDefn("id", ogr.OFTString)
        output_layer.CreateField(id_field)

        # Copy features from the OSM 'lines' layer to the output layer
        features_added = 0
        total_features = lines_layer.GetFeatureCount()
        log_message(f"Total features to process: {total_features}")

        for i, feature in enumerate(lines_layer):
            output_feature = ogr.Feature(output_layer.GetLayerDefn())
            output_feature.SetGeometry(feature.GetGeometryRef().Clone())
            output_feature.SetField("id", feature.GetField("osm_id"))
            output_layer.CreateFeature(output_feature)
            output_feature = None  # Free the feature

            features_added += 1
            if features_added % 1000 == 0 or features_added == total_features:
                progress = (features_added / total_features) * 100
                log_message(
                    f"Processed {features_added}/{total_features} features ({progress:.2f}%)"
                )

        # Close the data sources
        osm_data_source = None
        output_data_source = None

        total_end = time.perf_counter()
        log_message(f"GeoPackage written to: {self.output_path}")
        log_message(f"Total processing time: {total_end - total_start:.2f}s")

    def process_point_response(self, response_data: str) -> None:
        """Process the OSM response and save it as a GeoPackage."""
        root = ET.fromstring(response_data)
        layer = QgsVectorLayer("Point?crs=EPSG:4326", "OSM Point Data", "memory")
        provider = layer.dataProvider()
        provider.addAttributes([QgsField("id", QVariant.String)])
        layer.updateFields()
        features_added = 0
        log_message("Finding and processing all nodes...")

        for node in root.findall(".//node"):
            node_id = node.get("id")
            lat = float(node.get("lat"))
            lon = float(node.get("lon"))
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
            feature.setAttributes([node_id])
            provider.addFeature(feature)
            features_added += 1
            if features_added % 1000 == 0:
                log_message(f"Added {features_added} features to the layer...")
        QgsVectorFileWriter.writeAsVectorFormat(
            layer, self.output_path, "UTF-8", layer.crs(), "GPKG"
        )
        log_message(f"GeoPackage written to: {self.output_path}")

    def process_polygon_response(self, response_data: str) -> None:
        """Process the OSM response and save it as a GeoPackage."""
        root = ET.fromstring(response_data)
        layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "OSM Polygon Data", "memory")
        provider = layer.dataProvider()
        provider.addAttributes([QgsField("id", QVariant.String)])
        layer.updateFields()
        features_added = 0
        log_message("Finding and processing all nodes...")

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
                features_added += 1
                if features_added % 1000 == 0:
                    log_message(f"Added {features_added} features to the layer...")

        QgsVectorFileWriter.writeAsVectorFormat(
            layer, self.output_path, "UTF-8", layer.crs(), "GPKG"
        )
        log_message(f"GeoPackage written to: {self.output_path}")
