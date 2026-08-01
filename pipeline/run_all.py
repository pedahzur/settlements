"""End-to-end pipeline entrypoint: consolidate sources, then emit map data.

    python -m pipeline.run_all

Resilient by design: remote sources that are unreachable are skipped (their
tables come up empty and the snapshot simply omits those columns), so this
always produces a usable DB and map from whatever inputs are available. The
weekly GitHub Actions job runs exactly this on a runner with open egress, so
the voting / economic / built-up tables fill in there.
"""
from __future__ import annotations

from . import build_geojson, build_golan_map, consolidate, geocode_new_settlements
from .utils import log


def main() -> None:
    consolidate.run()
    build_geojson.build()
    geocode_new_settlements.build()   # geocode off-panel decisions + overlay
    build_golan_map.build()
    log("pipeline complete")


if __name__ == "__main__":
    main()
