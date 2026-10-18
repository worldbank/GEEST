# -*- coding: utf-8 -*-
"""Unit tests for TreePanel.prompt_build_missing_pyramids.

TreePanel is a heavy QWidget that needs a loaded .ui file and a full
JsonTreeModel to construct, so these tests call the unbound method
against a lightweight stand-in object instead of a real TreePanel,
matching the pattern in test_tree_panel_road_network.py.
"""
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from osgeo import ogr, osr

from geest.gui.panels.tree_panel import TreePanel


def _write_model_json(
    model_path,
    indicator_ids=("jobs",),
    factor_id="economic",
    dimension_id="opportunity",
    grid_type="square",
    h3_resolution=9,
):
    """Write a minimal model.json fixture.

    Args:
        model_path: Destination path for model.json.
        indicator_ids: Indicator ids to place under factor_id/dimension_id.
        factor_id: Factor id.
        dimension_id: Dimension id.
        grid_type: "square" (default, matches any existing project with no
            "grid_type" key at all) or "h3". Grid type is decided once at
            study-area creation time and never migrated, so "square" must
            remain the default for backward compatibility with every
            existing caller of this helper.
        h3_resolution: Written as "analysis_h3_resolution" only when
            grid_type == "h3" (ignored otherwise).
    """
    model = {
        "dimensions": [
            {
                "id": dimension_id,
                "factors": [
                    {
                        "id": factor_id,
                        "indicators": [{"id": indicator_id} for indicator_id in indicator_ids],
                    }
                ],
            }
        ]
    }
    if grid_type == "h3":
        model["grid_type"] = "h3"
        model["analysis_h3_resolution"] = h3_resolution
    with open(model_path, "w", encoding="utf-8") as f:
        json.dump(model, f)


def _build_grid(gpkg_path, score_fields=()):
    """Create a minimal study_area_grid with the given REAL (scored) fields."""
    driver = ogr.GetDriverByName("GPKG")
    ds = driver.CreateDataSource(gpkg_path)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(32626)
    layer = ds.CreateLayer("study_area_grid", srs, geom_type=ogr.wkbPolygon)
    layer.CreateField(ogr.FieldDefn("grid_id", ogr.OFTInteger))
    for field in score_fields:
        layer.CreateField(ogr.FieldDefn(field, ogr.OFTReal))

    for row in range(4):
        for col in range(4):
            xmin, ymin = col * 100.0, row * 100.0
            wkt = (
                f"POLYGON(({xmin} {ymin},{xmin + 100} {ymin},"
                f"{xmin + 100} {ymin + 100},{xmin} {ymin + 100},{xmin} {ymin}))"
            )
            feature = ogr.Feature(layer.GetLayerDefn())
            feature.SetField("grid_id", row * 4 + col)
            for field in score_fields:
                feature.SetField(field, float(row + col))
            feature.SetGeometry(ogr.CreateGeometryFromWkt(wkt))
            layer.CreateFeature(feature)
            feature = None
    ds = None


def _build_h3_grid(gpkg_path, h3_resolution=9, score_fields=(), bbox_wgs84=(36.80, -1.30, 36.82, -1.28)):
    """Create a minimal H3-indexed study_area_grid with the given REAL (scored) fields.

    Mirrors _build_grid() above but for the "h3" grid_type path: cells are
    real H3 hexagons (generated with h3-py v4's h3shape_to_cells) covering
    a small WGS84 bounding box, with an "h3_index" text column matching the
    field study_area_processing_task.py writes for H3-grid projects.

    Args:
        gpkg_path: Destination path for the study_area.gpkg fixture.
        h3_resolution: H3 resolution to generate cells at.
        score_fields: REAL (scored) column names to add and populate.
        bbox_wgs84: (min_lon, min_lat, max_lon, max_lat) tuple, kept small so
            the generated cell count stays low and tests run fast.
    """
    import h3

    driver = ogr.GetDriverByName("GPKG")
    ds = driver.CreateDataSource(gpkg_path)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    layer = ds.CreateLayer("study_area_grid", srs, geom_type=ogr.wkbPolygon)
    layer.CreateField(ogr.FieldDefn("grid_id", ogr.OFTInteger))
    h3_field = ogr.FieldDefn("h3_index", ogr.OFTString)
    h3_field.SetWidth(16)
    layer.CreateField(h3_field)
    for field in score_fields:
        layer.CreateField(ogr.FieldDefn(field, ogr.OFTReal))

    min_lon, min_lat, max_lon, max_lat = bbox_wgs84
    shape = h3.LatLngPoly([(min_lat, min_lon), (min_lat, max_lon), (max_lat, max_lon), (max_lat, min_lon)])
    cells = h3.h3shape_to_cells(shape, h3_resolution)
    if not cells:
        raise RuntimeError("No H3 cells generated for the test bbox - widen bbox_wgs84.")

    for grid_id, cell in enumerate(cells):
        boundary = h3.cell_to_boundary(cell)  # [(lat, lon), ...]
        ring = ogr.Geometry(ogr.wkbLinearRing)
        for lat, lon in boundary:
            ring.AddPoint(lon, lat)
        ring.CloseRings()
        polygon = ogr.Geometry(ogr.wkbPolygon)
        polygon.AddGeometry(ring)

        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField("grid_id", grid_id)
        feature.SetField("h3_index", cell)
        for field in score_fields:
            feature.SetField(field, float(grid_id))
        feature.SetGeometry(polygon)
        layer.CreateFeature(feature)
        feature = None
    ds = None


@contextmanager
def _fake_h3_pyramid_utils(has_structure, refresh=None):
    """Inject a stand-in geest.core.h3_pyramid_utils module for the duration of the `with` block.

    geest/core/h3_pyramid_utils.py does not exist in this working tree yet
    - it is a sibling deliverable that will provide the real H3 pyramid
    structure-check/build logic (has_h3_pyramid_structure,
    refresh_h3_pyramid_column) that TreePanel.prompt_build_missing_pyramids
    imports by name. Until that module lands, these tests exercise
    TreePanel's own control-flow/wiring in isolation via this stand-in,
    exactly as if the real collaborator functions returned the given
    canned results. Re-run against the real module once it exists.

    Args:
        has_structure: Return value for the stand-in's
            has_h3_pyramid_structure(gpkg_path, column_name, h3_resolution).
        refresh: Callable (or MagicMock) to use as the stand-in's
            refresh_h3_pyramid_column(gpkg_path, column_name, h3_resolution).
            Defaults to a MagicMock returning True.

    Yields:
        types.ModuleType: The injected fake module, so callers can assert
            on its mock call history.
    """
    fake_module = types.ModuleType("geest.core.h3_pyramid_utils")
    fake_module.has_h3_pyramid_structure = MagicMock(return_value=has_structure)
    fake_module.refresh_h3_pyramid_column = refresh if refresh is not None else MagicMock(return_value=True)
    with patch.dict(sys.modules, {"geest.core.h3_pyramid_utils": fake_module}):
        yield fake_module


class TestPromptBuildMissingPyramids(unittest.TestCase):
    """Tests for TreePanel.prompt_build_missing_pyramids()."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_pyramid_migration_")
        self.study_area_dir = os.path.join(self.temp_dir, "study_area")
        os.makedirs(self.study_area_dir)
        self.gpkg_path = os.path.join(self.study_area_dir, "study_area.gpkg")
        self.model_path = os.path.join(self.temp_dir, "model.json")

        self.panel = MagicMock()
        self.panel.working_directory = self.temp_dir
        self.panel.analysis_scale.return_value = "national"
        self.panel.cell_size_m.return_value = 100.0

        self.patchers = [
            patch("geest.gui.panels.tree_panel.sip.isdeleted", return_value=False),
            patch("geest.gui.panels.tree_panel.QgsApplication.taskManager"),
        ]
        self.mock_task_manager = self.patchers[1].start()
        self.patchers[0].start()
        self.mock_task_manager.return_value.countActiveTasks.return_value = 0

    def tearDown(self):
        for patcher in self.patchers:
            patcher.stop()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch("geest.gui.panels.tree_panel.QMessageBox")
    def test_no_model_json_does_not_prompt(self, mock_messagebox):
        _build_grid(self.gpkg_path)
        TreePanel.prompt_build_missing_pyramids(self.panel)
        mock_messagebox.question.assert_not_called()

    @patch("geest.gui.panels.tree_panel.QMessageBox")
    def test_fresh_project_with_no_scored_columns_does_not_prompt(self, mock_messagebox):
        _write_model_json(self.model_path)
        _build_grid(self.gpkg_path)  # "jobs" column doesn't exist yet - nothing scored
        TreePanel.prompt_build_missing_pyramids(self.panel)
        mock_messagebox.question.assert_not_called()

    @patch("geest.gui.panels.tree_panel.QMessageBox")
    def test_regional_analysis_scale_never_prompts(self, mock_messagebox):
        self.panel.analysis_scale.return_value = "regional"
        _write_model_json(self.model_path)
        _build_grid(self.gpkg_path, score_fields=("jobs",))
        TreePanel.prompt_build_missing_pyramids(self.panel)
        mock_messagebox.question.assert_not_called()

    @patch("geest.gui.panels.tree_panel.QgsTask")
    @patch("geest.gui.panels.tree_panel.QMessageBox.question")
    def test_missing_pyramid_prompts_and_builds_on_yes(self, mock_question, mock_qgstask):
        from qgis.PyQt.QtWidgets import QMessageBox

        _write_model_json(self.model_path, indicator_ids=("jobs",))
        _build_grid(self.gpkg_path, score_fields=("jobs",))
        mock_question.return_value = QMessageBox.StandardButton.Yes

        captured = {}

        def fake_from_function(_name, build_fn, on_finished=None):
            captured["build_fn"] = build_fn
            captured["on_finished"] = on_finished
            return MagicMock()

        mock_qgstask.fromFunction.side_effect = fake_from_function

        TreePanel.prompt_build_missing_pyramids(self.panel)

        mock_question.assert_called_once()
        self.assertIn("build_fn", captured)

        fake_task = MagicMock()
        fake_task.isCanceled.return_value = False
        result = captured["build_fn"](fake_task)
        self.assertEqual(result["succeeded"], ["jobs"])
        self.assertEqual(result["failed"], [])

        from geest.core.grid_pyramid_utils import is_pyramid_fresh

        self.assertTrue(is_pyramid_fresh(self.gpkg_path, "jobs"))

        # on_finished must not raise even without a real iface in this test env.
        captured["on_finished"](None, result)

    @patch("geest.gui.panels.tree_panel.QgsTask")
    @patch("geest.gui.panels.tree_panel.QMessageBox.question")
    def test_h3_missing_pyramid_prompts_and_builds_on_yes(self, mock_question, mock_qgstask):
        from qgis.PyQt.QtWidgets import QMessageBox

        self.panel.grid_type.return_value = "h3"
        _write_model_json(self.model_path, indicator_ids=("jobs",), grid_type="h3", h3_resolution=9)
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=("jobs",))
        mock_question.return_value = QMessageBox.StandardButton.Yes

        captured = {}

        def fake_from_function(_name, build_fn, on_finished=None):
            captured["build_fn"] = build_fn
            captured["on_finished"] = on_finished
            return MagicMock()

        mock_qgstask.fromFunction.side_effect = fake_from_function

        with _fake_h3_pyramid_utils(has_structure=False) as fake_module:
            TreePanel.prompt_build_missing_pyramids(self.panel)

            mock_question.assert_called_once()
            self.assertIn("build_fn", captured)

            fake_task = MagicMock()
            fake_task.isCanceled.return_value = False
            result = captured["build_fn"](fake_task)
            self.assertEqual(result["succeeded"], ["jobs"])
            self.assertEqual(result["failed"], [])
            fake_module.refresh_h3_pyramid_column.assert_called_once_with(
                self.gpkg_path, "jobs", 9, analysis_scale="national"
            )

        # on_finished must not raise even without a real iface in this test env.
        captured["on_finished"](None, result)

    @patch("geest.gui.panels.tree_panel.QMessageBox")
    def test_h3_already_fresh_pyramid_does_not_prompt(self, mock_messagebox):
        self.panel.grid_type.return_value = "h3"
        _write_model_json(self.model_path, indicator_ids=("jobs",), grid_type="h3", h3_resolution=9)
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=("jobs",))

        with _fake_h3_pyramid_utils(has_structure=True) as fake_module:
            TreePanel.prompt_build_missing_pyramids(self.panel)
            fake_module.has_h3_pyramid_structure.assert_called_once_with(
                self.gpkg_path, "jobs", 9, analysis_scale="national"
            )

        mock_messagebox.question.assert_not_called()

    @patch("geest.gui.panels.tree_panel.QMessageBox")
    def test_h3_built_then_invalidated_by_a_later_run_does_not_reprompt(self, mock_messagebox):
        # Regression (H3 path): invalidate_pyramid() is the SAME shared
        # bookkeeping function the square-grid path uses (see
        # geest.core.workflows.workflow_base's call site) - it only clears
        # the freshness row, never the structural "was this ever built"
        # fact. A merely-stale H3 pyramid must not look like "never
        # migrated" and re-trigger the one-time migration offer on every
        # project open, exactly like the square-grid case below.
        from geest.core.grid_pyramid_utils import invalidate_pyramid

        self.panel.grid_type.return_value = "h3"
        _write_model_json(self.model_path, indicator_ids=("jobs",), grid_type="h3", h3_resolution=9)
        _build_h3_grid(self.gpkg_path, h3_resolution=9, score_fields=("jobs",))

        invalidate_pyramid(self.gpkg_path, "jobs")

        with _fake_h3_pyramid_utils(has_structure=True):
            TreePanel.prompt_build_missing_pyramids(self.panel)

        mock_messagebox.question.assert_not_called()

    @patch("geest.gui.panels.tree_panel.QMessageBox")
    def test_already_fresh_pyramid_does_not_prompt(self, mock_messagebox):
        from geest.core.grid_pyramid_utils import refresh_pyramid_column

        _write_model_json(self.model_path, indicator_ids=("jobs",))
        _build_grid(self.gpkg_path, score_fields=("jobs",))
        self.assertTrue(refresh_pyramid_column(self.gpkg_path, "jobs", 100.0))

        TreePanel.prompt_build_missing_pyramids(self.panel)
        mock_messagebox.question.assert_not_called()

    @patch("geest.gui.panels.tree_panel.QMessageBox")
    def test_built_then_invalidated_by_a_later_run_does_not_reprompt(self, mock_messagebox):
        # Regression: every successful analysis run invalidates pyramid
        # freshness for its own column (so a stale pyramid is rebuilt on
        # next view). That must not look like "never migrated" and
        # re-trigger the one-time migration offer on every project open.
        from geest.core.grid_pyramid_utils import invalidate_pyramid, refresh_pyramid_column

        _write_model_json(self.model_path, indicator_ids=("jobs",))
        _build_grid(self.gpkg_path, score_fields=("jobs",))
        self.assertTrue(refresh_pyramid_column(self.gpkg_path, "jobs", 100.0))

        invalidate_pyramid(self.gpkg_path, "jobs")

        TreePanel.prompt_build_missing_pyramids(self.panel)
        mock_messagebox.question.assert_not_called()

    @patch("geest.gui.panels.tree_panel.QgsTask")
    @patch("geest.gui.panels.tree_panel.QMessageBox")
    def test_out_of_scope_columns_never_counted_as_missing(self, mock_messagebox, mock_qgstask):
        # geoe3_masked/geoe3_by_population etc. are raster-algebra derived
        # and must never trigger this prompt even if present and un-pyramided.
        _write_model_json(self.model_path, indicator_ids=("jobs",))
        _build_grid(self.gpkg_path, score_fields=("geoe3_masked", "geoe3_by_population"))
        TreePanel.prompt_build_missing_pyramids(self.panel)
        mock_messagebox.question.assert_not_called()

    @patch("geest.gui.panels.tree_panel.QMessageBox.question")
    def test_user_declines_does_not_build(self, mock_question):
        from qgis.PyQt.QtWidgets import QMessageBox

        _write_model_json(self.model_path, indicator_ids=("jobs",))
        _build_grid(self.gpkg_path, score_fields=("jobs",))
        mock_question.return_value = QMessageBox.StandardButton.No

        TreePanel.prompt_build_missing_pyramids(self.panel)

        self.mock_task_manager.return_value.addTask.assert_not_called()


if __name__ == "__main__":
    unittest.main()
