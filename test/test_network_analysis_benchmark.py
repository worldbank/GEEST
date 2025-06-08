import unittest
import os
import tempfile
from qgis.core import QgsFeature, QgsGeometry, QgsPointXY, QgsCoordinateReferenceSystem

from geest.core.algorithms.native_network_analysis_processor import (
    NativeNetworkAnalysisProcessor,
)
from geest.core.timer import Timer, timed


class NetworkAnalysisBenchmarkTest(unittest.TestCase):
    """Test benchmarking for network analysis processor."""

    @classmethod
    def setUpClass(cls):
        """Set up test resources."""
        # Define paths for test data - replace with actual path to test network
        cls.network_file = os.path.join(
            os.path.dirname(__file__),
            "test_data",
            "network_analysis",
            "network_layer.shp",
        )
        # Create temp directory for outputs
        cls.temp_dir = tempfile.mkdtemp()

    def setUp(self):
        """Setup for each test case."""
        # Reset timings before each test
        Timer.reset_timings()

        # Set CRS - update to match your test data
        self.crs = QgsCoordinateReferenceSystem("EPSG:3857")
        # Create an actual QgsFeature
        self.point_feature = QgsFeature()
        self.point_feature.setGeometry(
            QgsFeature().geometry().fromPointXY(QgsPointXY(643067.042, 3955294.999))
        )
        self.point_feature.setId(1)
        # Create an actual CRS
        self.crs = QgsCoordinateReferenceSystem("EPSG:32632")

        self.mode = "distance"
        self.values = [1000, 2000, 3000]  # Distances in meters
        self.working_directory = tempfile.mkdtemp()
        self.isochrone_output = os.path.join(
            self.working_directory, "isochrone_layer.gpkg"
        )
        # self.addCleanup(lambda: os.rmdir(self.working_directory))
        print(f"Network Analysis Benchmark Working directory: {self.working_directory}")

    @timed
    def test_benchmark_performance(self):
        """Benchmark the network analysis processor."""
        print("\nRunning network analysis benchmark...")

        # Create processor with test parameters
        with Timer("processor_initialization"):
            processor = NativeNetworkAnalysisProcessor(
                network_layer_path=self.network_file,
                isochrone_layer_path=self.isochrone_output,
                area_index=0,
                point_feature=self.point_feature,
                crs=self.crs,
                mode="distance",
                values=[500, 1000, 2000],  # Distances in meters
                working_directory=self.temp_dir,
            )

        # Run the processor
        with Timer("processor_execution"):
            result = processor.run()

        # Print benchmark results
        print("\n=== BENCHMARK RESULTS ===")

        # Print detailed breakdown of timings
        timings = Timer.get_timings()
        total_time = sum(timings.get("processor_execution", [0]))

        print("\nPerformance breakdown:")
        for name, times in sorted(timings.items()):
            if times:
                total_op_time = sum(times)
                percent = (total_op_time / total_time) * 100 if total_time > 0 else 0
                print(f"  {name:<30}: {total_op_time:6.2f}s ({percent:5.1f}%)")

        # Verify results
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.isochrone_output))

        # Check isochrone feature count
        with Timer("feature_count_check"):
            feature_count = processor.isochrone_feature_count()
        print(f"\nCreated {feature_count} isochrone features")

        # Cleanup explicit reference to processor to trigger __del__
        del processor


if __name__ == "__main__":
    unittest.main()
