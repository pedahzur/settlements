"""Integrity checks for the committed map-footprint extracts."""

from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_DATA = ROOT / "web" / "data"


def _coordinates(geometry):
    value = geometry["coordinates"]

    def walk(item):
        if item and isinstance(item[0], (int, float)):
            yield item
        else:
            for child in item:
                yield from walk(child)

    yield from walk(value)


class MapFootprintTest(unittest.TestCase):
    def _load(self, name: str) -> dict:
        return json.loads((WEB_DATA / name).read_text(encoding="utf-8"))

    def _assert_valid_polygons(self, collection: dict) -> None:
        self.assertEqual(collection["type"], "FeatureCollection")
        self.assertTrue(collection["features"])
        for feature in collection["features"]:
            self.assertIn(feature["geometry"]["type"], {"Polygon", "MultiPolygon"})
            self.assertIsInstance(feature["properties"]["settlement_id"], int)
            for lon, lat, *_ in _coordinates(feature["geometry"]):
                self.assertGreaterEqual(lon, 34.0)
                self.assertLessEqual(lon, 36.5)
                self.assertGreaterEqual(lat, 30.5)
                self.assertLessEqual(lat, 33.6)

    def test_golan_extract_covers_every_locality(self) -> None:
        collection = self._load("golan_footprints.geojson")
        self._assert_valid_polygons(collection)
        ids = {f["properties"]["settlement_id"] for f in collection["features"]}
        golan = self._load("golan.json")
        self.assertEqual(ids, {locality["id"] for locality in golan["localities"]})
        self.assertEqual(collection["license"], "Open Database License (ODbL) 1.0")

    def test_west_bank_extract_has_full_settlement_and_ej_coverage(self) -> None:
        collection = self._load("settlement_footprints.geojson")
        self._assert_valid_polygons(collection)
        footprint_ids = {f["properties"]["settlement_id"] for f in collection["features"]}
        entities = self._load("settlements.geojson")["features"]
        counts = Counter(
            f["properties"]["type"]
            for f in entities
            if f["properties"]["settlement_id"] in footprint_ids
        )
        self.assertEqual(counts["Settlement"], 129)
        self.assertEqual(counts["East Jerusalem"], 11)
        self.assertGreaterEqual(counts["Outpost"], 180)

    def test_maps_no_longer_use_population_scaled_circles(self) -> None:
        self.assertNotIn("circleMarker", (ROOT / "web/app.js").read_text())
        self.assertNotIn("circleMarker", (ROOT / "web/golan.js").read_text())


if __name__ == "__main__":
    unittest.main()
