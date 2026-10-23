# -*- coding: utf-8 -*-
"""Regression tests: GeoE3 x Population Score must be optional.

calculate_analysis_insights() used to hard-error ("Select a valid
population raster before running the analysis.") and abort the entire
analysis-level post-processing step whenever no population raster/S2S
demographics were configured - even though the population score has
always been an optional extra, same as the opportunities mask right
below it in the same function. It now skips just that one optional
product and continues computing everything else (worldbank/GeoE3 field
report, 2026-10-23).

TreePanel needs a loaded .ui file to construct for real, so these tests
call the unbound method against a lightweight MagicMock stand-in,
matching the established pattern elsewhere in this test suite.
"""
import unittest
from unittest.mock import ANY, MagicMock, patch

from geest.gui.panels.tree_panel import TreePanel


def _make_panel():
    panel = MagicMock()
    panel.working_directory = "/tmp/does-not-need-to-exist-for-this-test"  # nosec B108
    panel.cell_size_m.return_value = 100.0
    return panel


def _make_item(**attributes):
    defaults = {
        "analysis_scale": "national",
        "population_s2s_output_path": None,
        "population_source": "raster",
        "population_layer_source": None,
        "mask_mode": "None",
    }
    defaults.update(attributes)
    item = MagicMock()
    item.attribute.side_effect = lambda key, default=None: defaults.get(key, default)
    return item


class TestPopulationScoreIsOptional(unittest.TestCase):
    @patch("geest.gui.panels.tree_panel.SubnationalAggregationProcessingTask")
    @patch("geest.gui.panels.tree_panel.OpportunitiesByWeeScorePopulationProcessingTask")
    @patch("geest.gui.panels.tree_panel.OpportunitiesByWeeScoreProcessingTask")
    @patch("geest.gui.panels.tree_panel.OpportunitiesMaskProcessor")
    @patch("geest.gui.panels.tree_panel.WEEByPopulationScoreProcessingTask")
    @patch("geest.gui.panels.tree_panel.PopulationRasterProcessingTask")
    def test_no_population_input_skips_population_score_without_erroring(
        self, mock_pop_raster, mock_wee_by_pop, mock_mask, mock_mask_score, mock_mask_score_pop, mock_subnational
    ):
        panel = _make_panel()
        item = _make_item()  # no population_layer_source, no s2s path configured

        result = TreePanel.calculate_analysis_insights(panel, item)

        self.assertNotEqual(result, False, "must not abort just because population input wasn't configured")
        panel.on_processing_error.assert_not_called()
        mock_pop_raster.assert_not_called()
        mock_wee_by_pop.assert_not_called()
        self.assertFalse(
            any(call.args and call.args[0] == "geoe3_by_population" for call in item.setAttribute.call_args_list),
            "geoe3_by_population attribute must never be set when the score was never computed",
        )

    @patch("geest.gui.panels.tree_panel.SubnationalAggregationProcessingTask")
    @patch("geest.gui.panels.tree_panel.OpportunitiesByWeeScorePopulationProcessingTask")
    @patch("geest.gui.panels.tree_panel.OpportunitiesByWeeScoreProcessingTask")
    @patch("geest.gui.panels.tree_panel.OpportunitiesMaskProcessor")
    def test_mask_mode_without_population_input_only_masks_plain_score(
        self, mock_mask, mock_mask_score, mock_mask_score_pop, mock_subnational
    ):
        panel = _make_panel()
        item = _make_item(mask_mode="polygon")

        TreePanel.calculate_analysis_insights(panel, item)

        mock_mask_score.return_value.run.assert_called_once()
        mock_mask_score_pop.assert_not_called()

    @patch("os.path.exists", return_value=True)
    @patch("geest.gui.panels.tree_panel.WEEByPopulationScoreProcessingTask")
    @patch("geest.gui.panels.tree_panel.PopulationRasterProcessingTask")
    def test_configured_population_raster_still_computes_the_score(
        self, mock_pop_raster, mock_wee_by_pop, _mock_exists
    ):
        panel = _make_panel()
        item = _make_item(population_layer_source="/fake/population.tif")
        mock_pop_raster.return_value.run.return_value = True
        mock_wee_by_pop.return_value.run.return_value = True

        TreePanel.calculate_analysis_insights(panel, item)

        mock_pop_raster.return_value.run.assert_called_once()
        mock_wee_by_pop.return_value.run.assert_called_once()
        item.setAttribute.assert_any_call("geoe3_by_population", ANY)


if __name__ == "__main__":
    unittest.main()
