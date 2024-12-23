import os
import traceback
from typing import Optional, List
import shutil

from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsRasterLayer,
    QgsVectorLayer,
    QgsProject,
    QgsRasterStats,
    QgsField,
    QgsVectorFileWriter,
    QgsFeature,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
    QgsTask,
)
import processing
from geest.utilities import log_message, resources_path
from geest.core.algorithms import AreaIterator


class WEEByPopulationScoreProcessingTask(QgsTask):
    """
    A QgsTask subclass for calculating WEE x Population SCORE and or WEE score per aggregation area.

    It iterates over subnational boundaries, calculates the majoriy WEE SCORE or WEE x Population Score
    into a geopackage with the same polygons as original subnational boundaries but new attributes for
    the majority scores and applies a QML style.

    The subnational boundaries will NOT be split bu the study area polygons, so
    containment is not guaranteed between study area polygons and the subnational boundary polygons.
    Because of this, we will use the VRT combined outputs for the WEE SCORE and WEE x Population Score
    inputs.

    It will write 4 columns to the output gpkg:

    fid - generic incrementing id for each subnational area
    name - subnational area name
    wee_score - majority wee score for that subnational area
    wee_pop_score - majority wee x population score for that subnational area

    The WEE Score can be one of 5 classes:

    | Range  | Description               | Color      |
    |--------|---------------------------|------------|
    | 0 - 1  | Very Low Enablement       | ![#FF0000](#) `#FF0000` |
    | 1 - 2  | Low Enablement            | ![#FFA500](#) `#FFA500` |
    | 2 - 3  | Moderately Enabling       | ![#FFFF00](#) `#FFFF00` |
    | 3 - 4  | Enabling                  | ![#90EE90](#) `#90EE90` |
    | 4 - 5  | Highly Enabling           | ![#0000FF](#) `#0000FF` |

    The WEE x Population Score can be one of 15 classes:

    | Color      | Description                                 |
    |------------|---------------------------------------------|
    | ![#FF0000](#) `#FF0000` | Very low enablement, low population       |
    | ![#FF0000](#) `#FF0000` | Very low enablement, medium population    |
    | ![#FF0000](#) `#FF0000` | Very low enablement, high population      |
    | ![#FFA500](#) `#FFA500` | Low enablement, low population            |
    | ![#FFA500](#) `#FFA500` | Low enablement, medium population         |
    | ![#FFA500](#) `#FFA500` | Low enablement, high population           |
    | ![#FFFF00](#) `#FFFF00` | Moderately enabling, low population       |
    | ![#FFFF00](#) `#FFFF00` | Moderately enabling, medium population    |
    | ![#FFFF00](#) `#FFFF00` | Moderately enabling, high population      |
    | ![#90EE90](#) `#90EE90` | Enabling, low population                  |
    | ![#90EE90](#) `#90EE90` | Enabling, medium population               |
    | ![#90EE90](#) `#90EE90` | Enabling, high population                 |
    | ![#0000FF](#) `#0000FF` | Highly enabling, low population           |
    | ![#0000FF](#) `#0000FF` | Highly enabling, medium population        |
    | ![#0000FF](#) `#0000FF` | Highly enabling, high population          |

    See the wee_score_processor.py module for more details on how this is computed.

    📒 The majority score for each subnational area is calculated by counting the
       number of pixels in each WEE Score and WEE x Population Score class as per the
       above tables. Then majority pixel count is then allocated to the aggregate area.
       In the unlikely event of there being two or more classes with an equal pixel count,
       the highest enablement and population class is assigned.


    Args:
        study_area_gpkg_path (str): Path to the GeoPackage containing study area masks.
        working_directory (str): Directory to save the output rasters.
        target_crs (Optional[QgsCoordinateReferenceSystem]): CRS for the output rasters.
        force_clear (bool): Flag to force clearing of all outputs before processing.
    """

    def __init__(
        self,
        study_area_gpkg_path: str,
        working_directory: str,
        target_crs: Optional[QgsCoordinateReferenceSystem] = None,
        force_clear: bool = False,
    ):
        super().__init__("Subnational Aggregation Processor", QgsTask.CanCancel)
        self.study_area_gpkg_path = study_area_gpkg_path

        self.output_dir = os.path.join(working_directory, "subnational_aggregates")
        os.makedirs(self.output_dir, exist_ok=True)

        # These folders should already exist from the aggregation analysis and population raster processing
        self.population_folder = os.path.join(working_directory, "population")
        self.wee_folder = os.path.join(working_directory, "wee_score")

        self.force_clear = force_clear
        if self.force_clear and os.path.exists(self.output_dir):
            for file in os.listdir(self.output_dir):
                os.remove(os.path.join(self.output_dir, file))

        self.target_crs = target_crs
        if not self.target_crs:
            layer: QgsVectorLayer = QgsVectorLayer(
                f"{self.study_area_gpkg_path}|layername=study_area_clip_polygons",
                "study_area_clip_polygons",
                "ogr",
            )
            self.target_crs = layer.crs()
            del layer
        self.output_rasters: List[str] = []

        log_message("Initialized WEE Subnational Area Aggregation Processing Task")

    def run(self) -> bool:
        """
        Executes the WEE Subnational Area Aggregation Processing Task calculation task.
        """
        try:
            self.calculate_score()
            self.generate_vrt()
            return True
        except Exception as e:
            log_message(f"Task failed: {e}")
            log_message(traceback.format_exc())
            return False

    def validate_rasters(self, subnational_vector: QgsVectorLayer) -> None:
        # Inputs
        raster_path = "path/to/your/raster.tif"  # Replace with your raster file path
        polygon_layer_path = "path/to/your/polygon_layer.shp"  # Replace with your polygon layer file path
        output_geopackage = (
            "path/to/your/study_area.gpkg"  # Replace with your GeoPackage file path
        )
        output_layer_name = (
            "subnational_boundaries"  # Name of the layer in the GeoPackage
        )
        output_field_name = (
            "MostValue"  # Name of the field to store the most prevalent value
        )

        # Load the raster layer
        raster_layer = QgsRasterLayer(raster_path, "Raster Layer")
        if not raster_layer.isValid():
            raise Exception("Raster layer failed to load.")

        # Load the polygon layer
        polygon_layer = QgsVectorLayer(polygon_layer_path, "Polygon Layer", "ogr")
        if not polygon_layer.isValid():
            raise Exception("Polygon layer failed to load.")

        # Validate and fix geometry errors in the polygon layer
        fixed_polygons = []
        for feature in polygon_layer.getFeatures():
            geom = feature.geometry()
            if not geom.isGeosValid():
                geom = geom.makeValid()
            fixed_polygons.append(QgsFeature(geom))

        # Create a new layer in the GeoPackage for clean boundaries
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.layerName = output_layer_name
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
        options.onlySelected = False

        crs = polygon_layer.crs()
        new_fields = [
            QgsField(output_field_name, QVariant.Int)
        ]  # Only the output field

        writer = QgsVectorFileWriter.create(
            output_geopackage, new_fields, QgsWkbTypes.Polygon, crs, options
        )

        if writer.hasError() != QgsVectorFileWriter.NoError:
            raise Exception(f"Error creating output layer: {writer.errorMessage()}")

        # Add fixed polygons to the new layer
        for feature in fixed_polygons:
            writer.addFeature(feature)

        # Close the writer to save the layer
        writer.close()

        # Load the newly created layer
        cleaned_layer = QgsVectorLayer(
            f"{output_geopackage}|layername={output_layer_name}",
            output_layer_name,
            "ogr",
        )
        if not cleaned_layer.isValid():
            raise Exception("Failed to load cleaned layer from GeoPackage.")

        # Process each polygon
        cleaned_provider = cleaned_layer.dataProvider()
        for feature in cleaned_layer.getFeatures():
            # Get polygon geometry
            geometry = feature.geometry()

            # Calculate zonal statistics for the raster within the polygon
            zone_stats = QgsRasterStats()
            zone_stats.computeStatistics(
                raster_layer.dataProvider(),
                QgsRasterStats.Count,
                extent=geometry.boundingBox(),
                bands=[1],
            )

            # Initialize a dictionary to store pixel value counts
            pixel_value_counts = {}

            # Iterate through each pixel value in the raster statistics
            for value, count in zone_stats.histogram(1).items():
                pixel_value_counts[value] = pixel_value_counts.get(value, 0) + count

            # Determine the most prevalent pixel value
            if pixel_value_counts:
                most_prevalent_value = max(
                    pixel_value_counts, key=pixel_value_counts.get
                )
            else:
                most_prevalent_value = None  # No data in this polygon's extent

            # Update the feature with the most prevalent pixel value
            cleaned_provider.changeAttributeValues(
                {
                    feature.id(): {
                        cleaned_layer.fields().indexFromName(
                            output_field_name
                        ): most_prevalent_value
                    }
                }
            )

        # Commit changes to the cleaned layer
        cleaned_layer.commitChanges()

        # Add layers to the project (optional, for viewing in QGIS)
        QgsProject.instance().addMapLayer(raster_layer)
        QgsProject.instance().addMapLayer(cleaned_layer)

        log_message(
            f"Processing complete. Most prevalent pixel values assigned to polygons. {output_path}"
        )

    def apply_qml_style(self, source_qml: str, qml_path: str) -> None:

        # Apply QML Style
        if os.path.exists(source_qml):
            shutil.copy(source_qml, qml_path)
            log_message(f"Copied QML style from {source_qml} to {qml_path}")
        else:
            log_message("QML style file not found. Skipping QML copy.")

    def finished(self, result: bool) -> None:
        """
        Called when the task completes.
        """
        if result:
            log_message("WEE SCORE calculation completed successfully.")
        else:
            log_message("WEE SCORE calculation failed.")
