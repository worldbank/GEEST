# -*- coding: utf-8 -*-
"""Tests for flood data source parity (S2S ↔ Raster) across scales."""

import unittest

from geest.core.workflows.raster_reclassification_workflow import RasterReclassificationWorkflow
from geest.gui.panels.s2s_panel import S2SPanel


def _resolve_s2s_routing(is_flood: bool, analysis_scale: str, source_attr: str, s2s_configured: bool) -> bool:
    """Mirror the S2S routing decision in RasterReclassificationWorkflow.__init__."""
    source_attr = str(source_attr or "").strip().lower()
    if is_flood:
        use_s2s = source_attr == "s2s" or (source_attr == "" and s2s_configured)
    else:
        use_s2s = analysis_scale == "regional"
    return bool(use_s2s and s2s_configured)


def _flood_prefetch_jobs(model: dict) -> list:
    """Mirror S2SPanel._prepare_s2s_prefetch_jobs filtering for a given model."""
    jobs = []
    regional = model.get("analysis_scale") == "regional"
    for dimension in model.get("dimensions", []):
        for factor in dimension.get("factors", []):
            for indicator in factor.get("indicators", []):
                indicator_id = str(indicator.get("id", "")).strip()
                if not indicator_id:
                    continue
                if int(indicator.get("use_environmental_hazards", 0)) == 1:
                    hazard_id = indicator_id.lower()
                    if hazard_id != "flood" and not regional:
                        continue
                    jobs.append(
                        {
                            "type": "hazard",
                            "indicator_ids": [indicator_id],
                            "filename": f"s2s_environmental_hazards_{hazard_id}",
                        }
                    )
                if regional and int(indicator.get("use_polygon_per_cell", 0)) == 1:
                    if indicator_id.lower() == "education":
                        # Education reads the S2S demographics layer; no separate job.
                        continue
                    jobs.append(
                        {
                            "type": "polygon_per_cell",
                            "indicator_ids": [indicator_id],
                            "filename": f"s2s_polygon_per_cell_{indicator_id.lower()}",
                        }
                    )
    if regional:
        jobs.append({"type": "demographics", "filename": "s2s_demographics"})
    return jobs


class TestFloodPrefetchGate(unittest.TestCase):
    """Tests for _model_has_flood_hazard (S2S prefetch gating for flood)."""

    def _model_with_flood(self, enabled: int = 1) -> dict:
        return {
            "analysis_scale": "national",
            "dimensions": [
                {
                    "factors": [
                        {
                            "indicators": [
                                {
                                    "id": "Flood",
                                    "use_environmental_hazards": enabled,
                                }
                            ]
                        }
                    ]
                }
            ],
        }

    def test_flood_hazard_detected(self):
        """A configured flood hazard indicator is detected."""
        self.assertTrue(S2SPanel._model_has_flood_hazard(self._model_with_flood(1)))

    def test_flood_disabled_not_detected(self):
        """A disabled flood hazard indicator is not detected."""
        self.assertFalse(S2SPanel._model_has_flood_hazard(self._model_with_flood(0)))

    def test_empty_model_not_detected(self):
        """An empty model has no flood hazard."""
        self.assertFalse(S2SPanel._model_has_flood_hazard({}))

    def test_no_environmental_hazards_key(self):
        """A flood indicator without use_environmental_hazards is not detected."""
        model = {
            "dimensions": [
                {
                    "factors": [
                        {
                            "indicators": [
                                {"id": "Flood"},
                            ]
                        }
                    ]
                }
            ]
        }
        self.assertFalse(S2SPanel._model_has_flood_hazard(model))


class TestFloodRouting(unittest.TestCase):
    """Tests for the flood S2S routing decision (source attr vs scale)."""

    def test_flood_s2s_at_national(self):
        """Flood with source=s2s uses S2S at national scale."""
        self.assertTrue(
            _resolve_s2s_routing(is_flood=True, analysis_scale="national", source_attr="s2s", s2s_configured=True)
        )

    def test_flood_raster_at_regional(self):
        """Flood with source=raster does not use S2S at regional scale."""
        self.assertFalse(
            _resolve_s2s_routing(is_flood=True, analysis_scale="regional", source_attr="raster", s2s_configured=True)
        )

    def test_flood_empty_source_derives_from_config(self):
        """Empty flood source derives S2S when an S2S output is configured."""
        self.assertTrue(
            _resolve_s2s_routing(is_flood=True, analysis_scale="national", source_attr="", s2s_configured=True)
        )
        self.assertFalse(
            _resolve_s2s_routing(is_flood=True, analysis_scale="national", source_attr="", s2s_configured=False)
        )

    def test_other_hazard_regional_only(self):
        """Non-flood hazards use S2S at regional scale only."""
        self.assertTrue(
            _resolve_s2s_routing(is_flood=False, analysis_scale="regional", source_attr="s2s", s2s_configured=True)
        )
        self.assertFalse(
            _resolve_s2s_routing(is_flood=False, analysis_scale="national", source_attr="s2s", s2s_configured=True)
        )

    def test_workflow_uses_source_attribute(self):
        """The workflow routing reads the environmental_hazards_source attribute."""
        import inspect

        source = inspect.getsource(RasterReclassificationWorkflow)
        self.assertIn("environmental_hazards_source", source)
        self.assertIn("_use_s2s_grid_path", source)


class TestFloodPrefetchJobFilter(unittest.TestCase):
    """Tests for the S2S prefetch job filter across scales."""

    def _base_model(self, scale: str) -> dict:
        return {
            "analysis_scale": scale,
            "dimensions": [
                {
                    "factors": [
                        {
                            "indicators": [
                                {"id": "Flood", "use_environmental_hazards": 1},
                                {"id": "Fire", "use_environmental_hazards": 1},
                                {"id": "Schools", "use_polygon_per_cell": 1},
                                {"id": "Education", "use_s2s_urban_rural_share": 1},
                            ]
                        }
                    ]
                }
            ],
        }

    def test_regional_includes_all_types(self):
        """Regional prefetch includes hazard, polygon, and demographics jobs."""
        jobs = _flood_prefetch_jobs(self._base_model("regional"))
        types = {j["type"] for j in jobs}
        self.assertTrue(types.issuperset({"hazard", "polygon_per_cell", "demographics"}))
        indicator_ids = [indicator_id for job in jobs for indicator_id in job.get("indicator_ids", [])]
        self.assertNotIn("Education", indicator_ids)

    def test_national_only_flood_hazard(self):
        """National prefetch includes only the flood hazard job (no demographics)."""
        jobs = _flood_prefetch_jobs(self._base_model("national"))
        types = {j["type"] for j in jobs}
        self.assertEqual(types, {"hazard"})
        filenames = [j["filename"] for j in jobs]
        self.assertEqual(filenames, ["s2s_environmental_hazards_flood"])


if __name__ == "__main__":
    unittest.main()
