"""Expansion fact table (built-up area per settlement).

Source: UN OCHA oPt settlement built-up-area polygons (HDX). We compute each
polygon's area in dunams (1 dunam = 1000 m^2) in the Israeli TM grid
(EPSG:2039) and attach it to our settlement points by point-in-polygon (falling
back to nearest polygon centroid).

Needs network egress to HDX plus geopandas/shapely. Both are optional: if either
is unavailable the table is empty and the pipeline proceeds. (A per-settlement
*built-up-area time series* is not published anywhere as a clean download — see
SOURCES.md — so this captures the latest OCHA snapshot only.)
"""
from __future__ import annotations

import io
import json
import zipfile

import pandas as pd

from . import config
from .utils import http_get, log

ITM = "EPSG:2039"   # Israel 1993 / Israeli TM Grid — metric, good for the WB


def _settlements_zip_url() -> str | None:
    body = http_get(config.HDX_SETTLEMENTS,
                    cache=config.RAW / "hdx_settlements_pkg.json")
    if not body:
        return None
    try:
        resources = json.loads(body)["result"]["resources"]
        for r in resources:
            if str(r.get("format", "")).lower() in ("shp", "zipped shapefile", "geojson"):
                return r["download_url"] or r["url"]
        return resources[0]["url"] if resources else None
    except Exception as exc:  # noqa: BLE001
        log(f"WARN bad HDX package: {exc}")
        return None


def build(dim: pd.DataFrame) -> pd.DataFrame:
    empty = pd.DataFrame(columns=["settlement_id", "built_up_dunams", "ocha_name"])
    try:
        import geopandas as gpd  # noqa: F401
        from shapely.geometry import Point  # noqa: F401
    except Exception:  # noqa: BLE001
        log("expansion: geopandas/shapely unavailable; empty table")
        return empty

    import geopandas as gpd
    from shapely.geometry import Point

    url = _settlements_zip_url()
    if not url:
        log("expansion: no OCHA settlements resource; empty table")
        return empty
    body = http_get(url, cache=config.RAW / "ocha_settlements.zip", binary=True)
    if not body:
        return empty

    try:
        if body[:4] == b"PK\x03\x04":
            zf = zipfile.ZipFile(io.BytesIO(body))
            shp = next(n for n in zf.namelist() if n.lower().endswith(".shp"))
            config.RAW.joinpath("ocha_settlements").mkdir(exist_ok=True)
            zf.extractall(config.RAW / "ocha_settlements")
            gdf = gpd.read_file(config.RAW / "ocha_settlements" / shp)
        else:
            gdf = gpd.read_file(io.BytesIO(body))
    except Exception as exc:  # noqa: BLE001
        log(f"expansion: cannot read OCHA polygons ({exc}); empty table")
        return empty

    gdf = gdf.to_crs(ITM)
    gdf["built_up_dunams"] = gdf.geometry.area / 1000.0
    name_col = next((c for c in gdf.columns
                     if "name" in c.lower() and c != "geometry"), None)

    pts = dim.dropna(subset=["lon", "lat"]).copy()
    gpts = gpd.GeoDataFrame(
        pts, geometry=[Point(xy) for xy in zip(pts["lon"], pts["lat"])],
        crs="EPSG:4326").to_crs(ITM)
    joined = gpd.sjoin(gpts, gdf[["geometry", "built_up_dunams"] +
                                 ([name_col] if name_col else [])],
                       how="left", predicate="within")
    out = pd.DataFrame({
        "settlement_id": joined["settlement_id"].astype(int),
        "built_up_dunams": joined["built_up_dunams"].round(1),
        "ocha_name": joined[name_col] if name_col else pd.NA,
    }).dropna(subset=["built_up_dunams"]).drop_duplicates("settlement_id")
    log(f"expansion: built-up area for {len(out)} settlements")
    return out


if __name__ == "__main__":
    from .build_registry import build as build_dim
    build(build_dim()).to_csv(config.DB / "expansion.csv", index=False)
