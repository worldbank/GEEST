# -*- coding: utf-8 -*-
"""📦 Raster Reclassification Workflow module.
This module contains functionality for raster reclassification workflow.
"""
import os
from urllib.parse import unquote

from qgis import processing  # QGIS processing toolbox
from qgis.core import (
    Qgis,
    QgsFeedback,
    QgsGeometry,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsRasterLayer,
    QgsVectorLayer,
)

from geest.core import JsonTreeItem
from geest.core.constants import DEFAULT_S2S_ENV_HAZARD_FIELDS, DEFAULT_S2S_NTL_FIELD, GDAL_OUTPUT_DATA_TYPE
from geest.core.grid_column_utils import reclassify_grid_column_with_table, write_joined_values_to_grid
from geest.utilities import log_message

from .workflow_base import WorkflowBase


class RasterReclassificationWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'use_environmental_hazards' workflow.
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
        :param cell_size_m: Cell size in meters
        :param analysis_scale: Scale of the analysis, e.g., 'local', 'national'.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :param context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        :param working_directory: Folder containing study_area.gpkg and where the outputs will be placed. If not set will be taken from QSettings.
        """
        super().__init__(
            item, cell_size_m, analysis_scale, feedback, context, working_directory
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.workflow_name = "use_environmental_hazards"
        self.s2s_output_path = self.attributes.get("s2s_output_path", "")
        self.s2s_hazard_field = self._resolve_s2s_hazard_field()
        self._use_s2s_grid_path = bool(
            self.analysis_scale == "regional" and self.s2s_output_path and self.s2s_hazard_field
        )
        self._configure_reclassification_rules()

        if self._use_s2s_grid_path:
            self.features_layer = True
            self.use_grid_first = True
            self.raster_layer = None
            log_message(
                f"Using regional S2S grid path for environmental hazards ({self.layer_id}) field '{self.s2s_hazard_field}'.",
                tag="GeoE3",
                level=Qgis.Info,
            )
            return

        layer_name = self.attributes.get("environmental_hazards_raster", None)
        if layer_name:
            layer_name = unquote(layer_name)
        if not layer_name:
            log_message(
                "Invalid layer found in environmental_hazards_raster, trying environmental_hazards_layer_source.",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            layer_name = self.attributes.get("environmental_hazards_layer_source", None)
            if not layer_name:
                log_message(
                    "No layer found in environmental_hazards_layer_source.",
                    tag="GeoE3",
                    level=Qgis.Warning,
                )
                return
        self.raster_layer = QgsRasterLayer(layer_name, "Environmental Hazards Raster", "gdal")

    def _resolve_s2s_hazard_field(self) -> str:
        """Resolve and validate S2S hazard field for this indicator."""
        hazard_field = str(self.attributes.get("s2s_hazard_field", "") or "").strip()
        fallback_field = DEFAULT_S2S_ENV_HAZARD_FIELDS.get(self.layer_id, "")

        if not hazard_field:
            return fallback_field

        if hazard_field == DEFAULT_S2S_NTL_FIELD:
            if fallback_field:
                log_message(
                    f"S2S hazard field for {self.layer_id} was set to NTL field; using hazard default '{fallback_field}' instead.",
                    tag="GeoE3",
                    level=Qgis.Warning,
                )
                return fallback_field
            raise ValueError(
                f"Invalid S2S hazard field for {self.layer_id}: '{hazard_field}'. Configure a hazard-specific field."
            )

        return hazard_field

    def _configure_reclassification_rules(self) -> None:
        """Configure hazard-specific reclassification table and boundary mode."""
        if self.layer_id == "landslide":
            self.range_boundaries = 2  # min and max values are included
        else:
            self.range_boundaries = 0  # default value for range boundaries

        if self.layer_id == "fire":
            self.reclassification_rules = [
                "-inf",
                0,
                5.00,
                0,
                1,
                4.00,
                1,
                2,
                3.00,
                2,
                5,
                2.00,
                5,
                8,
                1.00,
                8,
                "inf",
                0,
            ]
        elif self.layer_id == "flood":
            self.reclassification_rules = [
                -1,
                0,
                5.00,
                0,
                180,
                4.00,
                180,
                360,
                3.00,
                360,
                540,
                2.00,
                540,
                720,
                1.00,
                720,
                900,
                0,
            ]
        elif self.layer_id == "landslide":
            self.reclassification_rules = [
                0,
                0,
                5.00,
                1,
                1,
                4.00,
                2,
                2,
                3.00,
                3,
                3,
                2.00,
                4,
                4,
                1.00,
                5,
                5,
                0,
            ]
        elif self.layer_id == "cyclone":
            self.reclassification_rules = [
                0,
                0,
                5.00,
                0,
                25,
                4.00,
                25,
                50,
                3.00,
                50,
                75,
                2.00,
                75,
                100,
                1.00,
                100,
                "inf",
                0,
            ]
        elif self.layer_id == "drought":
            self.reclassification_rules = [
                0,
                0,
                5.00,
                0,
                1,
                4.00,
                1,
                2,
                3.00,
                2,
                3,
                2.00,
                3,
                4,
                1.00,
                4,
                5,
                0,
            ]
        else:
            raise ValueError(f"Unsupported environmental hazard layer id: {self.layer_id}")

        log_message(
            f"Reclassification Rules for {self.layer_id}: {self.reclassification_rules}",
            tag="GeoE3",
            level=Qgis.Info,
        )

    def _process_raster_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_raster: str,
        index: int,
        area_name: str = None,
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
        del current_area  # Unused in this analysis noqa F841
        del clip_area  # Unused in this analysis noqa F841
        # Apply the reclassification rules
        reclassified_raster = self._apply_reclassification(
            area_raster,
            index,
            bbox=current_bbox,
        )
        return reclassified_raster

    def _apply_reclassification(
        self,
        input_raster: QgsRasterLayer,
        index: int,
        bbox: QgsGeometry,
    ):
        """
        Apply the reclassification using the raster calculator and save the output.
        """
        bbox = bbox.boundingBox()
        reclassified_raster_path = os.path.join(self.workflow_directory, f"{self.layer_id}_reclassified_{index}.tif")
        # Set up the reclassification using reclassifybytable
        params = {
            "INPUT_RASTER": input_raster,
            "RASTER_BAND": 1,  # Band number to apply the reclassification
            "TABLE": self.reclassification_rules,  # Reclassification table
            "RANGE_BOUNDARIES": self.range_boundaries,
            "OUTPUT": "TEMPORARY_OUTPUT",
            "PROGRESS": self.feedback,
        }
        # Perform the reclassification using the raster calculator
        reclass = processing.run("native:reclassifybytable", params, feedback=QgsProcessingFeedback())["OUTPUT"]
        clip_params = {
            "INPUT": reclass,
            "MASK": self.clip_areas_layer,
            "CROP_TO_CUTLINE": True,
            "KEEP_RESOLUTION": True,
            "DATA_TYPE": GDAL_OUTPUT_DATA_TYPE,
            "TARGET_EXTENT": f"{bbox.xMinimum()},{bbox.xMaximum()},{bbox.yMinimum()},{bbox.yMaximum()} [{self.target_crs.authid()}]",  # noqa E231
            "OUTPUT": reclassified_raster_path,
            "PROGRESS": self.feedback,
        }
        processing.run("gdal:cliprasterbymasklayer", clip_params, feedback=QgsProcessingFeedback())
        log_message(
            f"Reclassification for area {index} complete. Saved to {reclassified_raster_path}",
            tag="GeoE3",
            level=Qgis.Info,
        )
        return reclassified_raster_path

    # Not used in this workflow since we work with rasters
    def _process_features_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
        area_name: str = None,
    ) -> str:
        """
        Executes the actual workflow logic for a single area
        Must be implemented by subclasses.
        :current_area: Current polygon from our study area.
        :clip_area: Extended grid matched polygon for the study area.
        :current_bbox: Bounding box of the above area.
        :area_features: A vector layer of features to analyse that includes only features in the study area.
        :index: Iteration / number of area being processed.
        :return: A raster layer file path if processing completes successfully, False if canceled or failed.
        """
        _ = current_area
        _ = clip_area
        _ = area_features

        if not self._use_s2s_grid_path:
            return None

        if not area_name:
            raise ValueError("area_name is required for regional S2S environmental hazards processing.")

        source_layer = os.path.splitext(os.path.basename(self.s2s_output_path))[0]
        updated_count = write_joined_values_to_grid(
            gpkg_path=self.gpkg_path,
            column_name=self.layer_id,
            source_gpkg=self.s2s_output_path,
            source_layer=source_layer,
            source_key_field="hex_id",
            target_key_field="h3_index",
            source_value_field=self.s2s_hazard_field,
            area_name=area_name,
        )

        if updated_count < 0:
            raise RuntimeError("Failed to write S2S environmental hazards values to study_area_grid.")

        mapped_count = reclassify_grid_column_with_table(
            gpkg_path=self.gpkg_path,
            column_name=self.layer_id,
            reclassification_table=self.reclassification_rules,
            area_name=area_name,
            range_boundaries=self.range_boundaries,
        )
        if mapped_count < 0:
            raise RuntimeError("Failed to map S2S environmental hazards values to Likert scale.")

        log_message(
            f"Wrote {updated_count} regional S2S environmental hazards values and mapped {mapped_count} cells "
            f"to Likert scale in grid column {self.layer_id}",
            tag="GeoE3",
            level=Qgis.Info,
        )

        return self._rasterize_grid_column(
            column_name=self.layer_id,
            bbox=current_bbox,
            area_name=area_name,
            index=index,
        )

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
        area_name: str = None,
    ):
        """
        Executes the actual workflow logic for a single area using an aggregate.
        :current_area: Current polygon from our study area.
        :clip_area: Extended grid matched polygon for the study area.
        :current_bbox: Bounding box of the above area.
        :index: Index of the current area.
        :return: Path to the reclassified raster.
        """
        pass
