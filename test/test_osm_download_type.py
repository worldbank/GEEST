# -*- coding: utf-8 -*-
"""Unit tests for geest.core.osm_downloaders.resolve_point_osm_download_type().

This is the shared keyword-matching rule extracted from
VectorDataSourceWidget's previously-inline if/elif chain - both the
widget's "Download from OSM" button and
geest.core.download_all_resources now call this single function, so a
regression here affects both call sites identically. The ordering tests
guard the exact precedence the original if/elif chain had (e.g.
"primary school" hits EDUCATION before PRIMARY_SCHOOL gets a chance).
"""
import unittest

from geest.core.osm_downloaders import OSM_DOWNLOAD_TOOLTIPS, OSMDownloadType, resolve_point_osm_download_type


class TestResolvePointOsmDownloadType(unittest.TestCase):
    def test_no_match_returns_none(self):
        self.assertIsNone(resolve_point_osm_download_type("fire", "fire hazard", "fire hazard"))

    def test_matches_by_id(self):
        self.assertEqual(resolve_point_osm_download_type("pharmacies", "", ""), OSMDownloadType.PHARMACY)

    def test_matches_by_name(self):
        self.assertEqual(resolve_point_osm_download_type("", "water points", ""), OSMDownloadType.WATER_POINT)

    def test_matches_by_indicator_text(self):
        self.assertEqual(resolve_point_osm_download_type("", "", "access to green spaces"), OSMDownloadType.GREEN_SPACE)

    def test_education_matches_before_primary_school(self):
        # "school" alone satisfies the EDUCATION check, which runs first -
        # PRIMARY_SCHOOL can only ever match via "primary" without "school"
        # already present, or an id containing only "primary".
        self.assertEqual(resolve_point_osm_download_type("primary_school", "", ""), OSMDownloadType.EDUCATION)

    def test_primary_alone_matches_primary_school(self):
        self.assertEqual(resolve_point_osm_download_type("primary_facility", "", ""), OSMDownloadType.PRIMARY_SCHOOL)

    def test_public_transport_matches_before_education(self):
        self.assertEqual(
            resolve_point_osm_download_type("public_transport_training_hub", "", ""),
            OSMDownloadType.PUBLIC_TRANSPORT,
        )

    def test_every_download_type_has_a_tooltip(self):
        for osm_type in OSMDownloadType:
            if osm_type == OSMDownloadType.ACTIVE_TRANSPORT:
                continue  # not keyword-matched here - a separate, non-buffer-point trigger
            self.assertIn(osm_type, OSM_DOWNLOAD_TOOLTIPS)


if __name__ == "__main__":
    unittest.main()
