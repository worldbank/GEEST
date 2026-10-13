# -*- coding: utf-8 -*-
import unittest

from defusedxml import ElementTree as ET

from geest.core.osm_downloaders.osm_data_downloader_base import OSMDataDownloaderBase


class TestGetEntityName(unittest.TestCase):
    def test_returns_name_tag_value(self):
        node = ET.fromstring('<node id="1"><tag k="amenity" v="pharmacy"/><tag k="name" v="Corner Pharmacy"/></node>')
        self.assertEqual(OSMDataDownloaderBase._get_entity_name(node), "Corner Pharmacy")

    def test_returns_empty_string_when_no_name_tag(self):
        node = ET.fromstring('<node id="1"><tag k="amenity" v="pharmacy"/></node>')
        self.assertEqual(OSMDataDownloaderBase._get_entity_name(node), "")

    def test_returns_empty_string_when_no_tags(self):
        node = ET.fromstring('<node id="1"/>')
        self.assertEqual(OSMDataDownloaderBase._get_entity_name(node), "")


if __name__ == "__main__":
    unittest.main()
