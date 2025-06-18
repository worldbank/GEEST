import os
import csv
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem
from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeedback,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsPointXY,
    QgsProcessingContext,
    QgsProcessingException,
    QgsVectorFileWriter,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant
from qgis import processing
from geest.utilities import log_message


class AcledImpactWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'use_csv_to_point_layer' workflow.
    """

    def __init__(
        self,
        item: JsonTreeItem,
        cell_size_m: float,
        feedback: QgsFeedback,
        context: QgsProcessingContext,
        working_directory: str = None,
    ):
        """
        Initialize the workflow with attributes and feedback.
        """
        super().__init__(item, cell_size_m, feedback, context, working_directory)
        self.csv_file = self.attributes.get("use_csv_to_point_layer_csv_file", "")
        if not self.csv_file:
            error = "No CSV file provided."
            self.attributes["error"] = error
            raise Exception(error)

        # Load the CSV file as a point layer in a thread-safe manner
        self.features_layer = self.thread_safe_execute(self._load_csv_as_point_layer)
        if not self.features_layer.isValid():
            error = f"ACLED CSV layer is not valid: {self.csv_file}"
            self.attributes["error"] = error
            raise Exception(error)
        self.feedback.setProgress(1.0)

    def _process_features_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
    ) -> str:
        """
        Executes the actual workflow logic for a single area.
        """

        def process_area():
            # Step 1: Buffer the selected features by 5 km
            buffered_layer = self.thread_safe_execute(
                self._buffer_features, area_features
            )
            self.feedback.setProgress(10.0)

            # Step 2: Assign values based on event_type
            scored_layer = self.thread_safe_execute(self._assign_scores, buffered_layer)
            self.feedback.setProgress(40.0)

            # Step 3: Dissolve and remove overlapping areas, keeping areas with the lowest value
            dissolved_layer = self.thread_safe_execute(
                self._overlay_analysis, scored_layer
            )
            self.feedback.setProgress(60.0)

            # Step 4: Rasterize the dissolved layer
            raster_output = self.thread_safe_execute(
                self._rasterize,
                dissolved_layer,
                current_bbox,
                index,
                value_field="min_value",
                default_value=5,
            )
            self.feedback.setProgress(80.0)

            return raster_output

        # Execute the workflow logic in a thread-safe manner
        return self.thread_safe_execute(process_area)

    def _load_csv_as_point_layer(self) -> QgsVectorLayer:
        """
        Load the CSV file, extract relevant columns (latitude, longitude, event_type),
        create a point layer from the retained columns, reproject the points to match the
        CRS of the layers from the GeoPackage, and save the result as a shapefile.
        """
        source_crs = QgsCoordinateReferenceSystem(
            "EPSG:4326"
        )  # Assuming the CSV uses WGS84

        # Set up a coordinate transform from WGS84 to the target CRS
        transform_context = self.context.project().transformContext()
        coordinate_transform = QgsCoordinateTransform(
            source_crs, self.target_crs, transform_context
        )

        # Define fields for the point layer
        fields = QgsFields()
        fields.append(QgsField("event_type", QVariant.String))

        # Create an in-memory point layer in the target CRS
        point_layer = QgsVectorLayer(
            f"Point?crs={self.target_crs.authid()}", "acled_points", "memory"
        )
        point_provider = point_layer.dataProvider()
        point_provider.addAttributes(fields)
        point_layer.updateFields()

        # Read the CSV and add reprojected points to the layer
        with open(self.csv_file, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            features = []
            for row in reader:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
                event_type = row["event_type"]

                # Transform point to the target CRS
                point_wgs84 = QgsPointXY(lon, lat)
                point_transformed = coordinate_transform.transform(point_wgs84)

                feature = QgsFeature()
                feature.setGeometry(QgsGeometry.fromPointXY(point_transformed))
                feature.setAttributes([event_type])
                features.append(feature)

            point_provider.addFeatures(features)
            log_message(f"Loaded {len(features)} points from CSV")

        # Save the layer to disk as a shapefile
        if not os.path.exists(self.workflow_directory):
            os.makedirs(self.workflow_directory)
        shapefile_path = os.path.join(
            self.workflow_directory, f"{self.layer_id}_acled_points.shp"
        )
        log_message(f"Writing points to {shapefile_path}")
        error = QgsVectorFileWriter.writeAsVectorFormat(
            point_layer, shapefile_path, "utf-8", self.target_crs, "ESRI Shapefile"
        )

        if error[0] != 0:
            raise QgsProcessingException(
                f"Error saving point layer to disk: {error[1]}"
            )

        log_message(
            f"Point layer created from CSV saved to {shapefile_path}",
            tag="Geest",
            level=Qgis.Info,
        )

        # Reload the saved shapefile as the final point layer to ensure consistency
        saved_layer = QgsVectorLayer(shapefile_path, "acled_points", "ogr")
        if not saved_layer.isValid():
            raise QgsProcessingException(
                f"Failed to reload saved point layer from {shapefile_path}"
            )

        return saved_layer

    def _buffer_features(self, layer: QgsVectorLayer) -> QgsVectorLayer:
        """
        Buffer the input features by 5 km.
        """
        output_name = f"{self.layer_id}_buffered"
        output_path = os.path.join(self.workflow_directory, f"{output_name}.shp")
        buffered_layer = processing.run(
            "native:buffer",
            {
                "INPUT": layer,
                "DISTANCE": 5000,  # 5 km buffer
                "SEGMENTS": 5,
                "DISSOLVE": False,
                "OUTPUT": output_path,
            },
        )["OUTPUT"]
        return QgsVectorLayer(output_path, output_name, "ogr")

    def _assign_scores(self, layer: QgsVectorLayer) -> QgsVectorLayer:
        """
        Assign values to buffered polygons based on their event_type.
        """
        log_message(f"Assigning scores to {layer.name()}")
        event_scores = {
            "Battles": 0,
            "Explosions/Remote violence": 1,
            "Violence against civilians": 2,
            "Protests": 4,
            "Riots": 4,
        }

        layer.startEditing()
        layer.dataProvider().addAttributes([QgsField("value", QVariant.Int)])
        layer.updateFields()

        for feature in layer.getFeatures():
            event_type = feature["event_type"]
            score = event_scores.get(event_type, 5)
            feature.setAttribute("value", score)
            layer.updateFeature(feature)

        layer.commitChanges()
        return layer

    def _overlay_analysis(self, input_layer):
        """
        Perform an overlay analysis on a set of circular polygons, prioritizing areas with the lowest value in overlapping regions.
        """
        log_message("Overlay analysis started")
        result_layer = QgsVectorLayer(f"Polygon", "result_layer", "memory")
        result_layer.setCrs(self.target_crs)
        provider = result_layer.dataProvider()
        provider.addAttributes([QgsField("min_value", QVariant.Int)])
        result_layer.updateFields()

        dissolve = processing.run(
            "native:dissolve",
            {
                "INPUT": input_layer,
                "FIELD": ["value"],
                "SEPARATE_DISJOINT": True,
                "OUTPUT": "TEMPORARY_OUTPUT",
            },
        )["OUTPUT"]

        union = processing.run(
            "qgis:union",
            {
                "INPUT": dissolve,
                "OUTPUT": "memory:",
            },
        )["OUTPUT"]

        unique_geometries = {}
        for feature in union.getFeatures():
            geom = feature.geometry().asWkt()
            attrs = feature.attributes()
            value_1 = attrs[input_layer.fields().indexFromName("value")]
            value_2 = attrs[input_layer.fields().indexFromName("value_2")]
            min_value = min(value_1, value_2)

            if geom in unique_geometries:
                if min_value < unique_geometries[geom].attributes()[0]:
                    unique_geometries[geom].setAttribute(0, min_value)
            else:
                new_feature = QgsFeature()
                new_feature.setGeometry(feature.geometry())
                new_feature.setAttributes([min_value])
                unique_geometries[geom] = new_feature

        for unique_feature in unique_geometries.values():
            provider.addFeature(unique_feature)

        full_output_filepath = os.path.join(
            self.workflow_directory, f"{self.layer_id}_final.shp"
        )
        error = QgsVectorFileWriter.writeAsVectorFormat(
            result_layer,
            full_output_filepath,
            "UTF-8",
            result_layer.crs(),
            "ESRI Shapefile",
        )

        if error[0] == 0:
            log_message(
                f"Overlay analysis complete, output saved to {full_output_filepath}",
                tag="Geest",
                level=Qgis.Info,
            )
        else:
            raise QgsProcessingException(
                f"Error saving dissolved layer to disk: {error[1]}"
            )
        return QgsVectorLayer(full_output_filepath, f"{self.layer_id}_final", "ogr")

    # Default implementation of the abstract method - not used in this workflow
    def _process_raster_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_raster: str,
        index: int,
    ):
        """
        Executes the actual workflow logic for a single area using a raster.

        :current_area: Current polygon from our study area.
        :clip_area: Polygon to clip the raster to which is aligned to cell edges.
        :current_bbox: Bounding box of the above area.
        :area_raster: A raster layer of features to analyse that includes only bbox pixels in the study area.
        :index: Index of the current area.

        :return: Path to the reclassified raster.
        """
        pass

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
    ):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        pass
