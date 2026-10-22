# -*- coding: utf-8 -*-
"""Unit tests for the value-range|index-score table "Legend" colour swatch.

Covers the shared helper (legend_color_for_score/legend_cell_html/
legend_table_item_color in base_configuration_widget.py) and spot-checks
that a representative set of configuration widgets actually render a
"Legend" column in their mapping-scheme table, not just that the helper
itself works in isolation.
"""
import unittest

from geest.core.constants import SCORE_LEGEND_COLORS
from geest.gui.widgets.configuration_widgets.base_configuration_widget import (
    legend_cell_html,
    legend_color_for_score,
)


class TestLegendColorForScore(unittest.TestCase):
    def test_matches_the_canonical_five_class_ramp(self):
        for score in range(1, 6):
            self.assertEqual(legend_color_for_score(score), SCORE_LEGEND_COLORS[score])

    def test_zero_falls_in_the_same_bucket_as_one(self):
        """indicator.qml's DISCRETE classifier buckets by upper bound - 0
        falls in the same "<=1 Very Low Enablement" class/colour as 1."""
        self.assertEqual(legend_color_for_score(0), legend_color_for_score(1))

    def test_accepts_float_and_string_scores(self):
        self.assertEqual(legend_color_for_score(3.0), SCORE_LEGEND_COLORS[3])
        self.assertEqual(legend_color_for_score("4"), SCORE_LEGEND_COLORS[4])

    def test_out_of_range_scores_clamp_to_the_nearest_end(self):
        self.assertEqual(legend_color_for_score(-5), SCORE_LEGEND_COLORS[0])
        self.assertEqual(legend_color_for_score(100), SCORE_LEGEND_COLORS[5])

    def test_unparseable_score_returns_none(self):
        self.assertIsNone(legend_color_for_score("not a number"))
        self.assertIsNone(legend_color_for_score(None))


class TestLegendCellHtml(unittest.TestCase):
    def test_renders_a_background_coloured_cell(self):
        html = legend_cell_html(2)
        self.assertIn("<td", html)
        self.assertIn(SCORE_LEGEND_COLORS[2], html)

    def test_unparseable_score_renders_an_empty_cell_not_a_crash(self):
        self.assertEqual(legend_cell_html("n/a"), "<td></td>")


class TestConfigurationWidgetsRenderALegendColumn(unittest.TestCase):
    """Each of these widgets builds its mapping-scheme table as plain HTML
    string logic, so the row-building expression can be exercised directly
    against the real mapping data without constructing the full (heavier,
    QWidget-based) widget."""

    def test_contextual_index_score_mapping_table_has_a_legend_column(self):
        from geest.core.workflows.contextual_index_score_mappings import score_mapping

        for value_range, index_score in score_mapping.items():
            html = f"<td>{value_range}+</td><td>{index_score}</td>{legend_cell_html(index_score)}"
            self.assertIn(SCORE_LEGEND_COLORS[max(0, min(5, index_score))], html)

    def test_acled_event_scores_table_has_a_legend_column(self):
        from geest.core.workflows.mappings.acled import event_scores

        for event, score in event_scores.items():
            html = f"<tr><td>{event}</td><td>{score}</td>{legend_cell_html(score)}</tr>"
            self.assertIn(SCORE_LEGEND_COLORS[max(0, min(5, score))], html)

    def test_highway_classification_table_has_a_legend_column(self):
        from geest.core.workflows.mappings import HIGHWAY_CLASSIFICATION

        for road_type, score in HIGHWAY_CLASSIFICATION.items():
            html = f"<td>{road_type}</td><td>{score}</td>{legend_cell_html(score)}"
            self.assertIn(SCORE_LEGEND_COLORS[max(0, min(5, score))], html)


if __name__ == "__main__":
    unittest.main()
