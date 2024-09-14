import xml.etree.ElementTree as ET
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry,
    QgsPointXY, QgsPolygon, QgsFields, QgsField, QgsCoordinateReferenceSystem,
    QgsVectorFileWriter, QgsApplication, QgsBlockingNetworkRequest, QgsNetworkRequest
)
from qgis.PyQt.QtCore import QByteArray, QUrl, QObject, QVariant

# Please see https://gis.stackexchange.com/questions/343126/performing-sync-or-async-network-request-in-pyqgis
# for the QgsBlockingNetworkRequest class and QgsNetworkRequest class
# notes on when to use them
class OsmDataDownloader(QObject):
    def __init__(self, query: str = "", output_path: str = "", parent=None):
        """
        :param query: Overpass API query as a string
        :param output_path: File path for saving the output shapefile
        """
        super().__init__(parent)
        self.query = query
        self.output_path = output_path

    def send_query(self):
        """
        Sends the Overpass API query using QgsBlockingNetworkRequest to fetch OSM data synchronously.
        """
        url = QUrl("http://overpass-api.de/api/interpreter")
        request = QgsNetworkRequest(url)
        request.setMethod(QgsNetworkRequest.PostMethod)
        request.setHeader("Content-Type", "application/x-www-form-urlencoded")

        # Send the POST request using QgsBlockingNetworkRequest
        blocking_request = QgsBlockingNetworkRequest()
        reply = blocking_request.fetch(request, QByteArray(self.query.encode('utf-8')))

        # Check for errors in the reply
        if reply.error():
            print(f"Network Error: {reply.errorMessage()}")
            return None
        else:
            # Return the response data
            return reply.content().data().decode('utf-8')

    def download_line_data(self):
        """
        Processes line-based OSM data (e.g., footpaths) and saves it as a shapefile.
        """
        data = self.send_query()
        if not data:
            return

        # Parse the XML
        root = ET.fromstring(data)

        # Create a new layer to store the line-based data
        crs = QgsCoordinateReferenceSystem(4326)  # WGS 84
        layer = QgsVectorLayer("LineString?crs=EPSG:4326", "Lines", "memory")
        pr = layer.dataProvider()

        # Add attributes
        pr.addAttributes([QgsField("osm_id", QVariant.String)])
        layer.updateFields()

        # Iterate over the ways and extract coordinates
        for way in root.findall(".//way"):
            osm_id = way.get('id')
            coords = []
            for nd in way.findall("nd"):
                ref = nd.get('ref')
                node = root.find(f".//node[@id='{ref}']")
                lat = float(node.get('lat'))
                lon = float(node.get('lon'))
                coords.append(QgsPointXY(lon, lat))

            # Create a feature
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPolylineXY(coords))
            feature.setAttributes([osm_id])
            pr.addFeatures([feature])

        # Add the layer to the QGIS project
        QgsProject.instance().addMapLayer(layer)

        # Save to a shapefile
        QgsVectorFileWriter.writeAsVectorFormat(layer, self.output_path, "UTF-8", crs, "ESRI Shapefile")
        print(f"Line-based shapefile saved to {self.output_path}")

    def download_polygon_data(self):
        """
        Processes polygon-based OSM data (e.g., buildings) and saves it as a shapefile.
        """
        data = self.send_query()
        if not data:
            return

        # Parse the XML
        root = ET.fromstring(data)

        # Create a new layer to store the polygon-based data
        crs = QgsCoordinateReferenceSystem(4326)  # WGS 84
        layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "Polygons", "memory")
        pr = layer.dataProvider()

        # Add attributes
        pr.addAttributes([QgsField("osm_id", QVariant.String)])
        layer.updateFields()

        # Iterate over the ways and extract coordinates (forming polygons)
        for way in root.findall(".//way"):
            osm_id = way.get('id')
            coords = []
            for nd in way.findall("nd"):
                ref = nd.get('ref')
                node = root.find(f".//node[@id='{ref}']")
                lat = float(node.get('lat'))
                lon = float(node.get('lon'))
                coords.append(QgsPointXY(lon, lat))

            # Close the polygon (by connecting the first and last points)
            if coords[0] != coords[-1]:
                coords.append(coords[0])

            # Create a feature
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPolygonXY([coords]))
            feature.setAttributes([osm_id])
            pr.addFeatures([feature])

        # Add the layer to the QGIS project
        QgsProject.instance().addMapLayer(layer)

        # Save to a shapefile
        QgsVectorFileWriter.writeAsVectorFormat(layer, self.output_path, "UTF-8", crs, "ESRI Shapefile")
        print(f"Polygon-based shapefile saved to {self.output_path}")
