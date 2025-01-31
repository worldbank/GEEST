import unittest
import os
from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsField, QgsFields
from qgis.PyQt.QtCore import QVariant
from geest.core.algorithms.features_per_cell_processor import (
    select_grid_cells,
    assign_values_to_grid,
)
from utilities_for_testing import prepare_fixtures


class TestSpatialProcessing(unittest.TestCase):
    def setUp(self):
        """
        Set up mock data for the tests.
        """
        # Define working directories
        self.test_data_directory = prepare_fixtures()
        self.output_directory = os.path.join(self.test_data_directory, "output")

        # Create the output directory if it doesn't exist
        if not os.path.exists(self.output_directory):
            os.makedirs(self.output_directory)

        self.output_path = os.path.join(self.output_directory, "test_grid.gpkg")

        # Create an in-memory grid layer
        self.grid_layer = QgsVectorLayer(
            "Polygon?crs=EPSG:4326", "Grid Layer", "memory"
        )
        grid_provider = self.grid_layer.dataProvider()
        grid_fields = QgsFields()
        grid_fields.append(QgsField("id", QVariant.Int))
        grid_provider.addAttributes(grid_fields)
        self.grid_layer.updateFields()

        # Add grid cells (2x2 grid with simple square polygons)
        grid_features = [
            QgsFeature(),
            QgsFeature(),
            QgsFeature(),
            QgsFeature(),
        ]
        geometries = [
            QgsGeometry.fromWkt("POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))"),  # Cell 1
            QgsGeometry.fromWkt("POLYGON((1 0, 1 1, 2 1, 2 0, 1 0))"),  # Cell 2
            QgsGeometry.fromWkt("POLYGON((0 1, 0 2, 1 2, 1 1, 0 1))"),  # Cell 3
            QgsGeometry.fromWkt("POLYGON((1 1, 1 2, 2 2, 2 1, 1 1))"),  # Cell 4
        ]
        for i, feature in enumerate(grid_features):
            feature.setGeometry(geometries[i])
            feature.setAttributes([i + 1])  # Set 'id' attribute
        grid_provider.addFeatures(grid_features)

        # Create an in-memory features layer
        self.features_layer = QgsVectorLayer(
            "Point?crs=EPSG:4326", "Features Layer", "memory"
        )
        features_provider = self.features_layer.dataProvider()
        features_provider.addAttributes([QgsField("name", QVariant.String)])
        self.features_layer.updateFields()

        # Add points that intersect the grid cells
        feature_points = [
            QgsGeometry.fromWkt("POINT(0.5 0.5)"),  # Intersects Cell 1
            QgsGeometry.fromWkt("POINT(1.5 0.5)"),  # Intersects Cell 2
            QgsGeometry.fromWkt("POINT(1.5 1.5)"),  # Intersects Cell 4
            QgsGeometry.fromWkt("POINT(0.5 1.5)"),  # Intersects Cell 3
        ]
        features = [QgsFeature() for _ in feature_points]
        for i, feature in enumerate(features):
            feature.setGeometry(feature_points[i])
            feature.setAttributes([f"Feature {i + 1}"])
        features_provider.addFeatures(features)

    def test_select_grid_cells(self):
        """
        Test the select_grid_cells function.
        """
        output_layer = select_grid_cells(
            grid_layer=self.grid_layer,
            features_layer=self.features_layer,
            output_path=self.output_path,
        )

        self.assertTrue(output_layer.isValid(), "Output layer is not valid.")
        self.assertEqual(
            output_layer.featureCount(),
            4,
            "Output layer should have 4 grid cells.",
        )

        # Verify that the 'intersecting_features' field is populated correctly
        output_features = {
            f["id"]: f["intersecting_features"] for f in output_layer.getFeatures()
        }
        self.assertEqual(
            output_features[1], 1, "Cell 1 should have 1 intersecting feature."
        )
        self.assertEqual(
            output_features[2], 1, "Cell 2 should have 1 intersecting feature."
        )
        self.assertEqual(
            output_features[3], 1, "Cell 3 should have 1 intersecting feature."
        )
        self.assertEqual(
            output_features[4], 1, "Cell 4 should have 1 intersecting feature."
        )

    def test_assign_values_to_grid(self):
        """
        Test the assign_values_to_grid function.
        """
        # First, generate the intersecting feature counts
        output_layer = select_grid_cells(
            grid_layer=self.grid_layer,
            features_layer=self.features_layer,
            output_path=self.output_path,
        )
        updated_layer = assign_values_to_grid(output_layer)

        # Verify the 'value' field
        value_map = {f["id"]: f["value"] for f in updated_layer.getFeatures()}
        self.assertEqual(value_map[1], 3, "Cell 1 should have a value of 3.")
        self.assertEqual(value_map[2], 3, "Cell 2 should have a value of 3.")
        self.assertEqual(value_map[3], 3, "Cell 3 should have a value of 3.")
        self.assertEqual(value_map[4], 3, "Cell 4 should have a value of 3.")

    def tearDown(self):
        """
        Clean up test output files.
        """
        if os.path.exists(self.output_path):
            os.remove(self.output_path)


if __name__ == "__main__":
    unittest.main()
