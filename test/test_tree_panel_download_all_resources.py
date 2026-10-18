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
        self.panel._message_bar.pushMessage.assert_called_once()
        args, _kwargs = self.panel._message_bar.pushMessage.call_args
        self.assertIn("Configured 1 indicator(s)", args[1])


if __name__ == "__main__":
    unittest.main()
