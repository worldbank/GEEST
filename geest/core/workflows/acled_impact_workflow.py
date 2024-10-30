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
    QgsMessageLog,
    QgsPointXY,
    QgsProcessingContext,
    QgsProcessingException,
    QgsVectorFileWriter,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QVariant

import processing


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
    ):
        """
        Initialize the workflow with attributes and feedback.
        :param attributes: Item containing workflow parameters.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        """
        super().__init__(
            item, cell_size_m, feedback, context
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.workflow_name = "use_csv_to_point_layer"
        self.csv_file = self.attributes.get("use_csv_to_point_layer_csv_file", "")
        self.features_layer = self._load_csv_as_point_layer()
        self.workflow_is_legacy = False

    def _process_features_for_area(
        self,
        current_area: QgsGeometry,
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

        # Step 1: Buffer the selected features by 5 km
        buffered_layer = self._buffer_features(area_features)

        # Step 2: Assign values based on event_type
        scored_layer = self._assign_scores(buffered_layer)

        # Step 3: Dissolve and remove overlapping areas, keeping areas withe the lowest value
        dissolved_layer = self._overlay_analysis(scored_layer)

        # Step 4: Rasterize the dissolved layer
        raster_output = self._rasterize(
            dissolved_layer,
            current_bbox,
            index,
            value_field="min_value",
            default_value=5,
        )

        return raster_output

    def _load_csv_as_point_layer(self) -> QgsVectorLayer:
        """
        Load the CSV file, extract relevant columns (latitude, longitude, event_type),
        create a point layer from the retained columns, reproject the points to match the
        CRS of the layers from the GeoPackage, and save the result as a shapefile.

        Returns:
            QgsVectorLayer: The reprojected point layer created from the CSV.
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
            QgsMessageLog.logMessage(
                f"Loaded {len(features)} points from CSV", tag="Geest", level=Qgis.Info
            )
        # Save the layer to disk as a shapefile
        # Ensure the workflow directory exists
        if not os.path.exists(self.workflow_directory):
            os.makedirs(self.workflow_directory)
        shapefile_path = os.path.join(
            self.workflow_directory, f"{self.layer_id}_acled_points.shp"
        )
        QgsMessageLog.logMessage(
            f"Writing points to {shapefile_path}", tag="Geest", level=Qgis.Info
        )
        error = QgsVectorFileWriter.writeAsVectorFormat(
            point_layer, shapefile_path, "utf-8", self.target_crs, "ESRI Shapefile"
        )

        if error[0] != 0:
            raise QgsProcessingException(
                f"Error saving point layer to disk: {error[1]}"
            )

        QgsMessageLog.logMessage(
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

        Args:
            layer (QgsVectorLayer): The input feature layer.

        Returns:
            QgsVectorLayer: The buffered features layer.
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

        Args:
            layer_path (str): The buffered features layer.

        Returns:
            QgsVectorLayer: A new layer with a "value" field containing the assigned scores.
        """

        QgsMessageLog.logMessage(
            f"Assigning scores to {layer.name()}", tag="Geest", level=Qgis.Info
        )
        # Define scoring categories based on event_type
        event_scores = {
            "Battles": 0,
            "Explosions/Remote violence": 1,
            "Violence against civilians": 2,
            "Protests": 4,
            "Riots": 4,
        }

        # Create a new field in the layer for the scores
        layer.startEditing()
        layer.dataProvider().addAttributes([QgsField("value", QVariant.Int)])
        layer.updateFields()

        # Assign scores based on event_type
        for feature in layer.getFeatures():
            event_type = feature["event_type"]
            score = event_scores.get(event_type, 5)
            feature.setAttribute("value", score)
            layer.updateFeature(feature)

        layer.commitChanges()

        return layer

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
        QgsMessageLog.logMessage("Overlay analysis started", "Geest", Qgis.Info)
        # Step 1: Load the input layer from the provided shapefile path
        # layer = QgsVectorLayer(input_filepath, "circles_layer", "ogr")

        if not input_layer.isValid():
            QgsMessageLog.logMessage("Layer failed to load!", "Geest", Qgis.Info)
            return

        # Step 2: Create a memory layer to store the result
        result_layer = QgsVectorLayer(f"Polygon", "result_layer", "memory")
        result_layer.setCrs(self.target_crs)
        provider = result_layer.dataProvider()

        # Step 3: Add a field to store the minimum value (lower number = higher rank)
        provider.addAttributes([QgsField("min_value", QVariant.Int)])
        result_layer.updateFields()
        # Step 4: Perform the dissolve operation to separate disjoint polygons
        dissolve = processing.run(
            "native:dissolve",
            {
                "INPUT": input_layer,
                "FIELD": ["value"],
                "SEPARATE_DISJOINT": True,
                "OUTPUT": "TEMPORARY_OUTPUT",
            },
        )["OUTPUT"]
        QgsMessageLog.logMessage(
            f"Dissolved areas have {len(dissolve)} features",
            tag="Geest",
            level=Qgis.Info,
        )
        # Step 5: Perform the union to get all overlapping areas
        union = processing.run(
            "qgis:union",
            {
                "INPUT": dissolve,
                #'OVERLAY': '', #input_layer, # Do we need this?
                "OUTPUT": "memory:",
            },
        )["OUTPUT"]
        QgsMessageLog.logMessage(
            f"Unioned areas have {len(dissolve)} features", tag="Geest", level=Qgis.Info
        )
        # Step 6: Iterate through the unioned features to assign the minimum value in overlapping areas
        for feature in union.getFeatures():
            geom = feature.geometry()
            attrs = feature.attributes()
            value_1 = attrs[input_layer.fields().indexFromName("value")]
            value_2 = attrs[
                input_layer.fields().indexFromName("value_2")
            ]  # This comes from the unioned layer

            # Assign the minimum value to the overlapping area (lower number = higher rank)
            min_value = min(value_1, value_2)

            # Create a new feature with this geometry and the min value
            new_feature = QgsFeature()
            new_feature.setGeometry(geom)
            new_feature.setAttributes([min_value])

            # Add the new feature to the result layer
            provider.addFeature(new_feature)
        full_output_filepath = os.path.join(
            self.workflow_directory, f"{self.layer_id}_final.shp"
        )
        # Step 7: Save the result layer to the specified output shapefile
        error = QgsVectorFileWriter.writeAsVectorFormat(
            result_layer,
            full_output_filepath,
            "UTF-8",
            result_layer.crs(),
            "ESRI Shapefile",
        )

        if error[0] == 0:
            QgsMessageLog.logMessage(
                f"Overlay analysis complete, output saved to {full_output_filepath}",
                "Geest",
                Qgis.Info,
            )
        else:
            raise QgsProcessingException(
                f"Error saving dissolved layer to disk: {error[1]}"
            )
        return QgsVectorLayer(full_output_filepath, f"{self.layer_id}_final", "ogr")

    # deleteme after migrating all workflows
    def do_execute(self):
        return super().do_execute()

    # Default implementation of the abstract method - not used in this workflow
    def _process_raster_for_area(
        self,
        current_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_raster: str,
        index: int,
    ):
        """
        Executes the actual workflow logic for a single area using a raster.

        :current_area: Current polygon from our study area.
        :current_bbox: Bounding box of the above area.
        :area_raster: A raster layer of features to analyse that includes only bbox pixels in the study area.
        :index: Index of the current area.

        :return: Path to the reclassified raster.
        """
        pass

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
    ):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        pass
