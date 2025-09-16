import os
import tempfile
import unittest

from osgeo import ogr, osr
from qgis.core import (QgsFeature, QgsField, QgsVectorLayer,
                       QgsVectorLayerExporter)
from qgis.PyQt.QtCore import QVariant

from geest.core.reports.study_area_report import StudyAreaReport
from geest.utilities import log_message

# ================================
# Test Suite for StudyAreaReport
# ================================


@unittest.skip("Skipping this test for now")
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
        # Create a GeoPackage vector layer directly
        cls.temp_dir = tempfile.TemporaryDirectory()

        # Delete the file if it already exists
        gpkg_path = f"{cls.temp_dir.name}/study_area_creation_status.gpkg"
        if os.path.exists(gpkg_path):
            os.remove(gpkg_path)

        driver = ogr.GetDriverByName("GPKG")
        if not driver:
            raise RuntimeError("Could not find GPKG driver")

        ds = driver.CreateDataSource(gpkg_path)
        if not ds:
            raise RuntimeError(f"Could not create GeoPackage {gpkg_path}")
        ds = None  # Close

        # Check if table exists
        ds = ogr.Open(gpkg_path, 1)  # open in update mode
        if not ds:
            raise RuntimeError(f"Could not open or create {gpkg_path} for update.")

        # Otherwise, create it
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)  # Arbitrary SRS for table with no geometry
        status_table_name = "study_area_creation_status"
        cls.layer = ds.CreateLayer(status_table_name, srs, geom_type=ogr.wkbNone)
        cls.layer.CreateField(ogr.FieldDefn("area_name", ogr.OFTString))
        cls.layer.CreateField(ogr.FieldDefn("timestamp_start", ogr.OFTDateTime))
        cls.layer.CreateField(ogr.FieldDefn("timestamp_start", ogr.OFTDateTime))
        cls.layer.CreateField(ogr.FieldDefn("timestamp_end", ogr.OFTDateTime))
        cls.layer.CreateField(ogr.FieldDefn("geometry_processed", ogr.OFTInteger))
        cls.layer.CreateField(ogr.FieldDefn("clip_geometry_processed", ogr.OFTInteger))
        cls.layer.CreateField(ogr.FieldDefn("grid_processed", ogr.OFTInteger))
        cls.layer.CreateField(ogr.FieldDefn("mask_processed", ogr.OFTInteger))
        cls.layer.CreateField(ogr.FieldDefn("grid_creation_duration_secs", ogr.OFTReal))
        cls.layer.CreateField(
            ogr.FieldDefn("clip_geom_creation_duration_secs", ogr.OFTReal)
        )
        cls.layer.CreateField(ogr.FieldDefn("geom_total_duration_secs", ogr.OFTReal))

        log_message(f"Table '{status_table_name}' created in GeoPackage.")

        if not cls.layer.isValid():
            raise Exception("Failed to create GeoPackage layer")

        # Add sample features with known processing times
        features = []
        sample_values = [0.5, 1.0, 2.0, 3.0, 4.0]
        for val in sample_values:
            feat = QgsFeature(cls.layer.fields())
            feat.setAttribute("geom_total_duration_secs", val)
            # Geometry is not used in the statistics so we leave it empty (None)
            features.append(feat)
        cls.layer.dataProvider().addFeatures(features)

        # Save the layer to the GeoPackage
        error = QgsVectorLayerExporter.exportLayer(
            cls.layer, gpkg_path, "GPKG", cls.layer.crs(), False
        )
        if error[0] != QgsVectorLayerExporter.NoError:
            raise Exception(f"Failed to export layer to GeoPackage: {error[1]}")
        del cls.layer
        ds = None
        # Instantiate the report using the memory layer
        cls.report = StudyAreaReport(gpkg_path, report_name="Test Report")

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
