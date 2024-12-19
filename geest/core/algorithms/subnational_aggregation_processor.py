from qgis.core import (
    QgsRasterLayer,
    QgsVectorLayer,
    QgsProject,
    QgsRasterStats,
    QgsVectorDataProvider,
    QgsField,
    QgsVectorFileWriter,
    QgsGeometry,
    QgsFeature,
)
from qgis.PyQt.QtCore import QVariant
import os
import traceback
from typing import Optional, List
import shutil

from qgis.core import (
    QgsTask,
    QgsProcessingContext,
    QgsFeedback,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
)
import processing
from geest.utilities import log_message, resources_path
from geest.core.algorithms import AreaIterator


class WEEByPopulationScoreProcessingTask(QgsTask):
    """
    A QgsTask subclass for calculating WEE x Population SCORE using raster algebra.

    It iterates over study areas, calculates the WEE SCORE using aligned input rasters
    (WEE and POP), combines the resulting rasters into a VRT, and applies a QML style.

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
        super().__init__("WEE Score Processor", QgsTask.CanCancel)
        self.study_area_gpkg_path = study_area_gpkg_path

        self.output_dir = os.path.join(working_directory, "wee_score")
        os.makedirs(self.output_dir, exist_ok=True)

        # These folders should already exist from the aggregation analysis and population raster processing
        self.population_folder = os.path.join(working_directory, "population")
        self.wee_folder = working_directory

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

        log_message("Initialized WEE SCORE Processing Task")

    def run(self) -> bool:
        """
        Executes the WEE SCORE calculation task.
        """
        try:
            self.calculate_score()
            self.generate_vrt()
            return True
        except Exception as e:
            log_message(f"Task failed: {e}")
            log_message(traceback.format_exc())
            return False

    def validate_rasters(
        self,
        geest_raster: QgsRasterLayer,
        pop_raster: QgsRasterLayer,
        dimension_check=False,
    ) -> None:
        """
        Checks if GEEST and POP rasters have the same origin, dimensions, and pixel sizes.

        Raises an exception if the check fails.

        Args:
            geest_raster_path (QgsRasterLayer): Path to the GEEST raster.
            pop_raster_path (QgsRasterLayer): Path to the POP raster.
            dimension_check (bool): Flag to check if the rasters have the same dimensions.
        returns:
            None
        """
        log_message("Validating input rasters")
        log_message(f"GEEST Raster: {geest_raster.source()}")
        log_message(f"POP Raster  : {pop_raster.source()}")

        if not geest_raster.isValid() or not pop_raster.isValid():
            raise ValueError("One or both input rasters are invalid.")

        if not dimension_check:
            return

        geest_provider = geest_raster.dataProvider()
        pop_provider = pop_raster.dataProvider()

        geest_extent = geest_provider.extent()
        pop_extent = pop_provider.extent()
        if geest_extent != pop_extent:
            raise ValueError("Input rasters do not share the same extent.")

        geest_size = geest_provider.xSize(), geest_provider.ySize()
        pop_size = pop_provider.xSize(), pop_provider.ySize()
        if geest_size != pop_size:
            raise ValueError("Input rasters do not share the same dimensions.")

        log_message("Validation successful: rasters are aligned.")

    def calculate_score(self) -> None:
        """
        Calculates WEE by POP SCORE using raster algebra and saves the result for each area.
        """
        area_iterator = AreaIterator(self.study_area_gpkg_path)
        for index, (_, _, _, _) in enumerate(area_iterator):
            if self.isCanceled():
                return

            wee_path = os.path.join(self.wee_folder, f"wee_masked_{index}.tif")
            population_path = os.path.join(
                self.population_folder, f"reclassified_{index}.tif"
            )
            wee_layer = QgsRasterLayer(wee_path, "WEE")
            pop_layer = QgsRasterLayer(population_path, "POP")
            self.validate_rasters(wee_layer, pop_layer, dimension_check=False)

            output_path = os.path.join(
                self.output_dir, f"wee_by_population_score_{index}.tif"
            )

            log_message(f"WEE SCORE raster saved to {output_path}")

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


# Inputs
raster_path = "path/to/your/raster.tif"  # Replace with your raster file path
polygon_layer_path = (
    "path/to/your/polygon_layer.shp"  # Replace with your polygon layer file path
)
output_geopackage = (
    "path/to/your/study_area.gpkg"  # Replace with your GeoPackage file path
)
output_layer_name = "subnational_boundaries"  # Name of the layer in the GeoPackage
output_field_name = "MostValue"  # Name of the field to store the most prevalent value

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
new_fields = [QgsField(output_field_name, QVariant.Int)]  # Only the output field

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
    f"{output_geopackage}|layername={output_layer_name}", output_layer_name, "ogr"
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
        most_prevalent_value = max(pixel_value_counts, key=pixel_value_counts.get)
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

print("Processing complete. Most prevalent pixel values assigned to polygons.")
