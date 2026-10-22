# -*- coding: utf-8 -*-
"""📦 S2S Urban/Rural Share Workflow module.

Scores the Education indicator from the S2S population layer, which carries the
GHSL urban/rural settlement-class population fields alongside the total
population. No vector input is required; the values are joined onto the study
area grid by H3 key and scored as the urban population share (or the inverted
rural population share).
"""

import os
from typing import Optional

from osgeo import ogr
from qgis.core import Qgis, QgsFeedback, QgsGeometry, QgsProcessingContext

from geest.core import JsonTreeItem
from geest.core.constants import DEFAULT_S2S_EDUCATION_URBANIZATION_FIELDS
from geest.core.grid_column_utils import (
    _execute_sql_with_retry,
    _open_gpkg_for_write,
    clear_grid_column,
    rasterize_grid_column,
    write_joined_values_to_grid,
)
from geest.utilities import log_message

from .workflow_base import WorkflowBase, WorkflowNotConfiguredError

_REQUIRED_POPULATION_FIELDS = list(DEFAULT_S2S_EDUCATION_URBANIZATION_FIELDS)


class S2SUrbanRuralShareWorkflow(WorkflowBase):
    """Concrete implementation of a 'use_s2s_urban_rural_share' workflow.

    The urban/rural split is population data fetched alongside the main S2S
    population field (``s2s_demographics.gpkg``). The chosen measure
    (``education_measure``, default ``urban``) decides which share is scored.
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
        :param cell_size_m: Cell size in meters.
        :param analysis_scale: Scale of the analysis, e.g., 'local', 'national'.
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :param context: QgsProcessingContext object for processing.
        :param working_directory: Folder containing study_area.gpkg and the S2S output files.
        """
        super().__init__(
            item, cell_size_m, analysis_scale, feedback, context, working_directory
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.workflow_name = "use_s2s_urban_rural_share"
        self.education_measure = str(self.attributes.get("education_measure", "") or "urban").strip().lower() or "urban"

        population_s2s_path = str(self.attributes.get("population_s2s_output_path", "") or "").strip()
        if not population_s2s_path:
            population_s2s_path = os.path.join(self.working_directory, "study_area", "s2s_demographics.gpkg")
        self._population_s2s_path = population_s2s_path

        if not os.path.exists(self._population_s2s_path):
            raise WorkflowNotConfiguredError(
                "Education (urban/rural share) requires the S2S population download. "
                "Download population from S2S in the analysis settings, then re-run."
            )
        self._validate_population_layer()

        self.features_layer = True
        self.raster_layer = None
        self.use_grid_first = True
        self._column_cleared = False

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_population_layer(self) -> None:
        """Fail fast when the S2S population layer lacks the urban/rural fields."""
        source_layer = os.path.splitext(os.path.basename(self._population_s2s_path))[0]
        ds = ogr.Open(self._population_s2s_path, 0)
        if not ds:
            raise WorkflowNotConfiguredError(f"Could not open S2S population layer: {self._population_s2s_path}")
        try:
            layer = ds.GetLayerByName(source_layer)
            if layer is None:
                raise WorkflowNotConfiguredError(f"Layer '{source_layer}' not found in {self._population_s2s_path}")
            definition = layer.GetLayerDefn()
            columns = [definition.GetFieldDefn(i).GetName() for i in range(definition.GetFieldCount())]
        finally:
            ds = None

        missing = [field for field in _REQUIRED_POPULATION_FIELDS if field not in columns]
        if missing:
            raise WorkflowNotConfiguredError(
                "The S2S population layer is missing the urban/rural population fields "
                f"{missing}. Re-download the population data from S2S (prefetch or "
                "analysis settings), then re-run."
            )

    # ------------------------------------------------------------------
    # Area processing
    # ------------------------------------------------------------------

    def _process_features_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_features,
        index: int,
        area_name: str = None,
    ) -> Optional[str]:
        """Join the urban/rural population fields and score the chosen share."""
        _ = current_area
        _ = clip_area
        _ = area_features

        if not area_name:
            raise ValueError("area_name is required for S2S urban/rural share processing.")

        source_gpkg = self._population_s2s_path
        source_layer = os.path.splitext(os.path.basename(source_gpkg))[0]

        temp_column_prefix = f"{self.layer_id}_s2s"
        temp_columns = {
            "ghs_11_pop": f"{temp_column_prefix}_11",
            "ghs_12_pop": f"{temp_column_prefix}_12",
            "ghs_13_pop": f"{temp_column_prefix}_13",
            "ghs_22_pop": f"{temp_column_prefix}_22",
            "ghs_23_pop": f"{temp_column_prefix}_23",
            "ghs_30_pop": f"{temp_column_prefix}_30",
            "ghs_total_pop": f"{temp_column_prefix}_total",
        }

        if not self._column_cleared:
            clear_grid_column(self.gpkg_path, self.layer_id)
            self._column_cleared = True

        self.progressChanged.emit(10.0)

        for source_field, temp_column in temp_columns.items():
            updated_count = write_joined_values_to_grid(
                gpkg_path=self.gpkg_path,
                column_name=temp_column,
                source_gpkg=source_gpkg,
                source_layer=source_layer,
                source_key_field="hex_id",
                target_key_field="h3_index",
                source_value_field=source_field,
                area_name=area_name,
            )
            if updated_count < 0:
                raise RuntimeError(f"Failed joining S2S field '{source_field}' to grid.")

        self.progressChanged.emit(60.0)

        ds = _open_gpkg_for_write(self.gpkg_path)
        if not ds:
            raise RuntimeError(f"Could not open GeoPackage for urban/rural share update: {self.gpkg_path}")

        try:

            def q(name):
                return f'"{name.replace(" ", "_").replace("-", "_")[:63]}"'

            c11 = q(temp_columns["ghs_11_pop"])
            c12 = q(temp_columns["ghs_12_pop"])
            c13 = q(temp_columns["ghs_13_pop"])
            c22 = q(temp_columns["ghs_22_pop"])
            c23 = q(temp_columns["ghs_23_pop"])
            c30 = q(temp_columns["ghs_30_pop"])
            ctotal = q(temp_columns["ghs_total_pop"])
            target = q(self.layer_id)

            escaped_area_name = area_name.replace("'", "''")
            where_area = f"area_name = '{escaped_area_name}'"

            urban_level = f"((COALESCE({c22},0)+COALESCE({c23},0)+COALESCE({c30},0)) / COALESCE({ctotal},0))"
            rural_level = f"((COALESCE({c11},0)+COALESCE({c12},0)+COALESCE({c13},0)) / COALESCE({ctotal},0))"

            if self.education_measure == "rural":
                score_expr = (
                    f"CASE "
                    f"WHEN COALESCE({ctotal}, 0) <= 0 THEN NULL "
                    f"WHEN {rural_level} >= 0.8 THEN 1 "
                    f"WHEN {rural_level} >= 0.6 THEN 2 "
                    f"WHEN {rural_level} >= 0.4 THEN 3 "
                    f"WHEN {rural_level} >= 0.2 THEN 4 "
                    f"ELSE 5 END"
                )
            else:
                score_expr = (
                    f"CASE "
                    f"WHEN COALESCE({ctotal}, 0) <= 0 THEN NULL "
                    f"WHEN {urban_level} < 0.2 THEN 1 "
                    f"WHEN {urban_level} < 0.4 THEN 2 "
                    f"WHEN {urban_level} < 0.6 THEN 3 "
                    f"WHEN {urban_level} < 0.8 THEN 4 "
                    f"ELSE 5 END"
                )

            sql = f"UPDATE study_area_grid SET {target} = {score_expr} WHERE {where_area}"  # nosec B608
            _execute_sql_with_retry(ds, sql, dialect="SQLite")
        finally:
            ds = None

        self.progressChanged.emit(85.0)

        output_path = os.path.join(
            self.workflow_directory,
            f"{self.layer_id}_{index}.tif",
        )

        rect = current_bbox.boundingBox()
        extent = (rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum())

        rasterize_grid_column(
            gpkg_path=self.gpkg_path,
            column_name=self.layer_id,
            output_raster_path=output_path,
            cell_size=self.cell_size_m,
            extent=extent,
            nodata=-9999.0,
            area_name=area_name,
        )

        self.progressChanged.emit(100.0)
        log_message(
            f"Processed Education ({self.education_measure} population share) for area {area_name} "
            f"into column {self.layer_id}",
            tag="GeoE3",
            level=Qgis.Info,
        )
        return output_path

    # Default implementations of the abstract methods - not used in this workflow
    def _process_raster_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_raster: str,
        index: int,
        area_name: str = None,
    ):
        pass

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
        area_name: str = None,
    ):
        pass
