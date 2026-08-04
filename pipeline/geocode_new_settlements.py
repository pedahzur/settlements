"""Provenance-backed geocoding for the government establishment decisions.

Most of the 102 decisions (chiefly the brand-new settlements) are not in our
existing panel and therefore have no coordinates. This module geocodes those
unmatched names from authoritative open sources, so each mapped point carries a
citable origin rather than a guess:

  1. Wikidata  - exact Hebrew label -> coordinate (P625). Source: wikidata:<QID>.
  2. OSM/Nominatim - Hebrew name search, West-Bank-restricted. Source: osm:<id>.

Every candidate coordinate is validated to fall inside a West Bank bounding box;
anything outside is rejected (guards against same-name places inside Israel).
Results are cached to ``data/new_settlement_coords.csv`` with a ``coord_source``
and ``coord_confidence`` per row and are only queried once (the cache is
incremental across weekly runs). Requires outbound internet, so this populates
on the GitHub Actions runner; in a restricted sandbox it degrades to the cache.
"""
from __future__ import annotations

import json
import time

import pandas as pd
import requests

from . import config
from .utils import he_key, log

COORDS_CSV = config.DATA / "new_settlement_coords.csv"
DECISIONS_CSV = config.DATA / "govt_establishment_decisions.csv"

# West Bank bounding box (generous): lon 34.85-35.62, lat 31.30-32.62.
WB_BBOX = (34.85, 31.30, 35.62, 32.62)  # (min_lon, min_lat, max_lon, max_lat)

_HEADERS = {"User-Agent": config.USER_AGENT}


def _in_wb(lon: float, lat: float) -> bool:
    return (WB_BBOX[0] <= lon <= WB_BBOX[2]) and (WB_BBOX[1] <= lat <= WB_BBOX[3])


def _clean(name: str) -> str:
    # Primary name only (drop parenthetical alt names like "גודר (תבץ)").
    return name.split("(")[0].strip().strip(")").strip()


def _wikidata(name: str) -> dict | None:
    q = f'''SELECT ?item ?coord WHERE {{
      ?item rdfs:label "{name}"@he . ?item wdt:P625 ?coord .
    }} LIMIT 5'''
    try:
        r = requests.get(config.WIKIDATA_SPARQL, params={"query": q, "format": "json"},
                         headers=_HEADERS, timeout=config.HTTP_TIMEOUT)
        r.raise_for_status()
        for b in r.json()["results"]["bindings"]:
            m = b["coord"]["value"]  # "Point(lon lat)"
            lon, lat = (float(x) for x in m.replace("Point(", "").rstrip(")").split())
            if _in_wb(lon, lat):
                qid = b["item"]["value"].rsplit("/", 1)[-1]
                return {"lon": round(lon, 6), "lat": round(lat, 6),
                        "coord_source": f"wikidata:{qid}", "coord_confidence": "exact"}
    except Exception as exc:  # noqa: BLE001
        log(f"  wikidata error for {name!r}: {exc}")
    return None


def _nominatim(name: str) -> dict | None:
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search",
                         params={"q": name, "format": "json", "accept-language": "he",
                                 "viewbox": "34.85,32.62,35.62,31.30", "bounded": 1,
                                 "limit": 5},
                         headers=_HEADERS, timeout=config.HTTP_TIMEOUT)
        r.raise_for_status()
        for item in r.json():
            lon, lat = float(item["lon"]), float(item["lat"])
            if _in_wb(lon, lat):
                return {"lon": round(lon, 6), "lat": round(lat, 6),
                        "coord_source": f"osm:{item.get('osm_type','')[:1]}{item.get('osm_id','')}",
                        "coord_confidence": "approximate"}
    except Exception as exc:  # noqa: BLE001
        log(f"  nominatim error for {name!r}: {exc}")
    return None


def geocode(dim: pd.DataFrame) -> pd.DataFrame:
    """Geocode decision names not already present in the panel; update the cache."""
    cols = ["name_he", "lon", "lat", "coord_source", "coord_confidence"]
    cache = pd.read_csv(COORDS_CSV) if COORDS_CSV.exists() else pd.DataFrame(columns=cols)
    if not DECISIONS_CSV.exists():
        return cache
    dec = pd.read_csv(DECISIONS_CSV)

    have_panel = {he_key(n) for n in dim["name_he"] if isinstance(n, str)}
    cached = set(cache["name_he"]) if len(cache) else set()
    todo = [n for n in dec["name_he"].dropna().unique()
            if he_key(n) not in have_panel and n not in cached]
    log(f"geocode: {len(todo)} unmatched names to look up "
        f"({len(cached)} already cached)")

    rows = []
    for name in todo:
        clean = _clean(name)
        hit = _wikidata(clean) or _nominatim(clean)
        time.sleep(1.1)  # Nominatim/Wikidata courtesy rate limit
        if hit:
            rows.append({"name_he": name, **hit})
            log(f"  ✓ {name} -> {hit['lon']},{hit['lat']} [{hit['coord_source']}]")
        else:
            log(f"  · {name}: not found")
    if rows:
        cache = pd.concat([cache, pd.DataFrame(rows)], ignore_index=True)
        cache.drop_duplicates("name_he", keep="last").to_csv(COORDS_CSV, index=False)
    log(f"geocode: cache now holds {len(cache)} coordinates "
        f"({len(rows)} new this run)")
    return cache


def build_overlay(dim: pd.DataFrame) -> int:
    """Write web/data/new_settlements.geojson from geocoded, unmatched decisions."""
    if not (COORDS_CSV.exists() and DECISIONS_CSV.exists()):
        return 0
    dec = pd.read_csv(DECISIONS_CSV)
    coords = pd.read_csv(COORDS_CSV)
    have_panel = {he_key(n) for n in dim["name_he"] if isinstance(n, str)}
    merged = dec.merge(coords, on="name_he", how="inner")
    merged = merged[~merged["name_he"].map(he_key).isin(have_panel)]  # only off-panel
    feats = []
    for _, r in merged.iterrows():
        if pd.isna(r["lon"]) or pd.isna(r["lat"]):
            continue
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(r["lon"]), float(r["lat"])]},
            "properties": {
                "name_he": r["name_he"], "region_en": r.get("region_en"),
                "decision_date": r["decision_date"], "decision_type": r["decision_type"],
                "coord_source": r["coord_source"], "coord_confidence": r["coord_confidence"],
            },
        })
    (config.WEB_DATA / "new_settlements.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False))
    # Patch meta.json so the map can toggle the layer only when it has data.
    meta_path = config.WEB_DATA / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        meta["has_new_settlements"] = bool(feats)
        meta["new_settlement_count"] = len(feats)
        meta_path.write_text(json.dumps(meta, ensure_ascii=False))
    log(f"new-settlements overlay: {len(feats)} geocoded off-panel points")
    return len(feats)


def build() -> None:
    dim = pd.read_csv(config.DB / "settlement_dimension.csv")
    geocode(dim)
    build_overlay(dim)


if __name__ == "__main__":
    build()
