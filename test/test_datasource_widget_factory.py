# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch

from geest.gui.datasource_widget_factory import DataSourceWidgetFactory

MODULE = "geest.gui.datasource_widget_factory"


class TestEnvironmentalHazardsWidgetSelection(unittest.TestCase):
    """S2S download should only be offered for regional-scale analysis.

    Flood hazards previously got the S2S widget regardless of scale
    (worldbank/GeoE3#423), which regressed local/national flood analysis
    (worldbank/GeoE3#449). S2S must be gated on analysis_scale alone, same
    as every other hazard.
    """

    def _create(self, analysis_scale, hazard_id):
        attributes = {"analysis_scale": analysis_scale, "id": hazard_id}
        return DataSourceWidgetFactory.create_widget(
            widget_key="use_environmental_hazards", value=1, attributes=attributes
        )

    @patch(f"{MODULE}.S2SEnvironmentalHazardsRasterDataSourceWidget")
    @patch(f"{MODULE}.EnvironmentalHazardsRasterDataSourceWidget")
    def test_flood_at_local_scale_uses_non_s2s_widget(self, mock_raster_widget, mock_s2s_widget):
        self._create("local", "flood")
        mock_raster_widget.assert_called_once()
        mock_s2s_widget.assert_not_called()

    @patch(f"{MODULE}.S2SEnvironmentalHazardsRasterDataSourceWidget")
    @patch(f"{MODULE}.EnvironmentalHazardsRasterDataSourceWidget")
    def test_flood_at_national_scale_uses_non_s2s_widget(self, mock_raster_widget, mock_s2s_widget):
        self._create("national", "flood")
        mock_raster_widget.assert_called_once()
        mock_s2s_widget.assert_not_called()

    @patch(f"{MODULE}.S2SEnvironmentalHazardsRasterDataSourceWidget")
    @patch(f"{MODULE}.EnvironmentalHazardsRasterDataSourceWidget")
    def test_flood_at_regional_scale_uses_s2s_widget(self, mock_raster_widget, mock_s2s_widget):
        self._create("regional", "flood")
        mock_s2s_widget.assert_called_once()
        mock_raster_widget.assert_not_called()

    @patch(f"{MODULE}.S2SEnvironmentalHazardsRasterDataSourceWidget")
    @patch(f"{MODULE}.EnvironmentalHazardsRasterDataSourceWidget")
    def test_non_flood_hazard_at_local_scale_uses_non_s2s_widget(self, mock_raster_widget, mock_s2s_widget):
        self._create("local", "drought")
        mock_raster_widget.assert_called_once()
        mock_s2s_widget.assert_not_called()

    @patch(f"{MODULE}.S2SEnvironmentalHazardsRasterDataSourceWidget")
    @patch(f"{MODULE}.EnvironmentalHazardsRasterDataSourceWidget")
    def test_non_flood_hazard_at_regional_scale_uses_s2s_widget(self, mock_raster_widget, mock_s2s_widget):
        self._create("regional", "drought")
        mock_s2s_widget.assert_called_once()
        mock_raster_widget.assert_not_called()


class TestNighttimeLightsWidgetSelection(unittest.TestCase):
    """Regional scale gets the S2S widget; local/national get the in-app downloader."""

    def _create(self, analysis_scale):
        attributes = {"analysis_scale": analysis_scale}
        return DataSourceWidgetFactory.create_widget(widget_key="use_nighttime_lights", value=1, attributes=attributes)

    @patch(f"{MODULE}.S2SNTLRasterDataSourceWidget")
    @patch(f"{MODULE}.NTLDownloadRasterDataSourceWidget")
    def test_local_scale_uses_download_widget(self, mock_download_widget, mock_s2s_widget):
        self._create("local")
        mock_download_widget.assert_called_once()
        mock_s2s_widget.assert_not_called()

    @patch(f"{MODULE}.S2SNTLRasterDataSourceWidget")
    @patch(f"{MODULE}.NTLDownloadRasterDataSourceWidget")
    def test_national_scale_uses_download_widget(self, mock_download_widget, mock_s2s_widget):
        self._create("national")
        mock_download_widget.assert_called_once()
        mock_s2s_widget.assert_not_called()

    @patch(f"{MODULE}.S2SNTLRasterDataSourceWidget")
    @patch(f"{MODULE}.NTLDownloadRasterDataSourceWidget")
    def test_regional_scale_uses_s2s_widget(self, mock_download_widget, mock_s2s_widget):
        self._create("regional")
        mock_s2s_widget.assert_called_once()
        mock_download_widget.assert_not_called()


if __name__ == "__main__":
    unittest.main()
