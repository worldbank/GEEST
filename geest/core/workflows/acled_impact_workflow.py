import os
import csv
from functools import lru_cache
from .workflow_base import WorkflowBase
from geest.core import JsonTreeItem
from geest.core.timer import Timer, timed
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

    @timed
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
        :param attributes: Item containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        :working_directory: Folder containing study_area.gpkg and where the outputs will be placed. If not set will be taken from QSettings.
        """
        with Timer("🚀 init_workflow"):
            super().__init__(
                item, cell_size_m, feedback, context, working_directory
            )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree

            with Timer("📋 validate_inputs"):
                self.csv_file = self.attributes.get(
                    "use_csv_to_point_layer_csv_file", ""
                )
                if not self.csv_file:
                    error = "No CSV file provided."
                    self.attributes["error"] = error
                    raise Exception(error)

            with Timer("📊 load_csv_data"):
                self.features_layer = self._load_csv_as_point_layer()
                if not self.features_layer.isValid():
                    error = f"ACLED CSV layer is not valid.: {self.csv_file}"
                    self.attributes["error"] = error
                    raise Exception(error)

            self.feedback.setProgress(1.0)

    @timed
    def _process_features_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
    ) -> str:
        """
        Executes the actual workflow logic for a single area
        Must be implemented by subclasses.

        :current_area: Current polygon from our study area.
        :current_bbox: Bounding box of the above area.
        :area_features: A vector layer of features to analyse that includes only features in the study area.
        :index: Iteration / number of area being processed.

        :return: Raster file path of the output.
        """
        with Timer(f"🌎 process_area_{index}"):
            # Step 1: Buffer the selected features by 5 km
            with Timer("🔄 buffer_features"):
                buffered_layer = self._buffer_features(area_features)
                self.feedback.setProgress(10.0)

            # Step 2: Assign values based on event_type
            with Timer("📝 assign_scores"):
                scored_layer = self._assign_scores(buffered_layer)
                self.feedback.setProgress(40.0)

            # Step 3: Dissolve and remove overlapping areas, keeping areas with the lowest value
            with Timer("🔍 overlay_analysis"):
                dissolved_layer = self._overlay_analysis(scored_layer)
                self.feedback.setProgress(60.0)

            # Step 4: Rasterize the dissolved layer
            with Timer("📊 rasterize_output"):
                raster_output = self._rasterize(
                    dissolved_layer,
                    current_bbox,
                    index,
                    value_field="min_value",
                    default_value=5,
                )
                self.feedback.setProgress(80.0)

            return raster_output

    @timed
    def _load_csv_as_point_layer(self) -> QgsVectorLayer:
        """
        Load the CSV file, extract relevant columns (latitude, longitude, event_type),
        create a point layer from the retained columns, reproject the points to match the
        CRS of the layers from the GeoPackage, and save the result as a shapefile.

        Returns:
            QgsVectorLayer: The reprojected point layer created from the CSV.
        """
        with Timer("🌐 load_csv_data"):
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
            with Timer("📄 parse_csv"):
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
            # Ensure the workflow directory exists
            with Timer("💾 save_points"):
                if not os.path.exists(self.workflow_directory):
                    os.makedirs(self.workflow_directory)
                shapefile_path = os.path.join(
                    self.workflow_directory, f"{self.layer_id}_acled_points.shp"
                )
                log_message(f"Writing points to {shapefile_path}")
                error = QgsVectorFileWriter.writeAsVectorFormat(
                    point_layer,
                    shapefile_path,
                    "utf-8",
                    self.target_crs,
                    "ESRI Shapefile",
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

    @timed
    @lru_cache(
        maxsize=32
    )  # Cache buffer results as they may be repeated with same parameters
    def _buffer_features(self, layer: QgsVectorLayer) -> QgsVectorLayer:
        """
        Buffer the input features by 5 km.

        Args:
            layer (QgsVectorLayer): The input feature layer.

        Returns:
            QgsVectorLayer: The buffered features layer.
        """
        with Timer("⭕ create_buffers"):
            output_name = f"{self.layer_id}_buffered"
            output_path = os.path.join(self.workflow_directory, f"{output_name}.shp")

            with Timer("🔄 run_buffer_algorithm"):
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

    @timed
    def _assign_scores(self, layer: QgsVectorLayer) -> QgsVectorLayer:
        """
        Assign values to buffered polygons based on their event_type.

        Args:
            layer_path (str): The buffered features layer.

        Returns:
            QgsVectorLayer: A new layer with a "value" field containing the assigned scores.
        """
        with Timer("🏷️ score_assignment"):
            log_message(f"Assigning scores to {layer.name()}")

            # Define scoring categories based on event_type
            event_scores = {
                "Battles": 0,
                "Explosions/Remote violence": 1,
                "Violence against civilians": 2,
                "Protests": 4,
                "Riots": 4,
            }

            # Create a new field in the layer for the scores
            with Timer("🔢 add_value_field"):
                layer.startEditing()
                layer.dataProvider().addAttributes([QgsField("value", QVariant.Int)])
                layer.updateFields()

            # Assign scores based on event_type
            with Timer("📊 apply_scores"):
                for feature in layer.getFeatures():
                    event_type = feature["event_type"]
                    score = event_scores.get(event_type, 5)
                    feature.setAttribute("value", score)
                    layer.updateFeature(feature)

                layer.commitChanges()

            return layer

    @timed
    def _overlay_analysis(self, input_layer):
        """
        Perform an overlay analysis on a set of circular polygons, prioritizing areas with the lowest value in overlapping regions,
        and save the result as a shapefile.
        """
        with Timer("🧩 overlay_processing"):
            log_message("Overlay analysis started")

            # Step 2: Create a memory layer to store the result
            with Timer("🔧 create_result_layer"):
                result_layer = QgsVectorLayer(f"Polygon", "result_layer", "memory")
                result_layer.setCrs(self.target_crs)
                provider = result_layer.dataProvider()

                # Step 3: Add a field to store the minimum value (lower number = higher rank)
                provider.addAttributes([QgsField("min_value", QVariant.Int)])
                result_layer.updateFields()

            # Step 4: Perform the dissolve operation to separate disjoint polygons
            with Timer("🔄 dissolve_operation"):
                dissolve = processing.run(
                    "native:dissolve",
                    {
                        "INPUT": input_layer,
                        "FIELD": ["value"],
                        "SEPARATE_DISJOINT": True,
                        "OUTPUT": "TEMPORARY_OUTPUT",
                    },
                )["OUTPUT"]
                log_message(
                    f"Dissolved areas have {len(dissolve)} features",
                    tag="Geest",
                    level=Qgis.Info,
                )

            # Step 5: Perform the union to get all overlapping areas
            with Timer("🔄 union_operation"):
                union = processing.run(
                    "qgis:union",
                    {
                        "INPUT": dissolve,
                        "OUTPUT": "memory:",
                    },
                )["OUTPUT"]
                log_message(f"Unioned areas have {len(dissolve)} features")

            # Step 6: Iterate through the unioned features to assign the minimum value in overlapping areas
            with Timer("🔍 find_min_values"):
                unique_geometries = {}

                for feature in union.getFeatures():
                    geom = feature.geometry().asWkt()
                    attrs = (
                        feature.attributes()
                    )  # Use geometry as a key to identify unique areas
                    value_1 = attrs[input_layer.fields().indexFromName("value")]
                    value_2 = attrs[
                        input_layer.fields().indexFromName("value_2")
                    ]  # This comes from the unioned layer

                    # Assign the minimum value to the overlapping area
                    min_value = min(value_1, value_2)

                    log_message(
                        f"Processing feature with min value: {min_value}",
                        tag="Geest",
                        level=Qgis.Info,
                    )

                    # Check if this geometry is already in the dictionary
                    if geom in unique_geometries:
                        # If it exists, update only if the new min_value is lower
                        if min_value < unique_geometries[geom].attributes()[0]:
                            unique_geometries[geom].setAttribute(0, min_value)
                    else:
                        # Add new unique geometry with the min_value attribute
                        new_feature = QgsFeature()
                        new_feature.setGeometry(feature.geometry())
                        new_feature.setAttributes([min_value])
                        unique_geometries[geom] = new_feature

                # Add the filtered features to the result layer
                with Timer("📝 add_features_to_result"):
                    for unique_feature in unique_geometries.values():
                        provider.addFeature(unique_feature)

            # Step 7: Save the result layer to the specified output shapefile
            with Timer("💾 save_result"):
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

    @timed
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
        """
        pass

    @timed
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

    # Helper method for event type scoring with caching
    @lru_cache(maxsize=32)
    def _get_event_score(self, event_type: str) -> int:
        """
        Return score for an event type with caching.

        Args:
            event_type (str): The event type from ACLED data

        Returns:
            int: Score value (0-5, with lower being higher priority)
        """
        event_scores = {
            "Battles": 0,
            "Explosions/Remote violence": 1,
            "Violence against civilians": 2,
            "Protests": 4,
            "Riots": 4,
        }
        return event_scores.get(event_type, 5)
