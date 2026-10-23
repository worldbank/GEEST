# -*- coding: utf-8 -*-
import unittest
from uuid import UUID

from geest.core.json_tree_item import JsonTreeItem


class TestJsonTreeItem(unittest.TestCase):
    """Tests for the JsonTreeItem class."""

    def setUp(self):
        """Set up test data."""
        self.test_data = [
            "Test Item",
            "Configured",
            1.0,
            {  # Attributes dictionary
                "analysis_mode": "use_csv_to_point_layer",
                "default_factor_weighting": 1.0,
                "default_dimension_weighting": 2.0,
                "default_analysis_weighting": 3.0,
                "description": "Test Description",
                "factor_weighting": 1.0,
                "dimension_weighting": 2.0,
                "analysis_weighting": 3.0,
                "id": "FCV",
                "result": "Not Run",
            },
        ]

    def test_creation(self):
        """Test creating a JsonTreeItem instance."""
        item = JsonTreeItem(self.test_data, role="indicator")

        self.assertEqual(item.data(0), "Test Item")
        self.assertEqual(item.role, "indicator")
        self.assertTrue(UUID(item.guid))
        self.assertEqual(item.attributes()["id"], "FCV")

    def test_append_child(self):
        """Test appending child items."""
        parent = JsonTreeItem(self.test_data, role="dimension")
        child = JsonTreeItem(self.test_data, role="factor", parent=parent)

        parent.appendChild(child)
        self.assertEqual(parent.childCount(), 1)
        self.assertIs(parent.child(0), child)
        self.assertIs(child.parent(), parent)

    def test_visibility(self):
        """Test visibility toggling."""
        item = JsonTreeItem(self.test_data, role="indicator")
        self.assertTrue(item.is_visible())

        item.set_visibility(False)
        self.assertFalse(item.is_visible())

        item.set_visibility(True)
        self.assertTrue(item.is_visible())

    def test_is_only_child(self):
        """Test is_only_child method."""
        parent = JsonTreeItem(self.test_data, role="dimension")
        child = JsonTreeItem(self.test_data, role="factor", parent=parent)
        parent.appendChild(child)

        self.assertTrue(child.is_only_child())

        sibling = JsonTreeItem(self.test_data, role="factor", parent=parent)
        parent.appendChild(sibling)
        self.assertFalse(child.is_only_child())

    def test_internal_pointer(self):
        """Test internalPointer method."""
        item = JsonTreeItem(self.test_data, role="indicator")
        self.assertEqual(item.internalPointer(), item.guid)

    def test_icons(self):
        """Test getIcon method for different roles."""
        dimension = JsonTreeItem(self.test_data, role="dimension")
        factor = JsonTreeItem(self.test_data, role="factor")
        indicator = JsonTreeItem(self.test_data, role="indicator")

        self.assertIsNotNone(dimension.getIcon())
        self.assertIsNotNone(factor.getIcon())
        self.assertIsNotNone(indicator.getIcon())

    def test_grid_column_name(self):
        """gridColumnName() must match the sanitisation add_model_columns_to_grid()
        applies when the column is first created: spaces and hyphens both
        become underscores, with the dim_/fac_ role prefix workflows use
        for their own layer_id (indicators keep the bare, unprefixed id)."""
        data = [
            "Workplace Discrimination",
            "Configured",
            1.0,
            {"id": "Workplace-Discrimination Risk"},
        ]
        dimension = JsonTreeItem(data, role="dimension")
        factor = JsonTreeItem(data, role="factor")
        indicator = JsonTreeItem(data, role="indicator")

        self.assertEqual(dimension.gridColumnName(), "dim_workplace_discrimination_risk")
        self.assertEqual(factor.gridColumnName(), "fac_workplace_discrimination_risk")
        self.assertEqual(indicator.gridColumnName(), "workplace_discrimination_risk")

    def test_invalidate_ancestors_clears_every_ancestor_up_to_the_root(self):
        """A factor/dimension aggregate is only as fresh as the children it
        was computed from - if a child indicator is re-run afterwards,
        every ancestor's cached result is stale even though it may still
        show "Completed successfully" (worldbank/GeoE3 field report,
        2026-10-23: a factor aggregated hours before its own child
        indicator was re-run stayed stuck at a stale value forever)."""
        dimension = JsonTreeItem(
            ["Dimension", "Configured", 1.0, {"id": "dim", "result": "dimension_aggregation Workflow Completed"}],
            role="dimension",
        )
        factor = JsonTreeItem(
            ["Factor", "Configured", 1.0, {"id": "fac", "result": "factor_aggregation Workflow Completed"}],
            role="factor",
            parent=dimension,
        )
        indicator = JsonTreeItem(
            ["Indicator", "Configured", 1.0, {"id": "ind", "result": "multi_buffer_point Workflow Completed"}],
            role="indicator",
            parent=factor,
        )
        dimension.appendChild(factor)
        factor.appendChild(indicator)

        indicator.invalidateAncestors()

        self.assertEqual(factor.attribute("result"), "")
        self.assertEqual(dimension.attribute("result"), "")
        # The indicator's own, freshly-computed result must be untouched -
        # only ANCESTORS are invalidated, never the item that just ran.
        self.assertEqual(indicator.attribute("result"), "multi_buffer_point Workflow Completed")

    def test_invalidate_ancestors_on_a_root_item_is_a_safe_no_op(self):
        root = JsonTreeItem(["Analysis", "Configured", 1.0, {"id": "analysis"}], role="analysis")
        root.invalidateAncestors()  # must not raise - no parent to invalidate

    def test_fonts(self):
        """Test getFont method for different roles."""
        dimension = JsonTreeItem(self.test_data, role="dimension")
        factor = JsonTreeItem(self.test_data, role="factor")
        indicator = JsonTreeItem(self.test_data, role="indicator")

        self.assertTrue(dimension.getFont().bold())
        self.assertTrue(factor.getFont().italic())
        self.assertFalse(indicator.getFont().bold())
        self.assertFalse(indicator.getFont().italic())

    def test_attributes(self):
        """Test attribute retrieval and updates."""
        item = JsonTreeItem(self.test_data, role="indicator")
        self.assertEqual(item.attribute("id"), "FCV")
        self.assertEqual(item.attribute("nonexistent", "default"), "default")

    def test_set_attributes(self):
        """Test setAttribute and setAttributes methods."""
        item = JsonTreeItem(self.test_data, role="indicator")

        # Test setAttribute
        item.setAttribute("new_key", "new_value")
        self.assertEqual(item.attribute("new_key"), "new_value")

        # Test setAttributes
        new_attributes = {
            "key1": "value1",
            "key2": "value2",
        }
        item.setAttributes(new_attributes)
        self.assertEqual(item.attributes(), new_attributes)

    def test_attributes_as_markdown(self):
        """Test attributesAsMarkdown method."""
        item = JsonTreeItem(self.test_data, role="indicator")
        markdown = item.attributesAsMarkdown()
        self.assertIn("Key", markdown)
        self.assertIn("Value", markdown)
        self.assertIn("id", markdown)

    def test_child_count(self):
        """Test childCount method."""
        parent = JsonTreeItem(self.test_data, role="dimension")
        child1 = JsonTreeItem(self.test_data, role="factor", parent=parent)
        child2 = JsonTreeItem(self.test_data, role="factor", parent=parent)

        parent.appendChild(child1)
        parent.appendChild(child2)

        self.assertEqual(parent.childCount(), 2)

    def test_recursive_child_count(self):
        """Test childCount with recursive flag."""
        parent = JsonTreeItem(self.test_data, role="dimension")
        child1 = JsonTreeItem(self.test_data, role="factor", parent=parent)
        child2 = JsonTreeItem(self.test_data, role="factor", parent=parent)
        grandchild = JsonTreeItem(self.test_data, role="indicator", parent=child1)

        parent.appendChild(child1)
        parent.appendChild(child2)
        child1.appendChild(grandchild)

        self.assertEqual(parent.childCount(recursive=True), 3)

    def test_clear(self):
        """Test clear method."""
        item = JsonTreeItem(self.test_data, role="indicator")
        item.clear()
        attributes = item.attributes()
        self.assertEqual(attributes["result"], "Not Run")
        self.assertEqual(attributes["result_file"], "")

    def test_enable_disable(self):
        """Test enable and disable methods."""
        item = JsonTreeItem(self.test_data, role="indicator")
        item.disable()
        self.assertEqual(item.attribute("analysis_mode"), "Do Not Use")
        self.assertEqual(item.attribute("factor_weighting"), 0.0)

        item.enable()
        self.assertEqual(item.attribute("analysis_mode"), "")
        self.assertEqual(item.attribute("factor_weighting"), 1.0)

    def test_disable_factor_preserves_exclusion_state(self):
        """Test disabling a factor records its zero weighting and mode."""
        factor = JsonTreeItem(self.test_data, role="factor")

        factor.disable()

        self.assertEqual(factor.attribute("analysis_mode"), "Do Not Use")
        self.assertEqual(factor.attribute("dimension_weighting"), 0.0)

    def test_update_weighting(self):
        """Test updating weighting methods."""
        parent = JsonTreeItem(self.test_data, role="dimension")
        child = JsonTreeItem(self.test_data, role="factor", parent=parent)

        parent.appendChild(child)
        child.updateFactorWeighting(child.guid, 2.5)
        self.assertEqual(float(child.attribute("dimension_weighting")), 2.5)

    def test_status(self):
        """Test getStatus method."""
        # Setup item with default attributes
        item = JsonTreeItem(self.test_data, role="indicator")
        item.setAttribute("factor_weighting", 1.0)  # Ensure valid weight
        item.enable()
        self.assertEqual(item.getStatus(), "Excluded from analysis", msg=item.attributesAsMarkdown())

        # Test "Excluded from analysis"
        item.setAttribute("factor_weighting", 0.0)
        self.assertEqual(item.getStatus(), "Excluded from analysis", msg=item.attributesAsMarkdown())

        # Test "Completed successfully"
        item.setAttribute("result", "Workflow Completed")
        item.setAttribute("result_file", "test_file.tif")
        self.assertEqual(item.getStatus(), "Completed successfully", msg=item.attributesAsMarkdown())

        # Test "Workflow failed"
        item.setAttribute("analysis_mode", "use_csv_to_point_layer")
        item.setAttribute("result", "Error occurred")
        self.assertEqual(item.getStatus(), "Excluded from analysis", msg=item.attributesAsMarkdown())

        # Test "Required and not configured"
        item.setAttribute("analysis_mode", "Do Not Use")
        item.setAttribute("factor_weighting", 1.0)
        self.assertEqual(item.getStatus(), "Excluded from analysis", msg=item.attributesAsMarkdown())

        # Test "Not configured (optional)"
        item.setAttribute("factor_weighting", 0.0)
        self.assertEqual(item.getStatus(), "Excluded from analysis", msg=item.attributesAsMarkdown())

        # Test recursive weight checks
        parent = JsonTreeItem(self.test_data, role="factor")
        parent.setAttribute("dimension_weighting", 0.0)
        item.parentItem = parent
        self.assertEqual(item.getStatus(), "Excluded from analysis", msg=item.attributesAsMarkdown())

    def test_paths(self):
        """Test getPaths method."""
        dimension = JsonTreeItem(self.test_data, role="dimension")
        factor = JsonTreeItem(self.test_data, role="factor", parent=dimension)
        indicator = JsonTreeItem(self.test_data, role="indicator", parent=factor)

        dimension.appendChild(factor)
        factor.appendChild(indicator)

        self.assertEqual(indicator.getPaths(), ["fcv", "fcv", "fcv"])

    def test_get_descendant_indicators(self):
        """Test getDescendantIndicators method."""
        dimension = JsonTreeItem(self.test_data, role="dimension")
        factor = JsonTreeItem(self.test_data, role="factor", parent=dimension)
        indicator = JsonTreeItem(self.test_data, role="indicator", parent=factor)
        indicator.setAttribute("result", "Completed successfully")

        dimension.appendChild(factor)
        factor.appendChild(indicator)

        descendants = dimension.getDescendantIndicators()
        self.assertEqual(len(descendants), 1)
        self.assertIs(descendants[0], indicator)

    def test_get_descendant_dimensions(self):
        """Test getDescendantDimensions method."""
        analysis = JsonTreeItem(self.test_data, role="analysis")
        dimension = JsonTreeItem(self.test_data, role="dimension", parent=analysis)
        dimension.setAttribute("result", "Completed successfully")
        dimension.enable()

        # Append to establish hierarchy
        analysis.appendChild(dimension)

        # Debugging: ensure childItems is populated
        self.assertEqual(len(analysis.childItems), 1)

        descendants = analysis.getDescendantDimensions(include_completed=False, include_disabled=True)
        self.assertEqual(len(descendants), 1)
        self.assertIs(descendants[0], dimension)

    def test_get_descendant_factors(self):
        """Test getDescendantFactors method."""
        dimension = JsonTreeItem(self.test_data, role="dimension")
        factor = JsonTreeItem(self.test_data, role="factor", parent=dimension)
        factor.setAttribute("result", "Completed successfully")
        factor.enable()

        # Append to establish hierarchy
        dimension.appendChild(factor)

        # Debugging: ensure childItems is populated
        self.assertEqual(len(dimension.childItems), 1)

        descendants = dimension.getDescendantFactors(include_completed=False, include_disabled=True)
        self.assertEqual(len(descendants), 1)
        self.assertIs(descendants[0], factor)

    def test_get_item_by_guid(self):
        """Test getItemByGuid method."""
        parent = JsonTreeItem(self.test_data, role="dimension")
        child = JsonTreeItem(self.test_data, role="factor", parent=parent)
        parent.appendChild(child)

        found_item = parent.getItemByGuid(child.guid)
        self.assertIs(found_item, child)


if __name__ == "__main__":
    unittest.main()
