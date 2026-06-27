"""Build the canonical settlement dimension (one row per settlement).

Spine: the existing ``entity_registry`` and ``outposts`` sheets in
``settlements_master_panel.xlsx`` (Peace Now + B'Tselem, with coordinates and
source IDs). We enrich every entity with its CBS locality code (semel yishuv)
by matching the Hebrew name against the data.gov.il localities master — this
semel is the key that lets voting and economic data attach later.
"""
from __future__ import annotations

import pandas as pd

from . import config
from .utils import ckan_datastore_search, he_key, http_get, log


def _localities_semel_map() -> dict[str, int]:
    """Hebrew-name -> semel yishuv, from the data.gov.il localities master."""
    # Resolve the resource id from the package, then pull the datastore.
    import json
    pkg = http_get(f"{config.DATAGOV_BASE}/package_show",
                   cache=config.RAW / "localities_package.json",
                   params={"id": config.DATAGOV_LOCALITIES})
    if not pkg:
        return {}
    try:
        resources = json.loads(pkg)["result"]["resources"]
        rid = next(r["id"] for r in resources
                   if r.get("datastore_active") or r["format"].lower() in ("csv", "xlsx"))
    except Exception as exc:  # noqa: BLE001
        log(f"WARN cannot resolve localities resource: {exc}")
        return {}
    rows = ckan_datastore_search(rid, cache=config.RAW / "localities.json")
    if not rows:
        return {}
    out: dict[str, int] = {}
    for r in rows:
        # Column names vary; find the Hebrew-name and semel columns heuristically.
        name = r.get("שם_ישוב") or r.get("שם ישוב") or r.get("name")
        semel = r.get("סמל_ישוב") or r.get("סמל ישוב") or r.get("semel")
        if name and semel:
            try:
                out[he_key(name)] = int(float(semel))
            except (TypeError, ValueError):
                continue
    log(f"localities master: {len(out)} semel entries")
    return out


def build() -> pd.DataFrame:
    xl = pd.ExcelFile(config.MASTER_XLSX)
    reg = xl.parse("entity_registry")

    dim = pd.DataFrame({
        "settlement_id": reg["entity_id"].astype(int),
        "name_en": reg["name_en"],
        "name_he": reg["name_he"],
        "type": reg["type"],
        "source": reg["source"],
        "regional_council": reg["regional_council"],
        "urban_pattern": reg["urban_pattern"],
        "dist_gl_km": reg["dist_gl_km"],
        "elevation": reg["elevation"],
        "year_established": reg["year_established"],
        "pn_db_id": reg["pn_db_id"],
        "bt_gisid": reg["bt_gisid"],
        "lon": reg["lon"],
        "lat": reg["lat"],
    })
    dim["status"] = "active"

    # Outposts are already entities in the registry (type == "Outpost", linked
    # by pn_db_id == DB_ID) but lack coordinates. Backfill lon/lat from the
    # outposts sheet, whose "UTM" columns are actually lat/lon degrees.
    try:
        out = xl.parse("outposts")
        coords = pd.DataFrame({
            "pn_db_id": pd.to_numeric(out["DB_ID"], errors="coerce"),
            "o_lat": pd.to_numeric(out["x (UTM)"], errors="coerce"),
            "o_lon": pd.to_numeric(out["y(UTM)"], errors="coerce"),
        }).dropna(subset=["pn_db_id"])
        dim = dim.merge(coords, on="pn_db_id", how="left")
        fill = dim["lon"].isna() & dim["o_lon"].notna()
        dim.loc[fill, "lon"] = dim.loc[fill, "o_lon"]
        dim.loc[fill, "lat"] = dim.loc[fill, "o_lat"]
        dim = dim.drop(columns=["o_lat", "o_lon"])
        log(f"backfilled coordinates for {int(fill.sum())} outposts")
    except Exception as exc:  # noqa: BLE001
        log(f"WARN could not backfill outpost coords: {exc}")

    # Attach CBS semel yishuv via Hebrew name (best-effort; remote source).
    semel_map = _localities_semel_map()
    dim["cbs_semel"] = dim["name_he"].map(lambda n: semel_map.get(he_key(n)))
    matched = int(dim["cbs_semel"].notna().sum())
    log(f"semel matched for {matched}/{len(dim)} entities")

    dim["he_join_key"] = dim["name_he"].map(he_key)
    return dim


if __name__ == "__main__":
    d = build()
    d.to_csv(config.DB / "settlement_dimension.csv", index=False)
    log(f"wrote settlement_dimension.csv ({len(d)} rows)")
