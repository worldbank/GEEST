# -*- coding: utf-8 -*-
"""Unit tests for geest.core.download_all_resources.

Covers the spec-derivation/cache-check logic directly (using real
JsonTreeItem fixtures, mirroring test_workflow_job_e2e.py's
make_indicator() pattern) and the controller's queue-advancement logic
(using a fake task whose signals are plain MagicMocks - connect() calls
are captured and invoked manually, so the controller's state machine is
tested deterministically without a real QgsTask/thread/network).
"""
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from geest.core import JsonTreeItem
from geest.core.download_all_resources import (
    DownloadAllResourcesController,
    collect_missing_resources,
    resource_is_cached,
    resource_spec_for_indicator,
    sync_cached_resource_attributes,
)


def make_indicator(attributes, parent=None):
    """Build a minimal indicator JsonTreeItem (mirrors test_workflow_job_e2e.py)."""
    data = ["Test indicator", "Configured", 1.0, attributes]
    return JsonTreeItem(data, role="indicator", parent=parent)


def build_indicator_tree():
    """Build a small analysis/dimension/factor tree with 2 downloadable + 1 unrelated indicator."""
    analysis = JsonTreeItem(["Analysis", "Configured", 1.0, {"id": "analysis_1"}], role="analysis", parent=None)
    dimension = JsonTreeItem(
        ["Dimension", "Configured", 1.0, {"id": "dimension_1", "analysis_weighting": 1.0}],
        role="dimension",
        parent=analysis,
    )
    factor = JsonTreeItem(
        ["Factor", "Configured", 1.0, {"id": "factor_1", "dimension_weighting": 1.0}],
        role="factor",
        parent=dimension,
    )
    ntl = make_indicator(
        {
            "analysis_mode": "use_nighttime_lights",
            "analysis_scale": "local",
            "id": "nighttime_lights",
            "factor_weighting": 1.0,
        },
        parent=factor,
    )
    fire = make_indicator(
        {
            "analysis_mode": "use_environmental_hazards",
            "analysis_scale": "local",
            "id": "fire",
            "factor_weighting": 1.0,
        },
        parent=factor,
    )
    unrelated = make_indicator(
        {
            "analysis_mode": "use_point_per_cell",
            "analysis_scale": "local",
            "id": "jobs",
            "factor_weighting": 1.0,
        },
        parent=factor,
    )
    factor.appendChild(ntl)
    factor.appendChild(fire)
    factor.appendChild(unrelated)
    dimension.appendChild(factor)
    analysis.appendChild(dimension)
    return analysis


class TestResourceSpecForIndicator(unittest.TestCase):
    def test_do_not_use_has_no_spec(self):
        item = make_indicator({"analysis_mode": "Do Not Use", "id": "x"})
        self.assertIsNone(resource_spec_for_indicator(item))

    def test_regional_has_no_spec(self):
        item = make_indicator(
            {"analysis_mode": "use_nighttime_lights", "analysis_scale": "regional", "id": "nighttime_lights"}
        )
        self.assertIsNone(resource_spec_for_indicator(item))

    def test_unrelated_mode_has_no_spec(self):
        item = make_indicator({"analysis_mode": "use_point_per_cell", "id": "jobs"})
        self.assertIsNone(resource_spec_for_indicator(item))

    def test_nighttime_lights_spec(self):
        item = make_indicator(
            {"analysis_mode": "use_nighttime_lights", "analysis_scale": "local", "id": "nighttime_lights"}
        )
        spec = resource_spec_for_indicator(item)
        self.assertIsNotNone(spec)
        self.assertEqual(spec.attribute_key, "nighttime_lights_raster")
        self.assertEqual(spec.filename, "nighttime_lights_annual")

    def test_environmental_hazard_spec_uses_indicator_id_as_hazard_id(self):
        item = make_indicator(
            {"analysis_mode": "use_environmental_hazards", "analysis_scale": "national", "id": "fire"}
        )
        spec = resource_spec_for_indicator(item)
        self.assertIsNotNone(spec)
        self.assertEqual(spec.attribute_key, "environmental_hazards_raster")
        self.assertEqual(spec.filename, "fire_hazard")

    def test_environmental_hazard_spec_lowercases_id(self):
        item = make_indicator({"analysis_mode": "use_environmental_hazards", "analysis_scale": "local", "id": "Flood"})
        spec = resource_spec_for_indicator(item)
        self.assertEqual(spec.filename, "flood_hazard")

    def test_osm_matched_buffer_point_spec(self):
        item = make_indicator(
            {
                "analysis_mode": "use_multi_buffer_point",
                "analysis_scale": "local",
                "id": "pharmacies",
                "name": "Pharmacies",
            }
        )
        spec = resource_spec_for_indicator(item)
        self.assertIsNotNone(spec)
        self.assertEqual(spec.kind, "vector")
        self.assertEqual(spec.widget_key, "multi_buffer_point")
        self.assertEqual(spec.filename, "osm_pharmacy")
        self.assertIsNone(spec.attribute_key)

    def test_osm_matched_single_buffer_point_spec(self):
        item = make_indicator(
            {
                "analysis_mode": "use_single_buffer_point",
                "analysis_scale": "national",
                "id": "water",
                "name": "Water Points",
            }
        )
        spec = resource_spec_for_indicator(item)
        self.assertIsNotNone(spec)
        self.assertEqual(spec.widget_key, "single_buffer_point")
        self.assertEqual(spec.filename, "osm_water_point")

    def test_buffer_point_with_no_keyword_match_has_no_spec(self):
        item = make_indicator(
            {
                "analysis_mode": "use_multi_buffer_point",
                "analysis_scale": "local",
                "id": "some_custom_thing",
                "name": "Some Custom Thing",
            }
        )
        self.assertIsNone(resource_spec_for_indicator(item))

    def test_osm_regional_has_no_spec(self):
        item = make_indicator(
            {
                "analysis_mode": "use_multi_buffer_point",
                "analysis_scale": "regional",
                "id": "pharmacies",
            }
        )
        self.assertIsNone(resource_spec_for_indicator(item))

    def _make_checked_on_indicator(self, attributes):
        """A "Do Not Use" indicator checked on (factor_weighting > 0) in its
        factor's aggregation dialog - status "Required and not configured",
        per JsonTreeItem.getStatus(). Needs a real parent chain, since an
        indicator with no parent is always "Excluded from analysis"."""
        factor = JsonTreeItem(
            ["Factor", "Configured", 1.0, {"id": "factor_1", "dimension_weighting": 1.0}],
            role="factor",
            parent=None,
        )
        indicator = make_indicator(attributes, parent=factor)
        factor.appendChild(indicator)
        return indicator

    def test_do_not_use_checked_on_with_known_hazard_id_infers_environmental_hazard_spec(self):
        item = self._make_checked_on_indicator(
            {"analysis_mode": "Do Not Use", "analysis_scale": "national", "id": "Cyclone", "factor_weighting": 1.0}
        )
        self.assertEqual(item.getStatus(), "Required and not configured")

        spec = resource_spec_for_indicator(item)

        self.assertIsNotNone(spec)
        self.assertEqual(spec.filename, "cyclone_hazard")
        self.assertEqual(spec.mode_to_set, "use_environmental_hazards")

    def test_do_not_use_checked_on_with_unknown_id_has_no_spec(self):
        item = self._make_checked_on_indicator(
            {
                "analysis_mode": "Do Not Use",
                "analysis_scale": "national",
                "id": "some_custom_indicator",
                "factor_weighting": 1.0,
            }
        )
        self.assertEqual(item.getStatus(), "Required and not configured")

        self.assertIsNone(resource_spec_for_indicator(item))

    def test_do_not_use_not_checked_on_has_no_spec_even_with_known_hazard_id(self):
        item = self._make_checked_on_indicator(
            {"analysis_mode": "Do Not Use", "analysis_scale": "national", "id": "cyclone", "factor_weighting": 0.0}
        )
        self.assertNotEqual(item.getStatus(), "Required and not configured")

        self.assertIsNone(resource_spec_for_indicator(item))


class TestResourceIsCached(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_download_all_resources_")
        os.makedirs(os.path.join(self.temp_dir, "study_area"))

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_missing_file_is_not_cached(self):
        item = make_indicator(
            {"analysis_mode": "use_nighttime_lights", "analysis_scale": "local", "id": "nighttime_lights"}
        )
        spec = resource_spec_for_indicator(item)
        self.assertFalse(resource_is_cached(spec, self.temp_dir))

    def test_empty_file_is_not_cached(self):
        item = make_indicator(
            {"analysis_mode": "use_nighttime_lights", "analysis_scale": "local", "id": "nighttime_lights"}
        )
        spec = resource_spec_for_indicator(item)
        open(os.path.join(self.temp_dir, "study_area", "nighttime_lights_annual.tif"), "w").close()
        self.assertFalse(resource_is_cached(spec, self.temp_dir))

    def test_non_empty_file_is_cached(self):
        item = make_indicator(
            {"analysis_mode": "use_nighttime_lights", "analysis_scale": "local", "id": "nighttime_lights"}
        )
        spec = resource_spec_for_indicator(item)
        with open(os.path.join(self.temp_dir, "study_area", "nighttime_lights_annual.tif"), "w") as f:
            f.write("not really a tif but non-empty")
        self.assertTrue(resource_is_cached(spec, self.temp_dir))

    def test_vector_resource_output_path_uses_gpkg_extension(self):
        item = make_indicator(
            {
                "analysis_mode": "use_multi_buffer_point",
                "analysis_scale": "local",
                "id": "pharmacies",
                "name": "Pharmacies",
            }
        )
        spec = resource_spec_for_indicator(item)
        from geest.core.download_all_resources import resource_output_path

        self.assertTrue(resource_output_path(spec, self.temp_dir).endswith("osm_pharmacy.gpkg"))


class TestCollectMissingResources(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_download_all_resources_")
        os.makedirs(os.path.join(self.temp_dir, "study_area"))

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_only_missing_supported_resources_are_returned(self):
        root = build_indicator_tree()
        # Pre-cache the fire hazard raster - it must be excluded from the result.
        with open(os.path.join(self.temp_dir, "study_area", "fire_hazard.tif"), "w") as f:
            f.write("cached")

        missing = collect_missing_resources(root, self.temp_dir)

        missing_ids = {item.attribute("id") for item, _spec in missing}
        self.assertEqual(missing_ids, {"nighttime_lights"})


class TestSyncCachedResourceAttributes(unittest.TestCase):
    """Tests for sync_cached_resource_attributes().

    Covers the gap collect_missing_resources() deliberately leaves open:
    an indicator whose resource file is already cached on disk, but whose
    own source attribute was never set to point at it.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_download_all_resources_sync_")
        os.makedirs(os.path.join(self.temp_dir, "study_area"))

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cached_but_unconfigured_indicator_gets_wired_up(self):
        root = build_indicator_tree()
        with open(os.path.join(self.temp_dir, "study_area", "fire_hazard.tif"), "w") as f:
            f.write("cached")

        configured = sync_cached_resource_attributes(root, self.temp_dir)

        configured_ids = {item.attribute("id") for item, _spec in configured}
        self.assertEqual(configured_ids, {"fire"})
        fire_item = next(item for item, _spec in configured if item.attribute("id") == "fire")
        from urllib.parse import unquote

        self.assertEqual(
            unquote(fire_item.attribute("environmental_hazards_raster")),
            os.path.join(self.temp_dir, "study_area", "fire_hazard.tif"),
        )

    def test_already_configured_indicator_is_left_alone(self):
        from urllib.parse import quote

        root = build_indicator_tree()
        output_path = os.path.join(self.temp_dir, "study_area", "fire_hazard.tif")
        with open(output_path, "w") as f:
            f.write("cached")
        fire_item = next(
            item
            for item in root.getDescendantIndicators(include_completed=True, include_disabled=True)
            if item.attribute("id") == "fire"
        )
        fire_item.setAttribute("environmental_hazards_raster", quote(output_path))

        configured = sync_cached_resource_attributes(root, self.temp_dir)

        self.assertEqual(configured, [])

    def test_indicator_with_no_cached_file_is_left_unconfigured(self):
        root = build_indicator_tree()
        # Nothing cached on disk at all.

        configured = sync_cached_resource_attributes(root, self.temp_dir)

        self.assertEqual(configured, [])

    def test_checked_on_but_disabled_hazard_indicator_is_both_wired_up_and_switched_on(self):
        """A "Do Not Use" indicator checked on in its factor dialog whose
        hazard data is already cached should come out "ready to run": both
        its raster attribute AND its analysis_mode get set."""
        factor = JsonTreeItem(
            ["Factor", "Configured", 1.0, {"id": "factor_1", "dimension_weighting": 1.0}],
            role="factor",
            parent=None,
        )
        cyclone = make_indicator(
            {"analysis_mode": "Do Not Use", "analysis_scale": "national", "id": "cyclone", "factor_weighting": 1.0},
            parent=factor,
        )
        factor.appendChild(cyclone)
        with open(os.path.join(self.temp_dir, "study_area", "cyclone_hazard.tif"), "w") as f:
            f.write("cached")

        configured = sync_cached_resource_attributes(factor, self.temp_dir)

        self.assertEqual([item.attribute("id") for item, _spec in configured], ["cyclone"])
        self.assertEqual(cyclone.attribute("analysis_mode"), "use_environmental_hazards")
        from urllib.parse import unquote

        self.assertEqual(
            unquote(cyclone.attribute("environmental_hazards_raster")),
            os.path.join(self.temp_dir, "study_area", "cyclone_hazard.tif"),
        )

    def test_already_switched_on_hazard_indicator_is_left_alone(self):
        """Once analysis_mode has already been flipped, re-syncing must not
        loop forever re-"configuring" an indicator that is already done."""
        from urllib.parse import quote

        factor = JsonTreeItem(
            ["Factor", "Configured", 1.0, {"id": "factor_1", "dimension_weighting": 1.0}],
            role="factor",
            parent=None,
        )
        output_path = os.path.join(self.temp_dir, "study_area", "cyclone_hazard.tif")
        cyclone = make_indicator(
            {
                "analysis_mode": "use_environmental_hazards",
                "analysis_scale": "national",
                "id": "cyclone",
                "factor_weighting": 1.0,
                "environmental_hazards_raster": quote(output_path),
            },
            parent=factor,
        )
        factor.appendChild(cyclone)
        with open(output_path, "w") as f:
            f.write("cached")

        configured = sync_cached_resource_attributes(factor, self.temp_dir)

        self.assertEqual(configured, [])


def _write_point_gpkg(path, layer_name="pharmacy"):
    """Create a tiny real GeoPackage with one point feature, for OSM-resource tests."""
    from osgeo import ogr, osr

    driver = ogr.GetDriverByName("GPKG")
    ds = driver.CreateDataSource(path)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    layer = ds.CreateLayer(layer_name, srs, geom_type=ogr.wkbPoint)
    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetGeometry(ogr.CreateGeometryFromWkt("POINT (36.8 -1.3)"))
    layer.CreateFeature(feature)
    feature = None
    ds = None


class TestVectorResourceConfiguration(unittest.TestCase):
    """Tests for the OSM/vector-kind resource-configuration path.

    Unlike raster resources (a plain file-path attribute), a vector
    indicator's configured source is an actual QgsProject layer - these
    tests use a real small GeoPackage and the real QgsProject singleton
    (cleaning up afterward) rather than mocking QGIS objects, since the
    whole point is to verify the real add-layer/read-attributes round trip.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_download_all_resources_vector_")
        os.makedirs(os.path.join(self.temp_dir, "study_area"))
        self._added_layer_ids = []

    def tearDown(self):
        import shutil

        from qgis.core import QgsProject

        if self._added_layer_ids:
            QgsProject.instance().removeMapLayers(self._added_layer_ids)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_item_and_spec(self):
        item = make_indicator(
            {
                "analysis_mode": "use_multi_buffer_point",
                "analysis_scale": "local",
                "id": "pharmacies",
                "name": "Pharmacies",
            }
        )
        spec = resource_spec_for_indicator(item)
        return item, spec

    def test_configure_vector_resource_attributes_adds_layer_and_sets_attributes(self):
        from geest.core.download_all_resources import _configure_vector_resource_attributes

        item, spec = self._make_item_and_spec()
        output_path = os.path.join(self.temp_dir, "study_area", "osm_pharmacy.gpkg")
        _write_point_gpkg(output_path)

        self.assertTrue(_configure_vector_resource_attributes(item, spec, output_path))

        layer_id = item.attribute("multi_buffer_point_layer_id")
        self.assertTrue(layer_id)
        self._added_layer_ids.append(layer_id)

        from qgis.core import QgsProject

        self.assertIsNotNone(QgsProject.instance().mapLayer(layer_id))
        self.assertEqual(item.attribute("multi_buffer_point_layer_name"), "osm_pharmacy")
        self.assertIn("osm_pharmacy.gpkg", item.attribute("multi_buffer_point_layer_source"))
        self.assertEqual(item.attribute("multi_buffer_point_layer_provider_type"), "ogr")

    def test_configure_vector_resource_attributes_fails_cleanly_for_invalid_file(self):
        from geest.core.download_all_resources import _configure_vector_resource_attributes

        item, spec = self._make_item_and_spec()
        output_path = os.path.join(self.temp_dir, "study_area", "osm_pharmacy.gpkg")
        with open(output_path, "w") as f:
            f.write("not a real gpkg")

        self.assertFalse(_configure_vector_resource_attributes(item, spec, output_path))
        self.assertIsNone(item.attribute("multi_buffer_point_layer_id"))

    def test_sync_cached_resource_attributes_wires_up_an_already_downloaded_osm_layer(self):
        item, spec = self._make_item_and_spec()
        output_path = os.path.join(self.temp_dir, "study_area", "osm_pharmacy.gpkg")
        _write_point_gpkg(output_path)

        configured = sync_cached_resource_attributes(item, self.temp_dir)

        self.assertEqual(len(configured), 1)
        layer_id = item.attribute("multi_buffer_point_layer_id")
        self._added_layer_ids.append(layer_id)

        # A second sync pass must not re-configure (and must not add a
        # second copy of the layer) - it's already wired up.
        configured_again = sync_cached_resource_attributes(item, self.temp_dir)
        self.assertEqual(configured_again, [])


class _FakeTask:
    """Stand-in for a QgsTask-based downloader: real attributes, mocked signals."""

    def __init__(self, output_path):
        self.output_path = output_path
        self.progress_updated = MagicMock()
        self.error_occurred = MagicMock()
        self.taskCompleted = MagicMock()
        self.taskTerminated = MagicMock()

    def _captured(self, signal):
        """Return the callback connected to one of this task's fake signals."""
        return signal.connect.call_args[0][0]


class TestDownloadAllResourcesController(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_download_all_resources_controller_")
        os.makedirs(os.path.join(self.temp_dir, "study_area"))
        self.task_manager_patch = patch("qgis.core.QgsApplication.taskManager")
        self.mock_task_manager = self.task_manager_patch.start()

    def tearDown(self):
        self.task_manager_patch.stop()
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_successful_download_sets_attribute_and_advances_queue(self):
        item1 = make_indicator(
            {"analysis_mode": "use_nighttime_lights", "analysis_scale": "local", "id": "nighttime_lights"}
        )
        spec1 = resource_spec_for_indicator(item1)
        output_path1 = os.path.join(self.temp_dir, "study_area", "nighttime_lights_annual.tif")
        with open(output_path1, "w") as f:
            f.write("downloaded")
        fake_task1 = _FakeTask(output_path1)
        spec1.build_task = MagicMock(return_value=fake_task1)

        item2 = make_indicator({"analysis_mode": "use_environmental_hazards", "analysis_scale": "local", "id": "fire"})
        spec2 = resource_spec_for_indicator(item2)
        output_path2 = os.path.join(self.temp_dir, "study_area", "fire_hazard.tif")
        with open(output_path2, "w") as f:
            f.write("downloaded")
        fake_task2 = _FakeTask(output_path2)
        spec2.build_task = MagicMock(return_value=fake_task2)

        finished_calls = []
        all_finished_calls = []
        controller = DownloadAllResourcesController(
            items_and_specs=[(item1, spec1), (item2, spec2)],
            working_directory=self.temp_dir,
            extent=None,
            extent_crs_authid="EPSG:4326",
            on_item_finished=lambda item, spec, success, message: finished_calls.append((item, spec, success)),
            on_all_finished=lambda succeeded, failed: all_finished_calls.append((succeeded, failed)),
        )
        controller.start()

        # Simulate the first task completing successfully.
        from urllib.parse import unquote

        fake_task1._captured(fake_task1.taskCompleted)()
        self.assertEqual(unquote(item1.attribute("nighttime_lights_raster")), output_path1)

        # Second task must have been started automatically (queue advanced).
        spec2.build_task.assert_called_once()
        fake_task2._captured(fake_task2.taskCompleted)()
        self.assertEqual(unquote(item2.attribute("environmental_hazards_raster")), output_path2)

        self.assertEqual(len(finished_calls), 2)
        self.assertTrue(all(success for _item, _spec, success in finished_calls))
        self.assertEqual(len(all_finished_calls), 1)
        succeeded, failed = all_finished_calls[0]
        self.assertEqual(len(succeeded), 2)
        self.assertEqual(len(failed), 0)

    def test_failed_download_is_not_double_counted(self):
        item = make_indicator(
            {"analysis_mode": "use_nighttime_lights", "analysis_scale": "local", "id": "nighttime_lights"}
        )
        spec = resource_spec_for_indicator(item)
        fake_task = _FakeTask(os.path.join(self.temp_dir, "study_area", "nighttime_lights_annual.tif"))
        spec.build_task = MagicMock(return_value=fake_task)

        all_finished_calls = []
        controller = DownloadAllResourcesController(
            items_and_specs=[(item, spec)],
            working_directory=self.temp_dir,
            extent=None,
            extent_crs_authid="EPSG:4326",
            on_all_finished=lambda succeeded, failed: all_finished_calls.append((succeeded, failed)),
        )
        controller.start()

        # Simulate a real download failure: error_occurred fires, then
        # taskTerminated (run() returned False) - exactly the sequence
        # every downloader task actually follows.
        fake_task._captured(fake_task.error_occurred)("network error")
        fake_task._captured(fake_task.taskTerminated)()

        self.assertEqual(len(all_finished_calls), 1)
        succeeded, failed = all_finished_calls[0]
        self.assertEqual(len(succeeded), 0)
        self.assertEqual(len(failed), 1, "a single failure must only be recorded once, not once per signal")

    def test_vector_resource_loads_layer_and_sets_layer_attributes(self):
        item = make_indicator(
            {
                "analysis_mode": "use_multi_buffer_point",
                "analysis_scale": "local",
                "id": "pharmacies",
                "name": "Pharmacies",
            }
        )
        spec = resource_spec_for_indicator(item)
        output_path = os.path.join(self.temp_dir, "study_area", "osm_pharmacy.gpkg")
        _write_point_gpkg(output_path)
        fake_task = _FakeTask(output_path)
        spec.build_task = MagicMock(return_value=fake_task)

        all_finished_calls = []
        controller = DownloadAllResourcesController(
            items_and_specs=[(item, spec)],
            working_directory=self.temp_dir,
            extent=None,
            extent_crs_authid="EPSG:4326",
            on_all_finished=lambda succeeded, failed: all_finished_calls.append((succeeded, failed)),
        )
        controller.start()
        fake_task._captured(fake_task.taskCompleted)()

        layer_id = item.attribute("multi_buffer_point_layer_id")
        self.assertTrue(layer_id)
        try:
            from qgis.core import QgsProject

            self.assertIsNotNone(QgsProject.instance().mapLayer(layer_id))
        finally:
            from qgis.core import QgsProject

            QgsProject.instance().removeMapLayers([layer_id])

        succeeded, failed = all_finished_calls[0]
        self.assertEqual(len(succeeded), 1)
        self.assertEqual(len(failed), 0)


if __name__ == "__main__":
    unittest.main()
