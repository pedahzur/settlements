# West Bank & East Jerusalem Settlements — Quantitative Panel

A settlement-level panel dataset for the quantitative study of Israeli settlement in the West Bank and East Jerusalem. Unit of analysis: **settlement × year**.

## Contents

| File | Description |
|------|-------------|
| `settlements_master_panel.xlsx` | Master workbook. Sheets: `README`, `master_panel_long` (8,580 rows, entity × year, 1969–2024), `settlement_summary` (growth metrics + trajectory typology), `entity_registry` (483 entities), `outposts` (315), `source_agreement` (PN↔B'Tselem reliability audit), `crosswalk`, `peacenow_settlements_wide`. |
| `settlements_empirical_brief.md` | Empirical findings: aggregate growth, regional and typological variation, distance-from-Green-Line gradient, the declining Jordan Valley tail, outpost waves. |
| `figures/` | Six publication-quality charts (PNG). |
| `data/` | Raw source files (see Sources). |
| `archive/` | Superseded interim file (`settlements_panel_1996-2017.xlsx`, B'Tselem-only). |

## Sources

- **Peace Now** (Settlement Watch), public "list of settlements and outposts" (`data/peacenow_settlements.csv`, `data/peacenow_outposts.csv`), updated 1 May 2026. Population 1969–May 2024 plus distance from Green Line, regional council, urban pattern, elevation, coordinates. West Bank settlements only (East Jerusalem excluded). Underlying population: Israel CBS / Jerusalem Institute.
- **B'Tselem** settlement population file, October 2019 revision (`data/btselem_2019_source.xlsx`). Population 1996–2017; includes East Jerusalem settlements and Hebron enclaves that Peace Now omits. Source: Israel CBS + Jerusalem Institute for Policy Research.

The two sources are complementary (Peace Now for long/current West Bank population and geography; B'Tselem for East Jerusalem and Hebron) and mutually validating: **89.7%** of 2,614 overlapping settlement-years match exactly, **95.3%** within 1%.

## Method notes

- `pop_peacenow` and `pop_btselem` are kept as separate columns; `pop_best` coalesces them (Peace Now preferred where available; B'Tselem for East Jerusalem / Hebron / pre-1996). `pop_change`, `pop_change_pct`, and `cagr_pct` are derived.
- Trajectory typology (evacuated / surviving / declining / successful) is an editable operationalization; continuous `cagr_pct` and `decline_from_peak_pct` columns support re-binning.
- **Not yet included:** built-up area (dunams) and construction starts, which exist only in Peace Now's binary GIS package (`Peace_Now_Layers.mpk`) and aggregate charts, not as per-settlement tables.

## Caveats

East Jerusalem: CBS does not report annexed East Jerusalem as a separate geographic area; the 11 East Jerusalem entities (B'Tselem only, 1996–2017) are not directly comparable to West Bank settlement counts.
