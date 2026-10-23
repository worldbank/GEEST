# -*- coding: utf-8 -*-
"""Unit tests for FixedValueDataSourceWidget (the index_score spinbox used by
contextual-dimension indicators, e.g. Workplace Discrimination's single
hidden child).

Editing index_score here used to leave the indicator's "result"/"result_file"
untouched, so a plain Run (no Shift) on an ancestor factor/dimension would
silently keep using the OLD score's grid value - the indicator is hidden
behind its single-child factor and can't be cleared directly from the tree,
and queue_workflow_task()'s run_only_incomplete skip only looks at the
item's own result_file (worldbank/GeoE3 field report, 2026-10-22).
"""
import unittest

from utilities_for_testing import get_qgis_app

get_qgis_app()

from geest.gui.widgets.datasource_widgets.fixed_value_datasource_widget import (  # noqa: E402
    FixedValueDataSourceWidget,
)


class TestFixedValueDataSourceWidgetInvalidation(unittest.TestCase):
    def _make_widget(self, **attributes):
        attributes.setdefault("index_score", 50)
        return FixedValueDataSourceWidget(widget_key="use_contextual_index_score", attributes=attributes)

    def test_changing_the_score_invalidates_a_completed_indicator(self):
        widget = self._make_widget(
            index_score=50,
            result="contextual_index_score Workflow Completed",
            result_file="study_area/workplace_index/old_run_output.vrt",
        )

        widget.spin_box.setValue(77)

        self.assertEqual(widget.attributes["index_score"], 77)
        self.assertEqual(widget.attributes["result"], "Not Run")
        self.assertEqual(widget.attributes["result_file"], "")

    def test_setting_the_same_score_again_does_not_touch_result(self):
        widget = self._make_widget(
            index_score=50,
            result="contextual_index_score Workflow Completed",
            result_file="study_area/workplace_index/old_run_output.vrt",
        )

        widget.spin_box.setValue(50)

        self.assertEqual(widget.attributes["result"], "contextual_index_score Workflow Completed")
        self.assertEqual(widget.attributes["result_file"], "study_area/workplace_index/old_run_output.vrt")

    def test_initial_construction_does_not_invalidate(self):
        """Loading the widget for an already-completed indicator must not
        itself blank the result - only a genuine user edit afterward does."""
        widget = self._make_widget(
            index_score=77,
            result="contextual_index_score Workflow Completed",
            result_file="study_area/workplace_index/old_run_output.vrt",
        )

        self.assertEqual(widget.attributes["result"], "contextual_index_score Workflow Completed")
        self.assertEqual(widget.attributes["result_file"], "study_area/workplace_index/old_run_output.vrt")


if __name__ == "__main__":
    unittest.main()
