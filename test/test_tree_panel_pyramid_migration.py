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
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from osgeo import ogr, osr

from geest.gui.panels.tree_panel import TreePanel


def _write_model_json(model_path, indicator_ids=("jobs",), factor_id="economic", dimension_id="opportunity"):
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
