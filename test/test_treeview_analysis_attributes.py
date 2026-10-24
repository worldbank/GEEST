# -*- coding: utf-8 -*-
"""Regression tests for JsonTreeModel's analysis-item attribute whitelist.

loadJsonData() reconstructs the "analysis" item's attributes from an
explicit, hardcoded list of known keys whenever the model is (re)built
from saved JSON - any attribute key not in that list is silently dropped,
even if it was correctly computed and saved moments earlier. Two real,
actively-written keys (OpportunitiesByWeeScoreProcessingTask and its
population-score sibling, in opportunities_by_wee_score_processor.py /
opportunities_by_wee_score_population_processor.py) were missing from it,
so "GeoE3 x Opportunities Mask" always showed blank in the tree/report
despite the underlying raster being computed correctly (worldbank/GeoE3
field report, 2026-10-24).
"""
import unittest

from geest.gui.views import JsonTreeModel


class TestAnalysisItemAttributeRoundTrip(unittest.TestCase):
    def _minimal_json_data(self, **overrides):
        data = {"analysis_name": "Test Analysis", "dimensions": []}
        data.update(overrides)
        return data

    def _analysis_item(self, model):
        return model.rootItem.childItems[0]

    def test_geoe3_score_ghsl_masked_result_survives_a_reload(self):
        model = JsonTreeModel(
            self._minimal_json_data(
                geoe3_score_ghsl_masked_result="GeoE3 Score by Opportunities Mask Created OK",
                geoe3_score_ghsl_masked_result_file="/data/Tunisia/geoe3_score_ghsl_masked/geoe3_score_ghsl_masked.vrt",
            )
        )
        analysis_item = self._analysis_item(model)

        self.assertEqual(
            analysis_item.attribute("geoe3_score_ghsl_masked_result"),
            "GeoE3 Score by Opportunities Mask Created OK",
        )
        self.assertEqual(
            analysis_item.attribute("geoe3_score_ghsl_masked_result_file"),
            "/data/Tunisia/geoe3_score_ghsl_masked/geoe3_score_ghsl_masked.vrt",
        )

    def test_geoe3_score_by_population_ghsl_masked_result_survives_a_reload(self):
        model = JsonTreeModel(
            self._minimal_json_data(
                geoe3_score_by_population_ghsl_masked_result=(
                    "GeoE3 Score by Population by Opportunities Mask Created OK"
                ),
                geoe3_score_by_population_ghsl_masked_result_file=(
                    "/data/Tunisia/geoe3_score_by_population_ghsl_masked/geoe3_score_by_population_ghsl_masked.vrt"
                ),
            )
        )
        analysis_item = self._analysis_item(model)

        self.assertEqual(
            analysis_item.attribute("geoe3_score_by_population_ghsl_masked_result"),
            "GeoE3 Score by Population by Opportunities Mask Created OK",
        )
        self.assertEqual(
            analysis_item.attribute("geoe3_score_by_population_ghsl_masked_result_file"),
            "/data/Tunisia/geoe3_score_by_population_ghsl_masked/geoe3_score_by_population_ghsl_masked.vrt",
        )

    def test_a_reload_with_nothing_set_defaults_to_empty_strings_not_missing(self):
        model = JsonTreeModel(self._minimal_json_data())
        analysis_item = self._analysis_item(model)

        self.assertEqual(analysis_item.attribute("geoe3_score_ghsl_masked_result"), "")
        self.assertEqual(analysis_item.attribute("geoe3_score_ghsl_masked_result_file"), "")
        self.assertEqual(analysis_item.attribute("geoe3_score_by_population_ghsl_masked_result"), "")
        self.assertEqual(analysis_item.attribute("geoe3_score_by_population_ghsl_masked_result_file"), "")


if __name__ == "__main__":
    unittest.main()
