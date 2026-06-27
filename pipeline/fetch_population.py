"""Population fact table (settlement x year).

Source of record is the existing master panel ``master_panel_long`` sheet
(Peace Now 1969-2024 + B'Tselem 1996-2017, both tracing to Israel CBS /
Jerusalem Institute). This module normalises it into a tidy long table keyed on
settlement_id. It is fully local — no network required.
"""
from __future__ import annotations

import pandas as pd

from . import config
from .utils import log


def build() -> pd.DataFrame:
    xl = pd.ExcelFile(config.MASTER_XLSX)
    panel = xl.parse("master_panel_long")
    pop = pd.DataFrame({
        "settlement_id": panel["entity_id"].astype(int),
        "year": panel["year"].astype(int),
        "pop_peacenow": panel["pop_peacenow"],
        "pop_btselem": panel["pop_btselem"],
        "pop_best": panel["pop_best"],
        "pop_source": panel["pop_source"],
    })
    pop = pop.dropna(subset=["pop_best"], how="all")
    log(f"population_long: {len(pop)} settlement-year rows")
    return pop


if __name__ == "__main__":
    build().to_csv(config.DB / "population_long.csv", index=False)
