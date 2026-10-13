# -*- coding: utf-8 -*-
import unittest

try:
    from defusedxml import ElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET  # nosec B405

from geest.core.osm_downloaders.osm_data_downloader_base import OSMDataDownloaderBase


class TestGetEntityName(unittest.TestCase):
    def test_returns_name_tag_value(self):
        node = ET.fromstring(  # nosec B314
            '<node id="1"><tag k="amenity" v="pharmacy"/><tag k="name" v="Corner Pharmacy"/></node>'
        )
        self.assertEqual(OSMDataDownloaderBase._get_entity_name(node), "Corner Pharmacy")

    def test_falls_back_to_amenity_when_no_name_tag(self):
        node = ET.fromstring('<node id="1"><tag k="amenity" v="pharmacy"/></node>')  # nosec B314
        self.assertEqual(OSMDataDownloaderBase._get_entity_name(node), "pharmacy")

    def test_falls_back_to_shop_when_no_name_or_amenity_tag(self):
        node = ET.fromstring('<node id="1"><tag k="shop" v="bakery"/></node>')  # nosec B314
        self.assertEqual(OSMDataDownloaderBase._get_entity_name(node), "bakery")

    def test_name_tag_takes_precedence_over_amenity(self):
        node = ET.fromstring(  # nosec B314
            '<node id="1"><tag k="amenity" v="pharmacy"/><tag k="name" v="Corner Pharmacy"/></node>'
        )
        self.assertEqual(OSMDataDownloaderBase._get_entity_name(node), "Corner Pharmacy")

    def test_returns_empty_string_when_no_tags(self):
        node = ET.fromstring('<node id="1"/>')  # nosec B314
        self.assertEqual(OSMDataDownloaderBase._get_entity_name(node), "")


if __name__ == "__main__":
    unittest.main()
