# -*- coding: utf-8 -*-
"""Regression test: JsonTreeModel must round-trip grid_type/analysis_h3_resolution.

Both fields are written once into model.json at study-area creation time
(see geest/gui/panels/create_project_panel.py) but are read back later from
the live tree via JsonTreeModel.to_json() every time
TreePanel.save_json_to_working_directory() runs - which happens throughout
a normal analysis session, not just at creation. JsonTreeModel.loadJsonData()
previously only copied a fixed list of known keys (analysis_scale,
analysis_cell_size_m, ...) into the analysis item's attributes, silently
dropping grid_type/analysis_h3_resolution on the very first save after
creation and reverting an H3-grid project back to the square-grid pyramid
code path.
"""
import unittest

from geest.gui.views.treeview import JsonTreeModel


class TestJsonTreeModelGridTypeRoundtrip(unittest.TestCase):
    """Tests that grid_type/analysis_h3_resolution survive a load/save cycle."""

    def test_h3_grid_type_and_resolution_survive_roundtrip(self):
        model_json = {
            "analysis_name": "Test",
            "analysis_scale": "local",
            "analysis_cell_size_m": 100,
            "grid_type": "h3",
            "analysis_h3_resolution": 10,
            "dimensions": [],
        }
        model = JsonTreeModel(model_json)
        roundtripped = model.to_json()
        self.assertEqual(roundtripped.get("grid_type"), "h3")
        self.assertEqual(roundtripped.get("analysis_h3_resolution"), 10)

    def test_square_project_with_no_grid_type_key_defaults_and_roundtrips(self):
        """Pre-existing projects have no "grid_type" key in model.json at all."""
        model_json = {"analysis_name": "Test", "analysis_scale": "national", "dimensions": []}
        model = JsonTreeModel(model_json)
        roundtripped = model.to_json()
        self.assertEqual(roundtripped.get("grid_type"), "square")
        self.assertIsNone(roundtripped.get("analysis_h3_resolution"))

    def test_grid_type_survives_a_second_roundtrip(self):
        """Simulates two consecutive saves - the exact sequence that dropped
        the key in production: create (grid_type present) -> first save
        (model omits unknown keys -> bug would surface here) -> second
        save (confirms it stays present, not just survives once)."""
        model_json = {
            "analysis_name": "Test",
            "analysis_scale": "local",
            "analysis_cell_size_m": 100,
            "grid_type": "h3",
            "analysis_h3_resolution": 9,
            "dimensions": [],
        }
        model = JsonTreeModel(model_json)
        first_save = model.to_json()
        second_model = JsonTreeModel(first_save)
        second_save = second_model.to_json()
        self.assertEqual(second_save.get("grid_type"), "h3")
        self.assertEqual(second_save.get("analysis_h3_resolution"), 9)


if __name__ == "__main__":
    unittest.main()
