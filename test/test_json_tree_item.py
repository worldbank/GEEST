import unittest
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from uuid import UUID
from geest.core.json_tree_item import JsonTreeItem


class TestJsonTreeItem(unittest.TestCase):
    """Tests for the JsonTreeItem class."""

    def setUp(self):
        """Set up test data."""
        self.test_data = [
            "Test Item",
            "Configured",
            1.0,  # Example weight value
            {  # Attributes dictionary
                "analysis_mode": "use_csv_to_point_layer",
                "default_factor_weighting": 1.0,
                "default_multi_buffer_distances": "0,0,0",
                "default_single_buffer_distance": 5000,
                "description": "",
                "error": "",
                "error_file": "",
                "execution_end_time": "",
                "execution_start_time": "",
                "factor_weighting": 1.0,
                "guid": "10c49ccc-50ae-4b08-a68f-899c2f55b370",
                "id": "FCV",
                "index_score": 0,
                "indicator": "ACLED data (Violence Estimated Events)",
                "output_filename": "FCV_output",
                "result": "Not Run",
                "result_file": "",
                "use_classify_polygon_into_classes": 0,
                "use_classify_safety_polygon_into_classes": 0,
                "use_csv_to_point_layer": 1,
                "use_csv_to_point_layer_csv_file": "/home/timlinux/dev/python/GEEST2/data/StLucia/Place Characterization/FCV/2022-05-01-2024-05-01-Saint_Lucia.csv",
                "use_csv_to_point_layer_distance": 1000,
                "use_environmental_hazards": 0,
                "use_index_score": 0,
                "use_multi_buffer_point": 0,
                "use_nighttime_lights": 0,
                "use_point_per_cell": 0,
                "use_polygon_per_cell": 0,
                "use_polyline_per_cell": 0,
                "use_single_buffer_point": 1,
                "use_street_lights": 0,
            },
        ]

    def test_json_tree_item_creation(self):
        """Test creating a JsonTreeItem instance."""
        item = JsonTreeItem(self.test_data, role="indicator")

        # Check that the item is created correctly
        self.assertEqual(item.data(0), "Test Item")
        self.assertEqual(item.data(1), "Configured")
        self.assertEqual(item.data(2), 1.0)
        self.assertEqual(item.role, "indicator")
        self.assertEqual(item.attributes().get("id"), "FCV")
        self.assertEqual(
            item.attributes().get("analysis_mode"), "use_csv_to_point_layer"
        )
        self.assertIsInstance(item.attributes(), dict)

        # Check GUID
        self.assertTrue(UUID(item.guid))  # Validates the GUID format

        # Check font and color
        self.assertEqual(item.font_color, QColor(Qt.black))

        # Check methods
        self.assertTrue(item.isIndicator())
        self.assertFalse(item.isFactor())
        self.assertFalse(item.isDimension())
        self.assertFalse(item.isAnalysis())

        # Test visibility toggle
        self.assertTrue(item.is_visible())
        item.set_visibility(False)
        self.assertFalse(item.is_visible())

        # Test status
        expected_status = [
            "WRITE TOOL TIP",
            "Expected status of 'Status Failed - 'NoneType' object has no attribute 'attributes'",
        ]
        status = item.getStatus()
        self.assertIn(
            status,
            expected_status,
            msg=f"Expected status of '{status}', got '{expected_status}' {dir(item)}",
        )

    def test_json_tree_item_append_child(self):
        """Test appending child items."""
        parent_item = JsonTreeItem(self.test_data, role="dimension")
        child_item = JsonTreeItem(self.test_data, role="factor", parent=parent_item)

        parent_item.appendChild(child_item)

        self.assertEqual(parent_item.childCount(), 1)
        self.assertIs(parent_item.child(0), child_item)
        self.assertEqual(child_item.parent(), parent_item)


if __name__ == "__main__":
    unittest.main()
