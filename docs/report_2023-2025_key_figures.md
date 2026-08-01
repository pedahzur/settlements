# De-facto Annexation 2023–2025 — Key Figures

Source: **Peace Now & Kerem Navot**, joint report on the 37th Israeli
government's actions in the West Bank, from its formation (end of December 2022)
through the end of 2025 (published 2026). Full report:
[`peace_now_kerem_navot_west_bank_2023-2025.pdf`](peace_now_kerem_navot_west_bank_2023-2025.pdf).

These are the report's headline figures. They are recent, authoritative, and
complement the settlement-level panel — most are **aggregate** (West-Bank-wide),
not per-settlement, so they enrich the *narrative/discussion* rather than the map
directly. The one clearly per-settlement dataset (the 102 government
establishment decisions) is extracted to
[`../data/govt_establishment_decisions.csv`](../data/govt_establishment_decisions.csv)
and joined onto the map (see below).

## Outposts and land takeover

- **185 new outposts** established in the West Bank in 2023–2025, of which
  **~130 are farm / "hilltop" outposts** (מאחזי חווה וגבעות).
- Farm outposts are estimated to now control **> 1,070,000 dunam ≈ 18% of the
  West Bank**; **~300,000 dunam were added in 2025 alone**.
- Only **~40%** of the land under farm outposts is defined by the Civil
  Administration as "state land"; the rest is private Palestinian land, waqf,
  unregistered, or unmapped.
- **≥ 11,520 dunam** seized for agriculture (seasonal plowing, date/grape/olive
  planting) to entrench denial of Palestinian access.

## Dispossession

- **118 Palestinian herding communities / clusters expelled** in 2023–2025,
  chiefly through settler violence, denial of grazing/water access, and lack of
  protection; **+16 more in Q1 2026**, including **Ras Ein al-Auja** (the largest
  herding community in Area C, ~1,000 residents, expelled January 2026).
- **House demolitions in Area C** (OCHA data): from **~537/yr (2010–2022)** to
  **~966/yr** under this government — **an ~80% increase**.

## Construction and planning

- **40,064 housing units** advanced in settlement plans over three years —
  planning capacity for a future increase of **~160,000–200,000 settlers**.
- **27,941 units in 2025 alone** — more than double the previous annual record.
- Includes the **E1** area east of Jerusalem, whose build-out would sever
  Palestinian contiguity between Ramallah, East Jerusalem and Bethlehem.
- **June 2023:** removal of the Defense Minister's approval for each stage of
  settlement construction — planning pace handed to Minister Smotrich.

## New settlements

- **102 government decisions to establish settlements** across six cabinet
  decisions (Feb 2023 – March 2026): **50 new settlements, 15 neighbourhoods
  granted independent-settlement status, 37 outpost legalizations**.
- Renewed settlement in the **northern West Bank** — the 2005 "Disengagement"
  ban lifted; **Homesh, Sa-Nur, Ganim, Kadim** re-established, plus new
  settlements/outposts around Jenin and Nablus, and tourism/archaeology projects
  (Sebastia, the Mas'udiya railway station).

## Roads and access

- **≥ 223 km of new dirt roads** carved across the West Bank since the government
  formed (accelerating after 7 October 2023), plus dozens of km of upgrades —
  used to seat outposts, take over land, and block Palestinian access.
- **125 million NIS** allocated (January 2026 government decision) for "paving
  security routes."

## Land, legal and administrative

- **25,959 dunam declared "state land"** in 2023–2025 — **nearly half of all
  land declared state land since the start of the Oslo process**.
- **244 million NIS** allocated to open **land-settlement (הסדר מקרקעין)
  proceedings** in the West Bank — which the report warns could drive large-scale
  dispossession, as many Palestinians cannot prove ownership under Israeli terms.
- Structural change: transfer of broad civilian powers (planning, land
  registration, infrastructure, enforcement) from the Civil Administration and
  military chain of command to Minister Smotrich and the Settlement
  Administration in the Defense Ministry — described by Smotrich as changing the
  system's "DNA"; and the strengthening of the **Ministry of Settlement and
  National Missions** (Orit Strock) as a funding channel.

## How this feeds the repo

- **Discussion:** the aggregate figures above (referenced from `README.md` and
  the empirical brief) situate the panel's settlement-level trends inside the
  2023–2025 acceleration.
- **Map (panel entities):** the 102 establishment decisions are joined to the
  settlement dimension by Hebrew name. 24 match entities already in the panel
  (17 outpost legalizations of existing outposts, 7 neighbourhoods) and appear
  under the metric **"Gov't establishment decision (2023–26)"**, coloured by
  decision type with the decision date in the popup.
- **Map (geocoded overlay):** the remaining decisions — chiefly brand-new
  settlements not in the panel — are geocoded from **authoritative open sources**
  (`pipeline/geocode_new_settlements.py`): Wikidata coordinates (P625) first,
  then OSM/Nominatim, each candidate validated to fall inside a West Bank
  bounding box. Resolved points appear as a toggleable ring-marker overlay
  ("◇ New settlements 2023–26"), and every point carries its `coord_source`
  (`wikidata:<QID>` / `osm:<id>`) and `coord_confidence` (`exact`/`approximate`)
  in the popup. Coordinates are cached to `data/new_settlement_coords.csv`.
  Coverage is partial by design: well-known and re-established settlements
  (Homesh, Sa-Nur, Ganim, Kadim) and named outposts resolve; brand-new farm
  outposts absent from every gazetteer stay listed-but-unmapped rather than being
  placed at a guessed location.
