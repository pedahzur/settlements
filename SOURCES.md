# Data Sources — West Bank, East Jerusalem & Golan Settlements

A curated inventory of reliable, citable data sources for the quantitative study
of Israeli settlement, organised by theme. Each entry notes coverage,
granularity, format/access, and reliability caveats. Verified July 2026.

**Legend** — *Primary/official*: government statistical or UN bodies.
*NGO/watchdog*: original field collection with explicit orientation.
*Derived*: secondary compilations and crosswalks.

Which of these the consolidation pipeline ingests is marked **[ingested]**;
sources we document but do not yet pull are marked **[reference]**.

---

## 1. Population over time

| Source | Type | Coverage | Per-settlement series? | East Jerusalem | Outposts | Format / access |
|---|---|---|---|---|---|---|
| **Israel CBS (Lamas)** | Primary | WB recognised localities, 1967– | **Yes** (annual, locality code) | No (folded into Jerusalem) | No | XLSX/CSV/PDF — [cbs.gov.il/EN/settlements](https://www.cbs.gov.il/EN/settlements), [Population in Localities](https://www.cbs.gov.il/en/subjects/Pages/Population-in-Localities.aspx), [2022 Census](https://census.cbs.gov.il/en) |
| **Peace Now — Settlement Watch** | NGO | WB + EJ + outposts | Per-settlement; limited back-series | **Yes** | **Yes (best)** | Web/PDF — [population](https://peacenow.org.il/en/settlements-watch/settlements-data/population), [list](https://peacenow.org.il/en/settlements-watch/israeli-settlements-at-the-west-bank-the-list) **[ingested]** (`data/peacenow_settlements.csv`, 1969–May 2024) |
| **B'Tselem** | NGO | Aggregate WB + EJ | No (snapshots) | Yes (CBS + Jerusalem Inst.) | No | Web/PDF — [statistics](https://www.btselem.org/settlements/statistics) **[ingested]** (`data/btselem_2019_source.xlsx`, 1996–2017) |
| **Jerusalem Institute for Policy Research** — *Statistical Yearbook of Jerusalem* | Primary-adjacent | Jerusalem incl. EJ neighbourhoods, 1982– | Neighbourhood-level annual | **Yes (the standard EJ source)** | n/a | PDF + online DB — [yearbook](https://jerusaleminstitute.org.il/en/yearbook/) |
| **Ministry of Interior — Population Registry** | Primary | Registered residents by address | Raw, not published as a dataset | Yes | Partial | Restricted / fee — feedstock for CBS |
| **West Bank Jewish Population Stats** (Y. Katz / B. Ruberg) | NGO (pro-settlement) | WB excl. EJ | **Yes** (per-community, earliest each year) | No | Some | Report — [westbankjewishpopulationstats.com](https://westbankjewishpopulationstats.com/) |
| **Jewish Virtual Library** | Derived | Per-community + aggregate 1970– | Aggregate annual back-series | No | No | Web tables |
| **Wikipedia — population statistics** | Derived | Per-settlement snapshots | Inconsistent | Inconsistent | Some | Web tables (cross-check only) |
| **UN OCHA oPt / FMEP / EU EEAS / UN SG reports** | Primary/Int'l | Aggregate WB + EJ | No | Yes | Locations | PDF/HDX |

*To build a full 1967–2025 per-settlement series including East Jerusalem:* CBS
locality tables (backbone) + Jerusalem Institute (EJ) + West Bank Jewish
Population Stats (latest year before CBS) + Peace Now (outposts/integration).

---

## 2. Physical expansion over time (built-up area, construction, land)

| Source | Type | What it covers | Granularity | Format / access |
|---|---|---|---|---|
| **Peace Now — Settlement Watch GIS** (`Peace_Now_Layers.mpk`) | NGO | Built-up polygons, jurisdiction, Green Line, Areas A/B; construction starts, tenders, state-land | Per-settlement polygons; per-year reports | ArcGIS `.mpk` + PDFs — [maps & GIS layers](https://peacenow.org.il/en/maps-and-gis-layers), [construction](https://peacenow.org.il/en/settlements-watch/settlements-data/construction) |
| **UN OCHA oPt (HDX)** | Primary | Settlement built-up outlines, Areas A/B/C, Barrier, restricted areas | Settlement polygons; WB-wide areas | **Zipped shapefile / GeoJSON** — [HDX org](https://data.humdata.org/organization/ocha-opt), [settlements](https://data.humdata.org/dataset/state-of-palestine-settlements) **[ingested → built-up dunams]** |
| **Kerem Navot** | NGO | Land takeover (esp. grazing/farm outposts), state-land, dunams controlled | Per-outpost/region polygons | Report PDFs — [keremnavot.org](https://www.keremnavot.org) |
| **Peace Now + Kerem Navot — 2023–2025 report** | NGO | 37th-government actions: outposts (185 new), farm-outpost land (~1.07M dunam), 40,064 housing units planned, 25,959 dunam state-land, 118 communities expelled, 223 km new roads; **102 government establishment decisions** | Aggregate (WB-wide) + a per-settlement decisions list | PDF — `docs/peace_now_kerem_navot_west_bank_2023-2025.pdf` **[ingested → `data/govt_establishment_decisions.csv`; 24 joined to map as "Gov't establishment decision" metric]** |
| **Wikidata (P625) + OpenStreetMap / Nominatim** | Primary/crowdsourced | Coordinates for the off-panel establishment-decision settlements (new settlements, re-established sites, newer outposts) | Point per resolvable name | SPARQL + Nominatim, bbox-validated to the West Bank **[ingested → `data/new_settlement_coords.csv`; geocoded overlay "◇ New settlements 2023–26" with per-point `coord_source`/`coord_confidence`]** |
| **B'Tselem** | NGO | Jurisdiction vs built-up, Area C/state land, "Land Grab" | Per-settlement; WB-wide | Interactive map + PDF — [settlements](https://www.btselem.org/settlements), [Conquer & Divide](https://conquer-and-divide.btselem.org/) |
| **ARIJ / POICA** | NGO (Palestinian) | Colony expansion, land confiscation, masterplans via satellite | Site/district | Web/PDF — [arij.org](https://www.arij.org/geo-informatics-department/), [poica.org](https://poica.org) |
| **Israel CBS — construction starts** | Primary | Dwellings begun/completed, "Judea & Samaria" district | **District-level** (not per-settlement) | Quarterly time series |
| **Civil Administration / COGAT (Blue Line Team)** | Primary | Jurisdiction boundaries, state-land declarations, allocations | Per-settlement / per-parcel | FOIA-gated; partly via gov.il/cogat |
| **Bimkom, Terrestrial Jerusalem, Yesh Din, FMEP** | NGO | Area-C planning; EJ/E-1; outpost legal status; weekly tracker | Mixed | Web/PDF |

> **Known gap:** a machine-readable *per-settlement built-up-area time series in
> dunams* does **not** exist as a public download. It must be reconstructed from
> Peace Now / OCHA polygon snapshots + historical imagery, or read from report
> tables. The pipeline captures the latest OCHA built-up snapshot only.

---

## 3. Voting patterns per settlement over time

| Source | Type | Coverage | Granularity | Format / access |
|---|---|---|---|---|
| **data.gov.il — `votes-knesset`** | Primary | Knesset elections, per ballot box + per locality, ~K19–K25 | **Per-ballot-box & per-locality** (settlements = ordinary localities by semel) | CSV/XLSX + CKAN API — [dataset](https://data.gov.il/dataset/votes-knesset) **[ingested → bloc share, turnout, leading party]** |
| **Central Elections Committee** (`votesNN.bechirot.gov.il`) | Primary | Official per-Knesset results | Down to ballot box | Web + downloadable `expb` files — [K25](https://votes25.bechirot.gov.il/) |
| **Ministry of Interior — Mabat Pnim** | Primary | Local/municipal & regional-council elections (2018, 2024…) | Per local authority / council | Portal (PDF/Excel) — [mabat-pnim.moin.gov.il](https://mabat-pnim.moin.gov.il/results/DocumentSearch/4/0) |
| **CBS** | Primary | Locality registry (semel, regional-council membership), turnout tables | Per locality / council | XLSX/PDF — the join key for vote data |
| **harelc/elections-vote-transfer** (GitHub) | Derived (clean) | Harmonised ballot-box results K16–K25, joined to CBS socio-economic | Per ballot box & locality | CSV + Python — [repo](https://github.com/harelc/elections-vote-transfer) |
| **INES (Tel Aviv Univ.), IDI, Washington Institute** | Academic/think-tank | Survey + settlement-bloc analyses | Respondent / bloc | Datasets & articles |

*Caveats:* "double-envelope" special votes are reported nationally (settlement
turnout slightly understated); ballot boxes are subdivided across cycles;
small localities may be suppressed; Hebrew encodings/headers vary.

The pipeline keys settlements to the CEC files via **CBS semel yishuv**, derived
from the data.gov.il [localities master](https://data.gov.il/dataset/citiesandsettelments).

---

## 4. Comparative economic & socio-economic data

| Source | Type | Indicators | Granularity | Format / access |
|---|---|---|---|---|
| **CBS — Socio-Economic Index of Local Authorities** | Primary | Composite index value, **rank**, **cluster (1–10)** | Per authority **and** per locality within regional councils (Table B) | XLSX/PDF — [subject page](https://www.cbs.gov.il/en/subjects/Pages/Socio-Economic-Index-of-Local-Authorities.aspx), [2021 release](https://www.cbs.gov.il/he/mediarelease/DocLib/2024/230/24_24_230b.pdf) **[ingested → cluster/rank]** |
| **CBS — Local Authorities in Israel** (annual) | Primary | Municipal finance, budgets, education (bagrut), demographics | Per authority | XLSX comparison tables — [subject](https://www.cbs.gov.il/en/subjects/Pages/Local-Authorities.aspx) |
| **CBS — Peripherality Index** | Primary | Centrality/accessibility cluster | Per locality/authority | [subject](https://www.cbs.gov.il/en/subjects/Pages/Peripherality-Index-of-Local-Authorities.aspx) |
| **CBS — fertility & religiosity** | Primary | TFR by locality; religiosity (mostly national/district) | Per locality (TFR) | CBS vital statistics |
| **Ministry of Interior / Finance** | Primary | Audited municipal finance; National Priority Area subsidies | Per authority | gov.il / data.gov.il (Hebrew) |
| **Adva, Macro, Molad, Shir Hever** | Think-tank | Cost-of-settlements & subsidy estimates | Aggregate/programmatic | Free PDFs — [adva.org](https://adva.org), [macro.org.il](https://www.macro.org.il/en/publications/), molad.org |
| **World Bank / UNCTAD / PCBS** | Int'l/Palestinian | Broader oPt economy (context) | Aggregate | Reports |

*Key asymmetry:* the deepest economic indicators (income, employment, municipal
finance) are published **per local authority**, so settlements inside regional
councils get only a per-locality socio-economic cluster + population, not full
finance. Religiosity-per-settlement is generally *inferred*, not measured.
**Join key:** CBS locality code (semel yishuv).

---

## 5. Spatial / GIS, legal status & cross-cutting

| Source | Type | Coverage | Format / licence |
|---|---|---|---|
| **UN OCHA oPt (HDX)** | Primary | Settlements, Barrier, Area A/B/C, checkpoints, firing zones, admin boundaries | Shapefile/GeoJSON/CSV — mostly **CC BY** — [org](https://data.humdata.org/organization/ocha-opt) |
| **Geofabrik / OpenStreetMap** "Israel and Palestine" | Crowdsourced | Roads, buildings, places, land use, water | PBF/Shapefile/GeoPackage — **ODbL 1.0** — [download](https://download.geofabrik.de/asia/israel-and-palestine.html) **[ingested → Golan residential footprints]** |
| **Peace Now interactive map + GIS layers** | NGO | Settlements, outposts, Green Line, Areas A/B | ArcGIS map package containing shapefiles — [download page](https://peacenow.org.il/en/maps-and-gis-layers) **[ingested → West Bank/outpost and East Jerusalem footprints]** |
| **B'Tselem maps** | NGO | Settlements, state land, firing zones, Barrier | Web map + PDF |
| **Israel GovMap / Survey of Israel** | Primary | Cadastral blocks (Gush) & parcels (Helka), zoning | Viewer + WMS/feature services — [govmap.gov.il](https://www.govmap.gov.il/?lang=en) |
| **GeoMOLG** (Palestinian Ministry of Local Government) | Primary (PA) | Parcels, master plans, land use | ArcGIS viewer / REST — [geomolg.ps](https://geomolg.ps) |
| **PCBS** | Primary (PA) | Settlement/settler statistics, Area C land control | HTML/PDF/Excel — [pcbs.gov.ps](https://www.pcbs.gov.ps) |
| **Wikidata** | Derived | QIDs, coordinates, population, founding | **CC0** SPARQL — [query.wikidata.org](https://query.wikidata.org/) — ideal crosswalk spine |
| **Shaul Arieli — maps & atlas** | Expert | Settlements, Green Line, partition scenarios | PDF maps — [shaularieli.com](https://www.shaularieli.com/en/maps/settlements/) |
| **Harvard Dataverse / ICPSR** | Academic | Study-specific replication datasets | CSV/Stata, per-deposit DOIs |
| **Who Profits, Visualizing Palestine, Forensic Architecture** | Advocacy/derived | Corporate involvement; infographics; spatial investigations | Web/PDF/interactive (not GIS downloads) |

*Sourcing note:* "Whose Land" does not resolve to a settlement-data source;
the nearest real source is **Who Profits** (economic, not spatial).

---

## How the pipeline uses these

The consolidation pipeline (`pipeline/`) keys every record to one
`settlement_id` and attaches:

- **population** ← Peace Now + B'Tselem (local, master panel)
- **voting** ← data.gov.il `votes-knesset`, joined via CBS semel yishuv
- **economic** ← CBS Socio-Economic Index, joined via Hebrew locality name
- **expansion** ← OCHA settlement polygons → built-up dunams (point-in-polygon)
- **map footprints** ← Peace Now settlement/outpost shapefiles (West Bank and
  East Jerusalem) + OpenStreetMap `landuse=residential` polygons distributed by
  Geofabrik (Golan)

The compact derived footprint files are committed under `web/data/`. Peace Now
features join primarily through its `DB_ID`/`pn_db_id` crosswalk and secondarily
through point-in-polygon matching. Golan polygons join when the canonical
locality point falls inside an OSM residential polygon. Unmatched entities are
shown as point-only diamonds; the build does not manufacture approximate
boundaries.

Sources that require open egress (data.gov.il, CBS, HDX) populate on the weekly
GitHub Actions run; the local build always produces population + geography. See
`README.md` for the schema and `pipeline/config.py` for exact endpoints.
