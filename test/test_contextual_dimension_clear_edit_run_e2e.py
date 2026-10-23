# -*- coding: utf-8 -*-
"""End-to-end reproduction of the real-world Contextual-dimension bug report.

This drives the ACTUAL production code TreePanel.run_item() uses — real
JsonTreeItem tree, real WorkflowQueueManager, real ContextualIndexScoreWorkflow
/ FactorAggregationWorkflow / DimensionAggregationWorkflow classes executing
against a real study_area.gpkg — not hand-rolled fakes. Only the GUI chrome
(progress bars, labels, the QWidget itself) is stood in for, following the
established TreePanel-unbound-method pattern in test_tree_panel_road_network.py
(TreePanel is a heavy QWidget that needs a loaded .ui file to construct).

Reported protocol (worldbank/GeoE3, 2026-10-22): clear each of the three
Contextual factors (Workplace Discrimination, Regulatory Frameworks, Financial
Inclusion) — each has exactly one hidden child indicator, since the tree UI
hides a factor's only child and shows the factor row in its place — then clear
the Contextual dimension, set new index scores on the (hidden, unclearable
from the tree) indicators, and run the dimension. Expected: every indicator
equals its own new index score mapped through the 1-5 contextual scale, every
factor equals its one child indicator exactly, and the dimension equals the
mean of the three factors. None of this should be null or zero, and the
rasterized output for each indicator/factor must sample to the same value as
its grid column.

Two scenarios are run against the identical starting state:
  - test_plain_run_... (no Shift held - the default button).
  - test_shift_run_... (Shift held - run_only_incomplete forced False).

Both must land on the exact same fully-correct result. Before the fix in
FixedValueDataSourceWidget.update_attributes(), the plain-run scenario
produced stale-matching-stale (not null/0, but *wrong*, frozen at the old
index score): queue_workflow_task skips any item that already has a
result_file when run_only_incomplete is True, and the three indicators here
are never directly clearable (hidden), so editing index_score alone left
their old "Completed" result/result_file untouched. Step 3 below goes
through the real widget, so this test exercises that fix rather than
assuming it.
"""
import os
import shutil
import tempfile
import types
import unittest
from unittest.mock import MagicMock

import numpy as np
from osgeo import gdal, ogr
from qgis.PyQt.QtCore import QSettings

from geest.core import JsonTreeItem
from geest.core.workflow_queue_manager import WorkflowQueueManager
from geest.gui.panels.tree_panel import TreePanel
from geest.gui.widgets.datasource_widgets.fixed_value_datasource_widget import (
    FixedValueDataSourceWidget,
)

gdal.UseExceptions()
ogr.UseExceptions()

FIXTURE_STUDY_AREA = os.path.join(os.path.dirname(__file__), "test_data", "wee_score", "study_area")

# (factor_id, indicator_id, new_index_score, expected_value_after_rescaling)
# Rescaling comes straight from contextual_index_score_mappings.score_mapping:
# 77 -> 2 (>=75, <80), 88 -> 3 (>=80, <90), 95 -> 5 (>=95).
CONTEXTUAL_FACTORS = [
    ("workplace_discrimination", "Workplace_Index", 77, 2.0),
    ("regulatory_frameworks", "Pay_Parenthood_Index", 88, 3.0),
    ("financial_inclusion", "Entrepreneurship_Index", 95, 5.0),
]
DIM_COLUMN = "dim_contextual"
STALE_VALUE = 999.0  # obviously-not-a-real-score sentinel for "left over from a previous run"
OLD_INDEX_SCORE = 50  # maps to score_mapping's "0" bucket - also obviously stale/different


def _indicator_column(indicator_id):
    return indicator_id.lower().replace(" ", "_").replace("-", "_")


def _factor_column(factor_id):
    return f"fac_{factor_id.lower().replace(' ', '_').replace('-', '_')}"


def build_contextual_tree():
    """analysis -> Contextual dimension -> 3 factors, each with one hidden indicator."""
    analysis = JsonTreeItem(
        ["Analysis", "Configured", 1.0, {"id": "analysis_1", "analysis_scale": "local"}],
        role="analysis",
        parent=None,
    )
    dimension = JsonTreeItem(
        [
            "Contextual",
            "Configured",
            1.0,
            {"id": "contextual", "analysis_weighting": 1.0, "default_analysis_weighting": 1.0},
        ],
        role="dimension",
        parent=analysis,
    )
    analysis.appendChild(dimension)

    factors = {}
    for factor_id, indicator_id, _new_score, _expected in CONTEXTUAL_FACTORS:
        factor = JsonTreeItem(
            [
                factor_id,
                "Configured",
                1.0,
                {
                    "id": factor_id,
                    "dimension_weighting": 1.0 / 3.0,
                    "default_dimension_weighting": 1.0 / 3.0,
                },
            ],
            role="factor",
            parent=dimension,
        )
        indicator = JsonTreeItem(
            [
                indicator_id,
                "Configured",
                1.0,
                {
                    "id": indicator_id,
                    "analysis_mode": "use_contextual_index_score",
                    "factor_weighting": 1.0,
                    "default_factor_weighting": 1.0,
                    "index_score": OLD_INDEX_SCORE,
                    # Simulate a prior completed run - the clear/edit protocol
                    # below never touches these directly, since the indicator
                    # is hidden behind its single-child factor in the real UI.
                    "result": "contextual_index_score Workflow Completed",
                    "result_file": "contextual/stale_previous_run_output.vrt",
                },
            ],
            role="indicator",
            parent=factor,
        )
        factor.appendChild(indicator)
        dimension.appendChild(factor)
        factors[factor_id] = (factor, indicator)

    return analysis, dimension, factors


def seed_stale_grid_state(gpkg_path):
    """Add the model's grid columns and fill every row with STALE_VALUE.

    Mirrors what a previous, already-completed run would have left behind -
    not add_model_columns_to_grid()'s empty/NULL starting point.
    """
    ds = ogr.Open(gpkg_path, 1)
    layer = ds.GetLayerByName("study_area_grid")
    layer_defn = layer.GetLayerDefn()
    existing = {layer_defn.GetFieldDefn(i).GetName() for i in range(layer_defn.GetFieldCount())}

    columns = [DIM_COLUMN]
    for factor_id, indicator_id, _new_score, _expected in CONTEXTUAL_FACTORS:
        columns.append(_factor_column(factor_id))
        columns.append(_indicator_column(indicator_id))

    for column in columns:
        if column not in existing:
            layer.CreateField(ogr.FieldDefn(column, ogr.OFTReal))

    layer.StartTransaction()
    layer.ResetReading()
    for feature in layer:
        for column in columns:
            feature.SetField(column, STALE_VALUE)
        layer.SetFeature(feature)
    layer.CommitTransaction()
    ds = None


def read_grid_column(gpkg_path, column_name):
    """Read every value in a study_area_grid column from a FRESH connection."""
    ds = ogr.Open(gpkg_path, 0)
    layer = ds.GetLayerByName("study_area_grid")
    values = [feature.GetField(column_name) for feature in layer]
    ds = None
    return values


def sample_raster_values(raster_path):
    """Return the set of non-nodata pixel values in a raster/VRT."""
    ds = gdal.Open(raster_path)
    band = ds.GetRasterBand(1)
    nodata = band.GetNoDataValue()
    array = band.ReadAsArray().astype(float)
    ds = None
    if nodata is not None:
        values = array[~np.isclose(array, nodata)]
    else:
        values = array.flatten()
    return set(np.round(values, 4).tolist())


class TestContextualDimensionClearEditRunEndToEnd(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_contextual_e2e_")
        self.working_directory = os.path.join(self.temp_dir, "project")
        shutil.copytree(FIXTURE_STUDY_AREA, os.path.join(self.working_directory, "study_area"))
        self.gpkg_path = os.path.join(self.working_directory, "study_area", "study_area.gpkg")
        seed_stale_grid_state(self.gpkg_path)

        QSettings().setValue("last_working_directory", self.working_directory)

        self.analysis, self.dimension, self.factors = build_contextual_tree()

        try:
            from processing.core.Processing import Processing

            Processing.initialize()
        except Exception:  # nosec B110 — already initialized or unavailable
            pass

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_panel(self, run_only_incomplete):
        """A MagicMock stand-in for TreePanel carrying only the real state
        queue_workflow_task/start_workflows/run_next_workflow_queue touch -
        the same pattern test_tree_panel_road_network.py uses, since
        TreePanel itself needs a loaded .ui file to construct."""
        panel = MagicMock()
        panel.model.get_analysis_item.return_value = self.analysis
        panel.model.rootItem = self.analysis
        panel.working_directory = self.working_directory
        panel.run_only_incomplete = run_only_incomplete
        panel.queue_manager = WorkflowQueueManager(pool_size=1)
        panel.road_network_layer_path = MagicMock(return_value="")
        panel.ghsl_layer_path = MagicMock(return_value="")
        panel.cell_size_m = MagicMock(return_value=1000.0)
        panel.analysis_scale = MagicMock(return_value="local")
        # start_workflows() calls self.queue_workflow_task(...) - on a bare
        # MagicMock that resolves to an auto-generated no-op mock, not the
        # real method, so nothing would ever actually get queued. Bind the
        # real unbound method so the real skip-check/add_workflow logic runs.
        panel.queue_workflow_task = types.MethodType(TreePanel.queue_workflow_task, panel)
        return panel

    def _run_stage(self, panel, workflow_type):
        """Queue one stage ("indicators"/"factors"/"dimensions") and drain it
        synchronously - the real queue_workflow_task()/start_workflows()
        logic, with start_processing_in_foreground() (QGIS's own sanctioned
        "debugging and testing" synchronous path) standing in for the async
        QgsTaskManager pool + Qt-signal stage-chaining run_item() uses for
        real. The business logic executed per item is identical either way;
        only the thread-pool plumbing is swapped for a deterministic one."""
        TreePanel.start_workflows(panel, workflow_type=workflow_type)
        panel.queue_manager.start_processing_in_foreground()
        panel.queue_manager.workflow_queue.job_queue.clear()

    def _clear_items(self, panel, items):
        for item in items:
            index = MagicMock()
            index.internalPointer.return_value = item
            panel.treeView.currentIndex.return_value = index
            TreePanel.clear_item(panel)

    def _run_full_protocol(self, shift_pressed):
        # Step 1: clear each of the three factors (their own hidden
        # indicator is left completely untouched, same as the real tree).
        factor_items = [factor for factor, _indicator in self.factors.values()]
        panel = self._make_panel(run_only_incomplete=not shift_pressed)
        self._clear_items(panel, factor_items)
        # Step 2: clear the Contextual dimension itself.
        self._clear_items(panel, [self.dimension])

        # Step 3: set new index scores on the (hidden) indicators - through
        # the real FixedValueDataSourceWidget, same as the properties
        # dialog does, so its result/result_file invalidation (the actual
        # fix for the stale-skip bug below) is genuinely exercised rather
        # than assumed.
        for factor_id, indicator_id, new_score, _expected in CONTEXTUAL_FACTORS:
            _factor, indicator = self.factors[factor_id]
            widget = FixedValueDataSourceWidget(
                widget_key="use_contextual_index_score", attributes=indicator.attributes()
            )
            widget.spin_box.setValue(new_score)

        # Step 4: run the dimension item, exactly as run_item()'s staged
        # "indicators" -> "factors" -> "dimensions" queueing does.
        panel.workflow_scope_item = self.dimension
        self._run_stage(panel, "indicators")
        self._run_stage(panel, "factors")
        self._run_stage(panel, "dimensions")
        return panel

    def _assert_full_protocol_invariants(self):
        """Every invariant from the bug report: indicator == new score
        rescaled, factor == its one child indicator exactly, dimension ==
        mean of the three factors, nothing null or zero, and the
        rasterized output matches the column - for all three factors."""
        for factor_id, indicator_id, _new_score, expected in CONTEXTUAL_FACTORS:
            factor_item, indicator_item = self.factors[factor_id]

            indicator_values = read_grid_column(self.gpkg_path, _indicator_column(indicator_id))
            self.assertTrue(
                all(v == expected for v in indicator_values),
                f"{indicator_id} grid column: expected all {expected}, got {set(indicator_values)}",
            )

            factor_values = read_grid_column(self.gpkg_path, _factor_column(factor_id))
            self.assertTrue(
                all(v == expected for v in factor_values),
                f"{_factor_column(factor_id)}: expected all {expected} (same as its child "
                f"indicator), got {set(factor_values)}",
            )

            indicator_raster = indicator_item.attribute("result_file", "")
            self.assertTrue(indicator_raster and os.path.exists(indicator_raster))
            self.assertEqual(
                sample_raster_values(indicator_raster),
                {expected},
                f"{indicator_id} raster does not sample to its own grid value {expected}",
            )

            factor_raster = factor_item.attribute("result_file", "")
            self.assertTrue(factor_raster and os.path.exists(factor_raster))
            self.assertEqual(
                sample_raster_values(factor_raster),
                {expected},
                f"{factor_id} raster does not sample to its own grid value {expected}",
            )

        expected_dim = sum(expected for *_ignored, expected in CONTEXTUAL_FACTORS) / 3.0
        dim_values = read_grid_column(self.gpkg_path, DIM_COLUMN)
        self.assertTrue(
            all(abs(v - expected_dim) < 1e-6 for v in dim_values),
            f"{DIM_COLUMN}: expected all {expected_dim}, got {set(dim_values)}",
        )
        self.assertTrue(all(v not in (None, 0.0) for v in dim_values))

    def test_shift_run_recomputes_everything_correctly(self):
        """Shift+Run (run_only_incomplete=False) forces every item,
        including the hidden indicators, to recompute regardless of
        status - this must hold even without the index-score-edit
        invalidation fix below, since Shift bypasses the stale-skip
        entirely."""
        self._run_full_protocol(shift_pressed=True)
        self._assert_full_protocol_invariants()

    def test_plain_run_now_recomputes_edited_indicator_too(self):
        """A plain Run (no Shift) on the dimension must ALSO pick up an
        edited hidden indicator - it used to not: queue_workflow_task's
        run_only_incomplete skip only looks at the item's own result_file,
        and the three indicators here are never clearable/cleared directly
        (hidden in the tree), so they kept their old "Completed" result
        even after index_score was edited to a new value, silently
        aggregating stale data (worldbank/GeoE3 field report, 2026-10-22).

        Fixed in FixedValueDataSourceWidget.update_attributes(): changing
        index_score now blanks the indicator's own result/result_file, so
        the normal skip-if-already-complete check correctly recognizes it
        needs to run again - without requiring the user to know to hold
        Shift. This test exercises that fix (Step 3 of _run_full_protocol
        goes through the real widget), so it must produce the exact same
        fully-correct result as the Shift+Run case above."""
        self._run_full_protocol(shift_pressed=False)
        self._assert_full_protocol_invariants()


if __name__ == "__main__":
    unittest.main()
