# -*- coding: utf-8 -*-
"""📦 Acled Impact Workflow module.

This module contains functionality for acled impact workflow.
"""
import csv
import os

from qgis import processing
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

from geest.core import JsonTreeItem
from geest.utilities import log_message

from .mappings import buffer_distances, event_scores
from .workflow_base import WorkflowBase


class AcledImpactWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'use_csv_to_point_layer' workflow.
    """

    def __init__(
        self,
        item: JsonTreeItem,
        cell_size_m: float,
        analysis_scale: str,
        feedback: QgsFeedback,
        context: QgsProcessingContext,
        working_directory: str = None,
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param item: JsonTreeItem representing the analysis, dimension, or factor to process.
        :param cell_size_m: Cell size in meters for rasterization.
        :param analysis_scale: Scale of the analysis, e.g., 'local', 'national'
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :param context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        :param working_directory: Folder containing study_area.gpkg and where the outputs will be placed. If not set will be taken from QSettings.
        """
        super().__init__(
            item, cell_size_m, analysis_scale, feedback, context, working_directory
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.csv_file = self.attributes.get("use_csv_to_point_layer_csv_file", "")
        if not self.csv_file:
            error = "No CSV file provided."
            self.attributes["error"] = error
            raise Exception(error)
        self.features_layer = self._load_csv_as_point_layer()
        if not self.features_layer.isValid():
            error = f"ACLED CSV layer is not valid.: {self.csv_file}"
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
        Executes the actual workflow logic for a single area
        Must be implemented by subclasses.

        :current_area: Current polygon from our study area.
        :current_bbox: Bounding box of the above area.
        :area_features: A vector layer of features to analyse that includes only features in the study area.
        :index: Iteration / number of area being processed.

        :return: Raster file path of the output.
        """

        # Step 1: Buffer the selected features by relevant
        #         distance for each event type and assign values
        #         to the buffer layer
        buffered_layer = self._buffer_features(area_features)
        self.feedback.setProgress(10.0)

        # Step 2: Assign values based on event_type
        # scored_layer = self._assign_scores(buffered_layer)
        self.feedback.setProgress(40.0)

        # Step 3: Dissolve and remove overlapping areas, keeping areas with the lowest value
        dissolved_layer = self._overlay_analysis(buffered_layer)
        self.feedback.setProgress(60.0)

        # Step 4: Rasterize the dissolved layer
        raster_output = self._rasterize(
            dissolved_layer,
            current_bbox,
            index,
            value_field="min_value",
            default_value=5,
        )
        self.feedback.setProgress(80.0)

        return raster_output

    def _load_csv_as_point_layer(self) -> QgsVectorLayer:
        """
        Load the CSV file, extract relevant columns (latitude, longitude, event_type),
        create a point layer from the retained columns, reproject the points to match the
        CRS of the layers from the GeoPackage, and save the result as a shapefile.

        Returns:
            QgsVectorLayer: The reprojected point layer created from the CSV.
        """
        source_crs = QgsCoordinateReferenceSystem("EPSG:4326")  # Assuming the CSV uses WGS84
        # Set up a coordinate transform from WGS84 to the target CRS
        transform_context = self.context.project().transformContext()
        coordinate_transform = QgsCoordinateTransform(source_crs, self.target_crs, transform_context)

        # Define fields for the point layer
        fields = QgsFields()
        fields.append(QgsField("event_type", QVariant.String))
        fields.append(QgsField("value", QVariant.Int))
        fields.append(QgsField("buffer_m", QVariant.Int))
        fields.append(QgsField("score", QVariant.Int))

        # Create an in-memory point layer in the target CRS
        point_layer = QgsVectorLayer(f"Point?crs={self.target_crs.authid()}", "acled_points", "memory")
        point_provider = point_layer.dataProvider()
        point_provider.addAttributes(fields)  # type: ignore
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
                value = event_scores.get(event_type, 5)
                buffer_m = buffer_distances.get(event_type, 0)
                score = 0  # this will be replaced later with the lowest overlapping score
                feature.setAttributes([event_type, value, buffer_m, score])
                features.append(feature)

            point_provider.addFeatures(features)  # type: ignore
            log_message(f"Loaded {len(features)} points from CSV")
        # Save the layer to disk as a shapefile
        # Ensure the workflow directory exists
        if not os.path.exists(self.workflow_directory):
            os.makedirs(self.workflow_directory)
        shapefile_path = os.path.join(self.workflow_directory, f"{self.layer_id}_acled_points.shp")
        log_message(f"Writing points to {shapefile_path}")
        error = QgsVectorFileWriter.writeAsVectorFormat(
            point_layer, shapefile_path, "utf-8", self.target_crs, "ESRI Shapefile"
        )

        if error[0] != 0:
            raise QgsProcessingException(f"Error saving point layer to disk: {error[1]}")

        log_message(
            f"Point layer created from CSV saved to {shapefile_path}",
            tag="Geest",
            level=Qgis.Info,
        )

        # Reload the saved shapefile as the final point layer to ensure consistency
        saved_layer = QgsVectorLayer(shapefile_path, "acled_points", "ogr")
        if not saved_layer.isValid():
            raise QgsProcessingException(f"Failed to reload saved point layer from {shapefile_path}")

        return saved_layer

    def _buffer_features(self, layer: QgsVectorLayer) -> QgsVectorLayer:
        """
        Buffer the input features by 5 km.

        Args:
            layer (QgsVectorLayer): The input feature layer. This layer should be a point
               layer with two columns: value and buffer_m representing the geest score for
               the event and the distance to buffer in m.

        Returns:
            QgsVectorLayer: The buffered features layer.
        """
        # get a list of unique values for buffer_m in the input layer
        buffer_distances = layer.uniqueValues(layer.fields().indexFromName("buffer_m"))
        # Iterate the unique distances and buffer each set of features separately
        log_message(f"Buffering features in {layer.name()}")
        output_layer = None
        for distance in buffer_distances:
            log_message(f"Buffering features with buffer_m = {distance}")
            subset_expression = f'"buffer_m" = {distance}'
            subset_layer = processing.run(  # type: ignore[index]
                "native:extractbyexpression",
                {
                    "INPUT": layer,
                    "EXPRESSION": subset_expression,
                    "OUTPUT": "memory:",
                },
            )["OUTPUT"]
            buffered_subset = processing.run(  # type: ignore[index]
                "native:buffer",
                {
                    "INPUT": subset_layer,
                    "DISTANCE": distance,
                    "SEGMENTS": 5,
                    "DISSOLVE": False,
                    "OUTPUT": "memory:",
                },
            )["OUTPUT"]
            if output_layer is None:
                output_layer = buffered_subset
                continue
            # Append the buffered subset back to the main layer
            output_layer = processing.run(  # type: ignore[index]
                "native:mergevectorlayers",
                {
                    "LAYERS": [output_layer, buffered_subset],
                    "OUTPUT": "memory:",
                },
            )["OUTPUT"]
            del subset_layer

        output_name = f"{self.layer_id}_buffered"
        output_path = os.path.join(self.workflow_directory, f"{output_name}.shp")
        log_message(f"Writing buffered layer to {output_path}")
        error = QgsVectorFileWriter.writeAsVectorFormat(
            output_layer,
            output_path,
            "UTF-8",
            layer.crs(),
            "ESRI Shapefile",
        )
        log_message(f"Buffer result: {error}")
        del output_layer  # Free memory
        return QgsVectorLayer(output_path, output_name, "ogr")

    def _overlay_analysis(self, input_layer):
        """
        Perform an overlay analysis on a set of circular polygons, prioritizing areas with the lowest value in overlapping regions,
        and save the result as a shapefile.

        This function processes an input shapefile containing circular polygons, each with a value between 1 and 4, representing
        different priority levels. The function performs an overlay analysis where the polygons overlap and ensures that for any
        overlapping areas, the polygon with the lowest value (i.e., highest priority) is retained, while polygons with higher values
        are removed from those regions.

        The analysis is performed as follows:
        1. The input layer is loaded from the provided shapefile path.
        2. A dissolve operation is performed on the input layer to combine any adjacent polygons with the same value.
        3. A union operation is performed on the input layer to break the polygons into distinct, non-overlapping areas.
        4. For each distinct area, the value from the overlapping polygons is compared, and the minimum value (representing the highest priority) is assigned to that area.
        5. The resulting dataset, which consists of non-overlapping polygons with the highest priority (smallest value), is saved to a new shapefile at the specified output path.

        Parameters:
        -----------
        input_layer : QgsVectorLayer
            The input shapefile containing the circular polygons with values between 1 and 4.

        output_filepath : str
            The file path where the output shapefile with the results of the overlay analysis will be saved. The
            output will be saved in self.workflow_directory.

        Returns:
        --------
        None
            The function does not return a value but writes the result to the specified output shapefile.

        Logging:
        --------
        Messages related to the status of the operation (success or failure) are logged using QgsMessageLog with the tag 'Geest'
        and the log level set to Qgis.Info.

        Raises:
        -------
        IOError:
            If the input layer cannot be loaded or if an error occurs during the file writing process.

        Example:
        --------
        To perform an overlay analysis on a shapefile located at "path/to/input.shp" and save the result to "path/to/output.shp",
        use the following:

        overlay_analysis(qgis_vector_layer)
        """
        log_message("Overlay analysis started")
        # Step 1: Load the input layer from the provided shapefile path
        # layer = QgsVectorLayer(input_filepath, "circles_layer", "ogr")

        if not input_layer.isValid():
            log_message("Layer failed to load!")
            return

        # Step 2: Perform the dissolve operation to separate disjoint polygons
        dissolve_output_path = os.path.join(self.workflow_directory, f"{self.layer_id}_dissolve.shp")
        dissolve = processing.run(  # type: ignore[index]
            "native:dissolve",
            {
                "INPUT": input_layer,
                "FIELD": ["value"],
                "SEPARATE_DISJOINT": True,
                "OUTPUT": dissolve_output_path,
            },
        )["OUTPUT"]
        log_message(
            f"Dissolved areas have {len(dissolve)} features",
            tag="Geest",
            level=Qgis.Info,
        )
        # Step 3: Perform the union to get all overlapping areas
        union_output_path = os.path.join(self.workflow_directory, f"{self.layer_id}_union.shp")
        union = processing.run(  # type: ignore[index]
            "qgis:union",
            {
                "INPUT": dissolve_output_path,
                "OUTPUT": union_output_path,
            },
        )["OUTPUT"]
        log_message(f"Processing returned an object of type: {type(union)}")
        if type(union) is str:
            log_message(f"Union output is a file path: {union}")
            union = QgsVectorLayer(union, "union_layer", "ogr")
        log_message(f"Input layer fields: {[field.name() for field in union.fields()]}")
        # Also print the field types
        log_message(f"Input layer field types: {[field.typeName() for field in union.fields()]}")
        # Step 4: Iterate through the unioned features to assign the minimum value in overlapping areas
        unique_geometries = {}

        for feature in union.getFeatures():
            geom = feature.geometry().asWkt()
            attrs = feature.attributes()  # Use geometry as a key to identify unique areas
            value = attrs[union.fields().indexFromName("value")]

            log_message(
                f"Processing feature with min value: {value}",
            )

            # Check if this geometry is already in the dictionary
            if geom in unique_geometries:
                # If it exists, update only if the new min_value is lower
                if value < unique_geometries[geom].attributes()[0]:
                    unique_geometries[geom].setAttribute(0, value)
            else:
                # Add new unique geometry with the min_value attribute
                new_feature = QgsFeature()
                new_feature.setGeometry(feature.geometry())
                new_feature.setAttributes([value])
                unique_geometries[geom] = new_feature

        # Step 5: Create a memory layer to store the result
        result_layer = QgsVectorLayer("Polygon", "result_layer", "memory")
        result_layer.setCrs(self.target_crs)
        provider = result_layer.dataProvider()

        # Step 6: Add a field to store the minimum value (lower number = higher rank)
        provider.addAttributes([QgsField("min_value", QVariant.Int)])
        result_layer.updateFields()
        # Step 7: Add the filtered features to the result layer
        for unique_feature in unique_geometries.values():
            provider.addFeature(unique_feature)

        full_output_filepath = os.path.join(self.workflow_directory, f"{self.layer_id}_final.shp")
        # Step 8: Save the result layer to the specified output shapefile
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
            raise QgsProcessingException(f"Error saving dissolved layer to disk: {error[1]}")
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
