# -*- coding: utf-8 -*-
"""End-to-end 'run a model' test through the production execution path.

The unit suite exercises processors directly, but every QGIS 4 field crash
lived in the layer above: WorkflowQueueManager.add_workflow constructing a
WorkflowJob, the WorkflowFactory dispatching on analysis_mode, and the
workflow __init__ reading the item's data-source attributes. This test
drives that exact chain — a configured indicator runs to completion and an
unconfigured one is declined gracefully — on both the PyQt5 and PyQt6
images.
"""

import os
import unittest

from qgis.PyQt.QtCore import QSettings
from utilities_for_testing import get_qgis_app, prepare_fixtures

QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()

from geest.core import JsonTreeItem  # noqa: E402
from geest.core.workflow_queue_manager import WorkflowQueueManager  # noqa: E402


def make_indicator(attributes):
    """Build a minimal analysis→dimension→factor→indicator chain.

    Parents carry non-zero weightings so status checks do not classify the
    indicator as "Excluded from analysis".
    """
    analysis = JsonTreeItem(
        ["E2E analysis", "Configured", 1.0, {"id": "analysis_1"}],
        role="analysis",
        parent=None,
    )
    dimension = JsonTreeItem(
        ["E2E dimension", "Configured", 1.0, {"id": "dimension_1", "analysis_weighting": 1.0}],
        role="dimension",
        parent=analysis,
    )
    factor = JsonTreeItem(
        ["E2E factor", "Configured", 1.0, {"id": "factor_1", "dimension_weighting": 1.0}],
        role="factor",
        parent=dimension,
    )
    data = ["E2E indicator", "Configured", 1.0, attributes]
    return JsonTreeItem(data, role="indicator", parent=factor)


class TestWorkflowJobEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Some harnesses (the local docker runner) initialize Processing,
        # others (qgis_testrunner.sh in CI) do not — workflows need it.
        try:
            from processing.core.Processing import Processing

            Processing.initialize()
        except Exception:  # nosec B110 — already initialized or unavailable
            pass
        cls.test_data_directory = prepare_fixtures()
        cls.working_directory = os.path.join(cls.test_data_directory, "wee_score")
        # WorkflowJob does not pass a working directory — production
        # workflows read it from QSettings, so the test does the same.
        QSettings().setValue("last_working_directory", cls.working_directory)

    def test_configured_indicator_runs_through_queue(self):
        """A configured indicator executes end-to-end via the job queue."""
        points = os.path.join(os.path.dirname(__file__), "test_data", "points", "points.shp")
        item = make_indicator(
            {
                "analysis_mode": "use_point_per_cell",
                "id": "e2e_points_per_cell",
                "description": "E2E point per cell",
                "result": "Not Run",
                "default_factor_weighting": 1.0,
                "factor_weighting": 1.0,
                "point_per_cell_shapefile": points,
            }
        )
        manager = WorkflowQueueManager(pool_size=1)
        job = manager.add_workflow(item, cell_size_m=1000.0, analysis_scale="local")
        self.assertIsNotNone(job, "configured indicator must be accepted by the queue")

        manager.start_processing_in_foreground()

        result = item.attribute("result", "")
        error = item.attribute("error", "")
        self.assertIn(
            "Completed",
            result,
            msg=f"workflow did not complete: result={result!r} error={error!r}",
        )
        # Local/national indicators no longer rasterize per area at all
        # (visualization comes from the pyramid instead - see
        # geest.core.grid_pyramid_utils), so completion is now verified
        # against the grid column directly rather than a raster file.
        from geest.core.grid_column_utils import get_grid_column_values
        from geest.core.grid_pyramid_utils import is_pyramid_fresh

        self.assertFalse(item.attribute("result_file", ""))
        gpkg_path = os.path.join(self.working_directory, "study_area", "study_area.gpkg")
        values = get_grid_column_values(gpkg_path, "e2e_points_per_cell")
        self.assertTrue(values, "completed workflow must have scored grid cells")
        # The pyramid must already be built by the time execute() returns -
        # it must not be left merely invalidated for the next UI click to
        # rebuild synchronously (that used to block the UI thread for the
        # full rebuild duration on the very next click anywhere in the tree).
        self.assertTrue(
            is_pyramid_fresh(gpkg_path, "e2e_points_per_cell"),
            "pyramid must be rebuilt as part of the background workflow run, not left stale",
        )

    def test_mode_switch_does_not_orphan_configured_layer(self):
        """A polyline indicator configured through the OSM transport mode
        keys must still be accepted when analysis_mode is the plain
        polyline mode (Active Transport supports both modes)."""
        polylines = os.path.join(os.path.dirname(__file__), "test_data", "polylines", "polylines.shp")
        item = make_indicator(
            {
                "analysis_mode": "use_polyline_per_cell",
                "id": "e2e_mode_switch",
                "description": "E2E mode-switch fallback",
                "result": "Not Run",
                "osm_transport_polyline_per_cell_layer_source": polylines,
            }
        )
        manager = WorkflowQueueManager(pool_size=1)
        job = manager.add_workflow(item, cell_size_m=1000.0, analysis_scale="local")
        self.assertIsNotNone(job, "layer configured under the sibling mode key must be accepted")

    def test_unconfigured_indicator_is_declined_not_crashed(self):
        """An indicator without a data source is skipped, not a TypeError."""
        item = make_indicator(
            {
                "analysis_mode": "use_polyline_per_cell",
                "id": "e2e_unconfigured",
                "description": "E2E unconfigured indicator",
                "result": "Not Run",
            }
        )
        manager = WorkflowQueueManager(pool_size=1)
        job = manager.add_workflow(item, cell_size_m=1000.0, analysis_scale="local")
        self.assertIsNone(job, "unconfigured indicator must be declined by the queue")

    def test_broken_layer_marks_item_failed_and_run_continues(self):
        """A broken data source marks the item failed; the run continues.

        Regression for the field crash 'Exception: Invalid points layer
        found.' aborting run_all: the declined item must carry the failed
        status (red icon) and an accessible error tooltip, and the next
        indicator in a multi-indicator run must still be accepted.
        """
        broken = make_indicator(
            {
                "analysis_mode": "use_multi_buffer_point",
                "id": "e2e_broken_layer",
                "factor_weighting": 1.0,
                "description": "E2E broken layer",
                "result": "Not Run",
                "multi_buffer_travel_distances": "100,200",
                "multi_buffer_point_shapefile": "/nonexistent/points.shp",
            }
        )
        manager = WorkflowQueueManager(pool_size=1)
        job = manager.add_workflow(broken, cell_size_m=1000.0, analysis_scale="local")
        self.assertIsNone(job, "broken indicator must be declined, not raise")
        self.assertEqual(broken.getStatus(), "Workflow failed")
        error_text = broken.attribute("error", "")
        self.assertTrue(error_text, "declined item must carry an error message for its tooltip")
        self.assertNotIn("Traceback", error_text, "tooltip must be accessible language, not a traceback")

        # The rest of a multi-indicator run continues: a valid indicator is
        # still accepted by the same queue manager afterwards.
        points = os.path.join(os.path.dirname(__file__), "test_data", "points", "points.shp")
        healthy = make_indicator(
            {
                "analysis_mode": "use_point_per_cell",
                "id": "e2e_healthy_after_broken",
                "description": "E2E healthy indicator",
                "result": "Not Run",
                "point_per_cell_shapefile": points,
            }
        )
        job = manager.add_workflow(healthy, cell_size_m=1000.0, analysis_scale="local")
        self.assertIsNotNone(job, "a healthy indicator must still queue after a broken one")

    def test_empty_analysis_grid_fails_loudly(self):
        """A run against an empty study_area_grid must FAIL, not 'complete'.

        Field regression: a working directory whose grid was never populated
        let every grid-first workflow report 'Workflow Completed' while
        writing empty rasters ('Processing 0 grid cells against buffer
        layer'). The workflow must fail with an accessible message telling
        the user to re-create the study area.
        """
        import sqlite3

        from geest.core.grid_column_utils import grid_cell_count

        # Fresh fixture copy so the shared working directory stays intact.
        test_dir = prepare_fixtures()
        working_dir = os.path.join(test_dir, "wee_score")
        gpkg = os.path.join(working_dir, "study_area", "study_area.gpkg")
        self.assertGreater(grid_cell_count(gpkg), 0, "fixture grid should start populated")
        connection = sqlite3.connect(gpkg)
        connection.execute("DELETE FROM study_area_grid")
        connection.commit()
        connection.close()
        self.assertEqual(grid_cell_count(gpkg), 0)

        settings = QSettings()
        previous = settings.value("last_working_directory", "")
        settings.setValue("last_working_directory", working_dir)
        try:
            points = os.path.join(os.path.dirname(__file__), "test_data", "points", "points.shp")
            item = make_indicator(
                {
                    "analysis_mode": "use_point_per_cell",
                    "id": "e2e_empty_grid",
                    "factor_weighting": 1.0,
                    "description": "E2E empty grid",
                    "result": "Not Run",
                    "point_per_cell_shapefile": points,
                }
            )
            manager = WorkflowQueueManager(pool_size=1)
            job = manager.add_workflow(item, cell_size_m=1000.0, analysis_scale="local")
            self.assertIsNotNone(job, "the job itself is valid — failure happens at execution")

            manager.start_processing_in_foreground()

            result = item.attribute("result", "")
            self.assertNotIn("Completed", result, "an empty grid must never produce a completed run")
            self.assertIn("Error", result)
            error_text = item.attribute("error", "")
            self.assertIn("grid", error_text.lower())
            self.assertIn("re-create the study area", error_text.lower())
            self.assertEqual(item.getStatus(), "Workflow failed")
        finally:
            settings.setValue("last_working_directory", previous)

    def test_unexpected_exception_is_trapped_not_propagated(self):
        """Even a non-WorkflowNotConfiguredError must not abort queueing."""
        from unittest import mock

        item = make_indicator(
            {
                "analysis_mode": "use_point_per_cell",
                "id": "e2e_unexpected_boom",
                "factor_weighting": 1.0,
                "description": "E2E unexpected exception",
                "result": "Not Run",
            }
        )
        manager = WorkflowQueueManager(pool_size=1)
        with mock.patch(
            "geest.core.workflow_queue_manager.WorkflowJob",
            side_effect=RuntimeError("boom"),
        ):
            job = manager.add_workflow(item, cell_size_m=1000.0, analysis_scale="local")
        self.assertIsNone(job)
        self.assertEqual(item.getStatus(), "Workflow failed")
        self.assertIn("boom", item.attribute("error", ""))

    def test_h3_grid_pyramid_is_built_by_end_of_run(self):
        """Same production path, but for a project that opted into an H3 grid.

        Rebuilds the fixture's study_area_grid as real H3 hexagons and
        marks the project grid_type="h3" in model.json, so the workflow's
        end-of-run pyramid rebuild exercises the H3 branch
        (geest.core.h3_pyramid_utils.refresh_h3_pyramid_column) through the
        exact same WorkflowQueueManager -> WorkflowJob -> execute() chain
        as the square-grid test above, not a hand-rolled shortcut.
        """
        import json
        import os
        import sqlite3

        import h3
        from osgeo import ogr, osr

        from geest.core.h3_pyramid_utils import has_h3_pyramid_structure

        test_dir = prepare_fixtures()
        working_dir = os.path.join(test_dir, "wee_score")
        gpkg_path = os.path.join(working_dir, "study_area", "study_area.gpkg")

        model_path = os.path.join(working_dir, "model.json")
        with open(model_path) as f:
            model = json.load(f)
        model["grid_type"] = "h3"
        model["analysis_h3_resolution"] = 9
        with open(model_path, "w") as f:
            json.dump(model, f)

        connection = sqlite3.connect(gpkg_path)
        connection.execute("DELETE FROM study_area_grid")
        connection.commit()
        connection.close()

        ds = ogr.Open(gpkg_path, 1)
        layer = ds.GetLayer("study_area_grid")
        layer_defn = layer.GetLayerDefn()
        existing_fields = {layer_defn.GetFieldDefn(i).GetName().lower() for i in range(layer_defn.GetFieldCount())}
        # The fixture's base study_area_grid predates H3 support and has no
        # h3_index/h3_resolution fields - add them, same as
        # study_area_processing_task.py does for a real H3-grid project.
        if "h3_index" not in existing_fields:
            h3_field = ogr.FieldDefn("h3_index", ogr.OFTString)
            h3_field.SetWidth(16)
            layer.CreateField(h3_field)
        if "h3_resolution" not in existing_fields:
            layer.CreateField(ogr.FieldDefn("h3_resolution", ogr.OFTInteger))
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        shape = h3.LatLngPoly([(-1.30, 36.80), (-1.30, 36.82), (-1.28, 36.82), (-1.28, 36.80)])
        cells = list(h3.h3shape_to_cells(shape, 9))
        self.assertGreater(len(cells), 1, "test bbox must yield more than one H3 cell")
        for grid_id, cell in enumerate(cells):
            boundary = h3.cell_to_boundary(cell)
            ring = ogr.Geometry(ogr.wkbLinearRing)
            for lat, lon in boundary:
                ring.AddPoint(lon, lat)
            ring.CloseRings()
            polygon = ogr.Geometry(ogr.wkbPolygon)
            polygon.AddGeometry(ring)
            feature = ogr.Feature(layer.GetLayerDefn())
            # Matches the fixture's existing study_area_bboxes/polygons
            # area_name (AreaIterator's synthetic name for an
            # unpartitioned single study area), not an arbitrary value.
            feature.SetField("area_name", "none_part0")
            feature.SetField("h3_index", cell)
            feature.SetField("h3_resolution", 9)
            feature.SetGeometry(polygon)
            layer.CreateFeature(feature)
            feature = None
        ds = None

        settings = QSettings()
        previous = settings.value("last_working_directory", "")
        settings.setValue("last_working_directory", working_dir)
        try:
            points = os.path.join(os.path.dirname(__file__), "test_data", "points", "points.shp")
            item = make_indicator(
                {
                    "analysis_mode": "use_point_per_cell",
                    "id": "e2e_h3_points_per_cell",
                    "factor_weighting": 1.0,
                    "description": "E2E H3 point per cell",
                    "result": "Not Run",
                    "point_per_cell_shapefile": points,
                }
            )
            manager = WorkflowQueueManager(pool_size=1)
            job = manager.add_workflow(item, cell_size_m=100.0, analysis_scale="local")
            self.assertIsNotNone(job, "configured H3-grid indicator must be accepted by the queue")

            manager.start_processing_in_foreground()

            result = item.attribute("result", "")
            error = item.attribute("error", "")
            self.assertIn("Completed", result, msg=f"workflow did not complete: result={result!r} error={error!r}")
            self.assertTrue(
                has_h3_pyramid_structure(gpkg_path, "e2e_h3_points_per_cell", 9),
                "H3 pyramid must be built as part of the background workflow run",
            )
        finally:
            settings.setValue("last_working_directory", previous)


if __name__ == "__main__":
    unittest.main()
