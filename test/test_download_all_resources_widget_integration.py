# -*- coding: utf-8 -*-
"""End-to-end check: an attribute set by download_all_resources is read back by its widget.

The data-layer tests in test_download_all_resources.py and the GUI-wiring
tests in test_tree_panel_download_all_resources.py each verify half of the
"download all resources" pipeline in isolation; neither proves the two
halves actually agree on what to write/read. This test chains them: build
a real DownloadAllResourcesController, drive a fake completed download
task through it exactly as test_download_all_resources.py does, then
construct the REAL EnvironmentalHazardsRasterDataSourceWidget against the
resulting item attributes and assert it shows the downloaded file - the
same thing double-clicking the indicator's properties dialog would do.
"""
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from geest.core import JsonTreeItem
from geest.core.download_all_resources import DownloadAllResourcesController, resource_spec_for_indicator
from geest.gui.widgets.datasource_widgets.environmental_hazards_raster_datasource_widget import (
    EnvironmentalHazardsRasterDataSourceWidget,
)


class _FakeTask:
    """Stand-in for a QgsTask-based downloader: real attributes, mocked signals."""

    def __init__(self, output_path):
        self.output_path = output_path
        self.progress_updated = MagicMock()
        self.error_occurred = MagicMock()
        self.taskCompleted = MagicMock()
        self.taskTerminated = MagicMock()

    def _captured(self, signal):
        return signal.connect.call_args[0][0]


class TestDownloadedAttributeIsVisibleInTheWidget(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_download_widget_integration_")
        os.makedirs(os.path.join(self.temp_dir, "study_area"))
        self.task_manager_patch = patch("qgis.core.QgsApplication.taskManager")
        self.task_manager_patch.start()

    def tearDown(self):
        self.task_manager_patch.stop()
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_fire_hazard_download_populates_the_properties_dialog_widget(self):
        attributes = {"analysis_mode": "use_environmental_hazards", "analysis_scale": "local", "id": "Fire"}
        item = JsonTreeItem(["Fire Hazards", "Not Configured", 1.0, attributes], role="indicator", parent=None)
        spec = resource_spec_for_indicator(item)
        self.assertIsNotNone(spec)
        self.assertEqual(spec.filename, "fire_hazard")

        output_path = os.path.join(self.temp_dir, "study_area", "fire_hazard.tif")
        with open(output_path, "w") as f:
            f.write("downloaded")
        fake_task = _FakeTask(output_path)
        spec.build_task = MagicMock(return_value=fake_task)

        controller = DownloadAllResourcesController(
            items_and_specs=[(item, spec)],
            working_directory=self.temp_dir,
            extent=None,
            extent_crs_authid="EPSG:4326",
        )
        controller.start()
        fake_task._captured(fake_task.taskCompleted)()

        # Exactly what double-clicking the indicator opens: a fresh widget
        # built from the item's current (post-download) attributes.
        widget = EnvironmentalHazardsRasterDataSourceWidget(
            widget_key="environmental_hazards", attributes=item.attributes()
        )
        self.assertEqual(widget.raster_line_edit.text(), output_path)


if __name__ == "__main__":
    unittest.main()
