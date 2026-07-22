"""Emit the data the Golan Heights map consumes (web/data/golan.json).

One record per Golan locality from the canonical dimension, joined to the
committed CBS annual population series (2003-2024). Jewish settlements are the
subject of the map; the five Druze/Alawite localities are included as a
comparison group the page can toggle. Localities join by CBS semel first and
fall back to an exact Hebrew-name match against the committed CBS registry
(the dimension is missing the semel for Newe Ativ). Nimrod has no published
CBS series and ships with an empty population object.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone

from . import config
from .utils import log

GOLAN_TYPES = {
    "Golan Settlement": "jewish",
    "Golan Non-Jewish Locality": "druze",
}


def _semel(value: str) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _load_registry() -> dict[str, int]:
    """Hebrew locality name -> semel, from the committed CBS registry."""
    names: dict[str, int] = {}
    with (config.DATA / "cbs_golan_registry_2024.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            semel = _semel(row.get("semel", ""))
            name = (row.get("שם יישוב") or "").strip()
            if semel and name:
                names[name] = semel
    return names


def _load_series() -> dict[int, dict[str, int]]:
    series: dict[int, dict[str, int]] = {}
    with (config.DATA / "cbs_golan_2003_2024.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            semel = _semel(row["semel"])
            if semel is None:
                continue
            series.setdefault(semel, {})[row["year"]] = round(float(row["pop"]))
    return series


def build() -> None:
    registry = _load_registry()
    series = _load_series()

    localities = []
    with (config.DB / "settlement_dimension.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            group = GOLAN_TYPES.get(row["type"])
            if group is None or not row["lon"] or not row["lat"]:
                continue
            semel = _semel(row["cbs_semel"]) or registry.get(row["name_he"].strip())
            founded = _semel(row["year_established"])
            localities.append({
                "id": int(row["settlement_id"]),
                "name_en": row["name_en"],
                "name_he": row["name_he"],
                "group": group,
                "form": row["urban_pattern"] or None,
                "founded": founded,
                "elevation": _semel(row["elevation"]),
                "lon": float(row["lon"]),
                "lat": float(row["lat"]),
                "semel": semel,
                "pop": series.get(semel, {}) if semel else {},
            })

    years = sorted({int(y) for loc in localities for y in loc["pop"]})
    jewish = [loc for loc in localities if loc["group"] == "jewish"]
    out = {
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "years": years,
        "min_year": years[0] if years else None,
        "max_year": years[-1] if years else None,
        "n_jewish": len(jewish),
        "n_druze": len(localities) - len(jewish),
        "localities": sorted(localities, key=lambda l: l["id"]),
    }
    (config.WEB_DATA / "golan.json").write_text(
        json.dumps(out, ensure_ascii=False), encoding="utf-8")
    with_series = sum(1 for loc in localities if loc["pop"])
    log(f"golan map data: {len(localities)} localities "
        f"({len(jewish)} Jewish, {out['n_druze']} Druze/Alawite), "
        f"{with_series} with population series, years "
        f"{out['min_year']}-{out['max_year']}")


if __name__ == "__main__":
    build()
