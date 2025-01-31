import os
import traceback
from typing import Optional, List
import shutil

from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsVectorLayer,
    QgsTask,
    QgsCoordinateReferenceSystem,
)
import processing
from geest.utilities import log_message, resources_path
from geest.core import JsonTreeItem


class SubnationalAggregationProcessingTask(QgsTask):
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

    See the wee_by_population_score_processor.py module for more details on how this is computed.

    📒 The majority score for each subnational area is calculated by counting the
       number of pixels in each WEE Score and WEE x Population Score class as per the
       above tables. Then majority pixel count is then allocated to the aggregate area.
       In the unlikely event of there being two or more classes with an equal pixel count,
       the highest enablement and population class is assigned.

    See zonalstatisticsfb algorithm for more details on how the majority score is calculated.
    https://qgis.org/pyqgis/3.34/analysis/QgsZonalStatistics.html#qgis.analysis.QgsZonalStatistics.Majority


    Args:
        study_area_gpkg_path (str): Path to the study area geopackage. Used to determine the CRS.
        working_directory (str): Parent directory to save the output agregated data. Outputs will
            be saved in a subdirectory called "subnational_aggregates".
        target_crs (Optional[QgsCoordinateReferenceSystem]): CRS for the output rasters.
        force_clear (bool): Flag to force clearing of all outputs before processing.

    Note: item.attribute("aggregation_layer_source") must be set for the analysis item.
    """

    def __init__(
        self,
        item: JsonTreeItem,
        study_area_gpkg_path: str,
        working_directory: str,
        target_crs: Optional[QgsCoordinateReferenceSystem] = None,
        force_clear: bool = False,
    ):
        super().__init__("Subnational Aggregation Processor", QgsTask.CanCancel)
        self.item = item  # should be an item with role=analysis

        self.study_area_gpkg_path = study_area_gpkg_path

        self.aggregation_areas_path = item.attribute("aggregation_layer_source")

        self.aggregation_layer: QgsVectorLayer = QgsVectorLayer(
            self.aggregation_areas_path,
            "aggregation_areas",
            "ogr",
        )
        if not self.aggregation_layer.isValid():
            raise Exception(
                f"Invalid aggregation areas layer:\n{self.aggregation_areas_path}"
            )

        self.output_dir = os.path.join(working_directory, "subnational_aggregation")
        os.makedirs(self.output_dir, exist_ok=True)

        # This folder should already exist from the aggregation analysis and population raster processing
        self.wee_score_folder = os.path.join(working_directory, "wee_score")

        if not os.path.exists(self.wee_score_folder):
            raise Exception(
                f"WEE folder not found.\n{self.wee_score_folder}\nPlease run WEE raster processing first."
            )
        # This folder is optional  - user needs to have configured population layer in analysis properties dialog
        self.wee_by_population_folder = os.path.join(
            working_directory, "wee_by_population_score"
        )

        if not os.path.exists(self.wee_by_population_folder):
            log_message(
                f"WEE folder not found.\n{self.wee_by_population_folder}\nPlease run WEE raster processing first."
            )
            self.wee_by_population_folder = None
        # These two folders are optional - will only be set if user configured mask for
        # job opportunities in analysis properties dialog
        self.opportunities_by_wee_score_folder = os.path.join(
            working_directory, "opportunities_by_wee_score"
        )

        if not os.path.exists(self.opportunities_by_wee_score_folder):
            log_message(
                f"WEE folder not found.\n{self.wee_score_folder}\nPlease run WEE raster processing first."
            )
            self.opportunities_by_wee_score_folder = None

        self.opportunities_by_wee_by_population_folder = os.path.join(
            working_directory, "opportunities_by_wee_score_by_population"
        )

        if not os.path.exists(self.wee_by_population_folder):
            log_message(
                f"WEE folder not found.\n{self.opportunities_by_wee_score_by_population}\nPlease run WEE raster processing first."
            )
            self.opportunities_by_wee_by_population_folder = None

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
            log_message(
                f"Target CRS not set. Using CRS from study area clip polygon: {self.target_crs.authid()}"
            )
            log_message(f"{self.study_area_gpkg_path}|ayername=study_area_clip_polygon")
            del layer

        log_message("Initialized WEE Subnational Area Aggregation Processing Task")

    def run(self) -> bool:
        """
        Executes the WEE Subnational Area Aggregation Processing Task calculation task.
        """
        try:
            cleaned_aggregation_layer = self.fix_geometries()
            if self.wee_score_folder:
                log_message("Calculating WEE Score Aggregation")
                layer_name = "wee_score_subnational_aggregation"
                raster_layer_path = os.path.join(
                    self.wee_score_folder, "WEE_Score_combined.vrt"
                )
                output = self.aggregate(
                    cleaned_aggregation_layer,
                    raster_layer_path,
                    layer_name,
                )
                self.apply_qml_style(
                    source_qml=resources_path(
                        "resources", "qml", "wee_score_vector.qml"
                    ),
                    qml_path=os.path.join(self.output_dir, f"{layer_name}.qml"),
                )
                self.item.setAttribute(
                    f"{layer_name}", f"{output}|layername={layer_name}"
                )
            if self.wee_by_population_folder:
                log_message("Calculating WEE x Population Score Aggregation")
                layer_name = "wee_by_population_subnational_aggregation"
                raster_layer_path = os.path.join(
                    self.wee_by_population_folder, "wee_by_population_score.vrt"
                )
                output = self.aggregate(
                    cleaned_aggregation_layer,
                    raster_layer_path,
                    layer_name,
                )
                self.apply_qml_style(
                    source_qml=resources_path(
                        "resources", "qml", "wee_by_population_vector_score.qml"
                    ),
                    qml_path=os.path.join(self.output_dir, f"{layer_name}.qml"),
                )
                self.item.setAttribute(
                    f"{layer_name}", f"{output}|layername={layer_name}"
                )
            if self.opportunities_by_wee_score_folder:
                log_message("Calculating Opportunities by WEE Score Aggregation")
                layer_name = "opportunities_by_wee_score_subnational_aggregation"
                raster_layer_path = os.path.join(
                    self.opportunities_by_wee_score_folder,
                    "wee_by_opportunities_mask.vrt",
                )
                output = self.aggregate(
                    cleaned_aggregation_layer,
                    raster_layer_path,
                    layer_name,
                )
                self.apply_qml_style(
                    source_qml=resources_path(
                        "resources", "qml", "wee_score_vector.qml"
                    ),
                    qml_path=os.path.join(self.output_dir, f"{layer_name}.qml"),
                )
                self.item.setAttribute(
                    f"{layer_name}", f"{output}|layername={layer_name}"
                )
            if self.opportunities_by_wee_by_population_folder:
                log_message(
                    "Calculating Opportunities by WEE x Population Score Aggregation"
                )
                layer_name = (
                    "opportunities_by_wee_score_by_population_subnational_aggregation"
                )
                raster_layer_path = os.path.join(
                    self.opportunities_by_wee_by_population_folder,
                    "wee_by_opportunities_mask.vrt",
                )
                output = self.aggregate(
                    cleaned_aggregation_layer,
                    raster_layer_path,
                    layer_name,
                )
                self.apply_qml_style(
                    source_qml=resources_path(
                        "resources", "qml", "wee_by_population_vector_score.qml"
                    ),
                    qml_path=os.path.join(self.output_dir, f"{layer_name}.qml"),
                )
                self.item.setAttribute(
                    f"{layer_name}", f"{output}|layername={layer_name}"
                )
            log_message(self.item.attributesAsMarkdown())
            return True
        except Exception as e:
            log_message(f"Task failed: {e}")
            log_message(traceback.format_exc())
            return False

    def fix_geometries(self) -> QgsVectorLayer:
        """Fix geometries"""

        params = {
            "INPUT": self.aggregation_layer,
            "METHOD": 1,  # Structur method
            "OUTPUT": "TEMPORARY_OUTPUT",
        }
        output = processing.run("native:fixgeometries", params)["OUTPUT"]
        # Also drop all columns
        params = {"INPUT": output, "FIELDS": ["fid"], "OUTPUT": "TEMPORARY_OUTPUT"}
        output = processing.run("native:retainfields", params)["OUTPUT"]

        return output

    def aggregate(self, aggregation_layer, raster_layer_path: str, name: str) -> None:
        """Use aggregation vector to calculate the majority WEE SCORE and WEE x Population Score for each valid polygon."""
        output = os.path.join(self.output_dir, f"{name}.gpkg")
        params = {
            "INPUT": aggregation_layer,
            "INPUT_RASTER": raster_layer_path,
            "RASTER_BAND": 1,
            "COLUMN_PREFIX": "_",
            "STATISTICS": [9],  # Majority
            "OUTPUT": output,
        }
        processing.run("native:zonalstatisticsfb", params)
        return output

    def apply_qml_style(self, source_qml: str, qml_path: str) -> None:

        log_message(f"Copying QML style from {source_qml} to {qml_path}")
        # Apply QML Style
        if os.path.exists(source_qml):
            shutil.copy(source_qml, qml_path)
        else:
            log_message("QML style file not found. Skipping QML copy.")

    def finished(self, result: bool) -> None:
        """
        Called when the task completes.
        """
        if result:
            log_message("Subnational aggregate calculation completed successfully.")
        else:
            log_message("Subnational aggregate calculation failed.")
