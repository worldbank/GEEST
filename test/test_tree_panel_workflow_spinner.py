# -*- coding: utf-8 -*-
"""Regression test for TreePanel's per-item workflow spinner.

TreePanel is a heavy QWidget that needs a loaded .ui file to construct,
so this calls the unbound on_workflow_started()/_stop_item_spinner()
methods directly against a lightweight MagicMock stand-in carrying a
REAL JsonTreeModel + QTreeView (needed since these methods call real
Qt/model APIs: model.itemIndex(), treeView.rowHeight(),
treeView.setIndexWidget()), matching the pattern in
test_tree_panel_download_all_resources.py.

Guards against a real production bug: self.child_movie/self.parent_movie
were a single shared pair of attributes, not tracked per item. With two
items' start/stop events overlapping (concurrent_tasks > 1, or just two
sequential items racing), stopping one item's spinner could silently stop
a DIFFERENT, still-running item's spinner instead, freezing it on its
last rendered frame (worldbank/GeoE3 field report, 2026-10-24).
"""
import unittest
from unittest.mock import MagicMock, patch

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTreeView

from geest.core.json_tree_item import JsonTreeItem
from geest.gui.panels.tree_panel import TreePanel
from geest.gui.views import JsonTreeModel


class TestWorkflowSpinnerPerItemIsolation(unittest.TestCase):
    def setUp(self):
        self.model = JsonTreeModel({"dimensions": []})
        self.dimension_a = JsonTreeItem(
            ["Dimension A", "Status", 1.0, {"id": "dim_a"}], role="dimension", parent=self.model.rootItem
        )
        self.model.rootItem.appendChild(self.dimension_a)
        self.dimension_b = JsonTreeItem(
            ["Dimension B", "Status", 1.0, {"id": "dim_b"}], role="dimension", parent=self.model.rootItem
        )
        self.model.rootItem.appendChild(self.dimension_b)

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.model)

        self.panel = MagicMock()
        self.panel.model = self.model
        self.panel.treeView = self.tree_view
        self.panel._item_spinners = {}

    def _second_column_widget(self, item):
        index = self.model.itemIndex(item)
        second_column_index = self.model.index(index.row(), 1, index.parent())
        return self.tree_view.indexWidget(second_column_index)

    def test_two_items_get_independent_movie_objects(self):
        TreePanel.on_workflow_started(self.panel, self.dimension_a)
        TreePanel.on_workflow_started(self.panel, self.dimension_b)

        self.assertEqual(set(self.panel._item_spinners.keys()), {self.dimension_a.guid, self.dimension_b.guid})
        movie_a, _ = self.panel._item_spinners[self.dimension_a.guid]
        movie_b, _ = self.panel._item_spinners[self.dimension_b.guid]
        self.assertIsNot(movie_a, movie_b)

    def test_stopping_one_items_spinner_does_not_stop_a_different_items_spinner(self):
        TreePanel.on_workflow_started(self.panel, self.dimension_a)
        TreePanel.on_workflow_started(self.panel, self.dimension_b)

        movie_b, _ = self.panel._item_spinners[self.dimension_b.guid]
        state_before = movie_b.state()
        self.assertIsNotNone(self._second_column_widget(self.dimension_b))

        TreePanel._stop_item_spinner(self.panel, self.dimension_a)

        # dimension_a's spinner is gone and its row widget cleared.
        self.assertNotIn(self.dimension_a.guid, self.panel._item_spinners)
        self.assertIsNone(self._second_column_widget(self.dimension_a))

        # dimension_b's spinner must be completely untouched.
        self.assertIn(self.dimension_b.guid, self.panel._item_spinners)
        still_movie_b, _ = self.panel._item_spinners[self.dimension_b.guid]
        self.assertIs(still_movie_b, movie_b)
        self.assertEqual(still_movie_b.state(), state_before)
        self.assertIsNotNone(self._second_column_widget(self.dimension_b))

    def test_stopping_an_item_twice_is_a_safe_no_op(self):
        TreePanel.on_workflow_started(self.panel, self.dimension_a)

        TreePanel._stop_item_spinner(self.panel, self.dimension_a)
        TreePanel._stop_item_spinner(self.panel, self.dimension_a)

        self.assertNotIn(self.dimension_a.guid, self.panel._item_spinners)


class TestWorkflowSpinnerHiddenSingleChildFactor(unittest.TestCase):
    """Regression test for the "Access to Public Transport" case: a factor
    with exactly one indicator is hidden from the tree (its indicator is
    promoted to appear in its place - see JsonTreeItem.get_effective_visible_children()).

    JsonTreeModel._findIndexByGuid() can locate a hidden item's own
    CHILDREN but never the hidden item's own identity, so
    self.model.itemIndex(hidden_factor) is always invalid. The prior bug:
    on_workflow_started() unconditionally used that invalid index's
    rowHeight() (0, degenerate) to scale the CHILD's own spinner, making
    it invisible even though it was genuinely running - neither the
    child's nor a (non-existent, since there's no separate row) parent
    spinner ever appeared (worldbank/GeoE3 field report, 2026-10-24).
    """

    def setUp(self):
        self.model = JsonTreeModel({"dimensions": []})
        self.dimension = JsonTreeItem(
            ["Accessibility", "Status", 1.0, {"id": "accessibility"}], role="dimension", parent=self.model.rootItem
        )
        self.model.rootItem.appendChild(self.dimension)
        self.factor = JsonTreeItem(
            ["Access to Public Transport", "Status", 1.0, {"id": "access_to_public_transport"}],
            role="factor",
            parent=self.dimension,
        )
        self.dimension.appendChild(self.factor)
        self.factor.set_visibility(False)  # single-child factor: hidden, its indicator is promoted
        self.indicator = JsonTreeItem(
            ["Public Transport Location", "Status", 1.0, {"id": "public_transport_location"}],
            role="indicator",
            parent=self.factor,
        )
        self.factor.appendChild(self.indicator)

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.model)

        self.panel = MagicMock()
        self.panel.model = self.model
        self.panel.treeView = self.tree_view
        self.panel._item_spinners = {}

    def test_hidden_factors_own_index_is_unresolvable(self):
        # Documents the underlying model behaviour on_workflow_started()
        # must tolerate, so this test fails loudly (not silently) if
        # JsonTreeModel's promotion logic ever changes.
        self.assertFalse(self.model.itemIndex(self.factor).isValid())
        self.assertTrue(self.model.itemIndex(self.indicator).isValid())

    def test_child_spinner_uses_its_own_row_height_not_the_invalid_parents(self):
        # rowHeight() legitimately returns 0 for every index in a headless,
        # unmounted QTreeView, so asserting an absolute pixel size proves
        # nothing either way - control it deterministically instead: any
        # valid index reports a real height (42px), any invalid index
        # reports an unmistakably-wrong one (-1px, never a legitimate row
        # height), so the resulting scaled size tells us unambiguously
        # which index's height actually got used.
        with patch.object(self.tree_view, "rowHeight", side_effect=lambda idx: 42 if idx.isValid() else -1):
            TreePanel.on_workflow_started(self.panel, self.indicator)

        child_movie, parent_movie = self.panel._item_spinners[self.indicator.guid]
        expected = child_movie.currentPixmap().size().scaled(42, 42, Qt.AspectRatioMode.KeepAspectRatio)
        self.assertEqual(child_movie.scaledSize(), expected)
        # No separate row exists for the hidden factor, so there is
        # nothing meaningful to show a parent spinner on.
        self.assertIsNone(parent_movie)

    def test_child_spinner_widget_is_set_on_the_indicators_own_promoted_row(self):
        TreePanel.on_workflow_started(self.panel, self.indicator)

        self.assertIsNotNone(self._second_column_widget(self.indicator))

    def _second_column_widget(self, item):
        index = self.model.itemIndex(item)
        second_column_index = self.model.index(index.row(), 1, index.parent())
        return self.tree_view.indexWidget(second_column_index)


class TestWorkflowSpinnerHiddenFactorIsTheWorkflowItemItself(unittest.TestCase):
    """Regression test for a factor-level aggregation job: the WorkflowJob's
    own item is the hidden single-child factor itself, not its indicator.

    TestWorkflowSpinnerHiddenSingleChildFactor above covers an indicator
    whose PARENT factor is hidden. This covers the opposite direction: a
    factor_aggregation job's item IS the hidden factor. Before this fix,
    on_workflow_started(hidden_factor) hit self.model.itemIndex(item)
    invalid at the very top and bailed out with "animation not started"
    before ever reaching any promoted-child handling - no spinner showed
    at all for a single-indicator factor's own aggregation step
    (worldbank/GeoE3 field report, 2026-10-24).
    """

    def setUp(self):
        self.model = JsonTreeModel({"dimensions": []})
        self.dimension = JsonTreeItem(
            ["Place Characterization", "Status", 1.0, {"id": "place_characterization"}],
            role="dimension",
            parent=self.model.rootItem,
        )
        self.model.rootItem.appendChild(self.dimension)
        self.factor = JsonTreeItem(
            ["Education", "Status", 1.0, {"id": "fac_education"}], role="factor", parent=self.dimension
        )
        self.dimension.appendChild(self.factor)
        self.factor.set_visibility(False)  # single-child factor: hidden, its indicator is promoted
        self.indicator = JsonTreeItem(
            ["Education", "Status", 1.0, {"id": "education"}], role="indicator", parent=self.factor
        )
        self.factor.appendChild(self.indicator)

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.model)

        self.panel = MagicMock()
        self.panel.model = self.model
        self.panel.treeView = self.tree_view
        self.panel._item_spinners = {}

    def test_factors_own_index_is_unresolvable(self):
        self.assertFalse(self.model.itemIndex(self.factor).isValid())

    def test_starting_a_workflow_on_the_hidden_factor_itself_animates_its_promoted_child(self):
        TreePanel.on_workflow_started(self.panel, self.factor)

        self.assertIn(self.indicator.guid, self.panel._item_spinners)
        self.assertNotIn(self.factor.guid, self.panel._item_spinners)
        self.assertIsNotNone(self._second_column_widget(self.indicator))

    def test_stopping_a_workflow_on_the_hidden_factor_itself_clears_its_promoted_childs_spinner(self):
        TreePanel.on_workflow_started(self.panel, self.factor)

        TreePanel._stop_item_spinner(self.panel, self.factor)

        self.assertNotIn(self.indicator.guid, self.panel._item_spinners)
        self.assertIsNone(self._second_column_widget(self.indicator))

    def _second_column_widget(self, item):
        index = self.model.itemIndex(item)
        second_column_index = self.model.index(index.row(), 1, index.parent())
        return self.tree_view.indexWidget(second_column_index)


if __name__ == "__main__":
    unittest.main()
