import os
import traceback
from typing import Optional, List
import shutil

from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsVectorLayer,
    QgsRasterLayer,
    QgsCoordinateReferenceSystem,
    QgsTask,
)
import processing
from geest.utilities import log_message, resources_path


class OpportunitiesPolygonMaskProcessingTask(QgsTask):
    """
    A QgsTask subclass for masking WEE x Population SCORE or WEE score per polygon opportunities areas.

    It will generate a new raster with all pixels that do not coincide with one of the
    provided polygons set to no-data. The intent is to focus the analysis to specific areas
    where job creation initiatives are in place.

    Input can either be a WEE score layer, or a WEE x Population Score layer.

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

    The output will be a new raster with the same extent and resolution as the input raster,
    but with all pixels outside the provided polygons set to no-data.

    Args:
        study_area_gpkg_path (str): Path to the study area geopackage. Used to determine the CRS.
        mask_areas_path (str): Path to vector layer containing the mask polygon areas.
        working_directory (str): Parent directory to save the output agregated data. Outputs will
            be saved in a subdirectory called "subnational_aggregates".
        target_crs (Optional[QgsCoordinateReferenceSystem]): CRS for the output rasters.
        force_clear (bool): Flag to force clearing of all outputs before processing.
    """

    def __init__(
        self,
        study_area_gpkg_path: str,
        mask_areas_path: str,
        working_directory: str,
        force_clear: bool = False,
    ):
        super().__init__("Opportunities Polygon Mask Processor", QgsTask.CanCancel)
        self.study_area_gpkg_path = study_area_gpkg_path

        self.mask_areas_path = mask_areas_path

        self.mask_areas_layer: QgsVectorLayer = QgsVectorLayer(
            self.mask_areas_path,
            "mask_areas",
            "ogr",
        )
        if not self.mask_areas_layer.isValid():
            raise Exception(
                f"Invalid polygon mask areas layer:\n{self.mask_areas_path}"
            )

        self.output_dir = os.path.join(working_directory, "opportunity_masks")
        os.makedirs(self.output_dir, exist_ok=True)

        # These folders should already exist from the aggregation analysis and population raster processing
        self.wee_folder = os.path.join(working_directory, "wee_score")

        if not os.path.exists(self.wee_folder):
            raise Exception(
                f"WEE folder not found.\n{self.wee_folder}\nPlease run WEE raster processing first."
            )

        self.force_clear = force_clear
        if self.force_clear and os.path.exists(self.output_dir):
            for file in os.listdir(self.output_dir):
                os.remove(os.path.join(self.output_dir, file))

        layer: QgsVectorLayer = QgsVectorLayer(
            f"{self.study_area_gpkg_path}|layername=study_area_clip_polygons",
            "study_area_clip_polygons",
            "ogr",
        )
        self.target_crs = layer.crs()
        log_message(
            f"Using CRS from study area clip polygon: {self.target_crs.authid()}"
        )
        log_message(f"{self.study_area_gpkg_path}|ayername=study_area_clip_polygon")
        del layer

        log_message("Initialized WEE Opportunities Polygon Mask Processing Task")

    def run(self) -> bool:
        """
        Executes the WEE Opportunities Polygon Mask Processing Task calculation task.
        """
        try:
            self.mask()
            self.apply_qml_style(
                source_qml=resources_path(
                    "resources", "qml", "wee_by_population_score.qml"
                ),
                qml_path=os.path.join(self.output_dir, "wee_by_population_score.qml"),
            )
            return True
        except Exception as e:
            log_message(f"Task failed: {e}")
            log_message(traceback.format_exc())
            return False

    def mask(self) -> None:
        """Fix geometries then use mask vector to calculate masked WEE SCORE or WEE x Population Score layer."""

        # Load your raster layer
        wee_path = os.path.join(self.wee_folder, "wee_by_population_score.vrt")
        wee_layer = QgsRasterLayer(wee_path, "WEE by Population Score")

        if not wee_layer.isValid():
            log_message(f"The raster layer is invalid!\n{wee_path}\nTrying WEE score")
            wee_path = os.path.join(
                os.pardir(self.wee_folder), "WEE_Score_combined.vrt"
            )
            wee_layer = QgsRasterLayer(wee_path, "WEE Score")
            if not wee_layer.isValid():
                raise Exception(
                    f"Neither WEE x Population nor WEE Score layers are valid.\n{wee_path}\n"
                )
        else:
            # Get the extent of the raster layer
            extent = wee_layer.extent()

            # Get the data provider for the raster layer
            provider = wee_layer.dataProvider()

            # Get the raster's width, height, and size of cells
            width = provider.xSize()
            height = provider.ySize()

            cell_width = extent.width() / width
            cell_height = extent.height() / height
        log_message(f"Raster layer loaded: {wee_path}")
        log_message(f"Raster extent: {extent}")
        log_message(f"Raster cell size: {cell_width} x {cell_height}")
        fixed_geometries_path = os.path.join(
            self.output_dir, "fixed_opportunites_polygons.gpkg"
        )
        params = {
            "INPUT": self.mask_areas_layer,
            "METHOD": 1,  # Structure method
            "OUTPUT": fixed_geometries_path,
        }
        output = processing.run("native:fixgeometries", params)["OUTPUT"]
        log_message("Fixed mask layer geometries")

        reprojected_fixed_geometries_path = os.path.join(
            self.output_dir, "reprojected_fixed_opportunites_polygons.gpkg"
        )

        params = {
            "INPUT": fixed_geometries_path,
            "TARGET_CRS": self.target_crs,
            "CONVERT_CURVED_GEOMETRIES": False,
            "OPERATION": self.target_crs,
            "OUTPUT": reprojected_fixed_geometries_path,
        }
        output = processing.run("native:reprojectlayer", params)["OUTPUT"]
        log_message(
            f"Reprojected mask layer to {self.target_crs.authid()} and saved as \n{reprojected_fixed_geometries_path}"
        )

        rasterized_polygons_path = os.path.join(
            self.output_dir, "rasterized_opportunites_polygons.tif"
        )
        params = {
            "INPUT": reprojected_fixed_geometries_path,
            "FIELD": None,
            "BURN": 1,
            "USE_Z": False,
            "UNITS": 1,
            "WIDTH": cell_width,
            "HEIGHT": cell_height,
            "EXTENT": extent,
            "NODATA": 0,
            "OPTIONS": "",
            "DATA_TYPE": 0,  # byte
            "INIT": None,
            "INVERT": False,
            "EXTRA": "-co NBITS=1 -at",  # -at is for all touched cells
            "OUTPUT": rasterized_polygons_path,
        }

        output = processing.run("gdal:rasterize", params)["OUTPUT"]
        log_message(f"Masked WEE Score raster saved to {output}")
        opportunities_mask = os.path.join(self.output_dir, "oppotunities_mask.tif")
        params = {
            "INPUT_A": wee_layer,
            "BAND_A": 1,
            "INPUT_B": rasterized_polygons_path,
            "BAND_B": 1,
            "FORMULA": "A*B",
            "NO_DATA": None,
            "EXTENT_OPT": 3,
            "PROJWIN": None,
            "RTYPE": 0,
            "OPTIONS": "",
            "EXTRA": "",
            "OUTPUT": opportunities_mask,
        }

        processing.run("gdal:rastercalculator", params)
        self.output_rasters.append(opportunities_mask)

        log_message(f"WEE SCORE raster saved to {opportunities_mask}")

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
            log_message(
                "Opportunities Polygon Mask calculation completed successfully."
            )
        else:
            log_message("Opportunities Polygon Mask calculation failed.")
