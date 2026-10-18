# -*- coding: utf-8 -*-
"""Regression test: on_workflow_completed() shows feedback before the slow map-add step.

TreePanel is a heavy QWidget that needs a loaded .ui file and a full
JsonTreeModel to construct, so this test calls the unbound method against
a lightweight MagicMock stand-in instead of a real TreePanel, matching the
pattern in test_tree_panel_pyramid_migration.py.

Building a pyramid layer group is synchronous (one QgsVectorLayer + QML
style load per exposed level) and runs on the main thread for every
completed item during a batch run ("Run all"), with no progress feedback
of its own - the status label must be updated (and the event loop pumped
so it actually repaints) before that blocking call starts, so a long batch
run doesn't look frozen at the same percentage for every item in it.
"""
import unittest
from unittest.mock import MagicMock, patch

from geest.gui.panels.tree_panel import TreePanel


class TestOnWorkflowCompletedShowsProgressBeforeAddingToMap(unittest.TestCase):
    def setUp(self):
        self.panel = MagicMock()
        self.panel.items_to_run = 10
        self.panel.overall_progress_bar.value.return_value = 1

        self.item = MagicMock()
        self.item.role = "indicator"
        self.item.data.return_value = "Fire Hazards"
        self.item.attribute.side_effect = lambda key, default=None: {"id": "fire"}.get(key, default)

        self.add_pyramid_patch = patch("geest.gui.panels.tree_panel.add_pyramid_layer_to_map")
        self.mock_add_pyramid = self.add_pyramid_patch.start()
        self.process_events_patch = patch("geest.gui.panels.tree_panel.QApplication.processEvents")
        self.mock_process_events = self.process_events_patch.start()

    def tearDown(self):
        self.add_pyramid_patch.stop()
        self.process_events_patch.stop()

    def test_status_label_is_updated_and_repainted_before_the_blocking_call(self):
        order = []
        self.panel.status_label.setText.side_effect = lambda text: order.append(("setText", text))
        self.mock_process_events.side_effect = lambda: order.append(("processEvents",))
        self.mock_add_pyramid.side_effect = lambda *a, **k: order.append(("add_pyramid_layer_to_map",))

        TreePanel.on_workflow_completed(self.panel, self.item, True)

        self.assertIn(("setText", "Adding Fire Hazards to map..."), order)
        self.assertIn(("processEvents",), order)
        self.assertIn(("add_pyramid_layer_to_map",), order)
        self.assertLess(
            order.index(("setText", "Adding Fire Hazards to map...")),
            order.index(("add_pyramid_layer_to_map",)),
            "status label must be updated before the slow map-building call starts",
        )
        self.assertLess(
            order.index(("processEvents",)),
            order.index(("add_pyramid_layer_to_map",)),
            "the event loop must be pumped so the label repaints before the slow call blocks it",
        )


if __name__ == "__main__":
    unittest.main()
