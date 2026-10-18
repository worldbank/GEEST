# -*- coding: utf-8 -*-
"""Regression tests for TreePanel.download_all_resources().

TreePanel is a heavy QWidget that needs a loaded .ui file and a full
JsonTreeModel to construct, so these tests call the unbound method
against a lightweight MagicMock stand-in instead of a real TreePanel,
matching the pattern in test_tree_panel_pyramid_migration.py.

Guards against a real production bug: the early-exit paths called
self.show_message(...), a method TreePanel never defined (every other
message in this file goes through iface.messageBar().pushMessage() or
self._message_bar.pushMessage()) - every user hitting "no working
directory set" or "nothing to download" got an AttributeError traceback
instead of a message. These tests call the real early-exit code paths and
assert no exception escapes.
"""
import unittest
from unittest.mock import MagicMock, patch

from geest.gui.panels.tree_panel import TreePanel


class TestDownloadAllResourcesEarlyExits(unittest.TestCase):
    """Tests for the early-return branches of TreePanel.download_all_resources()."""

    def setUp(self):
        self.panel = MagicMock()
        self.panel._message_bar = MagicMock()

    def test_no_working_directory_pushes_message_without_crashing(self):
        self.panel.working_directory = None

        TreePanel.download_all_resources(self.panel)

        self.panel._message_bar.pushMessage.assert_called_once()
        args, _kwargs = self.panel._message_bar.pushMessage.call_args
        self.assertIn("No working directory", args[1])

    @patch("geest.core.download_all_resources.sync_cached_resource_attributes", return_value=[])
    @patch("geest.core.download_all_resources.collect_missing_resources", return_value=[])
    def test_nothing_missing_pushes_message_without_crashing(self, _mock_collect, _mock_sync):
        self.panel.working_directory = "/tmp/does-not-need-to-exist-for-this-path"  # nosec B108

        TreePanel.download_all_resources(self.panel)

        self.panel._message_bar.pushMessage.assert_called_once()
        args, _kwargs = self.panel._message_bar.pushMessage.call_args
        self.assertIn("already cached", args[1])

    @patch("geest.core.download_all_resources.sync_cached_resource_attributes")
    @patch("geest.core.download_all_resources.collect_missing_resources", return_value=[])
    def test_auto_configured_items_are_reported_and_saved(self, _mock_collect, mock_sync):
        self.panel.working_directory = "/tmp/does-not-need-to-exist-for-this-path"  # nosec B108
        mock_sync.return_value = [(MagicMock(), MagicMock())]

        TreePanel.download_all_resources(self.panel)

        self.panel.save_json_to_working_directory.assert_called_once()
        self.panel._refresh_tree_view.assert_called_once()
        self.panel._message_bar.pushMessage.assert_called_once()
        args, _kwargs = self.panel._message_bar.pushMessage.call_args
        self.assertIn("Configured 1 indicator(s)", args[1])

    @patch("geest.core.download_all_resources.sync_cached_resource_attributes", return_value=[])
    @patch("geest.core.download_all_resources.collect_missing_resources", return_value=[])
    def test_nothing_configured_does_not_refresh_the_tree(self, _mock_collect, _mock_sync):
        self.panel.working_directory = "/tmp/does-not-need-to-exist-for-this-path"  # nosec B108

        TreePanel.download_all_resources(self.panel)

        self.panel._refresh_tree_view.assert_not_called()


class TestRefreshTreeView(unittest.TestCase):
    """Tests for TreePanel._refresh_tree_view().

    Must use layoutChanged, never beginResetModel()/endResetModel() - a
    full model reset collapses every expanded tree node and clears the
    selection/scroll position, which is exactly what must NOT happen while
    a batch download is highlighting items one at a time.
    """

    def test_emits_layout_changed_and_repaints_without_resetting_the_model(self):
        panel = MagicMock()

        TreePanel._refresh_tree_view(panel)

        panel.model.layoutChanged.emit.assert_called_once()
        panel.model.beginResetModel.assert_not_called()
        panel.model.endResetModel.assert_not_called()
        panel.treeView.viewport.return_value.update.assert_called_once()


class TestDownloadAllResourcesSpinner(unittest.TestCase):
    """Tests that download_all_resources() highlights each item while it downloads.

    Reuses the same animated-throbber mechanism (on_workflow_started() /
    _stop_item_spinner()) a normal single-indicator run already shows on
    its tree row, instead of leaving the tree showing no per-item feedback
    during a batch download.
    """

    def setUp(self):
        self.panel = MagicMock()
        self.panel._message_bar = MagicMock()
        self.panel.working_directory = "/tmp/does-not-need-to-exist-for-this-path"  # nosec B108

        self.item = MagicMock()
        self.spec = MagicMock()
        self.spec.label = "Fire (Environmental Hazard)"

        self.sync_patch = patch("geest.core.download_all_resources.sync_cached_resource_attributes", return_value=[])
        self.sync_patch.start()
        self.collect_patch = patch(
            "geest.core.download_all_resources.collect_missing_resources",
            return_value=[(self.item, self.spec)],
        )
        self.collect_patch.start()

        self.captured = {}

        def fake_controller(*args, **kwargs):
            self.captured.update(kwargs)
            return MagicMock()

        self.controller_patch = patch(
            "geest.core.download_all_resources.DownloadAllResourcesController", side_effect=fake_controller
        )
        self.controller_patch.start()

        bbox_layer = MagicMock()
        bbox_layer.isValid.return_value = True
        bbox_layer.featureCount.return_value = 1
        self.vector_layer_patch = patch("geest.gui.panels.tree_panel.QgsVectorLayer", return_value=bbox_layer)
        self.vector_layer_patch.start()

    def tearDown(self):
        self.sync_patch.stop()
        self.collect_patch.stop()
        self.controller_patch.stop()
        self.vector_layer_patch.stop()

    def test_item_started_shows_the_spinner_and_item_finished_clears_it(self):
        TreePanel.download_all_resources(self.panel)

        self.captured["on_item_started"](self.item, self.spec)
        self.panel.on_workflow_started.assert_called_once_with(self.item)
        self.panel._stop_item_spinner.assert_not_called()

        self.captured["on_item_finished"](self.item, self.spec, True, "/tmp/fire_hazard.tif")  # nosec B108
        self.panel._stop_item_spinner.assert_called_once_with(self.item)


if __name__ == "__main__":
    unittest.main()
