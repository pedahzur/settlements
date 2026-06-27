"""Central configuration for the West Bank settlements consolidation pipeline.

Unit of analysis: the individual settlement (with outposts and East Jerusalem
settlements as separate typed entities). Every fact table joins back to one
`settlement_id` defined in the canonical dimension built by ``build_registry``.

Network note: several primary hosts (data.gov.il, HDX) block automated egress
from some sandboxes. Every fetcher therefore caches its raw download under
``db/raw/`` and falls back to the cached copy (or skips gracefully) when a host
is unreachable. The full pipeline always produces a consolidated DB from
whatever inputs are available locally; the network-dependent tables populate on
the GitHub Actions runner, which has open internet access.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"                  # raw committed source files (Peace Now, B'Tselem)
DB = ROOT / "db"                      # consolidated outputs (committed)
RAW = DB / "raw"                      # cached raw downloads from remote sources
WEB_DATA = ROOT / "web" / "data"      # geojson / json consumed by the map
MASTER_XLSX = ROOT / "settlements_master_panel.xlsx"

for _d in (DB, RAW, WEB_DATA):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Remote sources. All are official or canonical NGO endpoints; see SOURCES.md.
# ---------------------------------------------------------------------------

# data.gov.il CKAN portal (Israel national open data) — Hebrew column headers.
DATAGOV_BASE = "https://data.gov.il/api/3/action"

# Master locality registry: maps CBS locality code (semel yishuv) <-> Hebrew
# name. This is the crosswalk that lets us attach voting and economic data
# (keyed on semel yishuv) to our settlement dimension (keyed on Hebrew name).
DATAGOV_LOCALITIES = "citiesandsettelments"

# Knesset election results, per ballot box and per locality, for recent
# Knessets. Each row is a ballot box; West Bank settlements appear as ordinary
# localities identified by semel yishuv.
DATAGOV_VOTES = "votes-knesset"

# CBS socio-economic index of local authorities (cluster 1-10, rank, index
# value) mirrored on gov.il as an Excel ranking file. The canonical primary is
# the CBS media release; the gov.il mirror is the machine-readable entry point.
CBS_SOCIOECONOMIC_XLSX = (
    "https://www.cbs.gov.il/he/mediarelease/doclib/2024/230/24_24_230t1.xlsx"
)

# UN OCHA oPt settlement built-up-area polygons (HDX). Used to derive built-up
# area (dunams) per settlement for the expansion table.
HDX_SETTLEMENTS = (
    "https://data.humdata.org/api/3/action/package_show?id=state-of-palestine-settlements"
)

# Wikidata SPARQL endpoint — CC0 crosswalk for QIDs / coordinates.
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"

# Network behaviour.
HTTP_TIMEOUT = int(os.environ.get("PIPELINE_HTTP_TIMEOUT", "60"))
USER_AGENT = (
    "settlements-data-pipeline/1.0 (+https://github.com/pedahzur/settlements)"
)

# Right / pro-settlement bloc party slate letters (the Hebrew ballot "otiyot"),
# used to compute a comparable "right-religious bloc vote share" per settlement
# across Knesset elections. Lists are matched case-insensitively against the
# Hebrew slate-letter column; extend as new slates appear.
RIGHT_BLOC_SLATES = {
    "מחל",   # Likud
    "ט",     # Religious Zionism / Otzma
    "טב",    # HaBayit HaYehudi / Yamina lineage
    "שס",    # Shas
    "ג",     # United Torah Judaism
    "כן",    # New Right / Yamina (varies by cycle)
    "ב",     # Yamina (2021)
}
