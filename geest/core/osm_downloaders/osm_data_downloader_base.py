try:
    from defusedxml import ElementTree as ET
except ImportError:
    # Fallback to standard library with warning
    import xml.etree.ElementTree as ET  # nosec B405
    import warnings

    warnings.warn(
        "defusedxml not available, falling back to xml.etree.ElementTree. "
        "Consider installing defusedxml for better security: pip install defusedxml",
        UserWarning,
    )
from abc import ABC, abstractmethod
import time
import os
from osgeo import ogr

from qgis.core import (
    QgsProject,
    QgsCoordinateTransform,
    QgsVectorLayer,
    QgsFeature,
    QgsRectangle,
    QgsGeometry,
    QgsField,
    QgsVectorFileWriter,
    QgsPointXY,
    QgsNetworkAccessManager,
    QgsFeedback,
    QgsCoordinateReferenceSystem,
)
from qgis.PyQt.QtCore import QVariant, QUrl, QByteArray
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis import processing  # QGIS processing API

from geest.core import setting
from geest.utilities import log_message
from .query_preparation import QueryPreparation


class OSMDataDownloaderBase(ABC):
    def __init__(
        self,
        extents: QgsRectangle,
        output_path: str = None,
        output_crs: QgsCoordinateReferenceSystem = None,
        filename: str = None,  # will also set the layer name in the gpkg
        use_cache: bool = False,
        delete_gpkg: bool = True,
        feedback: QgsFeedback = None,
    ):
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
        self.output_crs = output_crs

        self.filename = filename  # will also set the layer name in the gpkg
        self.use_cache = use_cache
        self.delete_gpkg = delete_gpkg
        self.feedback = feedback

        # Use the base name of the output path + .xml to store the overpass response
        self.output_xml_path = output_path.replace(".gpkg", ".xml")

        if os.path.exists(self.output_xml_path) and not self.use_cache:
            log_message(
                "OSM xml file exists but use_cache is false: Deleting existing XML file..."
            )
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
        """Download OSM data using the Overpass API and save it as a shapefile.

        :return: None
        :raises ValueError: If the query or output path is not set.
        :raises RuntimeError: If the request fails or if the response is not valid.
        :raises Exception: If the request fails or if the response is not valid.
        """
        if self.use_cache and os.path.exists(self.output_xml_path):
            log_message(f"Using cached data from {self.output_xml_path}")
            return

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
            return
        else:
            raise RuntimeError(f"Request failed with error: {response.errorMessage()}")

    def process_response(self) -> bool:
        """ "Process the downloaded OSM data and save it as a GeoPackage.

        This method will call the appropriate processing method based on the output type.

        :return: bool True if processing was successful, False otherwise.
        """
        if self.output_type == "point":
            log_message("Processing point data...")
            try:
                self.process_point_response()
            except Exception as e:
                log_message(f"Error processing point data: {e}")
                raise e

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

    def process_line_response(self) -> None:
        """
        Process the streamed OSM XML response and efficiently save the 'lines' layer into a GeoPackage.

        This method uses OGR's built-in CopyLayer functionality for optimal performance, similar to ogr2ogr.
        If self.output_crs is provided, the data will be reprojected from EPSG:4326 to the specified CRS.
        It provides indeterminate progress feedback since exact feature count is unavailable.

        If the GeoPackage already exists:
        - When 'delete_gpkg' is True, the whole GeoPackage file is removed and recreated.
        - When 'delete_gpkg' is False, only the target layer ('OSM_Line_Data') is removed if it exists,
        and then recreated without deleting the entire GeoPackage.

        Raises:
            RuntimeError: If the input XML cannot be read or if the output GeoPackage layer cannot be created.
        """
        total_start = time.perf_counter()

        self.feedback.setProgress(20)

        # Open input OSM XML data source
        osm_driver = ogr.GetDriverByName("OSM")
        osm_data_source = osm_driver.Open(self.output_xml_path, 0)
        if osm_data_source is None:
            raise RuntimeError(f"Failed to open OSM XML file: {self.output_xml_path}")

        lines_layer = osm_data_source.GetLayerByName("lines")
        if lines_layer is None:
            raise RuntimeError("No 'lines' layer found in the OSM XML file.")

        gpkg_driver = ogr.GetDriverByName("GPKG")
        working_layer = self.filename + "_4326"
        if os.path.exists(self.output_path):
            if self.delete_gpkg:
                gpkg_driver.DeleteDataSource(self.output_path)
                output_data_source = gpkg_driver.CreateDataSource(self.output_path)
            else:
                output_data_source = gpkg_driver.Open(self.output_path, update=1)
                # Remove existing layer if present
                existing_layer = output_data_source.GetLayerByName(self.filename)
                if existing_layer:
                    output_data_source.DeleteLayer(self.filename)
                existing_layer = output_data_source.GetLayerByName(working_layer)
                if existing_layer:
                    output_data_source.DeleteLayer(working_layer)
        else:
            output_data_source = gpkg_driver.CreateDataSource(self.output_path)

        if output_data_source is None:
            raise RuntimeError(
                f"Failed to create or open GeoPackage: {self.output_path}"
            )

        self.feedback.setProgress(40)

        # Perform layer copy with reprojection if specified
        output_layer = output_data_source.CopyLayer(lines_layer, working_layer)
        if output_layer is None:
            raise RuntimeError("Failed to copy lines layer to GeoPackage.")

        self.feedback.setProgress(60)

        # Cleanup data sources
        osm_data_source = None
        output_data_source = None

        # Now use QGIS processing to reproject the layer from 4326 to the project crs
        # I tried to do this in one operation passing options for crs to CopyLayer
        # but it seems it is not supported / working
        log_message(f"Using CRS: {self.output_crs.authid()} for OSM download")
        source_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        transform_context = QgsProject.instance().transformContext()

        transform = QgsCoordinateTransform(
            source_crs, self.output_crs, transform_context
        )
        # pipeline = transform.coordinateOperation().projString()

        # log_message(f"Proj4 operation: {pipeline}")
        reproject = processing.run(
            "native:reprojectlayer",
            {
                "INPUT": f"{self.output_path}|layername={self.filename}_4326",
                "TARGET_CRS": self.output_crs,
                "CONVERT_CURVED_GEOMETRIES": False,
                # "OPERATION": "+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +proj=utm +zone=36 +ellps=WGS84",
                # The proj4 pipeline string is only available in QGIS >= 3.26
                # "OPERATION": pipeline,
                "OUTPUT": f"ogr:dbname='{self.output_path}' table=\"{self.filename}\" (geom)",
            },
        )
        self.feedback.setProgress(100)  # Set progress complete

        total_end = time.perf_counter()
        log_message(f"GeoPackage written to: {self.output_path} table: {self.filename}")
        log_message(f"Total processing time: {total_end - total_start:.2f}s")

    def process_point_response(self, response_data: str) -> None:
        """Process the OSM response and save it as a GeoPackage."""
        root = ET.fromstring(response_data)  # nosec B314
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
        root = ET.fromstring(response_data)  # nosec B314
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
