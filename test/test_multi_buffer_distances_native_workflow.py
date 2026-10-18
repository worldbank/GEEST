# -*- coding: utf-8 -*-
import os
import unittest

from qgis.core import (
    QgsFeedback,
    QgsProcessingContext,
)
from utilities_for_testing import prepare_fixtures

from geest.core import JsonTreeItem
from geest.core.workflows import MultiBufferDistancesNativeWorkflow


class TestMultiBufferDistancesNativeWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up shared resources for the test suite."""

        cls.test_data_directory = prepare_fixtures()
        cls.working_directory = os.path.join(cls.test_data_directory, "wee_score")

        cls.context = QgsProcessingContext()
        cls.feedback = QgsFeedback()

    def setUp(self):
        self.study_area_gpkg_path = (f"{self.working_directory}/study_area/study_area.gpkg",)
        self.road_network_layer_path = os.path.join(
            os.path.dirname(__file__),
            "test_data",
            "network_analysis",
            "network_layer.shp",
        )
        self.points_layer_path = os.path.join(
            os.path.dirname(__file__),
            "test_data",
            "network_analysis",
            "points.shp",
        )

        self.analysis_item = JsonTreeItem({"id": "analysis_1"}, role="analysis", parent=None)
        self.dimension_item = JsonTreeItem({"id": "dimension_1"}, role="dimension", parent=self.analysis_item)
        self.factor_item = JsonTreeItem({"id": "factor_1"}, role="factor", parent=self.dimension_item)
        self.test_data = [
            "Test Item TestMultiBufferDistancesNativeWorkflow",
            "Configured",
            1.0,
            {  # attributes dictionary
                "analysis_mode": "use_multibuffer_point",
                "default_factor_weighting": 1.0,
                "default_dimension_weighting": 1.0,
                "default_analysis_weighting": 1.0,
                "description": "Multibuffer Native Test",
                "factor_weighting": 1.0,
                "dimension_weighting": 1.0,
                "analysis_weighting": 1.0,
                "id": "street_crossings",
                "result": "Not Run",
                "multi_buffer_travel_distances": "1000,2000,3000",
                "multi_buffer_point_shapefile": self.points_layer_path,
                "multi_buffer_travel_mode": "Walking",
                "multi_buffer_travel_units": "Distance",
                "road_network_layer_path": self.road_network_layer_path,
            },
        ]
        self.indicator_item = JsonTreeItem(
            self.test_data,
            role="indicator",
            parent=self.factor_item,
        )

    def test_run(self):
        """Test creating a running the workflow."""

        # Assign the top-level item
        self.working_directory = self.working_directory
        self.workflow = MultiBufferDistancesNativeWorkflow(
            item=self.indicator_item,
            cell_size_m=10.0,
            analysis_scale="local",
            feedback=self.feedback,
            context=self.context,
            working_directory=self.working_directory,
        )
        self.workflow.execute()

    def test_run_no_isochrones_uses_zero_score_fallback(self):
        """No isochrones (e.g. no points reachable from the road network)
        should produce a neutral 0-score in the grid rather than an error.

        Regression test for issue #381. Local/national indicators no longer
        rasterize per area at all (visualization comes from the pyramid
        instead - see geest.core.grid_pyramid_utils), so the fallback is now
        verified against the grid column directly rather than a raster file.
        """
        from geest.core.grid_column_utils import get_grid_column_values

        workflow = MultiBufferDistancesNativeWorkflow(
            item=self.indicator_item,
            cell_size_m=10.0,
            analysis_scale="local",
            feedback=self.feedback,
            context=self.context,
            working_directory=self.working_directory,
        )
        # Simulate network analysis completing without producing isochrones
        workflow.create_isochrones = lambda **kwargs: None
        result = workflow.execute()
        self.assertTrue(result)
        self.assertEqual(
            self.indicator_item.attribute("result"),
            f"{workflow.workflow_name} Workflow Completed",
        )
        self.assertFalse(self.indicator_item.attribute("result_file"))
        values = get_grid_column_values(workflow.gpkg_path, "street_crossings")
        self.assertTrue(values)
        self.assertTrue(all(value == 0 for value in values))

    def test_road_network_cache_reused_across_clip_calls(self):
        """_clip_network_to_area must reuse the cached network layer object

        across multiple calls (multiple areas) rather than reloading and
        re-reprojecting the source file each time. Regression for the
        performance cliff in worldbank/GeoE3#445/#448.
        """
        from qgis.core import QgsGeometry

        workflow = MultiBufferDistancesNativeWorkflow(
            item=self.indicator_item,
            cell_size_m=10.0,
            analysis_scale="local",
            feedback=self.feedback,
            context=self.context,
            working_directory=self.working_directory,
        )
        self.assertIsNone(workflow._cached_road_network_layer, "cache must start empty")

        # Use a geometry covering the whole network's extent so clipping succeeds.
        network_extent_geom = QgsGeometry.fromRect(self._network_layer_extent(workflow))

        # The clip itself succeeding isn't the point of this test (that's
        # covered by test_run); what matters is that the expensive
        # load+reproject step only happens once no matter how many areas
        # call _clip_network_to_area afterwards.
        workflow._clip_network_to_area(network_extent_geom, area_index=0)
        self.assertIsNotNone(workflow._cached_road_network_layer, "network must be cached after first use")
        cached_after_first = workflow._cached_road_network_layer

        workflow._clip_network_to_area(network_extent_geom, area_index=1)
        self.assertIs(
            workflow._cached_road_network_layer,
            cached_after_first,
            "the second area must reuse the same cached layer object, not reload it",
        )

    @staticmethod
    def _network_layer_extent(workflow):
        from qgis.core import QgsVectorLayer

        layer = QgsVectorLayer(workflow.road_network_layer_path, "network", "ogr")
        extent = layer.extent()
        extent.grow(1000)
        return extent


if __name__ == "__main__":
    unittest.main()
