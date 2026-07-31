"""Government settlement-establishment decisions (2023-2026).

Source: the joint Peace Now + Kerem Navot report on the 37th government's actions
in the West Bank (Dec 2022 - end 2025), table "List of settlements the government
decided to establish" (`docs/peace_now_kerem_navot_west_bank_2023-2025.pdf`,
extracted to `data/govt_establishment_decisions.csv`).

Each of the 102 government decisions is one of three types:
  * outpost_legalization        - retroactively legalising an existing outpost
  * neighborhood_to_settlement  - a "neighbourhood" spun off as an independent settlement
  * new_settlement              - an entirely new settlement (incl. re-established
                                  disengagement sites like Homesh, Sa-Nur, Ganim)

We attach the decision to our settlement dimension by Hebrew name. Only entities
already in the panel (chiefly existing outposts being legalised, and
neighbourhoods) carry coordinates; the brand-new settlements are not yet mapped
(no published coordinate table) and are kept in the CSV for reference.
"""
from __future__ import annotations

import pandas as pd

from . import config
from .utils import he_key, log

CSV = config.DATA / "govt_establishment_decisions.csv"


def build(dim: pd.DataFrame) -> pd.DataFrame:
    empty = pd.DataFrame(columns=["settlement_id", "govt_decision_type",
                                  "govt_decision_date"])
    if not CSV.exists():
        log("govt decisions: CSV missing; skipping")
        return empty
    dec = pd.read_csv(CSV)
    key_to_id = (dim.dropna(subset=["name_he"]).drop_duplicates("name_he")
                 .assign(_k=lambda d: d["name_he"].map(he_key))
                 .set_index("_k")["settlement_id"].to_dict())
    dec["settlement_id"] = dec["name_he"].map(he_key).map(key_to_id)
    matched = dec.dropna(subset=["settlement_id"]).copy()
    matched["settlement_id"] = matched["settlement_id"].astype(int)
    # If an entity appears in several decisions, keep the most recent.
    matched = (matched.sort_values("decision_date")
               .drop_duplicates("settlement_id", keep="last"))
    out = matched[["settlement_id", "decision_type", "decision_date"]].rename(
        columns={"decision_type": "govt_decision_type",
                 "govt_decision_date": "govt_decision_date",
                 "decision_date": "govt_decision_date"})
    log(f"govt decisions: {len(dec)} total, {len(out)} matched to mapped entities")
    return out


if __name__ == "__main__":
    d = pd.read_csv(config.DB / "settlement_dimension.csv")
    print(build(d).head(20).to_string())
