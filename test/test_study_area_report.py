import unittest
from qgis.core import QgsVectorLayer, QgsField, QgsFeature
from qgis.PyQt.QtCore import QVariant
from geest.core.reports.study_area_report import StudyAreaReport

# ================================
# Test Suite for StudyAreaReport
# ================================


class TestStudyAreaReport(unittest.TestCase):
    """
    Test suite for the StudyAreaReport class.

    This suite creates a memory layer with a 'geom_total_duration_secs' field and sample data,
    then tests the computation of statistics, creation of layout, and PDF export functionality.
    """

    @classmethod
    def setUpClass(cls):
        """
        Set up a memory layer with sample data for testing.
        """
        # Create a memory vector layer
        cls.layer = QgsVectorLayer("Point?crs=EPSG:4326", "test_layer", "memory")
        provider = cls.layer.dataProvider()
        provider.addAttributes([QgsField("geom_total_duration_secs", QVariant.Double)])
        cls.layer.updateFields()

        # Add sample features with known processing times
        features = []
        sample_values = [0.5, 1.0, 2.0, 3.0, 4.0]
        for val in sample_values:
            feat = QgsFeature(cls.layer.fields())
            feat.setAttribute("geom_total_duration_secs", val)
            # Geometry is not used in the statistics so we leave it empty (None)
            features.append(feat)
        provider.addFeatures(features)
        cls.layer.updateExtents()

        # Instantiate the report using the memory layer
        cls.report = StudyAreaReport(cls.layer, report_name="Test Report")

    def test_compute_statistics(self):
        """
        Test that the compute_statistics method returns correct summary values.
        """
        stats = self.report.compute_statistics()
        expected_sum = sum([0.5, 1.0, 2.0, 3.0, 4.0])
        expected_mean = expected_sum / 5
        self.assertEqual(stats["count"], 5)
        self.assertAlmostEqual(stats["min"], 0.5)
        self.assertAlmostEqual(stats["max"], 4.0)
        self.assertAlmostEqual(stats["mean"], expected_mean)
        self.assertAlmostEqual(stats["sum"], expected_sum)

    def test_create_layout(self):
        """
        Test that the layout is created and contains at least two items (the title and summary).
        """
        self.report.create_layout()
        self.assertIsNotNone(self.report.layout)
        items = self.report.layout.items()
        self.assertGreaterEqual(len(items), 2)

    def test_export_pdf(self):
        """
        Test that the PDF export function creates a file successfully.
        """
        output_pdf = "test_report.pdf"
        success = self.report.export_pdf(output_pdf)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(output_pdf))
        # Clean up the test PDF file.
        os.remove(output_pdf)


if __name__ == "__main__":
    # Run the test suite without exiting the interpreter.
    unittest.main(exit=False)
