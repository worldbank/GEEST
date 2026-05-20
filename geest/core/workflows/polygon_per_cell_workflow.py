# -*- coding: utf-8 -*-
"""📦 Polygon Per Cell Workflow module.

This module contains functionality for polygon per cell workflow.

Supports grid-first mode where feature counts are written directly to
the study_area_grid column, then rasterized.
"""

import os
from typing import Optional
from urllib.parse import unquote

from qgis.core import (
    Qgis,
    QgsFeedback,
    QgsGeometry,
    QgsProcessingContext,
    QgsVectorLayer,
)

from geest.core import JsonTreeItem
from geest.core.constants import DEFAULT_S2S_EDUCATION_URBANIZATION_FIELDS
from geest.core.grid_column_utils import (
    clear_grid_column,
    count_features_per_grid_cell,
    rasterize_grid_column,
    write_joined_values_to_grid,
)
from geest.utilities import log_message

from .workflow_base import WorkflowBase


class PolygonPerCellWorkflow(WorkflowBase):
    """
    Concrete implementation of a 'use_polygon_per_cell' workflow.
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
        :param analysis_scale: Scale of the analysis, e.g., 'local', 'national
        :param feedback: QgsFeedback object for progress reporting and cancellation.
        :param context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
        :param working_directory: Folder containing study_area.gpkg and where the outputs will be placed. If not set will be taken from QSettings.
        """
        super().__init__(
            item, cell_size_m, analysis_scale, feedback, context, working_directory
        )  # ⭐️ Item is a reference - whatever you change in this item will directly update the tree
        self.workflow_name = "use_polygon_per_cell"
        self.s2s_output_path = self.attributes.get("s2s_output_path", "")
        self.s2s_fields = self._resolve_s2s_fields()
        self._use_s2s_education_proxy = bool(
            self.analysis_scale == "regional"
            and self.layer_id == "education"
            and self.s2s_output_path
            and self.s2s_fields
        )

        if self._use_s2s_education_proxy:
            self.features_layer = True
            self.workflow_name = "polygon_per_cell"
            self.use_grid_first = True
            self._column_cleared = False
            return

        layer_path = self.attributes.get("polygon_per_cell_shapefile", None)
        if layer_path:
            layer_path = unquote(layer_path)
        if not layer_path:
            log_message(
                "Invalid raster found in polygon_per_cell_shapefile, trying polygon_per_cell_layer_source.",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            layer_path = self.attributes.get("polygon_per_cell_layer_source", None)
            if not layer_path:
                log_message(
                    "No points layer found in polygon_per_cell_layer_source.",
                    tag="GeoE3",
                    level=Qgis.Warning,
                )
                return False
        self.features_layer = QgsVectorLayer(layer_path, "polygon_per_cell_layer", "ogr")
        self.workflow_name = "polygon_per_cell"
        # Grid-first mode: write results to grid columns first, then rasterize
        self.use_grid_first = True
        # Track if we've cleared the column (only do once, not per area)
        self._column_cleared = False

    def _process_features_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
        area_name: Optional[str] = None,
    ) -> str:
        """
        Executes the actual workflow logic for a single area.

        Supports grid-first mode where counts are written directly to study_area_grid.

        :current_area: Current polygon from our study area.
        :current_bbox: Bounding box of the above area.
        :area_features: A vector layer of features to analyse that includes only features in the study area.
        :index: Iteration / number of area being processed.
        :area_name: Name of the area being processed.

        :return: A raster layer file path if processing completes successfully.
        """
        if self.use_grid_first:
            if self._use_s2s_education_proxy:
                return self._process_s2s_education_proxy(
                    current_bbox=current_bbox,
                    index=index,
                    area_name=area_name,
                )

            area_features_count = area_features.featureCount() if area_features is not None else 0
            log_message(
                f"Features layer for area {index + 1} loaded with {area_features_count} features.",
                tag="GeoE3",
                level=Qgis.Info,
            )
            return self._process_grid_first(
                current_bbox=current_bbox,
                area_features=area_features,
                index=index,
                area_name=area_name,
            )
        else:
            return self._process_raster_first(
                current_bbox=current_bbox,
                area_features=area_features,
                index=index,
            )

    def _process_raster_first(
        self,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
    ) -> str:
        """Legacy raster-first processing using polygon perimeter classification."""
        from geest.core.algorithms.polygon_per_cell_processor import (
            assign_reclassification_to_polygons,
        )

        polygon_areas = assign_reclassification_to_polygons(area_features)
        raster_output = self._rasterize(
            polygon_areas,
            current_bbox,
            index,
            value_field="value",
            default_value=0,
        )
        return raster_output

    def _process_grid_first(
        self,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
        area_name: str,
    ) -> str:
        """Grid-first processing - writes directly to study_area_grid."""
        # Clear column once at the start (not per area)
        if not self._column_cleared:
            log_message(f"Clearing column {self.layer_id} before processing")
            clear_grid_column(self.gpkg_path, self.layer_id)
            self._column_cleared = True

        self.progressChanged.emit(10.0)

        # Count features and write to grid
        log_message(f"Counting features for column {self.layer_id}")
        count_features_per_grid_cell(
            gpkg_path=self.gpkg_path,
            column_name=self.layer_id,
            features_layer=area_features,
            feedback=self.feedback,
        )

        self.progressChanged.emit(50.0)

        # Rasterize from grid column
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
        log_message(f"Rasterized grid column to {output_path}")
        return output_path

    def _resolve_s2s_fields(self):
        """Resolve ordered S2S fields configured for this indicator."""
        fields = self.attributes.get("s2s_fields", [])
        if isinstance(fields, str):
            fields = [token.strip() for token in fields.split(",") if token.strip()]
        elif isinstance(fields, list):
            fields = [str(token).strip() for token in fields if str(token).strip()]
        else:
            fields = []

        unique_fields = []
        for field in fields:
            if field not in unique_fields:
                unique_fields.append(field)

        return unique_fields

    def _process_s2s_education_proxy(self, current_bbox: QgsGeometry, index: int, area_name: str) -> str:
        """Process Education indicator using S2S urbanization population fields.

        Proxy rules:
        - urban_pop = ghs_22_pop + ghs_23_pop + ghs_30_pop
        - rural_pop = ghs_11_pop + ghs_12_pop + ghs_13_pop
        - urban_share = urban_pop / ghs_total_pop
        - likert score (1-5) from urban_share thresholds [0.2, 0.4, 0.6, 0.8]

        Notes:
        - ghs_21_pop (suburban) is intentionally excluded.
        - Cells with invalid/zero denominator are set to NULL.
        """
        if not area_name:
            raise ValueError("area_name is required for S2S education proxy processing.")

        if not os.path.exists(self.s2s_output_path):
            raise ValueError(f"S2S output not found for Education proxy: {self.s2s_output_path}")

        required_fields = list(DEFAULT_S2S_EDUCATION_URBANIZATION_FIELDS)
        missing_fields = [field for field in required_fields if field not in self.s2s_fields]
        if missing_fields:
            raise ValueError("Education S2S proxy requires fields " f"{required_fields}, but missing {missing_fields}.")

        source_layer = os.path.splitext(os.path.basename(self.s2s_output_path))[0]
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

        # Clear target column once before first area, then write per-area values.
        if not self._column_cleared:
            clear_grid_column(self.gpkg_path, self.layer_id)
            self._column_cleared = True

        self.progressChanged.emit(10.0)

        for source_field, temp_column in temp_columns.items():
            updated_count = write_joined_values_to_grid(
                gpkg_path=self.gpkg_path,
                column_name=temp_column,
                source_gpkg=self.s2s_output_path,
                source_layer=source_layer,
                source_key_field="hex_id",
                target_key_field="h3_index",
                source_value_field=source_field,
                area_name=area_name,
            )
            if updated_count < 0:
                raise RuntimeError(f"Failed joining S2S field '{source_field}' to grid for Education proxy.")

        self.progressChanged.emit(60.0)

        # Compute Likert score from urban share.
        from osgeo import ogr

        ds = ogr.Open(self.gpkg_path, 1)
        if not ds:
            raise RuntimeError(f"Could not open GeoPackage for Education proxy update: {self.gpkg_path}")

        try:
            q = lambda name: f'"{name.replace(" ", "_").replace("-", "_")[:63]}"'

            c11 = q(temp_columns["ghs_11_pop"])
            c12 = q(temp_columns["ghs_12_pop"])
            c13 = q(temp_columns["ghs_13_pop"])
            c22 = q(temp_columns["ghs_22_pop"])
            c23 = q(temp_columns["ghs_23_pop"])
            c30 = q(temp_columns["ghs_30_pop"])
            ctotal = q(temp_columns["ghs_total_pop"])
            target = q(self.layer_id)

            where_area = f"area_name = '{area_name.replace("'", "''")}'"
            score_expr = (
                f"CASE "
                f"WHEN COALESCE({ctotal}, 0) <= 0 THEN NULL "
                f"WHEN ((COALESCE({c22},0)+COALESCE({c23},0)+COALESCE({c30},0)) / {ctotal}) < 0.2 THEN 1 "
                f"WHEN ((COALESCE({c22},0)+COALESCE({c23},0)+COALESCE({c30},0)) / {ctotal}) < 0.4 THEN 2 "
                f"WHEN ((COALESCE({c22},0)+COALESCE({c23},0)+COALESCE({c30},0)) / {ctotal}) < 0.6 THEN 3 "
                f"WHEN ((COALESCE({c22},0)+COALESCE({c23},0)+COALESCE({c30},0)) / {ctotal}) < 0.8 THEN 4 "
                f"ELSE 5 END"
            )

            sql = f"UPDATE study_area_grid SET {target} = {score_expr} WHERE {where_area}"  # nosec B608
            ds.ExecuteSQL(sql, dialect="SQLite")
        finally:
            ds = None

        self.progressChanged.emit(85.0)

        # Rasterize from computed Education proxy column.
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
            f"Processed Education (S2S urbanization proxy) for area {area_name} into column {self.layer_id}",
            tag="GeoE3",
            level=Qgis.Info,
        )
        return output_path

    # Default implementation of the abstract method - not used in this workflow
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
        pass

    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
        area_name: str = None,
    ):
        """
        Executes the workflow, reporting progress through the feedback object and checking for cancellation.
        """
        pass
