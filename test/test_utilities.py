import unittest
import os
from unittest.mock import patch, MagicMock
from qgis.core import Qgis

#!/usr/bin/env python
"""
Test suite for utilities.py

versionadded: 2023-03-14
"""


# Import the utilities module
from geest.utilities import (
    theme_background_image,
    theme_stylesheet,
    log_window_geometry,
    get_free_memory_mb,
    log_layer_count,
    resources_path,
    resource_url,
    get_ui_class,
    log_message,
    geest_layer_ids,
    is_qgis_dark_theme_active,
    linear_interpolation,
    vector_layer_type,
    version,
    calculate_utm_zone_from_layer,
    calculate_utm_zone,
)


class TestUtilities(unittest.TestCase):
    """Test suite for utilities.py."""

    def test_resources_path(self):
        """Test the resources_path function."""
        # Test with single argument
        path = resources_path("test")
        self.assertTrue(os.path.isabs(path))
        self.assertTrue(path.endswith("test"))

        # Test with multiple arguments
        path = resources_path("test", "subfolder", "file.txt")
        self.assertTrue(os.path.isabs(path))
        self.assertTrue(path.endswith(os.path.join("test", "subfolder", "file.txt")))

    def test_resource_url(self):
        """Test the resource_url function."""
        # Create a test path
        test_path = os.path.join(os.path.dirname(__file__), "test_file.txt")
        url = resource_url(test_path)
        self.assertTrue(url.startswith("file:///"))
        self.assertTrue(url.endswith("test_file.txt"))

    @unittest.skip("TODO Check and fix")
    @patch("qgis.PyQt.QtWidgets.QApplication")
    def test_is_qgis_dark_theme_active(self, mock_app):
        """Test is_qgis_dark_theme_active function."""
        # Mock QSettings
        with patch("qgis.PyQt.QtCore.QSettings") as mock_settings:
            # Test when theme is 'nightmapping'
            mock_settings_instance = mock_settings.return_value
            mock_settings_instance.value.return_value = "nightmapping"
            self.assertTrue(is_qgis_dark_theme_active())

            # Test when theme is not 'nightmapping' but palette is dark
            mock_settings_instance.value.return_value = "default"
            mock_app_instance = mock_app.instance.return_value
            mock_palette = MagicMock()
            mock_window_color = MagicMock()
            mock_text_color = MagicMock()
            mock_window_color.lightness.return_value = 10  # Dark
            mock_text_color.lightness.return_value = 90  # Light
            mock_palette.Window = 0
            mock_palette.WindowText = 1
            mock_palette.color.side_effect = lambda index: (
                mock_window_color if index == 0 else mock_text_color
            )
            mock_app_instance.palette.return_value = mock_palette
            self.assertTrue(is_qgis_dark_theme_active())

            # Test when theme is not dark and palette is light
            mock_window_color.lightness.return_value = 90  # Light
            mock_text_color.lightness.return_value = 10  # Dark
            self.assertFalse(is_qgis_dark_theme_active())

    def test_linear_interpolation(self):
        """Test linear_interpolation function."""
        # Test normal interpolation
        self.assertEqual(linear_interpolation(5, 0, 10, 0, 10), 5)
        self.assertEqual(linear_interpolation(0, 0, 10, 0, 10), 0)
        self.assertEqual(linear_interpolation(10, 0, 10, 0, 10), 10)

        # Test interpolation with different ranges
        self.assertEqual(linear_interpolation(5, 0, 100, 0, 10), 50)
        self.assertEqual(linear_interpolation(50, 0, 1, 0, 100), 0.5)

        # Test clamping
        self.assertEqual(linear_interpolation(-5, 0, 10, 0, 10), 0)
        self.assertEqual(linear_interpolation(15, 0, 10, 0, 10), 10)

        # Test invalid input
        with self.assertRaises(ValueError):
            linear_interpolation(5, 0, 10, 10, 10)

    @patch("qgis.core.QgsVectorLayer")
    def test_vector_layer_type(self, mock_layer_class):
        """Test vector_layer_type function."""
        # Test GeoPackage
        mock_gpkg_layer = MagicMock()
        mock_gpkg_layer.isValid.return_value = True
        mock_gpkg_layer.source.return_value = "/path/to/file.gpkg|layerid=0"
        self.assertEqual(vector_layer_type(mock_gpkg_layer), "GPKG")

        # Test Shapefile
        mock_shp_layer = MagicMock()
        mock_shp_layer.isValid.return_value = True
        mock_shp_layer.source.return_value = "/path/to/file.shp"
        self.assertEqual(vector_layer_type(mock_shp_layer), "SHP")

        # Test unknown type
        mock_unknown_layer = MagicMock()
        mock_unknown_layer.isValid.return_value = True
        mock_unknown_layer.source.return_value = "/path/to/file.xyz"
        self.assertEqual(vector_layer_type(mock_unknown_layer), "Unknown")

        # Test invalid layer
        mock_invalid_layer = MagicMock()
        mock_invalid_layer.isValid.return_value = False
        self.assertEqual(vector_layer_type(mock_invalid_layer), "Invalid layer")

    @patch(
        "builtins.open",
        new_callable=unittest.mock.mock_open,
        read_data="version=1.0.0\nother=stuff",
    )
    @unittest.skip("TODO Check and fix")
    @patch("os.path.join")
    def test_version(self, mock_join, mock_open):
        """Test version function."""
        # Mock the path to metadata.txt
        mock_join.return_value = "/path/to/metadata.txt"

        # Test when file exists and has version
        self.assertEqual(version(), "1.0.0")

        # Test when file exists but has no version
        mock_open.read_data = "other=stuff"
        self.assertEqual(version(), "Unknown")

        # Test when file does not exist
        mock_open.side_effect = FileNotFoundError
        self.assertEqual(version(), "Unknown")

    def test_calculate_utm_zone(self):
        """Test calculate_utm_zone function."""
        # Mock osr.SpatialReference and osr.CoordinateTransformation
        with patch("geest.utilities.osr.SpatialReference"), patch(
            "geest.utilities.osr.CoordinateTransformation"
        ), patch("geest.utilities.ogr.Geometry") as mock_geometry:

            # Mock the point transformation
            mock_point = MagicMock()
            mock_point.GetX.return_value = 5
            mock_point.GetY.return_value = 5
            mock_geometry.return_value = mock_point

            # Test Northern Hemisphere
            self.assertEqual(calculate_utm_zone((0, 10, 0, 10), "4326"), 32631)

            # Test Southern Hemisphere
            mock_point.GetY.return_value = -5
            self.assertEqual(calculate_utm_zone((0, 10, -10, 0), "4326"), 32731)

            # Test without source EPSG
            with patch("geest.utilities.log_message") as mock_log:
                mock_point.GetX.return_value = 5
                mock_point.GetY.return_value = 5
                self.assertEqual(calculate_utm_zone((0, 10, 0, 10)), 32631)
                mock_log.assert_called_once()

    @unittest.skip("TODO Check and fix")
    @patch("qgis.core.QgsMessageLog")
    @patch("logging.info")
    @patch("logging.warning")
    @patch("logging.critical")
    @patch("logging.debug")
    @patch("geest.utilities.setting")
    def test_log_message(
        self,
        mock_setting,
        mock_debug,
        mock_critical,
        mock_warning,
        mock_info,
        mock_qgs_log,
    ):
        """Test log_message function."""
        # Test when verbose mode is off
        mock_setting.return_value = 0
        log_message("Test message")
        mock_qgs_log.logMessage.assert_not_called()
        mock_info.assert_not_called()

        # Test when verbose mode is on
        mock_setting.return_value = 1

        # Test Info level
        log_message("Test info", level=Qgis.Info)
        mock_info.assert_called_once()
        mock_qgs_log.logMessage.assert_not_called()

        # Test Critical level
        mock_info.reset_mock()
        mock_qgs_log.logMessage.reset_mock()
        log_message("Test critical", level=Qgis.Critical)
        mock_critical.assert_called_once()
        mock_qgs_log.logMessage.assert_called_once()

        # Test force flag
        mock_critical.reset_mock()
        mock_qgs_log.logMessage.reset_mock()
        mock_setting.return_value = 0  # verbose off
        log_message("Test force", force=True)
        mock_info.assert_called_once()
        mock_qgs_log.logMessage.assert_called_once()

    @unittest.skip("TODO Check and fix")
    @patch("qgis.core.QgsLayerTreeGroup")
    @patch("qgis.core.QgsProject")
    def test_geest_layer_ids(self, mock_project, mock_layer_tree_group):
        """Test geest_layer_ids function."""
        # Mock layer tree structure
        mock_root = MagicMock()
        mock_project.instance.return_value.layerTreeRoot.return_value = mock_root

        # Test when Geest group doesn't exist
        mock_root.findGroup.return_value = None
        self.assertIsNone(geest_layer_ids())

        # Test when Geest group exists with layers
        mock_geest_group = MagicMock()
        mock_root.findGroup.return_value = mock_geest_group

        # Create mock layer and subgroup
        mock_layer = MagicMock()
        mock_layer.layerId.return_value = "layer1"
        mock_subgroup = MagicMock()
        mock_sublayer = MagicMock()
        mock_sublayer.layerId.return_value = "layer2"
        mock_subgroup.children.return_value = [mock_sublayer]
        mock_geest_group.children.return_value = [mock_layer, mock_subgroup]

        # Check the result
        result = geest_layer_ids()
        self.assertIsInstance(result, set)
        self.assertEqual(len(result), 2)
        self.assertIn("layer1", result)
        self.assertIn("layer2", result)

    @patch("platform.system")
    def test_get_free_memory_mb(self, mock_system):
        """Test get_free_memory_mb function."""

        # Test Linux
        mock_system.return_value = "Linux"
        with patch(
            "builtins.open",
            unittest.mock.mock_open(read_data="MemAvailable:    102400 kB\n"),
        ):
            self.assertEqual(get_free_memory_mb(), 100.0)

        # Test unsupported OS
        mock_system.return_value = "Unknown"
        self.assertEqual(get_free_memory_mb(), 0.0)

    @unittest.skip("TODO Check and fix")
    @patch("qgis.core.QgsProject")
    @patch("geest.utilities.get_free_memory_mb")
    @patch("geest.utilities.log_message")
    @patch("datetime.datetime")
    def test_log_layer_count(
        self, mock_datetime, mock_log_message, mock_free_memory, mock_project
    ):
        """Test log_layer_count function."""
        # Setup mocks
        mock_project.instance.return_value.mapLayers.return_value = {
            "layer1": "obj1",
            "layer2": "obj2",
        }
        mock_free_memory.return_value = 100.0
        mock_datetime.now.return_value.strftime.return_value = "2023-01-01 12:00:00"

        # Test logging
        with patch("builtins.open", unittest.mock.mock_open()) as mock_file:
            log_layer_count()
            expected_log = (
                "2023-01-01 12:00:00 - Layer count: 2 - Free memory: 100.00 MB\n"
            )
            mock_log_message.assert_called_once_with(
                expected_log, level=Qgis.Info, tag="LayerCount"
            )
            mock_file().write.assert_called_once_with(expected_log)

    @patch("qgis.PyQt.uic.loadUiType")
    def test_get_ui_class(self, mock_load_ui):
        """Test get_ui_class function."""
        mock_ui_class = MagicMock()
        mock_load_ui.return_value = (mock_ui_class, MagicMock())

        result = get_ui_class("test.ui")
        mock_load_ui.assert_called_once()
        self.assertEqual(result, mock_ui_class)

        # Check correct path construction
        call_args = mock_load_ui.call_args[0][0]
        self.assertTrue("ui" in call_args)
        self.assertTrue("test.ui" in call_args)

    @patch("geest.utilities.calculate_utm_zone")
    def test_calculate_utm_zone_from_layer(self, mock_calc_utm):
        """Test calculate_utm_zone_from_layer function."""
        # Setup mock layer
        mock_layer = MagicMock()
        mock_extent = MagicMock()
        mock_extent.xMinimum.return_value = 0
        mock_extent.xMaximum.return_value = 10
        mock_extent.yMinimum.return_value = 0
        mock_extent.yMaximum.return_value = 10
        mock_layer.extent.return_value = mock_extent

        mock_crs = MagicMock()
        mock_crs.authid.return_value = "EPSG:4326"
        mock_layer.crs.return_value = mock_crs

        mock_calc_utm.return_value = 32601
        result = calculate_utm_zone_from_layer(mock_layer)

        mock_calc_utm.assert_called_once_with((0, 10, 0, 10), "4326")
        self.assertEqual(result, 32601)

    @patch("geest.utilities.log_message")
    def test_log_window_geometry(self, mock_log_message):
        """Test log_window_geometry function."""
        # Test with QRect
        mock_rect = MagicMock()
        mock_rect.width.return_value = 500
        mock_rect.height.return_value = 300

        log_window_geometry(mock_rect)
        mock_log_message.assert_called_once()

        # Test with geometry object
        mock_log_message.reset_mock()
        mock_geom = MagicMock()
        mock_geom.rect.return_value = mock_rect

        log_window_geometry(mock_geom)
        mock_log_message.assert_called_once()

        # Test with invalid object
        mock_log_message.reset_mock()
        mock_invalid = MagicMock()
        mock_invalid.rect.side_effect = AttributeError

        log_window_geometry(mock_invalid)
        self.assertEqual(mock_log_message.call_count, 2)  # Two calls for warning

    @unittest.skip("TODO Check and fix")
    @patch("geest.utilities.is_qgis_dark_theme_active")
    @patch("geest.utilities.resources_path")
    @patch("qgis.PyQt.QtGui.QPixmap")
    def test_theme_background_image(
        self, mock_qpixmap, mock_resources_path, mock_is_dark
    ):
        """Test theme_background_image function."""
        # Test dark theme
        mock_is_dark.return_value = True
        mock_resources_path.return_value = "/path/to/dark-image.png"

        theme_background_image()
        mock_qpixmap.assert_called_once_with("/path/to/dark-image.png")

        # Test light theme
        mock_qpixmap.reset_mock()
        mock_is_dark.return_value = False
        mock_resources_path.return_value = "/path/to/light-image.png"

        theme_background_image()
        mock_qpixmap.assert_called_once_with("/path/to/light-image.png")

    @patch("geest.utilities.is_qgis_dark_theme_active")
    @patch("geest.utilities.resources_path")
    def test_theme_stylesheet(self, mock_resources_path, mock_is_dark):
        """Test theme_stylesheet function."""
        mock_resources_path.return_value = "/path/to/resources"

        # Test dark theme
        mock_is_dark.return_value = True
        style = theme_stylesheet()
        self.assertIn("background-color: #000000", style)

        # Test light theme
        mock_is_dark.return_value = False
        style = theme_stylesheet()
        self.assertIn("background-color: rgba(255, 255, 255, 255)", style)


if __name__ == "__main__":
    unittest.main()
