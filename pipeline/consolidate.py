"""Consolidate every source into one settlement-level database.

Outputs (all under ``db/``):
  * settlements.sqlite          - dimension + all fact tables (relational)
  * settlement_dimension.csv    - one row per settlement
  * population_long.csv         - settlement x year population
  * voting_long.csv             - settlement x Knesset election
  * economic.csv                - settlement socio-economic standing
  * expansion.csv               - settlement built-up area (dunams)
  * settlements_latest.csv      - ONE WIDE ROW PER SETTLEMENT (analysis table)
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pandas as pd

from . import config
from .build_registry import build as build_dim
from .fetch_economic import build as build_economic
from .fetch_expansion import build as build_expansion
from .fetch_population import build as build_population
from .fetch_voting import build as build_voting
from .utils import log


def _map_to_settlement(df: pd.DataFrame, dim: pd.DataFrame) -> pd.DataFrame:
    """Attach settlement_id to a remote table via semel, then Hebrew name."""
    if df.empty:
        df["settlement_id"] = pd.Series(dtype="Int64")
        return df
    out = df.copy()
    out["settlement_id"] = pd.NA
    if "cbs_semel" in out.columns and dim["cbs_semel"].notna().any():
        semel_to_id = (dim.dropna(subset=["cbs_semel"])
                       .set_index("cbs_semel")["settlement_id"].to_dict())
        out["settlement_id"] = pd.to_numeric(out["cbs_semel"], errors="coerce").map(semel_to_id)
    key_to_id = dim.drop_duplicates("he_join_key").set_index("he_join_key")["settlement_id"].to_dict()
    miss = out["settlement_id"].isna()
    if "he_join_key" in out.columns:
        out.loc[miss, "settlement_id"] = out.loc[miss, "he_join_key"].map(key_to_id)
    return out


def _latest_snapshot(dim, population, voting, economic, expansion) -> pd.DataFrame:
    xl = pd.ExcelFile(config.MASTER_XLSX)
    summary = xl.parse("settlement_summary")[
        ["entity_id", "pop_2024", "peak_pop", "peak_year", "cagr_pct",
         "decline_from_peak_pct", "trajectory"]
    ].rename(columns={"entity_id": "settlement_id"})

    # Latest population per settlement from the long table.
    pop = population.dropna(subset=["pop_best"]).sort_values("year")
    latest_pop = (pop.groupby("settlement_id")
                  .agg(latest_pop=("pop_best", "last"),
                       latest_pop_year=("year", "last"),
                       first_pop_year=("year", "first")).reset_index())

    snap = dim.merge(latest_pop, on="settlement_id", how="left")
    snap = snap.merge(summary, on="settlement_id", how="left")

    # Most recent election per settlement.
    if not voting.empty and voting["settlement_id"].notna().any():
        v = voting.dropna(subset=["settlement_id"]).copy()
        v["settlement_id"] = v["settlement_id"].astype(int)
        v = v.sort_values("knesset")
        latest_v = (v.groupby("settlement_id")
                    .agg(latest_knesset=("knesset", "last"),
                         right_bloc_share=("right_bloc_share", "last"),
                         top_party=("top_party", "last"),
                         turnout=("turnout", "last") if "turnout" in v.columns
                         else ("knesset", "last")).reset_index())
        snap = snap.merge(latest_v, on="settlement_id", how="left")

    if not economic.empty and economic["settlement_id"].notna().any():
        e = economic.dropna(subset=["settlement_id"]).copy()
        e["settlement_id"] = e["settlement_id"].astype(int)
        snap = snap.merge(e[["settlement_id", "se_cluster", "se_rank", "se_index"]]
                          .drop_duplicates("settlement_id"),
                          on="settlement_id", how="left")

    if not expansion.empty:
        snap = snap.merge(expansion[["settlement_id", "built_up_dunams"]],
                          on="settlement_id", how="left")
    return snap


def run() -> dict[str, pd.DataFrame]:
    log("=== consolidation start ===")
    dim = build_dim()
    population = build_population()
    voting = _map_to_settlement(build_voting(), dim)
    economic = _map_to_settlement(build_economic(), dim)
    expansion = build_expansion(dim)
    snapshot = _latest_snapshot(dim, population, voting, economic, expansion)

    # Persist CSVs.
    dim.to_csv(config.DB / "settlement_dimension.csv", index=False)
    population.to_csv(config.DB / "population_long.csv", index=False)
    voting.to_csv(config.DB / "voting_long.csv", index=False)
    economic.to_csv(config.DB / "economic.csv", index=False)
    expansion.to_csv(config.DB / "expansion.csv", index=False)
    snapshot.to_csv(config.DB / "settlements_latest.csv", index=False)

    # Persist relational SQLite.
    con = sqlite3.connect(config.DB / "settlements.sqlite")
    dim.to_sql("settlements", con, if_exists="replace", index=False)
    population.to_sql("population", con, if_exists="replace", index=False)
    voting.to_sql("voting", con, if_exists="replace", index=False)
    economic.to_sql("economic", con, if_exists="replace", index=False)
    expansion.to_sql("expansion", con, if_exists="replace", index=False)
    snapshot.to_sql("settlements_latest", con, if_exists="replace", index=False)
    con.execute("CREATE INDEX IF NOT EXISTS ix_pop ON population(settlement_id, year)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_vote ON voting(settlement_id, knesset)")
    con.commit()
    con.close()

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    (config.DB / "LAST_UPDATED.txt").write_text(
        f"{stamp}\nsettlements={len(dim)} pop_rows={len(population)} "
        f"voting_rows={len(voting)} economic_rows={len(economic)} "
        f"expansion_rows={len(expansion)}\n")
    log(f"=== consolidation done ({stamp}) ===")
    return {"dim": dim, "population": population, "voting": voting,
            "economic": economic, "expansion": expansion, "snapshot": snapshot}


if __name__ == "__main__":
    run()
