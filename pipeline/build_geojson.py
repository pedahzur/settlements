"""Emit the data the dynamic map consumes (web/data/).

  * settlements.geojson    - point per settlement with the latest snapshot props
  * population_by_year.json - {settlement_id: {year: pop}} for the time slider
  * meta.json              - build timestamp, available years, value ranges
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd

from . import config
from .utils import log


def _num(v):
    if pd.isna(v):
        return None
    if isinstance(v, (int,)):
        return int(v)
    f = float(v)
    return round(f, 4) if f != int(f) else int(f)


def build() -> None:
    snap = pd.read_csv(config.DB / "settlements_latest.csv")
    pop = pd.read_csv(config.DB / "population_long.csv")

    props_cols = [
        "settlement_id", "name_en", "name_he", "type", "regional_council",
        "urban_pattern", "dist_gl_km", "elevation", "year_established", "status",
        "latest_pop", "latest_pop_year", "peak_pop", "peak_year", "cagr_pct",
        "decline_from_peak_pct", "trajectory", "latest_knesset",
        "right_bloc_share", "top_party", "turnout", "se_cluster", "se_rank",
        "built_up_dunams", "govt_decision_type", "govt_decision_date",
    ]
    have = [c for c in props_cols if c in snap.columns]

    features = []
    for _, r in snap.iterrows():
        lon, lat = r.get("lon"), r.get("lat")
        if pd.isna(lon) or pd.isna(lat):
            continue
        props = {c: _num(r[c]) if pd.api.types.is_number(r[c]) else (
                 None if pd.isna(r[c]) else r[c]) for c in have}
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
            "properties": props,
        })
    fc = {"type": "FeatureCollection", "features": features}
    (config.WEB_DATA / "settlements.geojson").write_text(
        json.dumps(fc, ensure_ascii=False))
    log(f"geojson: {len(features)} mapped settlements")

    # Population-by-year for the slider (best series, compact).
    by_year: dict[str, dict[str, int]] = {}
    pp = pop.dropna(subset=["pop_best"])
    for sid, grp in pp.groupby("settlement_id"):
        by_year[str(int(sid))] = {str(int(y)): int(v) for y, v in
                                  zip(grp["year"], grp["pop_best"])}
    (config.WEB_DATA / "population_by_year.json").write_text(
        json.dumps(by_year, ensure_ascii=False))

    years = sorted({int(y) for y in pp["year"].unique()})
    meta = {
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "settlement_count": len(features),
        "years": years,
        "min_year": years[0] if years else None,
        "max_year": years[-1] if years else None,
        "has_voting": bool(snap.get("right_bloc_share").notna().any()
                           if "right_bloc_share" in snap.columns else False),
        "has_economic": bool(snap.get("se_cluster").notna().any()
                             if "se_cluster" in snap.columns else False),
        "has_builtup": bool(snap.get("built_up_dunams").notna().any()
                            if "built_up_dunams" in snap.columns else False),
        "has_govt_decision": bool(snap.get("govt_decision_type").notna().any()
                                  if "govt_decision_type" in snap.columns else False),
    }
    (config.WEB_DATA / "meta.json").write_text(json.dumps(meta, ensure_ascii=False))
    log(f"meta: years {meta['min_year']}-{meta['max_year']}, "
        f"voting={meta['has_voting']} economic={meta['has_economic']} "
        f"builtup={meta['has_builtup']}")


if __name__ == "__main__":
    build()
