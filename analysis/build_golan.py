"""Build the standalone Golan population summary used by the analysis artifact."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIME_SERIES = ROOT / "data" / "cbs_golan_2003_2024.csv"
DEFAULT_REGISTRY = ROOT / "data" / "cbs_golan_registry_2024.csv"
DEFAULT_OUTPUT = ROOT / "analysis" / "golan_data.json"
YEARS = list(range(2003, 2025))

# CBS settlement-form code to readable label.
FORM_LABELS = {
    "180": "Town",
    "270": "Druze town",
    "280": "Druze town",
    "290": "Druze town",
    "310": "Moshav",
    "320": "Cooperative moshav",
    "330": "Kibbutz",
    "370": "Community",
    "510": "Outpost",
}

Registry = dict[int, dict[str, str]]
PopulationSeries = dict[int, dict[int, float]]


def parse_args() -> argparse.Namespace:
    """Parse repository-relative input and output paths."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--time-series",
        type=Path,
        default=DEFAULT_TIME_SERIES,
        help="CBS Golan population CSV (default: data/cbs_golan_2003_2024.csv)",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY,
        help="CBS Golan registry CSV (default: data/cbs_golan_registry_2024.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Destination JSON (default: analysis/golan_data.json)",
    )
    return parser.parse_args()


def _semel(value: str) -> int:
    """Normalize a CBS locality identifier stored as an integer or float."""
    return int(float(value))


def load_registry(path: Path) -> Registry:
    """Load the CBS locality registry keyed by semel yishuv."""
    registry: Registry = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                semel = _semel(row["semel"])
            except (KeyError, TypeError, ValueError):
                continue
            registry[semel] = {
                "name": (row.get("שם יישוב באנגלית") or "").strip(),
                "founded": (row.get("שנת ייסוד") or "").strip(),
                "form": (row.get("צורת יישוב שוטפת") or "").strip(),
                "religion": (row.get("דת יישוב") or "").strip(),
            }
    return registry


def load_series(path: Path) -> PopulationSeries:
    """Load annual locality populations keyed by semel and year."""
    series: PopulationSeries = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            semel = _semel(row["semel"])
            year = int(row["year"])
            population = float(row["pop"])
            series.setdefault(semel, {})[year] = population
    return series


def aggregate(
    semels: Iterable[int],
    series: PopulationSeries,
) -> list[int]:
    """Sum available locality populations for every analysis year."""
    identifiers = list(semels)
    return [
        round(sum(series.get(semel, {}).get(year, 0.0) for semel in identifiers))
        for year in YEARS
    ]


def _locality_summary(
    semel: int,
    registry: Registry,
    series: PopulationSeries,
) -> dict[str, Any]:
    values = series[semel]
    years = sorted(values)
    first_year, last_year = years[0], years[-1]
    first_population, last_population = values[first_year], values[last_year]
    peak = max(values.values())
    elapsed = last_year - first_year
    cagr = (
        ((last_population / first_population) ** (1 / elapsed) - 1) * 100
        if first_population > 0 and elapsed > 0
        else 0.0
    )
    decline_from_peak = (last_population / peak - 1) * 100 if peak > 0 else 0.0
    entry = registry.get(semel, {})
    form_code = entry.get("form", "").removesuffix(".0")
    return {
        "semel": semel,
        "name": entry.get("name") or str(semel),
        "founded": entry.get("founded", ""),
        "form": FORM_LABELS.get(form_code, entry.get("form", "")),
        "pop24": round(last_population),
        "pop03": round(values.get(2003, first_population)),
        "first_year": first_year,
        "cagr": round(cagr, 2),
        "peak": round(peak),
        "decline_from_peak": round(decline_from_peak, 1),
        "multiplier": (
            round(last_population / first_population, 2)
            if first_population > 0
            else None
        ),
    }


def build_output(registry: Registry, series: PopulationSeries) -> dict[str, Any]:
    """Calculate aggregate series and locality-level summaries."""
    non_jewish = {
        semel for semel, entry in registry.items() if entry.get("religion") == "2.0"
    }
    jewish_semels = [semel for semel in series if semel not in non_jewish]
    non_jewish_semels = [semel for semel in series if semel in non_jewish]

    jewish = aggregate(jewish_semels, series)
    druze = aggregate(non_jewish_semels, series)
    localities = sorted(
        (_locality_summary(semel, registry, series) for semel in jewish_semels),
        key=lambda item: -item["pop24"],
    )
    druze_towns = sorted(
        (
            {
                "name": registry.get(semel, {}).get("name") or str(semel),
                "pop24": round(series[semel][max(series[semel])]),
                "pop03": round(
                    series[semel].get(2003, series[semel][min(series[semel])])
                ),
            }
            for semel in non_jewish_semels
        ),
        key=lambda item: -item["pop24"],
    )

    return {
        "years": YEARS,
        "jewish": jewish,
        "druze": druze,
        "jewish_2003": jewish[0],
        "jewish_2024": jewish[-1],
        "druze_2003": druze[0],
        "druze_2024": druze[-1],
        "n_jewish": len(jewish_semels),
        "n_druze": len(non_jewish_semels),
        "locs": localities,
        "druze_towns": druze_towns,
    }


def main() -> None:
    """Build and write the Golan analysis summary."""
    args = parse_args()
    output = build_output(load_registry(args.registry), load_series(args.time_series))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {args.output} "
        f"({output['n_jewish']} Jewish localities, "
        f"{output['n_druze']} Druze/Alawite localities)"
    )


if __name__ == "__main__":
    main()
