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
        should produce a neutral 0-scored raster rather than an error.

        Regression test for issue #381.
        """
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
        result_file = self.indicator_item.attribute("result_file")
        self.assertTrue(result_file)
        self.assertTrue(os.path.exists(result_file))

    def test_road_network_cache_reused_across_clip_calls(self):
        """_clip_network_to_area must reuse the cached network layer object

        across multiple calls (multiple areas) rather than reloading and
        re-reprojecting the source file each time. Regression for the
        performance cliff in worldbank/GeoE3#445/#448.
        """
        from qgis.core import QgsVectorLayer

        workflow = MultiBufferDistancesNativeWorkflow(
            item=self.indicator_item,
            cell_size_m=10.0,
            analysis_scale="local",
            feedback=self.feedback,
            context=self.context,
            working_directory=self.working_directory,
        )
        self.assertIsNone(workflow._cached_road_network_layer, "cache must start empty")

        point_layer = QgsVectorLayer(self.points_layer_path, "points", "ogr")

        # The clip itself succeeding isn't the point of this test (that's
        # covered by test_run); what matters is that the expensive
        # load+reproject step only happens once no matter how many areas
        # call _clip_network_to_area afterwards. _get_cached_road_network_layer()
        # runs before the clip's own success/failure is known, so this holds
        # regardless of whether the points' CRS lines up with the network's.
        workflow._clip_network_to_area(point_layer, area_index=0)
        self.assertIsNotNone(workflow._cached_road_network_layer, "network must be cached after first use")
        cached_after_first = workflow._cached_road_network_layer

        workflow._clip_network_to_area(point_layer, area_index=1)
        self.assertIs(
            workflow._cached_road_network_layer,
            cached_after_first,
            "the second area must reuse the same cached layer object, not reload it",
        )

    def test_clip_follows_the_points_not_a_larger_area_polygon(self):
        """_clip_network_to_area must clip around a dissolved buffer of the
        points actually being analysed, not the (often much larger)
        surrounding study-area polygon - buffering the whole area clips
        network nowhere near any point whenever points are sparse relative
        to the area, wasting graph build and traversal time on network that
        can never appear in the result (worldbank/GeoE3 perf review,
        2026-10-24).

        Regression target: the clipped network's extent must stay within
        the single point's own max(distances) buffer, not sprawl out to
        cover a much larger area.
        """
        from qgis.core import (
            QgsCoordinateTransform,
            QgsFeature,
            QgsProject,
            QgsVectorLayer,
        )

        workflow = MultiBufferDistancesNativeWorkflow(
            item=self.indicator_item,
            cell_size_m=10.0,
            analysis_scale="local",
            feedback=self.feedback,
            context=self.context,
            working_directory=self.working_directory,
        )
        self.assertEqual(max(workflow.distances), 3000)

        source_points = QgsVectorLayer(self.points_layer_path, "points", "ogr")
        first_point_geom = next(source_points.getFeatures()).geometry()
        transform = QgsCoordinateTransform(
            source_points.crs(), workflow.target_crs, QgsProject.instance().transformContext()
        )
        first_point_geom.transform(transform)

        single_point_layer = QgsVectorLayer(f"Point?crs={workflow.target_crs.authid()}", "single_point", "memory")
        feature = QgsFeature()
        feature.setGeometry(first_point_geom)
        single_point_layer.dataProvider().addFeatures([feature])
        single_point_layer.updateExtents()

        clipped_path = workflow._clip_network_to_area(single_point_layer, area_index=0)
        self.assertIsNotNone(clipped_path, "expected a successful clip around the point")

        clipped_extent = QgsVectorLayer(clipped_path, "clipped", "ogr").extent()

        # native:clip keeps any road segment that TOUCHES the buffer, so a
        # segment can cross slightly outside it - allow a small tolerance
        # rather than requiring an exact edge match.
        expected_bound = first_point_geom.buffer(3000, 5).boundingBox()
        expected_bound.grow(200)

        self.assertTrue(
            expected_bound.contains(clipped_extent),
            f"clipped network extent {clipped_extent.toString()} extends beyond the "
            f"point's own 3000m buffer {expected_bound.toString()} - looks like it clipped "
            f"to something larger than the points (e.g. the area polygon)",
        )


if __name__ == "__main__":
    unittest.main()
